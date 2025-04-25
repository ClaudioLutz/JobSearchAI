import os
import json
import logging
import threading
import urllib.parse
import traceback
from pathlib import Path
from flask import (
    Blueprint, request, redirect, url_for, flash, send_file, jsonify,
    render_template, current_app
)
from werkzeug.utils import secure_filename

# Add project root to path
import sys
sys.path.append('.')

# Import necessary functions from other modules
# We now call the specific function from letter_generation_utils directly in the task
# from motivation_letter_generator import main as generate_motivation_letter_main # Keep old import name distinct if needed elsewhere
from word_template_generator import json_to_docx, create_word_document_from_json_file
# Import functions needed for manual text structuring and generation
from job_details_utils import structure_text_with_openai, has_sufficient_content, get_job_details
from letter_generation_utils import generate_motivation_letter # Import the correct generator function

motivation_letter_bp = Blueprint('motivation_letter', __name__, url_prefix='/motivation_letter')

logger = logging.getLogger("dashboard.motivation_letter") # Use a child logger

# Helper function to get job details - uses the function attached to current_app
def get_job_details_for_url(job_url):
    """Gets job details using the function attached to the app context."""
    if hasattr(current_app, 'get_job_details_for_url'):
        # Use the implementation attached during app creation in dashboard.py
        return current_app.get_job_details_for_url(job_url)
    else:
        # This case should ideally not happen if the app is set up correctly
        logger.error("get_job_details_for_url function not found on current_app context!")
        return {} # Return empty dict or raise an error

# Helper function to sanitize filenames (consider moving to utils)
def sanitize_filename(name, length=30):
    sanitized = ''.join(c if c.isalnum() or c in [' ', '_', '-'] else '_' for c in name)
    sanitized = sanitized.replace(' ', '_')
    return sanitized[:length]

@motivation_letter_bp.route('/generate', methods=['POST'])
def generate_motivation_letter_route():
    """Generate a motivation letter for a single job"""
    try:
        # Get data from the form
        cv_filename = request.form.get('cv_filename')
        job_url = request.form.get('job_url')
        report_file = request.form.get('report_file') # To redirect back to the correct results page
        manual_job_text = request.form.get('manual_job_text') # Get manual text if provided

        log_msg = f"Generating motivation letter for CV: {cv_filename}, job URL: {job_url}"
        if manual_job_text:
            log_msg += " (using manual text input)"
        logger.info(log_msg)

        if not cv_filename or not job_url:
            logger.error(f"Missing CV filename or job URL: cv_filename={cv_filename}, job_url={job_url}")
            flash('Missing CV filename or job URL')
            if report_file:
                return redirect(url_for('job_matching.view_results', report_file=report_file))
            else:
                return redirect(url_for('index'))

        # Check if the CV summary file exists (relative to app root)
        summary_path = Path(current_app.root_path) / 'process_cv/cv-data/processed' / f"{cv_filename}_summary.txt"
        if not summary_path.exists():
            logger.error(f"CV summary file not found: {summary_path}")
            flash(f'CV summary file not found: {summary_path.name}')
            return redirect(url_for('job_matching.view_results', report_file=report_file))

        # --- Check if letter already exists --- ONLY if not using manual text input ---
        if not manual_job_text:
            job_details_check = get_job_details_for_url(job_url) # Use helper that accesses current_app
            existing_letter_found = False
            existing_html_path = None
            existing_json_path = None
            existing_docx_path = None

            if job_details_check and 'Job Title' in job_details_check:
                job_title = job_details_check['Job Title']
                sanitized_job_title = sanitize_filename(job_title)
                letters_dir = Path(current_app.root_path) / 'motivation_letters'
                html_path = letters_dir / f"motivation_letter_{sanitized_job_title}.html"
                json_path = letters_dir / f"motivation_letter_{sanitized_job_title}.json"
                docx_path = letters_dir / f"motivation_letter_{sanitized_job_title}.docx"

                if html_path.is_file() and json_path.is_file():
                    logger.info(f"Motivation letter already exists for job title: {job_title} (Automatic check)")
                    existing_letter_found = True
                    existing_html_path = str(html_path.relative_to(current_app.root_path))
                    existing_json_path = str(json_path.relative_to(current_app.root_path))
                    if docx_path.is_file():
                        existing_docx_path = str(docx_path.relative_to(current_app.root_path))

            if existing_letter_found:
                flash(f'Existing motivation letter found for job title: {job_title}')
                return redirect(url_for('.view_motivation_letter',
                                        operation_id='existing',
                                        html_path=existing_html_path,
                                        json_path=existing_json_path,
                                        docx_path=existing_docx_path,
                                        report_file=report_file))
        # --- End Check if letter already exists --- (Skipped if manual_job_text is present)

        # --- Generate new letter ---
        start_operation = current_app.extensions['start_operation']
        update_operation_progress = current_app.extensions['update_operation_progress']
        complete_operation = current_app.extensions['complete_operation']
        operation_status = current_app.extensions['operation_status']
        app_instance = current_app._get_current_object() # Get app instance for context

        operation_id = start_operation('motivation_letter_generation')

        # Define background task function (takes app context and manual_job_text)
        def generate_motivation_letter_task(app, op_id, cv_name, job_url_task, report_file_task, manual_job_text_task):
            with app.app_context(): # Establish app context for the thread
                job_details = None
                cv_summary_text = None # Initialize variable for CV summary content
                try:
                    # --- Load CV Summary ---
                    # cv_name is the base filename passed to the task
                    summary_path_task = Path(app.root_path) / 'process_cv/cv-data/processed' / f"{cv_name}_summary.txt"
                    if not summary_path_task.is_file():
                         logger.error(f"CV summary file not found inside task: {summary_path_task}")
                         complete_operation(op_id, 'failed', f'CV summary file not found: {cv_name}_summary.txt')
                         return
                    try:
                        with open(summary_path_task, 'r', encoding='utf-8') as f_cv:
                            cv_summary_text = f_cv.read()
                        if not cv_summary_text:
                             raise ValueError("CV summary file is empty.")
                        logger.info(f"Successfully loaded CV summary for {cv_name}")
                    except Exception as cv_load_err:
                         logger.error(f"Error reading CV summary file {summary_path_task}: {cv_load_err}", exc_info=True)
                         complete_operation(op_id, 'failed', f'Error reading CV summary: {cv_load_err}')
                         return

                    # --- Step 1: Get or Structure Job Details ---
                    if manual_job_text_task:
                        update_operation_progress(op_id, 10, 'processing', 'Structuring manual text...')
                        logger.info(f"Structuring manually provided text for job URL: {job_url_task}")
                        # Call the structuring function from job_details_utils
                        job_details = structure_text_with_openai(manual_job_text_task, job_url_task, source_type="Manual Input")

                        if not job_details:
                            logger.error("Failed to structure manually provided text.")
                            complete_operation(op_id, 'failed', 'Failed to structure manually provided text.')
                            return
                        if not has_sufficient_content(job_details):
                             logger.warning("Manually provided text structured, but content might be insufficient.")
                             # Proceed anyway, but log warning
                             update_operation_progress(op_id, 20, 'processing', 'Manual text structured (warning: content may be insufficient). Generating letter...')
                        else:
                             update_operation_progress(op_id, 20, 'processing', 'Manual text structured successfully. Generating letter...')

                    else:
                        update_operation_progress(op_id, 10, 'processing', 'Fetching/Scraping job details...')
                        logger.info(f"Attempting automatic job detail fetching for URL: {job_url_task}")
                        # Use the existing automatic fetching logic
                        job_details = get_job_details(job_url_task) # Assumes get_job_details is imported correctly

                        if not job_details or not has_sufficient_content(job_details):
                             logger.error(f"Failed to fetch sufficient job details automatically for {job_url_task}.")
                             complete_operation(op_id, 'failed', 'Failed to fetch sufficient job details automatically.')
                             return
                        update_operation_progress(op_id, 20, 'processing', 'Job details fetched successfully. Generating letter...')

                    # --- Step 2: Generate Letter using job_details and cv_summary_text ---
                    logger.info(f"Calling letter_generation_utils.generate_motivation_letter for CV '{cv_name}'")
                    # Call the function from letter_generation_utils, passing the loaded CV summary text
                    result = generate_motivation_letter(cv_summary_text, job_details) # Pass the actual summary text

                    if not result:
                        logger.error("Failed to generate motivation letter (letter_generation_utils.generate_motivation_letter returned None)")
                        complete_operation(op_id, 'failed', 'Failed to generate motivation letter')
                        return

                    update_operation_progress(op_id, 70, 'processing', 'Formatting motivation letter...')
                    logger.info(f"Successfully generated motivation letter content")

                    has_json = 'motivation_letter_json' in result and 'json_file_path' in result
                    docx_file_path_rel = None

                    if has_json:
                        json_file_path_abs_str = result['json_file_path']
                        logger.info(f"Generated JSON motivation letter: {json_file_path_abs_str}")
                        update_operation_progress(op_id, 80, 'processing', 'Creating Word document...')
                        try:
                            # Ensure paths are absolute for docx generation
                            abs_json_path = Path(json_file_path_abs_str)
                            if not abs_json_path.is_absolute():
                                abs_json_path = Path(app.root_path) / json_file_path_abs_str

                            abs_docx_path = abs_json_path.with_suffix('.docx')
                            docx_path_abs = json_to_docx(result['motivation_letter_json'], output_path=str(abs_docx_path))

                            if docx_path_abs:
                                 docx_file_path_rel = str(Path(docx_path_abs).relative_to(app.root_path))
                                 logger.info(f"Generated Word document: {docx_path_abs}")
                            else:
                                 logger.warning(f"json_to_docx returned None for {abs_json_path}")
                        except Exception as docx_e:
                             logger.error(f"Error generating DOCX from JSON {abs_json_path}: {docx_e}", exc_info=True)
                    else:
                        logger.info(f"Generated HTML motivation letter: {result.get('file_path', 'N/A')}")

                    update_operation_progress(op_id, 95, 'processing', 'Finalizing...')

                    # Determine relative paths for storing in result
                    html_file_path_abs_str = result.get('html_file_path') if has_json else result.get('file_path')
                    html_file_path_rel = None
                    if html_file_path_abs_str:
                         abs_html_path = Path(html_file_path_abs_str)
                         if not abs_html_path.is_absolute():
                              abs_html_path = Path(app.root_path) / html_file_path_abs_str
                         html_file_path_rel = str(abs_html_path.relative_to(app.root_path))


                    complete_operation(op_id, 'completed', 'Motivation letter generated successfully')

                    # Store relative paths and necessary info in the operation status
                    # Make sure job_details used here is the one obtained above
                    operation_status[op_id]['result'] = {
                        'has_json': has_json,
                        'motivation_letter_content': result.get('motivation_letter_html'), # Should always come from result dict now
                        'html_file_path': html_file_path_rel,
                        'json_file_path': result.get('json_file_path'), # Pass json path too
                        'docx_file_path': docx_file_path_rel,
                        'job_details': job_details, # Store the details used (structured or scraped)
                        'report_file': report_file_task
                    }
                except Exception as e:
                    logger.error(f'Error in motivation letter generation task: {str(e)}', exc_info=True)
                    complete_operation(op_id, 'failed', f'Error generating motivation letter: {str(e)}')

        # Start the background thread, passing the app instance and necessary args (including manual_job_text)
        thread_args = (app_instance, operation_id, cv_filename, job_url, report_file, manual_job_text)
        thread = threading.Thread(target=generate_motivation_letter_task, args=thread_args)
        thread.daemon = True
        thread.start()

        # Return JSON response with operation ID instead of flashing and redirecting
        return jsonify({'success': True, 'operation_id': operation_id})

    except Exception as e:
        # Return JSON error response
        logger.error(f'Error generating motivation letter route: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': f'Error starting generation: {str(e)}'}), 500


@motivation_letter_bp.route('/generate_multiple', methods=['POST'])
def generate_multiple_letters():
    """Generate motivation letters for multiple selected jobs"""
    data = request.get_json()
    if not data:
        logger.error("Invalid request format for /generate_multiple_letters")
        return jsonify({'error': 'Invalid request format'}), 400

    job_urls = data.get('job_urls')
    cv_base_name = data.get('cv_filename')

    if not job_urls or not isinstance(job_urls, list) or not cv_base_name:
        logger.error(f"Missing job_urls or cv_filename in request: {data}")
        return jsonify({'error': 'Missing job_urls or cv_filename'}), 400

    logger.info(f"Received request to generate {len(job_urls)} letters for CV: {cv_base_name}")

    # Check if the corresponding CV summary exists
    summary_path = Path(current_app.root_path) / 'process_cv/cv-data/processed' / f"{cv_base_name}_summary.txt"
    if not summary_path.exists():
        logger.error(f"Required CV summary file not found: {summary_path}")
        return jsonify({'error': f'Required CV summary file not found for {cv_base_name}'}), 400

    # --- Use threading with app context ---
    results = {'success_count': 0, 'errors': []}
    threads = []
    lock = threading.Lock()
    app_instance = current_app._get_current_object() # Get app instance

    def generate_single_letter_task(app, job_url): # Pass app instance
        nonlocal results
        # Create an app context for this thread
        with app.app_context():
            if not job_url or job_url == 'N/A' or not job_url.startswith('http'):
                logger.warning(f"Skipping invalid job URL: {job_url}")
                with lock:
                    results['errors'].append(job_url)
                return

            try:
                logger.info(f"Generating letter for CV '{cv_base_name}' and URL '{job_url}'")
                # job_details = get_job_details_for_url(job_url) # No longer needed here

                # Call the main generation function - remove existing_job_details to force live scrape
                logger.info(f"Calling generate_motivation_letter for CV '{cv_base_name}' and URL '{job_url}' (forcing live scrape)")
                result = generate_motivation_letter(cv_base_name, job_url) # Removed existing_job_details

                if result:
                    logger.info(f"Generator returned result for URL: {job_url}")
                    with lock:
                        results['success_count'] += 1
                    # Generate DOCX if JSON was produced
                    if 'motivation_letter_json' in result and 'json_file_path' in result:
                         try:
                             # Ensure paths are absolute for docx generation
                             abs_json_path = Path(result['json_file_path'])
                             if not abs_json_path.is_absolute():
                                 abs_json_path = Path(app.root_path) / result['json_file_path']

                             abs_docx_path = abs_json_path.with_suffix('.docx')
                             # TODO: Update json_to_docx in word_template_generator.py to accept and use
                             # the 'contact_person' field from result['motivation_letter_json']
                             # Example: docx_path = json_to_docx(result['motivation_letter_json'], output_path=str(abs_docx_path), contact_person=result['motivation_letter_json'].get('contact_person'))
                             docx_path = json_to_docx(result['motivation_letter_json'], output_path=str(abs_docx_path))
                             if docx_path:
                                 logger.info(f"Generated Word document: {docx_path} for URL: {job_url}")
                             else:
                                 logger.warning(f"Failed to generate Word document (json_to_docx returned None) for URL: {job_url}")
                         except Exception as docx_e:
                             logger.error(f"Exception generating Word document for URL {job_url}: {str(docx_e)}")
                else:
                    logger.error(f"Failed to generate letter (generate_motivation_letter returned None) for URL: {job_url}")
                    with lock:
                        results['errors'].append(job_url)
            except Exception as e:
                logger.error(f"Exception generating letter for URL {job_url}: {str(e)}", exc_info=True)
                with lock:
                    results['errors'].append(job_url)

    # Create and start threads, passing the app instance
    for url in job_urls:
        thread = threading.Thread(target=generate_single_letter_task, args=(app_instance, url,))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    logger.info(f"Multiple letter generation complete. Success: {results['success_count']}, Failures: {len(results['errors'])}")
    return jsonify(results)


@motivation_letter_bp.route('/generate_multiple_emails', methods=['POST'])
def generate_multiple_emails():
    """Generate email texts for multiple selected jobs and update their JSON files."""
    data = request.get_json()
    if not data:
        logger.error("Invalid request format for /generate_multiple_emails")
        return jsonify({'error': 'Invalid request format'}), 400

    job_urls = data.get('job_urls')
    cv_base_name = data.get('cv_filename') # Base name like 'Lebenslauf'

    if not job_urls or not isinstance(job_urls, list) or not cv_base_name:
        logger.error(f"Missing job_urls or cv_filename in request: {data}")
        return jsonify({'error': 'Missing job_urls or cv_filename'}), 400

    logger.info(f"Received request to generate {len(job_urls)} email texts for CV: {cv_base_name}")

    # --- Load CV Summary ---
    cv_summary = None
    try:
        summary_path = Path(current_app.root_path) / 'process_cv/cv-data/processed' / f"{cv_base_name}_summary.txt"
        if not summary_path.exists():
            logger.error(f"Required CV summary file not found: {summary_path}")
            return jsonify({'error': f'Required CV summary file not found for {cv_base_name}'}), 400
        with open(summary_path, 'r', encoding='utf-8') as f:
            cv_summary = f.read()
    except Exception as e:
        logger.error(f"Error loading CV summary {summary_path}: {e}", exc_info=True)
        return jsonify({'error': f'Error loading CV summary: {e}'}), 500

    if not cv_summary:
         return jsonify({'error': 'CV summary could not be loaded.'}), 500

    # --- Use threading with app context for generation and file updates ---
    results = {'success_count': 0, 'errors': [], 'not_found': []}
    threads = []
    lock = threading.Lock()
    app_instance = current_app._get_current_object() # Get app instance

    # Import the new function using absolute import from project root
    from letter_generation_utils import generate_email_text_only

    def generate_and_update_task(app, job_url): # Pass app instance
        nonlocal results
        with app.app_context(): # Establish app context for this thread
            if not job_url or job_url == 'N/A' or not job_url.startswith('http'):
                logger.warning(f"Skipping invalid job URL for email generation: {job_url}")
                with lock: results['errors'].append({'url': job_url, 'reason': 'Invalid URL'})
                return

            try:
                # 1. Get Job Details (needed for title and context)
                # Use the app's shared function
                job_details = get_job_details_for_url(job_url)
                if not job_details or not job_details.get('Job Title'):
                    logger.warning(f"Could not get sufficient job details for URL: {job_url}")
                    with lock: results['errors'].append({'url': job_url, 'reason': 'Failed to get job details'})
                    return

                job_title = job_details['Job Title']
                sanitized_job_title = sanitize_filename(job_title) # Use helper
                letters_dir = Path(app.root_path) / 'motivation_letters'
                json_file_path = letters_dir / f"motivation_letter_{sanitized_job_title}.json"

                # 2. Generate Email Text
                logger.info(f"Generating email text for CV '{cv_base_name}' and Job '{job_title}' (URL: {job_url})")
                email_text = generate_email_text_only(cv_summary, job_details)

                if not email_text:
                    logger.error(f"Failed to generate email text (generate_email_text_only returned None) for Job: {job_title}")
                    with lock: results['errors'].append({'url': job_url, 'reason': 'Email text generation failed'})
                    return

                # 3. Load existing JSON or create new dict
                letter_data = {}
                if json_file_path.is_file():
                    try:
                        with open(json_file_path, 'r', encoding='utf-8') as f:
                            letter_data = json.load(f)
                        logger.info(f"Loaded existing JSON: {json_file_path}")
                    except Exception as load_e:
                        logger.error(f"Error loading existing JSON {json_file_path}: {load_e}. Will overwrite.")
                        letter_data = {} # Reset if loading failed
                else:
                    logger.info(f"JSON file not found ({json_file_path}), will create new.")
                    # Optionally populate with minimal data if needed, or just add email_text
                    letter_data['job_title_source'] = job_title # Add source title for reference

                # 4. Update email_text field
                letter_data['email_text'] = email_text

                # 5. Save JSON back
                try:
                    letters_dir.mkdir(parents=True, exist_ok=True) # Ensure directory exists
                    with open(json_file_path, 'w', encoding='utf-8') as f:
                        json.dump(letter_data, f, ensure_ascii=False, indent=2)
                    logger.info(f"Successfully updated/created JSON with email text: {json_file_path}")
                    with lock:
                        results['success_count'] += 1
                except Exception as save_e:
                    logger.error(f"Error saving updated JSON {json_file_path}: {save_e}", exc_info=True)
                    with lock: results['errors'].append({'url': job_url, 'reason': f'Failed to save JSON: {save_e}'})

            except Exception as e:
                logger.error(f"Exception generating/updating email text for URL {job_url}: {str(e)}", exc_info=True)
                with lock:
                    results['errors'].append({'url': job_url, 'reason': f'Unexpected error: {e}'})

    # Create and start threads
    for url in job_urls:
        thread = threading.Thread(target=generate_and_update_task, args=(app_instance, url,))
        threads.append(thread)
        thread.start()

    # Wait for all threads
    for thread in threads:
        thread.join()

    logger.info(f"Multiple email text generation/update complete. Success: {results['success_count']}, Failures: {len(results['errors'])}")
    return jsonify(results)


@motivation_letter_bp.route('/view/<operation_id>')
def view_motivation_letter(operation_id):
    """View a generated motivation letter (newly generated or existing)"""
    try:
        # --- Handle viewing existing letters passed via query params ---
        if operation_id == 'existing':
            html_path_rel = request.args.get('html_path')
            docx_path_rel = request.args.get('docx_path')
            report_file = request.args.get('report_file')

            if not html_path_rel:
                flash('Motivation letter HTML path missing')
                return redirect(url_for('index'))

            html_full_path = Path(current_app.root_path) / html_path_rel
            if not html_full_path.is_file():
                flash(f'Motivation letter file not found: {html_path_rel}')
                return redirect(url_for('index'))

            with open(html_full_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            job_title_guess = html_full_path.stem.replace('motivation_letter_', '').replace('_', ' ')
            job_details = {'Job Title': job_title_guess, 'Application URL': '#'}

            return render_template('motivation_letter.html',
                                  motivation_letter=html_content,
                                  file_path=html_path_rel,
                                  has_docx=bool(docx_path_rel),
                                  docx_file_path=docx_path_rel,
                                  job_details=job_details,
                                  report_file=report_file)

        # --- Handle viewing newly generated letters via operation ID ---
        operation_status = current_app.extensions.get('operation_status', {})
        if operation_id not in operation_status or 'result' not in operation_status[operation_id]:
            flash('Motivation letter generation result not found or not ready.')
            status_info = operation_status.get(operation_id, {})
            report_file_from_status = status_info.get('result', {}).get('report_file')
            if report_file_from_status:
                 return redirect(url_for('job_matching.view_results', report_file=report_file_from_status))
            else:
                 return redirect(url_for('index'))

        result = operation_status[operation_id]['result']

        return render_template('motivation_letter.html',
                              motivation_letter=result.get('motivation_letter_content', 'Error: Content not found.'),
                              file_path=result.get('html_file_path'),
                              has_docx=bool(result.get('docx_file_path')),
                              docx_file_path=result.get('docx_file_path'),
                              job_details=result.get('job_details', {}),
                              report_file=result.get('report_file'))

    except Exception as e:
        flash(f'Error viewing motivation letter: {str(e)}')
        logger.error(f'Error viewing motivation letter (op_id/path: {operation_id}): {str(e)}', exc_info=True)
        return redirect(url_for('index'))


@motivation_letter_bp.route('/download_html')
def download_motivation_letter_html():
    """Download a generated motivation letter (HTML version using relative path)"""
    file_path_rel = request.args.get('file_path')

    if not file_path_rel:
        flash('No file path provided for HTML download')
        return redirect(url_for('index'))

    try:
        full_path = Path(current_app.root_path) / file_path_rel
        if not full_path.is_file():
             flash(f'File not found: {file_path_rel}')
             logger.error(f"HTML file not found for download: {full_path}")
             return redirect(url_for('index'))

        return send_file(str(full_path), as_attachment=True)
    except Exception as e:
        flash(f'Error downloading motivation letter HTML: {str(e)}')
        logger.error(f'Error downloading HTML {file_path_rel}: {str(e)}', exc_info=True)
        return redirect(url_for('index'))


@motivation_letter_bp.route('/download_docx')
def download_motivation_letter_docx():
    """Download a generated motivation letter (Word document version using relative path)"""
    file_path_rel = request.args.get('file_path')

    if not file_path_rel:
        flash('No file path provided for DOCX download')
        return redirect(url_for('index'))

    try:
        full_path = Path(current_app.root_path) / file_path_rel
        if not full_path.is_file():
             flash(f'File not found: {file_path_rel}')
             logger.error(f"DOCX file not found for download: {full_path}")
             return redirect(url_for('index'))

        return send_file(str(full_path), as_attachment=True)
    except Exception as e:
        flash(f'Error downloading Word document: {str(e)}')
        logger.error(f'Error downloading DOCX {file_path_rel}: {str(e)}', exc_info=True)
        return redirect(url_for('index'))


@motivation_letter_bp.route('/download_docx_from_json')
def download_docx_from_json():
    """Generate (if needed) and download DOCX from JSON file path"""
    json_file_path_rel = request.args.get('json_file_path')

    if not json_file_path_rel:
        flash('No JSON file path provided')
        return redirect(url_for('index'))

    try:
        json_full_path = Path(current_app.root_path) / json_file_path_rel
        docx_full_path = json_full_path.with_suffix('.docx')

        if not json_full_path.is_file():
             flash(f'JSON file not found: {json_file_path_rel}')
             logger.error(f"JSON file not found for DOCX generation: {json_full_path}")
             return redirect(url_for('index'))

        if not docx_full_path.is_file():
            logger.info(f"Generating Word document from JSON file: {json_full_path}")
            generated_docx_path = create_word_document_from_json_file(str(json_full_path))

            if not generated_docx_path or not Path(generated_docx_path).is_file():
                flash('Failed to generate Word document from JSON')
                logger.error(f"create_word_document_from_json_file failed for {json_full_path}")
                return redirect(url_for('index'))
            docx_full_path = Path(generated_docx_path)

        return send_file(str(docx_full_path), as_attachment=True)
    except Exception as e:
        flash(f'Error downloading Word document from JSON: {str(e)}')
        logger.error(f'Error downloading DOCX from JSON {json_file_path_rel}: {str(e)}', exc_info=True)
        return redirect(url_for('index'))


@motivation_letter_bp.route('/view_scraped_data/<scraped_data_filename>')
def view_scraped_data(scraped_data_filename):
    """Display the contents of a specific scraped job data JSON file."""
    try:
        secure_name = secure_filename(scraped_data_filename)
        file_path = Path(current_app.root_path) / 'motivation_letters' / secure_name

        if not file_path.is_file():
            flash(f'Scraped job data file not found: {secure_name}')
            logger.error(f"Scraped job data file not found: {file_path}")
            return redirect(url_for('index'))

        with open(file_path, 'r', encoding='utf-8') as f:
            job_details = json.load(f)

        return render_template('scraped_data_view.html', job_details=job_details, filename=secure_name)

    except FileNotFoundError:
        flash(f'Scraped job data file not found: {scraped_data_filename}')
        logger.error(f"FileNotFoundError for scraped data file: {scraped_data_filename}")
        return redirect(url_for('index'))
    except json.JSONDecodeError:
        flash(f'Error decoding JSON from file: {scraped_data_filename}')
        logger.error(f"JSONDecodeError for scraped data file: {scraped_data_filename}")
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'An error occurred while viewing scraped job data: {str(e)}')
        logger.error(f'Error in view_scraped_data for {scraped_data_filename}: {str(e)}', exc_info=True)
        return redirect(url_for('index'))


@motivation_letter_bp.route('/view_email_text/existing')
def view_email_text():
    """View the generated email text from a JSON file."""
    json_path_rel = request.args.get('json_path')
    report_file = request.args.get('report_file') # Optional, for back button context

    if not json_path_rel:
        flash('Motivation letter JSON path missing')
        logger.error("Missing json_path for viewing email text.")
        return redirect(url_for('index'))

    try:
        json_full_path = Path(current_app.root_path) / json_path_rel
        if not json_full_path.is_file():
            flash(f'Motivation letter JSON file not found: {json_path_rel}')
            logger.error(f"JSON file not found for email text view: {json_full_path}")
            # Try redirecting back to results if possible
            if report_file:
                 return redirect(url_for('job_matching.view_results', report_file=report_file))
            else:
                 return redirect(url_for('index'))

        with open(json_full_path, 'r', encoding='utf-8') as f:
            letter_data = json.load(f)

        # Get email_text, default to None if not found or empty
        email_text = letter_data.get('email_text')
        if not email_text: # Check if it's None or empty string
             logger.warning(f"No 'email_text' found or text is empty in {json_path_rel}")
             email_text = None # Ensure it's None if empty for template logic

        return render_template('email_text_view.html',
                               email_text=email_text,
                               report_file=report_file) # Pass report_file for potential back button logic

    except json.JSONDecodeError:
        flash(f'Error decoding JSON from file: {json_path_rel}')
        logger.error(f"JSONDecodeError for email text view: {json_path_rel}")
        if report_file:
             return redirect(url_for('job_matching.view_results', report_file=report_file))
        else:
             return redirect(url_for('index'))
    except Exception as e:
        flash(f'Error viewing email text: {str(e)}')
        logger.error(f'Error viewing email text from {json_path_rel}: {str(e)}', exc_info=True)
        if report_file:
             return redirect(url_for('job_matching.view_results', report_file=report_file))
        else:
             return redirect(url_for('index'))

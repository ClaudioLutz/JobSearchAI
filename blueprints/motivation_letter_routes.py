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
from motivation_letter_generator import main as generate_motivation_letter
from word_template_generator import json_to_docx, create_word_document_from_json_file

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
        # Get the CV filename (base name without extension) and job URL from the form
        cv_filename = request.form.get('cv_filename')
        job_url = request.form.get('job_url')
        report_file = request.form.get('report_file') # To redirect back to the correct results page

        logger.info(f"Generating motivation letter for CV: {cv_filename} and job URL: {job_url}")

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

        # --- Check if letter already exists ---
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
                logger.info(f"Motivation letter already exists for job title: {job_title}")
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

        # --- Generate new letter ---
        start_operation = current_app.extensions['start_operation']
        update_operation_progress = current_app.extensions['update_operation_progress']
        complete_operation = current_app.extensions['complete_operation']
        operation_status = current_app.extensions['operation_status']
        app_instance = current_app._get_current_object() # Get app instance for context

        operation_id = start_operation('motivation_letter_generation')

        # Define background task function (takes app context)
        def generate_motivation_letter_task(app, op_id, cv_name, job_url_task, report_file_task):
            with app.app_context(): # Establish app context for the thread
                try:
                    update_operation_progress(op_id, 10, 'processing', 'Extracting job details...')
                    # job_details = get_job_details_for_url(job_url_task) # No longer needed here, generator will fetch live data

                    logger.info(f"Calling generate_motivation_letter with cv_filename={cv_name}, job_url={job_url_task} (forcing live scrape)")
                    # Remove existing_job_details to force live scraping within the generator
                    result = generate_motivation_letter(cv_name, job_url_task) # Removed existing_job_details

                    if not result:
                        logger.error("Failed to generate motivation letter (generator returned None)")
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
                    operation_status[op_id]['result'] = {
                        'has_json': has_json,
                        'motivation_letter_content': result.get('motivation_letter_html') if has_json else result.get('motivation_letter'),
                        'html_file_path': html_file_path_rel,
                        'docx_file_path': docx_file_path_rel,
                        'job_details': job_details,
                        'report_file': report_file_task
                    }
                except Exception as e:
                    logger.error(f'Error in motivation letter generation task: {str(e)}', exc_info=True)
                    complete_operation(op_id, 'failed', f'Error generating motivation letter: {str(e)}')

        # Start the background thread, passing the app instance and necessary args
        thread = threading.Thread(target=generate_motivation_letter_task, args=(app_instance, operation_id, cv_filename, job_url, report_file))
        thread.daemon = True
        thread.start()

        flash(f'Motivation letter generation started. Please wait. (operation_id={operation_id})')
        return redirect(url_for('job_matching.view_results', report_file=report_file))

    except Exception as e:
        flash(f'Error generating motivation letter: {str(e)}')
        logger.error(f'Error generating motivation letter route: {str(e)}', exc_info=True)
        report_file_param = request.form.get('report_file')
        if report_file_param:
            return redirect(url_for('job_matching.view_results', report_file=report_file_param))
        else:
            return redirect(url_for('index'))


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

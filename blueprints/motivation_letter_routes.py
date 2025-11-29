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
from flask_login import login_required
from werkzeug.utils import secure_filename

# Add project root to path
import sys
sys.path.append('.')

# Import necessary functions from other modules
from word_template_generator import json_to_docx, create_word_document_from_json_file
# Import functions needed for manual text structuring and generation
from job_details_utils import structure_text_with_openai, has_sufficient_content, get_job_details
from letter_generation_utils import generate_motivation_letter, generate_email_text_only # Import the correct generator functions
from utils.decorators import admin_required
from services.application_service import update_application_status, get_application_status
from utils.db_utils import JobMatchDatabase

motivation_letter_bp = Blueprint('motivation_letter', __name__, url_prefix='/motivation_letter')

logger = logging.getLogger("dashboard.motivation_letter") # Use a child logger

# Helper function to get job details - uses the function attached to current_app
# Note: This might be redundant if get_job_details from job_details_utils is always used now.
# Consider refactoring depending on usage patterns.
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
@login_required
@admin_required
def generate_motivation_letter_route():
    """Generate a motivation letter for a single job, handling manual text input."""
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
            return jsonify({'success': False, 'error': 'Missing CV filename or job URL'}), 400

        # Check if the CV summary file exists (relative to app root)
        summary_path = Path(current_app.root_path) / 'process_cv/cv-data/processed' / f"{cv_filename}_summary.txt"
        if not summary_path.exists():
            logger.error(f"CV summary file not found: {summary_path}")
            return jsonify({'success': False, 'error': f'CV summary file not found: {summary_path.name}'}), 400
        
        # --- Auto-transition status to PREPARING on letter generation ---
        try:
            from utils.url_utils import URLNormalizer
            normalizer = URLNormalizer()
            normalized_url = normalizer.normalize(job_url)
            
            # Get CV key from filename (remove _summary.txt)
            cv_key = cv_filename
            
            # Find the job match
            db = JobMatchDatabase()
            db.create_connection()
            cursor = db.conn.cursor()
            
            cursor.execute('''
                SELECT id FROM job_matches 
                WHERE job_url = ? AND cv_key = ?
            ''', (normalized_url, cv_key))
            
            result = cursor.fetchone()
            db.close_connection()
            
            if result:
                job_match_id = result[0]
                
                # Check current status
                current_status = get_application_status(job_match_id)
                
                # Only update if in early stages (MATCHED or INTERESTED)
                if current_status in ['MATCHED', 'INTERESTED']:
                    success = update_application_status(job_match_id, 'PREPARING')
                    if success:
                        logger.info(f"Auto-transitioned job {job_match_id} to PREPARING on letter generation")
                    else:
                        logger.warning(f"Failed to auto-transition job {job_match_id} to PREPARING")
                else:
                    logger.info(f"Skipped auto-transition for job {job_match_id} (current status: {current_status})")
            else:
                logger.warning(f"Could not find job match for auto-transition (URL: {job_url}, CV: {cv_key})")
        except Exception as e:
            # Don't fail letter generation if status update fails
            logger.exception(f"Error during auto-transition on letter generation: {str(e)}")

        # --- Check if letter already exists --- ONLY if not using manual text input ---
        if not manual_job_text:
            job_details_check = get_job_details(job_url) # Use the main function
            existing_letter_found = False

            if job_details_check and 'Job Title' in job_details_check:
                job_title = job_details_check['Job Title']
                sanitized_job_title = sanitize_filename(job_title)
                letters_dir = Path(current_app.root_path) / 'motivation_letters'
                html_path = letters_dir / f"motivation_letter_{sanitized_job_title}.html"
                json_path = letters_dir / f"motivation_letter_{sanitized_job_title}.json"

                if html_path.is_file() and json_path.is_file():
                    logger.info(f"Motivation letter already exists for job title: {job_title} (Automatic check)")
                    existing_letter_found = True

            if existing_letter_found:
                logger.warning(f"Attempted to generate letter automatically, but it already exists for: {job_title}")
                return jsonify({'success': False, 'error': f'Letter already exists for {job_title}. Generate manually to overwrite or delete existing files.'}), 409 # 409 Conflict

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
                        job_details = structure_text_with_openai(manual_job_text_task, job_url_task, source_type="Manual Input")

                        if not job_details:
                            logger.error("Failed to structure manually provided text.")
                            complete_operation(op_id, 'failed', 'Failed to structure manually provided text.')
                            return
                        if not has_sufficient_content(job_details):
                             logger.warning("Manually provided text structured, but content might be insufficient.")
                             update_operation_progress(op_id, 20, 'processing', 'Manual text structured (warning: content may be insufficient). Generating letter...')
                        else:
                             update_operation_progress(op_id, 20, 'processing', 'Manual text structured successfully. Generating letter...')
                    else:
                        update_operation_progress(op_id, 10, 'processing', 'Fetching/Scraping job details...')
                        logger.info(f"Attempting automatic job detail fetching for URL: {job_url_task}")
                        job_details = get_job_details(job_url_task)

                        if not job_details or not has_sufficient_content(job_details):
                             logger.error(f"Failed to fetch sufficient job details automatically for {job_url_task}.")
                             complete_operation(op_id, 'failed', 'Failed to fetch sufficient job details automatically.')
                             return
                        update_operation_progress(op_id, 20, 'processing', 'Job details fetched successfully. Generating letter...')

                    # --- Step 2: Generate Letter using job_details and cv_summary_text ---
                    logger.info(f"Calling letter_generation_utils.generate_motivation_letter for CV '{cv_name}'")
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

                    html_file_path_abs_str = result.get('html_file_path') if has_json else result.get('file_path')
                    html_file_path_rel = None
                    if html_file_path_abs_str:
                         abs_html_path = Path(html_file_path_abs_str)
                         if not abs_html_path.is_absolute():
                              abs_html_path = Path(app.root_path) / html_file_path_abs_str
                         html_file_path_rel = str(abs_html_path.relative_to(app.root_path))

                    complete_operation(op_id, 'completed', 'Motivation letter generated successfully')

                    operation_status[op_id]['result'] = {
                        'has_json': has_json,
                        'motivation_letter_content': result.get('motivation_letter_html'),
                        'html_file_path': html_file_path_rel,
                        'json_file_path': result.get('json_file_path'),
                        'docx_file_path': docx_file_path_rel,
                        'job_details': job_details,
                        'report_file': report_file_task
                    }
                except Exception as e:
                    logger.error(f'Error in motivation letter generation task: {str(e)}', exc_info=True)
                    complete_operation(op_id, 'failed', f'Error generating motivation letter: {str(e)}')

        thread_args = (app_instance, operation_id, cv_filename, job_url, report_file, manual_job_text)
        thread = threading.Thread(target=generate_motivation_letter_task, args=thread_args)
        thread.daemon = True
        thread.start()

        return jsonify({'success': True, 'operation_id': operation_id})

    except Exception as e:
        logger.error(f'Error generating motivation letter route: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': f'Error starting generation: {str(e)}'}), 500


@motivation_letter_bp.route('/generate_multiple', methods=['POST'])
@login_required
@admin_required
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

    results = {'success_count': 0, 'errors': []}
    threads = []
    lock = threading.Lock()
    app_instance = current_app._get_current_object()

    cv_summary_text = None
    try:
        summary_path_main = Path(app_instance.root_path) / 'process_cv/cv-data/processed' / f"{cv_base_name}_summary.txt"
        with open(summary_path_main, 'r', encoding='utf-8') as f_cv_main:
            cv_summary_text = f_cv_main.read()
        if not cv_summary_text:
            raise ValueError("CV summary file is empty.")
        logger.info(f"Successfully loaded CV summary for {cv_base_name} for bulk generation.")
    except Exception as cv_load_err:
        logger.error(f"Error reading CV summary file {summary_path_main} before starting threads: {cv_load_err}", exc_info=True)
        return jsonify({'error': f'Error reading CV summary: {cv_load_err}'}), 500

    def generate_single_letter_task(app, job_url, cv_summary_content, cv_name_for_log):
        nonlocal results
        with app.app_context():
            if not job_url or job_url == 'N/A' or not job_url.startswith('http'):
                logger.warning(f"Skipping invalid job URL: {job_url}")
                with lock: results['errors'].append(job_url)
                return

            try:
                logger.info(f"Generating letter for CV '{cv_name_for_log}' and URL '{job_url}'")
                logger.info(f"Fetching job details for URL: {job_url}")
                job_details = get_job_details(job_url)

                if not job_details or not has_sufficient_content(job_details):
                     logger.error(f"Failed to fetch sufficient job details for {job_url} in bulk generation.")
                     with lock: results['errors'].append(job_url)
                     return

                logger.info(f"Calling generate_motivation_letter for CV '{cv_name_for_log}' and URL '{job_url}'")
                result = generate_motivation_letter(cv_summary_content, job_details)

                if result:
                    logger.info(f"Generator returned result for URL: {job_url}")
                    with lock: results['success_count'] += 1
                    if 'motivation_letter_json' in result and 'json_file_path' in result:
                         try:
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
                    with lock: results['errors'].append(job_url)
            except Exception as e:
                logger.error(f"Exception generating letter for URL {job_url}: {str(e)}", exc_info=True)
                with lock: results['errors'].append(job_url)

    for url in job_urls:
        thread = threading.Thread(target=generate_single_letter_task, args=(app_instance, url, cv_summary_text, cv_base_name))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    logger.info(f"Multiple letter generation complete. Success: {results['success_count']}, Failures: {len(results['errors'])}")
    return jsonify(results)


@motivation_letter_bp.route('/generate_multiple_emails', methods=['POST'])
@login_required
@admin_required
def generate_multiple_emails():
    """Generate email texts for multiple selected jobs and update their JSON files."""
    data = request.get_json()
    if not data:
        logger.error("Invalid request format for /generate_multiple_emails")
        return jsonify({'error': 'Invalid request format'}), 400

    job_urls = data.get('job_urls')
    cv_base_name = data.get('cv_filename')

    if not job_urls or not isinstance(job_urls, list) or not cv_base_name:
        logger.error(f"Missing job_urls or cv_filename in request: {data}")
        return jsonify({'error': 'Missing job_urls or cv_filename'}), 400

    logger.info(f"Received request to generate {len(job_urls)} email texts for CV: {cv_base_name}")

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

    results = {'success_count': 0, 'errors': [], 'not_found': []}
    threads = []
    lock = threading.Lock()
    app_instance = current_app._get_current_object()

    from letter_generation_utils import generate_email_text_only

    def generate_and_update_task(app, job_url):
        nonlocal results
        with app.app_context():
            # VALIDATE AND CLEAN URL FIRST
            from utils.url_utils import URLNormalizer
            original_url = job_url
            job_url = URLNormalizer.clean_malformed_url(job_url)
            
            if original_url != job_url:
                logger.info(f"Cleaned malformed URL: '{original_url}' → '{job_url}'")
            
            if not job_url or job_url == 'N/A' or not job_url.startswith('http'):
                logger.warning(f"Skipping invalid job URL after cleaning: {job_url} (original: {original_url})")
                with lock: results['errors'].append({'url': original_url, 'reason': 'Invalid URL'})
                return

            try:
                job_details = get_job_details(job_url)
                if not job_details or not job_details.get('Job Title'):
                    logger.warning(f"Could not get sufficient job details for URL: {job_url}")
                    with lock: results['errors'].append({'url': job_url, 'reason': 'Failed to get job details'})
                    return

                job_title = job_details['Job Title']
                sanitized_job_title = sanitize_filename(job_title)
                letters_dir = Path(app.root_path) / 'motivation_letters'
                json_file_path = letters_dir / f"motivation_letter_{sanitized_job_title}.json"

                logger.info(f"Generating email text for CV '{cv_base_name}' and Job '{job_title}' (URL: {job_url})")
                email_text = generate_email_text_only(cv_summary, job_details)

                if not email_text:
                    logger.error(f"Failed to generate email text (generate_email_text_only returned None) for Job: {job_title}")
                    with lock: results['errors'].append({'url': job_url, 'reason': 'Email text generation failed'})
                    return

                letter_data = {}
                if json_file_path.is_file():
                    try:
                        with open(json_file_path, 'r', encoding='utf-8') as f:
                            letter_data = json.load(f)
                        logger.info(f"Loaded existing JSON: {json_file_path}")
                    except Exception as load_e:
                        logger.error(f"Error loading existing JSON {json_file_path}: {load_e}. Will overwrite.")
                        letter_data = {}
                else:
                    logger.info(f"JSON file not found ({json_file_path}), will create new.")
                    letter_data['job_title_source'] = job_title

                letter_data['email_text'] = email_text

                try:
                    letters_dir.mkdir(parents=True, exist_ok=True)
                    with open(json_file_path, 'w', encoding='utf-8') as f:
                        json.dump(letter_data, f, ensure_ascii=False, indent=2)
                    logger.info(f"Successfully updated/created JSON with email text: {json_file_path}")
                    with lock: results['success_count'] += 1
                except Exception as save_e:
                    logger.error(f"Error saving updated JSON {json_file_path}: {save_e}", exc_info=True)
                    with lock: results['errors'].append({'url': job_url, 'reason': f'Failed to save JSON: {save_e}'})

            except Exception as e:
                logger.error(f"Exception generating/updating email text for URL {job_url}: {str(e)}", exc_info=True)
                with lock: results['errors'].append({'url': job_url, 'reason': f'Unexpected error: {e}'})

    for url in job_urls:
        thread = threading.Thread(target=generate_and_update_task, args=(app_instance, url,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    logger.info(f"Multiple email text generation/update complete. Success: {results['success_count']}, Failures: {len(results['errors'])}")
    return jsonify(results)


@motivation_letter_bp.route('/view/<operation_id>')
@login_required
def view_motivation_letter(operation_id):
    """View a generated motivation letter (newly generated or existing)"""
    try:
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
        # Retrieve report_file from the stored result to pass to the template
        report_file = result.get('report_file')

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
@login_required
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
@login_required
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
@login_required
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
@login_required
def view_scraped_data(scraped_data_filename):
    """Display the contents of a specific scraped job data JSON file."""
    try:
        # Use the filename directly as passed from the URL (it was determined safely before)
        filename = scraped_data_filename
        file_path = Path(current_app.root_path) / 'motivation_letters' / filename

        if not file_path.is_file():
            flash(f'Scraped job data file not found: {filename}')
            logger.error(f"Scraped job data file not found: {file_path}")
            return redirect(url_for('index'))

        with open(file_path, 'r', encoding='utf-8') as f:
            job_details = json.load(f)

        return render_template('scraped_data_view.html', job_details=job_details, filename=filename)

    except FileNotFoundError:
        flash(f'Scraped job data file not found: {filename}') # Use original filename in flash
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
@login_required
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


@motivation_letter_bp.route('/upload_pdf', methods=['POST'])
@login_required
def upload_bewerbungsschreiben_pdf():
    """Upload Bewerbungsschreiben PDF for sending"""
    try:
        if 'pdf_file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        
        file = request.files['pdf_file']
        
        if not file.filename or file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'success': False, 'error': 'Only PDF files are allowed'}), 400
        
        # Secure filename and save
        job_title = request.form.get('job_title', 'application')
        sanitized_title = sanitize_filename(job_title)
        filename = f"Bewerbungsschreiben_{sanitized_title}.pdf"
        
        # Save to ready_to_send directory
        upload_dir = Path(current_app.root_path) / 'motivation_letters/ready_to_send'
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / filename
        file.save(str(file_path))
        
        logger.info(f"Uploaded Bewerbungsschreiben PDF: {file_path}")
        
        return jsonify({
            'success': True,
            'file_path': str(file_path.relative_to(current_app.root_path)),
            'filename': filename
        })
    
    except Exception as e:
        logger.error(f'Error uploading PDF: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@motivation_letter_bp.route('/send_application', methods=['POST'])
@login_required
def send_application_email():
    """Send job application email with PDF attachments"""
    try:
        data = request.get_json()
        
        recipient_email = data.get('recipient_email')
        subject = data.get('subject')
        email_text = data.get('email_text')
        bewerbungsschreiben_pdf_path = data.get('bewerbungsschreiben_pdf_path')
        job_title = data.get('job_title', '')
        company_name = data.get('company_name', '')
        
        # Validate required fields
        if not all([recipient_email, subject, email_text, bewerbungsschreiben_pdf_path]):
            return jsonify({
                'success': False,
                'error': 'Missing required fields'
            }), 400
        
        # Build attachment paths
        bewerbungsschreiben_full_path = Path(current_app.root_path) / bewerbungsschreiben_pdf_path
        lebenslauf_full_path = Path(current_app.root_path) / 'process_cv/cv-data/input/Lebenslauf_-_Lutz_Claudio.pdf'
        
        # Validate both files exist
        if not bewerbungsschreiben_full_path.is_file():
            return jsonify({
                'success': False,
                'error': 'Bewerbungsschreiben PDF not found'
            }), 400
        
        if not lebenslauf_full_path.is_file():
            return jsonify({
                'success': False,
                'error': 'Lebenslauf PDF not found. Please ensure CV is at process_cv/cv-data/input/Lebenslauf_-_Lutz_Claudio.pdf'
            }), 400
        
        # Send email with attachments
        from utils.email_sender import EmailSender
        sender = EmailSender()
        success, message = sender.send_application_with_attachments(
            recipient_email=recipient_email,
            subject=subject,
            body_text=email_text,
            attachment_paths=[
                str(bewerbungsschreiben_full_path),
                str(lebenslauf_full_path)
            ],
            job_title=job_title,
            company_name=company_name
        )
        
        if success:
            logger.info(f"Application sent successfully to {recipient_email} for {job_title} at {company_name}")
        
        return jsonify({
            'success': success,
            'message': message
        })
    
    except Exception as e:
        logger.error(f'Error sending application: {str(e)}', exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Error sending application: {str(e)}'
        }), 500


@motivation_letter_bp.route('/prepare_send/<job_title>')
@login_required
def prepare_send_application(job_title):
    """Show the send application page with email text and upload form"""
    try:
        # Load the email text from JSON
        sanitized_title = sanitize_filename(job_title)
        json_path = Path(current_app.root_path) / 'motivation_letters' / f'motivation_letter_{sanitized_title}.json'
        
        email_text = ""
        job_details = {}
        
        if json_path.is_file():
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                email_text = data.get('email_text', '')
                # Load job details from the JSON
                job_details = {
                    'Job Title': data.get('job_title_source', job_title),
                    'Company Name': data.get('company_name', ''),
                    'Application Email': data.get('contact_email', ''),
                    'Application URL': data.get('job_url', '')
                }
        
        return render_template(
            'send_application.html',
            job_title=job_title,
            email_text=email_text,
            job_details=job_details
        )
    
    except Exception as e:
        flash(f'Error preparing send application: {str(e)}')
        logger.error(f'Error in prepare_send_application: {str(e)}', exc_info=True)
        return redirect(url_for('index'))


@motivation_letter_bp.route('/delete/<json_filename>')
@login_required
def delete_letter_set(json_filename):
    """Delete a generated letter JSON and its associated HTML, DOCX, and scraped data files."""
    try:
        # Do NOT use secure_filename here as it might alter valid chars like umlauts
        filename_base = json_filename.replace('motivation_letter_', '').replace('.json', '')
        letters_dir = Path(current_app.root_path) / 'motivation_letters'

        # Define paths for all potential files
        json_path = letters_dir / f"motivation_letter_{filename_base}.json"
        html_path = letters_dir / f"motivation_letter_{filename_base}.html"
        docx_path = letters_dir / f"motivation_letter_{filename_base}.docx"
        scraped_path = letters_dir / f"motivation_letter_{filename_base}_scraped_data.json"

        deleted_files = []
        not_found_files = []

        # Attempt to delete each file if it exists
        for file_path in [json_path, html_path, docx_path, scraped_path]:
            if file_path.is_file():
                try:
                    os.remove(file_path)
                    deleted_files.append(file_path.name)
                    logger.info(f"Deleted file: {file_path}")
                except Exception as e:
                    logger.error(f"Error deleting file {file_path}: {e}")
                    flash(f"Error deleting file {file_path.name}: {e}", "danger")
            else:
                not_found_files.append(file_path.name)
                logger.debug(f"File not found for deletion (this is okay): {file_path}")

        if deleted_files:
            flash(f"Successfully deleted files related to: {filename_base.replace('_', ' ')}", "success")
        else:
            flash(f"No files found to delete for: {filename_base.replace('_', ' ')}", "warning")

    except Exception as e:
        flash(f"An unexpected error occurred during deletion: {str(e)}", "danger")
        logger.error(f"Error deleting letter set for {json_filename}: {str(e)}", exc_info=True)

    # Redirect back to the main dashboard index
    return redirect(url_for('index'))

import os
import json
import logging
import threading
import urllib.parse
import os # Added import
import json
import logging
import threading
import urllib.parse
import traceback
import datetime
import concurrent.futures # Added for ThreadPoolExecutor
from pathlib import Path
from flask import (
    Blueprint, request, redirect, url_for, flash, send_file, jsonify,
    render_template, current_app
)
from werkzeug.utils import secure_filename
from utils.database_utils import database_connection # Import database context manager
from config import ConfigManager # Import config

# Add project root to path
import sys
sys.path.append('.')

# Import necessary functions from other modules
from word_template_generator import json_to_docx, create_word_document_from_json_file
# Import functions needed for manual text structuring and generation
# get_job_details is the new canonical one: get_job_details(job_ref, scraped_data)
from job_details_utils import structure_text_with_openai, has_sufficient_content, get_job_details 
from letter_generation_utils import generate_motivation_letter, generate_email_text_only # Import the correct generator functions

motivation_letter_bp = Blueprint('motivation_letter', __name__, url_prefix='/motivation_letter')

logger = logging.getLogger("dashboard.motivation_letter") # Use a child logger

# Helper function to load raw data from the latest job_data_*.json file
def _load_latest_raw_job_data() -> list[dict] | dict | None:
    """Loads the latest job_data_*.json file and returns its raw content."""
    try:
        cfg = ConfigManager()
        job_data_dir = cfg.get_path('job_data')
        if not job_data_dir:
            logger.error("Configuration error: 'job_data' path not found in config.")
            return None
        
        if not job_data_dir.exists():
            logger.error(f"Job data directory does not exist: {job_data_dir}")
            return None

        job_data_files = list(job_data_dir.glob('job_data_*.json'))
        if not job_data_files:
            logger.error(f"No job_data_*.json files found in {job_data_dir}")
            return None

        latest_job_data_file = max(job_data_files, key=os.path.getctime)
        logger.info(f"Loading raw job data from: {latest_job_data_file}")

        with open(latest_job_data_file, 'r', encoding='utf-8') as f:
            raw_job_data = json.load(f)
        
        return raw_job_data
        
    except Exception as e:
        logger.error(f"Error loading latest raw job data: {e}", exc_info=True)
        return None

# Helper function to sanitize filenames (consider moving to utils)
def sanitize_filename(name, length=30):
    sanitized = ''.join(c if c.isalnum() or c in [' ', '_', '-'] else '_' for c in name)
    sanitized = sanitized.replace(' ', '_')
    return sanitized[:length]

@motivation_letter_bp.route('/generate', methods=['POST'])
def generate_motivation_letter_route():
    """Generate a motivation letter for a single job, handling manual text input."""
    try:
        config = ConfigManager() # Instantiate config manager here
        # Get data from the form
        cv_filename = request.form.get('cv_filename') # This is the relative path
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

        # Check if the CV summary file exists using the helper function
        # Note: get_cv_summary handles path construction and logging if not found
        if not current_app.get_cv_summary(cv_filename):
             # Error is logged within get_cv_summary if file not found/readable
             return jsonify({'success': False, 'error': f'CV summary file not found or readable for {cv_filename}'}), 400

        # --- Check if letter already exists --- ONLY if not using manual text input ---
        if not manual_job_text:
            raw_scraped_data = _load_latest_raw_job_data()
            job_details_check = None
            existing_letter_found = False

            if raw_scraped_data is not None:
                try:
                    # Use the new get_job_details(job_ref, scraped_data)
                    job_details_check = get_job_details(job_url, raw_scraped_data) 
                except KeyError: # Raised by get_job_details if job_ref not found
                    logger.info(f"Job URL {job_url} not found in latest scraped data for pre-check.")
                    job_details_check = None # Ensure it's None if not found
                except Exception as e_check:
                    logger.error(f"Error getting job_details for pre-check of {job_url}: {e_check}", exc_info=True)
                    job_details_check = None


            if job_details_check and job_details_check.get('Job Title'):
                job_title = job_details_check['Job Title']
                sanitized_job_title = sanitize_filename(job_title)
                # Use config path for consistency
                letters_dir_rel = Path(config.get_path('motivation_letters'))
                letters_dir_abs = Path(config.get_path('data_root')) / letters_dir_rel
                html_path = letters_dir_abs / f"motivation_letter_{sanitized_job_title}.html"
                json_path = letters_dir_abs / f"motivation_letter_{sanitized_job_title}.json"

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
        config = ConfigManager() # Get config instance

        # Create a cancellation event for this operation
        cancel_event = threading.Event()
        operation_id = start_operation('motivation_letter_generation', cancel_event=cancel_event) # Pass event to start_operation

        # Define background task function (takes app context, manual_job_text, and cancel_event)
        def generate_motivation_letter_task(app, op_id, cv_name, job_url_task, report_file_task, manual_job_text_task, cancel_event_task):
            with app.app_context(): # Establish app context for the thread
                job_details = None
                # Use the database_connection context manager
                try:
                    # --- Load CV Summary using helper (checks cache) ---
                    # cv_name is the relative path passed to the task
                    cv_summary_text = current_app.get_cv_summary(cv_name)
                    if cv_summary_text is None:
                        # get_cv_summary already logs errors/warnings
                        complete_operation(op_id, 'failed', f'Could not load CV summary for {cv_name}.')
                        return
                    # --- Check if summary is empty ---
                    if not cv_summary_text or not cv_summary_text.strip():
                         logger.error(f"Retrieved CV summary for {cv_name} is empty. Cannot generate letter without CV content.")
                         complete_operation(op_id, 'failed', f'CV summary for {cv_name} is empty. Please re-process the CV.')
                         return
                    # --- End Check if summary is empty ---
                    logger.info(f"Successfully obtained non-empty CV summary for {cv_name} (from cache or file).")

                    # --- Cancellation Check 1 ---
                    if cancel_event_task.is_set():
                        logger.info(f"Operation {op_id} cancelled before fetching/structuring job details.")
                        complete_operation(op_id, 'cancelled', 'Operation cancelled by user.')
                        return

                    # --- Step 1: Get or Structure Job Details ---
                    scraped_data_rel_path = None # Initialize path for saved job details (relative to data_root)
                    job_title_for_file = "unknown_job" # Default filename part
                    company_name_for_db = None # Initialize company name

                    if manual_job_text_task:
                        update_operation_progress(op_id, 10, 'processing', 'Structuring manual text...')
                        logger.info(f"Structuring manually provided text for job URL: {job_url_task}")
                        # TODO: Consider adding cancellation check within structure_text_with_openai if it's long-running
                        job_details = structure_text_with_openai(manual_job_text_task, job_url_task, source_type="Manual Input")

                        if cancel_event_task.is_set(): # Check after potentially long call
                            logger.info(f"Operation {op_id} cancelled after structuring manual text.")
                            complete_operation(op_id, 'cancelled', 'Operation cancelled by user.')
                            return

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
                        update_operation_progress(op_id, 10, 'processing', 'Loading and searching job details...')
                        logger.info(f"Attempting to load and find job details for URL: {job_url_task}")
                        
                        raw_scraped_data_task = _load_latest_raw_job_data()
                        if raw_scraped_data_task is None:
                            logger.error(f"Failed to load raw scraped data for {job_url_task}.")
                            complete_operation(op_id, 'failed', 'Failed to load job data source.')
                            return

                        try:
                            # Use the new get_job_details(job_ref, scraped_data)
                            job_details = get_job_details(job_url_task, raw_scraped_data_task)
                        except KeyError:
                            logger.error(f"Job URL {job_url_task} not found in latest scraped data.")
                            complete_operation(op_id, 'failed', f'Job details not found for {job_url_task} in pre-scraped data.')
                            return
                        except Exception as e_task_fetch:
                            logger.error(f"Error getting job_details for {job_url_task} from scraped data: {e_task_fetch}", exc_info=True)
                            complete_operation(op_id, 'failed', f'Error processing job data for {job_url_task}.')
                            return

                        if cancel_event_task.is_set(): # Check after potentially long call
                            logger.info(f"Operation {op_id} cancelled after loading job details.")
                            complete_operation(op_id, 'cancelled', 'Operation cancelled by user.')
                            return

                        if not job_details or not has_sufficient_content(job_details):
                             logger.error(f"Failed to fetch sufficient job details automatically for {job_url_task}.")
                             complete_operation(op_id, 'failed', 'Failed to fetch sufficient job details automatically.')
                             return
                        update_operation_progress(op_id, 20, 'processing', 'Job details fetched successfully. Generating letter...')

                    # --- Cancellation Check 2 ---
                    if cancel_event_task.is_set():
                        logger.info(f"Operation {op_id} cancelled before saving job details JSON.")
                        complete_operation(op_id, 'cancelled', 'Operation cancelled by user.')
                        return

                    # --- Save Job Details JSON ---
                    if job_details:
                        job_title_for_file = sanitize_filename(job_details.get('Job Title', 'unknown_job'))
                        company_name_for_db = job_details.get('Company Name') # Get company name for DB
                        # Use config path relative to data_root for storage consistency
                        letters_dir_rel = Path(config.get_path('motivation_letters')) # Path relative to data_root
                        letters_dir_abs = Path(config.get_path('data_root')) / letters_dir_rel # Absolute path for writing
                        letters_dir_abs.mkdir(parents=True, exist_ok=True)

                        scraped_data_filename = f"motivation_letter_{job_title_for_file}_scraped_data.json"
                        scraped_data_abs_path = letters_dir_abs / scraped_data_filename
                        try:
                            with open(scraped_data_abs_path, 'w', encoding='utf-8') as f_scrape:
                                json.dump(job_details, f_scrape, ensure_ascii=False, indent=2)
                            # Store path relative to data_root in DB
                            scraped_data_rel_path = str(letters_dir_rel / scraped_data_filename)
                            logger.info(f"Saved job details to: {scraped_data_abs_path} (DB path: {scraped_data_rel_path})")
                        except Exception as save_err:
                            logger.error(f"Error saving job details JSON to {scraped_data_abs_path}: {save_err}", exc_info=True)
                            # Decide if this is fatal or just a warning

                    # --- Cancellation Check 3 ---
                    if cancel_event_task.is_set():
                        logger.info(f"Operation {op_id} cancelled before generating letter content.")
                        complete_operation(op_id, 'cancelled', 'Operation cancelled by user.')
                        return

                    # --- Step 2: Generate Letter using job_details and cv_summary_text ---
                    logger.info(f"Calling letter_generation_utils.generate_motivation_letter for CV '{cv_name}'")
                    # TODO: Consider adding cancellation check within generate_motivation_letter if it's long-running (OpenAI call)
                    # Function now returns (success, result_or_error)
                    success, result_or_error = generate_motivation_letter(cv_summary_text, job_details)

                    if cancel_event_task.is_set(): # Check after potentially long call
                        logger.info(f"Operation {op_id} cancelled after generating letter content.")
                        complete_operation(op_id, 'cancelled', 'Operation cancelled by user.')
                        return

                    if not success:
                        error_message = result_or_error if isinstance(result_or_error, str) else "Unknown generation error"
                        logger.error(f"Failed to generate motivation letter: {error_message}")
                        complete_operation(op_id, 'failed', f'Failed to generate motivation letter: {error_message}')
                        return

                    # If successful, result_or_error is the result dictionary
                    result = result_or_error
                    update_operation_progress(op_id, 70, 'processing', 'Formatting motivation letter...')
                    logger.info(f"Successfully generated motivation letter content")

                    # Check for expected keys in the result dictionary
                    has_json = isinstance(result, dict) and 'motivation_letter_json' in result and 'json_file_path' in result
                    docx_file_path_rel_db = None # Relative path for DB (data_root)
                    json_file_path_rel_db = None # Relative path for DB (data_root)
                    html_file_path_rel_db = None # Relative path for DB (data_root)

                    # Paths relative to project root for operation_status result (UI links)
                    docx_file_path_rel_ui = None
                    json_file_path_rel_ui = None
                    html_file_path_rel_ui = None

                    if has_json:
                        json_file_path_abs_str = result['json_file_path']
                        logger.info(f"Generated JSON motivation letter: {json_file_path_abs_str}")
                        update_operation_progress(op_id, 80, 'processing', 'Creating Word document...')
                        try:
                            abs_json_path = Path(json_file_path_abs_str)
                            if not abs_json_path.is_absolute():
                                abs_json_path = Path(app.root_path) / json_file_path_abs_str

                            # Calculate relative paths for DB (data_root)
                            json_file_path_rel_db = str(abs_json_path.relative_to(config.get_path('data_root')))
                            # Calculate relative paths for UI (project root)
                            json_file_path_rel_ui = str(abs_json_path.relative_to(app.root_path))

                            abs_docx_path = abs_json_path.with_suffix('.docx')
                            docx_path_abs = json_to_docx(result['motivation_letter_json'], output_path=str(abs_docx_path))
                            if docx_path_abs:
                                 # Calculate relative paths for DB (data_root)
                                 docx_file_path_rel_db = str(Path(docx_path_abs).relative_to(config.get_path('data_root')))
                                 # Calculate relative paths for UI (project root)
                                 docx_file_path_rel_ui = str(Path(docx_path_abs).relative_to(app.root_path))
                                 logger.info(f"Generated Word document: {docx_path_abs}")
                            else:
                                 logger.warning(f"json_to_docx returned None for {abs_json_path}")
                        except Exception as docx_e:
                             logger.error(f"Error generating DOCX from JSON {abs_json_path}: {docx_e}", exc_info=True)
                             # Optionally check cancel_event here if DOCX generation is slow
                    else:
                        logger.info(f"Generated HTML motivation letter: {result.get('file_path', 'N/A')}")

                    # --- Cancellation Check 4 ---
                    if cancel_event_task.is_set():
                        logger.info(f"Operation {op_id} cancelled before database insertion.")
                        complete_operation(op_id, 'cancelled', 'Operation cancelled by user.')
                        # Note: Files might have been created (JSON, DOCX, HTML). Consider cleanup?
                        return

                    update_operation_progress(op_id, 95, 'processing', 'Finalizing and saving to database...')

                    html_file_path_abs_str = result.get('html_file_path') if has_json else result.get('file_path')
                    if html_file_path_abs_str:
                         abs_html_path = Path(html_file_path_abs_str)
                         if not abs_html_path.is_absolute():
                              abs_html_path = Path(app.root_path) / html_file_path_abs_str
                         # Calculate relative paths for DB (data_root)
                         html_file_path_rel_db = str(abs_html_path.relative_to(config.get_path('data_root')))
                         # Calculate relative paths for UI (project root)
                         html_file_path_rel_ui = str(abs_html_path.relative_to(app.root_path))


                    # --- Step 3: Insert into Database ---
                    # Database operations happen within this 'with' block
                    with database_connection() as conn:
                        cursor = conn.cursor()

                        # --- Get CV ID --- (Moved inside DB block)
                        cv_id = None
                        try:
                            # Assuming cv_name is the base filename without extension, find matching record
                            # Use original_filepath which stores relative path from data_root
                            cursor.execute("SELECT id FROM CVS WHERE original_filepath LIKE ?", ('%' + cv_name + '%',)) # Simplified search
                            cv_record = cursor.fetchone()
                            if cv_record:
                                cv_id = cv_record[0]
                                logger.info(f"Found cv_id: {cv_id} for cv_name: {cv_name}")
                            else:
                                logger.error(f"Could not find cv_id for cv_name: {cv_name}")
                                # Decide if this is fatal or not - for now, proceed without cv_id
                        except Exception as db_err:
                            logger.error(f"Database error fetching cv_id for {cv_name}: {db_err}", exc_info=True)
                            # Decide if fatal

                        # --- Get Job Match Report ID (if report_file_task is provided) --- (Moved inside DB block)
                        job_match_report_id = None
                        if report_file_task:
                            try:
                                # report_file_task might be just a filename or a relative path
                                try:
                                    # Try to convert to a path relative to data_root if it's a full path
                                    report_rel_path = str(Path(report_file_task).relative_to(config.get_path('data_root')))
                                except ValueError:
                                    # If it's just a filename, use it as is
                                    report_rel_path = f"job_matches/{report_file_task}"
                                
                                cursor.execute("SELECT id FROM JOB_MATCH_REPORTS WHERE report_filepath_md LIKE ?", ('%' + os.path.basename(report_file_task) + '%',))
                                report_record = cursor.fetchone()
                                if report_record:
                                    job_match_report_id = report_record[0]
                                    logger.info(f"Found job_match_report_id: {job_match_report_id} for report_file: {report_file_task} (relative: {report_rel_path})")
                                else:
                                    logger.warning(f"Could not find job_match_report_id for report_file: {report_file_task} (relative: {report_rel_path})")
                            except Exception as db_err:
                                logger.error(f"Database error fetching job_match_report_id for {report_file_task}: {db_err}", exc_info=True)

                        # --- Insert Letter Record ---
                        if html_file_path_rel_db or json_file_path_rel_db: # Only insert if at least one file was created
                            try:
                                insert_data = {
                                    "cv_id": cv_id,
                                    "job_match_report_id": job_match_report_id,
                                    "job_title": job_details.get('Job Title', 'N/A') if job_details else 'N/A',
                                    "company_name": company_name_for_db,
                                    "generation_timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "letter_filepath_html": html_file_path_rel_db,
                                    "letter_filepath_json": json_file_path_rel_db,
                                    "letter_filepath_docx": docx_file_path_rel_db,
                                    "scraped_data_filepath": scraped_data_rel_path,
                                    "job_url": job_url_task # Store the job URL
                                }
                                columns = ', '.join(insert_data.keys())
                                placeholders = ', '.join('?' * len(insert_data))
                                sql = f"INSERT INTO MOTIVATION_LETTERS ({columns}) VALUES ({placeholders})"
                                cursor.execute(sql, list(insert_data.values()))
                                # Commit happens automatically when exiting 'with database_connection()' block if no errors
                                logger.info(f"Successfully inserted motivation letter record into database for job: {insert_data['job_title']}")
                            except Exception as db_insert_err:
                                logger.error(f"Database error inserting motivation letter record: {db_insert_err}", exc_info=True)
                                # Rollback happens automatically due to exception within 'with database_connection()'
                                # Decide if this should mark the operation as failed
                                # No cancellation check needed within DB transaction (should be fast)

                    # --- Finalize Operation Status --- (Outside DB connection block)
                    if cancel_event_task.is_set(): # Final check before completion
                        logger.info(f"Operation {op_id} cancelled just before final completion.")
                        complete_operation(op_id, 'cancelled', 'Operation cancelled by user.')
                        # Note: DB record might have been inserted. Consider cleanup?
                        return

                    complete_operation(op_id, 'completed', 'Motivation letter generated successfully')
                    # Store paths relative to project root for UI/download links
                    operation_status[op_id]['result'] = {
                        'has_json': has_json,
                        'motivation_letter_content': result.get('motivation_letter_html'),
                        'html_file_path': html_file_path_rel_ui,
                        'json_file_path': json_file_path_rel_ui,
                        'docx_file_path': docx_file_path_rel_ui,
                        'job_details': job_details,
                        'report_file': report_file_task
                    }
                # The 'with database_connection()' handles commit/rollback/close automatically
                except Exception as e:
                    logger.error(f'Error in motivation letter generation task: {str(e)}', exc_info=True)
                    # Check if cancelled before reporting failure
                    if not cancel_event_task.is_set():
                        complete_operation(op_id, 'failed', f'Error generating motivation letter: {str(e)}')
                    else:
                        # If cancelled during the exception handling? Unlikely but possible.
                        logger.info(f"Operation {op_id} was cancelled during error handling for: {str(e)}")
                        complete_operation(op_id, 'cancelled', f'Operation cancelled during error: {str(e)}')
                    # Rollback is handled by the context manager on exception

        # Pass the cancel_event to the thread arguments
        thread_args = (app_instance, operation_id, cv_filename, job_url, report_file, manual_job_text, cancel_event)
        thread = threading.Thread(target=generate_motivation_letter_task, args=thread_args)
        thread.daemon = True
        thread.start()

        return jsonify({'success': True, 'operation_id': operation_id})

    except Exception as e:
        logger.error(f'Error generating motivation letter route: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': f'Error starting generation: {str(e)}'}), 500


@motivation_letter_bp.route('/generate_multiple', methods=['POST'])
def generate_multiple_letters():
    """Generate motivation letters for multiple selected jobs using a ThreadPoolExecutor."""
    # Define max concurrent workers for bulk generation
    MAX_WORKERS = 5 # Limit concurrent threads

    data = request.get_json()
    if not data:
        logger.error("Invalid request format for /generate_multiple_letters")
        return jsonify({'error': 'Invalid request format'}), 400

    job_urls = data.get('job_urls')
    cv_base_name = data.get('cv_filename') # This is the relative path

    if not job_urls or not isinstance(job_urls, list) or not cv_base_name:
        logger.error(f"Missing job_urls or cv_filename in request: {data}")
        return jsonify({'error': 'Missing job_urls or cv_filename'}), 400

    logger.info(f"Received request to generate {len(job_urls)} letters for CV: {cv_base_name}")

    # Load the CV summary ONCE before starting tasks, using the helper
    cv_summary_text = current_app.get_cv_summary(cv_base_name)
    if cv_summary_text is None:
        logger.error(f"Could not load or generate CV summary for {cv_base_name} before starting bulk generation.")
        return jsonify({'error': f'Could not load or generate CV summary for {cv_base_name}.'}), 500
    logger.info(f"Successfully obtained CV summary for {cv_base_name} for bulk generation.")

    results = {'success_count': 0, 'errors': []}
    lock = threading.Lock()
    app_instance = current_app._get_current_object()
    config = ConfigManager() # Get config instance

    # Define the task function separately to be used with ThreadPoolExecutor
    # It now receives the pre-loaded summary text
    def generate_single_letter_task(app_context, job_url, cv_summary_content, cv_name_for_log, config_instance, lock_instance, results_dict):
        """Task to generate a single letter, designed for ThreadPoolExecutor."""
        # Note: This function now takes lock and results dict explicitly
        with app_context(): # Use the passed app context
            try:
                if not job_url or job_url == 'N/A' or not job_url.startswith('http'):
                    logger.warning(f"Skipping invalid job URL: {job_url}")
                    with lock_instance: results_dict['errors'].append(job_url)
                    return

                # Use the database_connection context manager
                cv_id = None
                with database_connection() as conn:
                    cursor = conn.cursor()
                    try:
                        # Extract the filename part from cv_name_for_log (which might be a relative path)
                        cv_filename_only = os.path.basename(cv_name_for_log)
                        cursor.execute("SELECT id FROM CVS WHERE original_filepath LIKE ?", ('%' + cv_filename_only + '%',))
                        cv_record = cursor.fetchone()
                        if cv_record: 
                            cv_id = cv_record[0]
                            logger.info(f"Bulk: Found cv_id: {cv_id} for cv_name: {cv_name_for_log}")
                        else: 
                            logger.warning(f"Bulk: Could not find cv_id for {cv_name_for_log}")
                    except Exception as db_err:
                        logger.error(f"Bulk DB error fetching cv_id for {cv_name_for_log}: {db_err}", exc_info=True)

                logger.info(f"Bulk: Generating letter for CV '{cv_name_for_log}' and URL '{job_url}'")
                logger.info(f"Bulk: Loading and searching job details for URL: {job_url}")
                raw_scraped_data_bulk = _load_latest_raw_job_data()
                if raw_scraped_data_bulk is None:
                    logger.error(f"Bulk: Failed to load raw scraped data for {job_url}.")
                    with lock_instance: results_dict['errors'].append(job_url)
                    return
                
                try:
                    job_details = get_job_details(job_url, raw_scraped_data_bulk)
                except KeyError:
                    logger.error(f"Bulk: Job URL {job_url} not found in latest scraped data.")
                    with lock_instance: results_dict['errors'].append(job_url)
                    return
                except Exception as e_bulk_fetch:
                    logger.error(f"Bulk: Error getting job_details for {job_url} from scraped data: {e_bulk_fetch}", exc_info=True)
                    with lock_instance: results_dict['errors'].append(job_url)
                    return

                if not job_details or not has_sufficient_content(job_details): # Check content after successful fetch
                     logger.error(f"Bulk: Fetched job details for {job_url}, but content is insufficient.")
                     with lock_instance: results_dict['errors'].append(job_url)
                     return

                logger.info(f"Bulk: Calling generate_motivation_letter for CV '{cv_name_for_log}' and URL '{job_url}'")
                # TODO: Consider adding cancellation check within generate_motivation_letter if it becomes very long
                # Function now returns (success, result_or_error)
                success, result_or_error = generate_motivation_letter(cv_summary_content, job_details)

                if success:
                    result = result_or_error # result is the dictionary
                    logger.info(f"Bulk: Generator returned result for URL: {job_url}")
                    with lock_instance: results_dict['success_count'] += 1

                    # --- Save Job Details JSON ---
                    scraped_data_rel_path = None
                    job_title_for_file = sanitize_filename(job_details.get('Job Title', 'unknown_job'))
                    company_name_for_db = job_details.get('Company Name')
                    letters_dir_rel = Path(config_instance.get_path('motivation_letters')) # Use passed config
                    letters_dir_abs = Path(config_instance.get_path('data_root')) / letters_dir_rel # Use passed config
                    letters_dir_abs.mkdir(parents=True, exist_ok=True)
                    scraped_data_filename = f"motivation_letter_{job_title_for_file}_scraped_data.json"
                    scraped_data_abs_path = letters_dir_abs / scraped_data_filename
                    try:
                        with open(scraped_data_abs_path, 'w', encoding='utf-8') as f_scrape:
                            json.dump(job_details, f_scrape, ensure_ascii=False, indent=2)
                        scraped_data_rel_path = str(letters_dir_rel / scraped_data_filename)
                        logger.info(f"Bulk: Saved job details to: {scraped_data_abs_path} (DB path: {scraped_data_rel_path})")
                    except Exception as save_err:
                        logger.error(f"Bulk: Error saving job details JSON to {scraped_data_abs_path}: {save_err}")
                        # Consider if this should add to errors list

                    # --- Calculate Paths and Insert into DB ---
                    has_json = 'motivation_letter_json' in result and 'json_file_path' in result
                    docx_file_path_rel_db = None
                    json_file_path_rel_db = None
                    html_file_path_rel_db = None

                    if has_json:
                        try:
                            abs_json_path = Path(result['json_file_path'])
                            if not abs_json_path.is_absolute(): abs_json_path = Path(app_context.root_path) / result['json_file_path'] # Use app_context
                            json_file_path_rel_db = str(abs_json_path.relative_to(config_instance.get_path('data_root'))) # Use passed config

                            abs_docx_path = abs_json_path.with_suffix('.docx')
                            docx_path = json_to_docx(result['motivation_letter_json'], output_path=str(abs_docx_path))
                            if docx_path:
                                docx_file_path_rel_db = str(Path(docx_path).relative_to(config_instance.get_path('data_root'))) # Use passed config
                                logger.info(f"Bulk: Generated Word document: {docx_path} for URL: {job_url}")
                            else:
                                logger.warning(f"Bulk: Failed to generate Word document for URL: {job_url}")
                        except Exception as docx_e:
                            logger.error(f"Bulk: Exception generating Word document for URL {job_url}: {str(docx_e)}")

                    html_file_path_abs_str = result.get('html_file_path') if has_json else result.get('file_path')
                    if html_file_path_abs_str:
                        abs_html_path = Path(html_file_path_abs_str)
                        if not abs_html_path.is_absolute(): abs_html_path = Path(app_context.root_path) / html_file_path_abs_str # Use app_context
                        html_file_path_rel_db = str(abs_html_path.relative_to(config_instance.get_path('data_root'))) # Use passed config

                    # Insert into database with the database_connection context manager
                    if html_file_path_rel_db or json_file_path_rel_db:
                        with database_connection() as conn:
                            cursor = conn.cursor()
                            try:
                                insert_data = {
                                    "cv_id": cv_id,
                                    "job_match_report_id": None, # No report context in bulk generation
                                    "job_title": job_details.get('Job Title', 'N/A'),
                                    "company_name": company_name_for_db,
                                    "generation_timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "letter_filepath_html": html_file_path_rel_db,
                                    "letter_filepath_json": json_file_path_rel_db,
                                    "letter_filepath_docx": docx_file_path_rel_db,
                                    "scraped_data_filepath": scraped_data_rel_path,
                                    "job_url": job_url # Store job URL
                                }
                                columns = ', '.join(insert_data.keys())
                                placeholders = ', '.join('?' * len(insert_data))
                                sql = f"INSERT INTO MOTIVATION_LETTERS ({columns}) VALUES ({placeholders})"
                                cursor.execute(sql, list(insert_data.values()))
                                # Commit happens automatically when exiting 'with database_connection()' block
                                logger.info(f"Bulk: Successfully inserted DB record for job: {insert_data['job_title']}")
                            except Exception as db_insert_err:
                                logger.error(f"Bulk: DB error inserting record for {job_url}: {db_insert_err}", exc_info=True)
                                # Rollback happens automatically on exception within 'with database_connection()'
                                # Consider adding URL to errors list here?
                                with lock_instance: results_dict['errors'].append(f"{job_url} (DB Insert Error)")
                else: # Handle generation failure
                    error_message = result_or_error if isinstance(result_or_error, str) else "Unknown generation error"
                    logger.error(f"Bulk: Failed to generate letter for URL: {job_url}. Error: {error_message}")
                    with lock_instance: results_dict['errors'].append(f"{job_url} ({error_message})")
            except Exception as e:
                logger.error(f"Bulk: Exception generating letter for URL {job_url}: {str(e)}", exc_info=True)
                with lock_instance: results_dict['errors'].append(job_url)

    # Use ThreadPoolExecutor to manage threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Create futures by submitting tasks
        # Pass necessary context/objects to each task explicitly
        futures = [executor.submit(generate_single_letter_task, app_instance.app_context(), url, cv_summary_text, cv_base_name, config, lock, results) for url in job_urls]

        # Wait for all futures to complete (optional, as executor shutdown waits by default)
        concurrent.futures.wait(futures)
        # Note: Error handling for exceptions raised *within* tasks needs care.
        # The current task catches exceptions and updates the shared 'results' dict.
        # If tasks raised exceptions directly, you'd check future.exception().

    logger.info(f"Multiple letter generation complete. Success: {results['success_count']}, Failures: {len(results['errors'])}")
    return jsonify(results)


@motivation_letter_bp.route('/generate_multiple_emails', methods=['POST'])
def generate_multiple_emails():
    """Generate email texts for multiple selected jobs and update their JSON files using ThreadPoolExecutor."""
    # Define max concurrent workers for bulk email generation
    MAX_WORKERS_EMAIL = 5 # Limit concurrent threads

    data = request.get_json()
    if not data:
        logger.error("Invalid request format for /generate_multiple_emails")
        return jsonify({'error': 'Invalid request format'}), 400

    job_urls = data.get('job_urls')
    cv_base_name = data.get('cv_filename') # This is the relative path

    if not job_urls or not isinstance(job_urls, list) or not cv_base_name:
        logger.error(f"Missing job_urls or cv_filename in request: {data}")
        return jsonify({'error': 'Missing job_urls or cv_filename'}), 400

    logger.info(f"Received request to generate {len(job_urls)} email texts for CV: {cv_base_name}")

    # Load CV summary ONCE using the helper
    cv_summary = current_app.get_cv_summary(cv_base_name)
    if cv_summary is None:
        logger.error(f"Could not load or generate CV summary for {cv_base_name} before starting bulk email generation.")
        return jsonify({'error': f'Could not load or generate CV summary for {cv_base_name}.'}), 500
    logger.info(f"Successfully obtained CV summary for {cv_base_name} for bulk email generation.")

    results = {'success_count': 0, 'errors': [], 'not_found': []}
    lock = threading.Lock()
    app_instance = current_app._get_current_object()
    config = ConfigManager() # Get config instance

    # Define the task function separately
    def generate_and_update_email_task(app_context, job_url, cv_summary_content, cv_base_name_log, config_instance, lock_instance, results_dict):
        """Task to generate email text and update JSON, designed for ThreadPoolExecutor."""
        with app_context(): # Use passed context
            if not job_url or job_url == 'N/A' or not job_url.startswith('http'):
                logger.warning(f"Skipping invalid job URL for email generation: {job_url}")
                with lock_instance: results_dict['errors'].append({'url': job_url, 'reason': 'Invalid URL'})
                return

            try:
                # Load raw data then get details
                raw_scraped_data_email = _load_latest_raw_job_data()
                if raw_scraped_data_email is None:
                    logger.error(f"Email Task: Failed to load raw scraped data for {job_url}.")
                    with lock_instance: results_dict['errors'].append({'url': job_url, 'reason': 'Failed to load job data source'})
                    return

                try:
                    job_details = get_job_details(job_url, raw_scraped_data_email)
                except KeyError:
                    logger.warning(f"Email Task: Job URL {job_url} not found in latest scraped data.")
                    with lock_instance: results_dict['errors'].append({'url': job_url, 'reason': 'Job details not found in pre-scraped data'})
                    return
                except Exception as e_email_fetch:
                    logger.error(f"Email Task: Error getting job_details for {job_url} from scraped data: {e_email_fetch}", exc_info=True)
                    with lock_instance: results_dict['errors'].append({'url': job_url, 'reason': f'Error processing job data: {e_email_fetch}'})
                    return

                if not job_details or not job_details.get('Job Title'): # Check content after successful fetch
                    logger.warning(f"Email Task: Could not get sufficient job details for URL: {job_url} (after fetch).")
                    with lock_instance: results_dict['errors'].append({'url': job_url, 'reason': 'Fetched job details, but content insufficient'})
                    return

                job_title = job_details['Job Title']
                sanitized_job_title = sanitize_filename(job_title)
                # Use config path relative to data_root
                letters_dir_rel = Path(config_instance.get_path('motivation_letters')) # Use passed config
                letters_dir_abs = Path(config_instance.get_path('data_root')) / letters_dir_rel # Use passed config
                json_file_path_abs = letters_dir_abs / f"motivation_letter_{sanitized_job_title}.json"

                logger.info(f"Generating email text for CV '{cv_base_name_log}' and Job '{job_title}' (URL: {job_url})")
                # TODO: Consider adding cancellation check within generate_email_text_only if long-running
                # Function now returns (success, result_or_error)
                success, result_or_error = generate_email_text_only(cv_summary_content, job_details)

                if not success:
                    error_message = result_or_error if isinstance(result_or_error, str) else "Unknown email generation error"
                    logger.error(f"Failed to generate email text for Job: {job_title}. Error: {error_message}")
                    with lock_instance: results_dict['errors'].append({'url': job_url, 'reason': f'Email text generation failed: {error_message}'})
                    return

                # If successful, result_or_error is the email_text string
                email_text = result_or_error
                letter_data = {}
                if json_file_path_abs.is_file():
                    try:
                        with open(json_file_path_abs, 'r', encoding='utf-8') as f:
                            letter_data = json.load(f)
                        logger.info(f"Loaded existing JSON: {json_file_path_abs}")
                    except Exception as load_e:
                        logger.error(f"Error loading existing JSON {json_file_path_abs}: {load_e}. Will overwrite.")
                        letter_data = {} # Reset data if loading fails
                else:
                    logger.info(f"JSON file not found ({json_file_path_abs}), will create new.")
                    # Optionally pre-populate with job title if creating new
                    letter_data['job_title_source'] = job_title # Example field

                letter_data['email_text'] = email_text

                try:
                    letters_dir_abs.mkdir(parents=True, exist_ok=True) # Ensure directory exists
                    with open(json_file_path_abs, 'w', encoding='utf-8') as f:
                        json.dump(letter_data, f, ensure_ascii=False, indent=2)
                    logger.info(f"Successfully updated/created JSON with email text: {json_file_path_abs}")
                    with lock_instance: results_dict['success_count'] += 1
                except Exception as save_e:
                    logger.error(f"Error saving updated JSON {json_file_path_abs}: {save_e}", exc_info=True)
                    with lock_instance: results_dict['errors'].append({'url': job_url, 'reason': f'Failed to save JSON: {save_e}'})

            except Exception as e:
                logger.error(f"Exception generating/updating email text for URL {job_url}: {str(e)}", exc_info=True)
                with lock_instance: results_dict['errors'].append({'url': job_url, 'reason': f'Unexpected error: {e}'})

    # Use ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS_EMAIL) as executor:
        futures = [executor.submit(generate_and_update_email_task, app_instance.app_context(), url, cv_summary, cv_base_name, config, lock, results) for url in job_urls]
        concurrent.futures.wait(futures)

    logger.info(f"Multiple email text generation/update complete. Success: {results['success_count']}, Failures: {len(results['errors'])}")
    return jsonify(results)


@motivation_letter_bp.route('/view/<operation_id>')
def view_motivation_letter(operation_id):
    """View a generated motivation letter (newly generated or existing)"""
    try:
        config = ConfigManager() # Get config
        if operation_id == 'existing':
            # Log incoming arguments for debugging
            logger.info(f"Received request args for /view/existing: {request.args}")
            # Paths passed are relative to data_root from DB
            html_path_rel_db = request.args.get('letter_filepath_html')
            docx_path_rel_db = request.args.get('letter_filepath_docx')
            report_file = request.args.get('report_file') # Still relative to project root? Assume yes for now.

            if not html_path_rel_db:
                flash('Motivation letter HTML path missing')
                return redirect(url_for('index'))

            # Construct absolute path for reading
            html_full_path = Path(config.get_path('data_root')) / html_path_rel_db
            if not html_full_path.is_file():
                flash(f'Motivation letter file not found: {html_path_rel_db}')
                return redirect(url_for('index'))

            with open(html_full_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            job_title_guess = html_full_path.stem.replace('motivation_letter_', '').replace('_', ' ')
            job_details = {'Job Title': job_title_guess, 'Application URL': '#'}

            # Convert paths back to relative to project root for template links
            html_path_rel_ui = str(html_full_path.relative_to(current_app.root_path))
            docx_path_rel_ui = None
            if docx_path_rel_db:
                 docx_full_path = Path(config.get_path('data_root')) / docx_path_rel_db
                 docx_path_rel_ui = str(docx_full_path.relative_to(current_app.root_path))

            return render_template('motivation_letter.html',
                                  motivation_letter=html_content,
                                  file_path=html_path_rel_ui, # Use path relative to project root for link
                                  has_docx=bool(docx_path_rel_ui),
                                  docx_file_path=docx_path_rel_ui, # Use path relative to project root for link
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

        # Paths in result are already relative to project root (for UI)
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
    """Download a generated motivation letter (HTML version using relative path from project root)"""
    file_path_rel = request.args.get('file_path') # Expecting path relative to project root

    if not file_path_rel:
        flash('No file path provided for HTML download')
        return redirect(url_for('index'))

    try:
        full_path = Path(current_app.root_path) / file_path_rel # Construct absolute path
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
    """Download a generated motivation letter (Word document version using relative path from project root)"""
    file_path_rel = request.args.get('file_path') # Expecting path relative to project root

    if not file_path_rel:
        flash('No file path provided for DOCX download')
        return redirect(url_for('index'))

    try:
        full_path = Path(current_app.root_path) / file_path_rel # Construct absolute path
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
    """Generate (if needed) and download DOCX from JSON file path (relative to project root)"""
    json_file_path_rel = request.args.get('json_file_path') # Expecting path relative to project root

    if not json_file_path_rel:
        flash('No JSON file path provided')
        return redirect(url_for('index'))

    try:
        json_full_path = Path(current_app.root_path) / json_file_path_rel # Construct absolute path
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
        config = ConfigManager()
        # Construct path relative to data_root
        letters_dir_rel = Path(config.get_path('motivation_letters'))
        file_path_rel_db = letters_dir_rel / scraped_data_filename
        file_path_abs = Path(config.get_path('data_root')) / file_path_rel_db

        if not file_path_abs.is_file():
            flash(f'Scraped job data file not found: {scraped_data_filename}')
            logger.error(f"Scraped job data file not found: {file_path_abs}")
            return redirect(url_for('index'))

        with open(file_path_abs, 'r', encoding='utf-8') as f:
            job_details = json.load(f)

        return render_template('scraped_data_view.html', job_details=job_details, filename=scraped_data_filename)

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
    """View the generated email text from a JSON file (path relative to project root)."""
    json_path_rel_ui = request.args.get('letter_filepath_json') # Expecting path relative to project root
    report_file = request.args.get('report_file') # Optional, for back button context

    if not json_path_rel_ui:
        flash('Motivation letter JSON path missing')
        logger.error("Missing json_path for viewing email text.")
        return redirect(url_for('index'))

    try:
        json_full_path = Path(current_app.root_path) / json_path_rel_ui # Construct absolute path
        if not json_full_path.is_file():
            flash(f'Motivation letter JSON file not found: {json_path_rel_ui}')
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
             logger.warning(f"No 'email_text' found or text is empty in {json_path_rel_ui}")
             email_text = None # Ensure it's None if empty for template logic

        return render_template('email_text_view.html',
                               email_text=email_text,
                               report_file=report_file) # Pass report_file for potential back button logic

    except json.JSONDecodeError:
        flash(f'Error decoding JSON from file: {json_path_rel_ui}')
        logger.error(f"JSONDecodeError for email text view: {json_path_rel_ui}")
        if report_file:
             return redirect(url_for('job_matching.view_results', report_file=report_file))
        else:
             return redirect(url_for('index'))
    except Exception as e:
        flash(f'Error viewing email text: {str(e)}')
        logger.error(f'Error viewing email text from {json_path_rel_ui}: {str(e)}', exc_info=True)
        if report_file:
             return redirect(url_for('job_matching.view_results', report_file=report_file))
        else:
             return redirect(url_for('index'))


@motivation_letter_bp.route('/delete/<json_filename>')
def delete_letter_set(json_filename):
    """Delete a generated letter JSON and its associated HTML, DOCX, and scraped data files."""
    # Use database_connection context manager
    try:
        config = ConfigManager()
        with database_connection() as conn: # Use context manager
            cursor = conn.cursor()

            # Assume json_filename is just the filename part passed from the URL
            # We need to find the record in the DB using LIKE based on the filename ending
            db_json_path_pattern = '%' + json_filename # Pattern for LIKE query

            cursor.execute("SELECT id, letter_filepath_html, letter_filepath_json, letter_filepath_docx, scraped_data_filepath FROM MOTIVATION_LETTERS WHERE letter_filepath_json LIKE ?", (db_json_path_pattern,))
            record = cursor.fetchone()

            if not record:
                flash(f"Could not find database record for file ending with {json_filename}", "warning")
                logger.warning(f"Delete request: DB record not found for json_file_path LIKE '{db_json_path_pattern}'")
                # Context manager handles closing connection
                return redirect(url_for('index'))

            record_id, html_rel_db, json_rel_db, docx_rel_db, scraped_rel_db = record
            data_root = Path(config.get_path('data_root'))
            deleted_files = []
            error_files = []

            # Attempt to delete each file using paths relative to data_root
            for file_rel_db in [json_rel_db, html_rel_db, docx_rel_db, scraped_rel_db]:
                if file_rel_db: # Check if path exists in DB record
                    file_abs_path = data_root / file_rel_db
                    if file_abs_path.is_file():
                        try:
                            os.remove(file_abs_path)
                            deleted_files.append(Path(file_rel_db).name)
                            logger.info(f"Deleted file: {file_abs_path}")
                        except Exception as e:
                            error_files.append(Path(file_rel_db).name)
                            logger.error(f"Error deleting file {file_abs_path}: {e}")
                            flash(f"Error deleting file {Path(file_rel_db).name}: {e}", "danger")
                    else:
                        logger.debug(f"File not found for deletion (this is okay): {file_abs_path}")

            # Delete the database record
            try:
                cursor.execute("DELETE FROM MOTIVATION_LETTERS WHERE id = ?", (record_id,))
                # Commit happens automatically when exiting 'with database_connection()' block
                logger.info(f"Deleted MOTIVATION_LETTERS record with id: {record_id}")
                if not error_files:
                     flash(f"Successfully deleted letter and associated files for record ID {record_id}", "success")
                else:
                     flash(f"Deleted database record ID {record_id}, but failed to delete files: {', '.join(error_files)}", "warning")

            except Exception as db_del_err:
                # Rollback happens automatically on exception within 'with' block
                logger.error(f"Error deleting MOTIVATION_LETTERS record ID {record_id}: {db_del_err}", exc_info=True)
                flash(f"Successfully deleted files: {', '.join(deleted_files)}, but failed to delete database record: {db_del_err}", "danger")

    except Exception as e:
        flash(f"An unexpected error occurred during deletion: {str(e)}", "danger")
        logger.error(f"Error in delete_letter_set for {json_filename}: {str(e)}", exc_info=True)
        # Rollback is handled by the context manager on exception
    # finally block is handled by the context manager

    # Redirect back to the main dashboard index
    return redirect(url_for('index'))

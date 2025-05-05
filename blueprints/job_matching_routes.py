import os
import json
import logging
import threading
import urllib.parse
import importlib.util
import sqlite3
from pathlib import Path
from datetime import datetime
import math # Added for pagination calculation
from flask import (
    Blueprint, request, redirect, url_for, flash, render_template,
    send_file, jsonify, current_app, abort # Added abort
)
from werkzeug.utils import secure_filename
from config import config # Import config object
from utils.database_utils import database_connection # Added

# Add project root to path to find modules
import sys
sys.path.append('.')

# Import necessary functions from other modules
from job_matcher import match_jobs_with_cv, generate_report
# Assuming get_job_details_for_url might be needed and moved to a utils module or kept in main app
# from dashboard import get_job_details_for_url # Example

job_matching_bp = Blueprint('job_matching', __name__, url_prefix='/job_matching')

logger = logging.getLogger("dashboard.job_matching") # Use a child logger

# Placeholder for get_job_details_for_url if it's moved/shared
# This function is complex and might be better in a dedicated 'utils' or 'helpers' module
# For now, assume it might be attached to current_app or imported from its final location.
def get_job_details_for_url(job_url):
    """Placeholder: Get job details for a URL from the latest job data file"""
    # This function needs access to the job data directory and logic from the original dashboard.
    # It should ideally be refactored into a shared utility.
    # For now, we'll try accessing it via current_app if attached there, or raise NotImplementedError.
    if hasattr(current_app, 'get_job_details_for_url'):
        return current_app.get_job_details_for_url(job_url)
    else:
        # Fallback or raise error - depends on where the function ends up
        logger.warning("get_job_details_for_url not found on current_app, using basic implementation.")
        # Basic implementation attempt (might fail depending on context)
        job_details = {}
        try:
            job_id = job_url.split('/')[-1]
            # Use getattr for safer access to current_app properties in fallback
            root_path = getattr(current_app, 'root_path', '.')
            job_data_dir = Path(root_path) / 'job-data-acquisition/job-data-acquisition/data'
            if job_data_dir.exists():
                job_data_files = list(job_data_dir.glob('job_data_*.json'))
                if job_data_files:
                    latest_job_data_file = max(job_data_files, key=os.path.getctime)
                    with open(latest_job_data_file, 'r', encoding='utf-8') as f:
                        job_data = json.load(f)
                    job_listings = []
                    if isinstance(job_data, list):
                         if len(job_data) > 0:
                            if isinstance(job_data[0], list):
                                for job_array in job_data: job_listings.extend(job_array)
                            elif isinstance(job_data[0], dict) and 'content' in job_data[0]:
                                job_listings = job_data[0]['content']
                            else: job_listings = job_data
                    for job in job_listings:
                        job_application_url = job.get('Application URL', '')
                        if job_id in job_application_url:
                            job_details = job
                            break
                    if not job_details and job_listings: job_details = job_listings[0]
        except Exception as e:
            logger.error(f'Error in fallback get_job_details_for_url: {str(e)}')
        return job_details
        # raise NotImplementedError("get_job_details_for_url needs to be provided or refactored.")


@job_matching_bp.route('/run_matcher', methods=['POST'])
def run_job_matcher():
    """Run the job matcher with the selected CV"""
    cv_path_rel = request.form.get('cv_path') # This is the relative path from the form
    min_score = int(request.form.get('min_score', 3))
    max_jobs = int(request.form.get('max_jobs', 50))
    max_results = int(request.form.get('max_results', 10))

    if not cv_path_rel:
        flash('No CV selected')
        return redirect(url_for('index'))

    # Construct the full path to the CV relative to the app root
    # Use config to get the base CV data directory
    cv_base_dir = config.get_path('cv_data')
    if not cv_base_dir:
        flash('Configuration error: CV data directory not found.', 'error')
        logger.error("Configuration error: 'cv_data' path not found in config for job matching.")
        return redirect(url_for('index'))
    full_cv_path = cv_base_dir / cv_path_rel # Use Path object joining

    if not full_cv_path.is_file(): # Use Path object check
         flash(f'CV file not found at expected location: {full_cv_path}')
         logger.error(f"CV file not found for matching: {full_cv_path} (relative path was {cv_path_rel})")
         return redirect(url_for('index'))

    try:
        # Access operation tracking functions
        start_operation = current_app.extensions['start_operation']
        update_operation_progress = current_app.extensions['update_operation_progress']
        complete_operation = current_app.extensions['complete_operation']
        app_instance = current_app._get_current_object() # Get app instance for context

        # Create a cancellation event
        cancel_event = threading.Event()
        # Start tracking the operation, passing the event
        operation_id = start_operation('job_matching', cancel_event=cancel_event)

        # Define a function to run the job matcher in a background thread
        def run_job_matcher_task(app, op_id, cv_full_path_task, cv_path_rel_task, min_score_task, max_jobs_task, max_results_task, cancel_event_task):
             with app.app_context(): # Establish app context for the thread
                try:
                    # Update status
                    update_operation_progress(op_id, 10, 'processing', 'Loading job data and starting matching...')

                    # --- Cancellation Check 1 ---
                    if cancel_event_task.is_set():
                        logger.info(f"Operation {op_id} (job_matching) cancelled before matching.")
                        complete_operation(op_id, 'cancelled', 'Operation cancelled by user.')
                        return

                    # Match jobs with CV - pass both max_jobs and max_results
                    # Pass the absolute path as a string
                    # TODO: Consider adding cancellation check *within* match_jobs_with_cv if it's very long-running
                    matches = match_jobs_with_cv(str(cv_full_path_task), min_score=min_score_task, max_jobs=max_jobs_task, max_results=max_results_task)

                    # --- Cancellation Check 2 ---
                    if cancel_event_task.is_set():
                        logger.info(f"Operation {op_id} (job_matching) cancelled after matching.")
                        complete_operation(op_id, 'cancelled', 'Operation cancelled by user.')
                        return

                    if not matches:
                        complete_operation(op_id, 'completed', 'No job matches found') # Use complete_operation
                        return

                    # Update status
                    update_operation_progress(op_id, 80, 'processing', 'Adding CV path to matches and generating report...')

                    # Add cv_path (relative path is fine here for identification) to each match dictionary before saving
                    for match in matches:
                        match['cv_path'] = cv_path_rel_task # Store the relative path used for matching identification

                    # --- Cancellation Check 3 ---
                    if cancel_event_task.is_set():
                        logger.info(f"Operation {op_id} (job_matching) cancelled before generating report.")
                        complete_operation(op_id, 'cancelled', 'Operation cancelled by user.')
                        return

                    # Generate report (which now includes cv_path in the saved JSON)
                    # TODO: Consider adding cancellation check *within* generate_report if it's long-running
                    report_file_path = generate_report(matches) # Returns full path
                    report_filename = os.path.basename(report_file_path) # report_file_path is absolute

                    # --- Cancellation Check 4 ---
                    if cancel_event_task.is_set():
                        logger.info(f"Operation {op_id} (job_matching) cancelled before database insertion.")
                        complete_operation(op_id, 'cancelled', 'Operation cancelled by user.')
                        # Note: Report files might exist. Cleanup?
                        return

                    # --- Database Insertion ---
                    try:
                        report_timestamp = datetime.now().isoformat()
                        data_root = config.get_path('data_root')
                        if not data_root:
                            raise ValueError("Configuration error: 'data_root' path not found in config.")

                        report_path_md_abs = Path(report_file_path)
                        report_path_json_abs = report_path_md_abs.with_suffix('.json')

                        report_filepath_md_rel = str(report_path_md_abs.relative_to(data_root)).replace('\\', '/')
                        report_filepath_json_rel = str(report_path_json_abs.relative_to(data_root)).replace('\\', '/')

                        parameters_used = json.dumps({
                            'min_score': min_score_task,
                            'max_jobs': max_jobs_task,
                            'max_results': max_results_task
                        })
                        match_count = len(matches)

                        cv_id = None
                        job_data_batch_id = None

                        with database_connection() as conn:
                            cursor = conn.cursor()
                            # Get CV ID
                            cursor.execute("SELECT id FROM CVS WHERE original_filepath = ?", (cv_path_rel_task,))
                            cv_row = cursor.fetchone()
                            if cv_row:
                                cv_id = cv_row['id']
                            else:
                                logger.warning(f"Could not find CV ID for path: {cv_path_rel_task}")

                            # Get latest Job Data Batch ID (assuming matcher uses latest)
                            cursor.execute("SELECT id FROM JOB_DATA_BATCHES ORDER BY batch_timestamp DESC LIMIT 1")
                            batch_row = cursor.fetchone()
                            if batch_row:
                                job_data_batch_id = batch_row['id']
                            else:
                                logger.warning("Could not find any job data batch ID.")

                            # Insert report record
                            cursor.execute("""
                                INSERT INTO JOB_MATCH_REPORTS (
                                    report_timestamp, report_filepath_json, report_filepath_md,
                                    cv_id, job_data_batch_id, parameters_used, match_count
                                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (
                                report_timestamp, report_filepath_json_rel, report_filepath_md_rel,
                                cv_id, job_data_batch_id, parameters_used, match_count
                            ))
                        logger.info(f"Successfully added job match report record to database: {report_filepath_md_rel}")

                        # --- Final Cancellation Check ---
                        if cancel_event_task.is_set():
                            logger.info(f"Operation {op_id} (job_matching) cancelled just before final completion.")
                            complete_operation(op_id, 'cancelled', 'Operation cancelled by user.')
                            # Note: DB record inserted. Cleanup?
                            return

                        complete_operation(op_id, 'completed', f'Job matching completed and recorded. Report: {report_filename}')

                    except Exception as db_err:
                        logger.error(f"Database error adding job match report record for {report_filename}: {db_err}", exc_info=True)
                        # Check cancellation status before reporting error type
                        if cancel_event_task.is_set():
                            complete_operation(op_id, 'cancelled', f'Operation cancelled during DB error: {db_err}')
                        else:
                            # Still report completion, but mention DB error
                            complete_operation(op_id, 'completed_with_errors', f'Job matching completed, but failed to record in database. Report: {report_filename}. Error: {db_err}')
                    # --- End Database Insertion ---

                except Exception as e:
                    logger.error(f'Error in job matcher task: {str(e)}', exc_info=True)
                    # Check cancellation status before reporting failure
                    if cancel_event_task.is_set():
                        complete_operation(op_id, 'cancelled', f'Operation cancelled during error: {str(e)}')
                    else:
                        complete_operation(op_id, 'failed', f'Error running job matcher: {str(e)}')

        # Start the background thread, passing app instance, args, and cancel_event
        # Pass the absolute path as a Path object
        thread_args = (app_instance, operation_id, full_cv_path, cv_path_rel, min_score, max_jobs, max_results, cancel_event)
        thread = threading.Thread(target=run_job_matcher_task, args=thread_args)
        thread.daemon = True
        thread.start()

        # Return immediately with the operation ID
        flash(f'Job matcher started. Please wait while the results are being processed. (operation_id={operation_id})')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'Error running job matcher: {str(e)}')
        logger.error(f'Error running job matcher: {str(e)}', exc_info=True)
        return redirect(url_for('index'))

@job_matching_bp.route('/run_combined', methods=['POST'])
def run_combined_process():
    """Run both job data acquisition and job matcher in one go"""
    try:
        # Get parameters from the form
        cv_path_rel = request.form.get('cv_path')
        max_pages = int(request.form.get('max_pages', 50))
        min_score = int(request.form.get('min_score', 3))
        max_jobs = int(request.form.get('max_jobs', 50))
        max_results = int(request.form.get('max_results', 10))

        if not cv_path_rel:
            flash('No CV selected')
            return redirect(url_for('index'))

        # Construct the full path to the CV using config
        cv_base_dir = config.get_path('cv_data')
        if not cv_base_dir:
            flash('Configuration error: CV data directory not found.', 'error')
            logger.error("Configuration error: 'cv_data' path not found in config for combined process.")
            return redirect(url_for('index'))
        full_cv_path = cv_base_dir / cv_path_rel # Use Path object joining

        if not full_cv_path.is_file(): # Use Path object check
             flash(f'CV file not found at expected location: {full_cv_path}')
             logger.error(f"CV file not found for combined process: {full_cv_path} (relative path was {cv_path_rel})")
             return redirect(url_for('index'))

        # Access operation tracking functions
        start_operation = current_app.extensions['start_operation']
        update_operation_progress = current_app.extensions['update_operation_progress']
        complete_operation = current_app.extensions['complete_operation']
        app_instance = current_app._get_current_object() # Get app instance for context

        # Create cancellation event
        cancel_event = threading.Event()
        # Start tracking the operation, passing the event
        operation_id = start_operation('combined_process', cancel_event=cancel_event)

        # Define a function to run the combined process in a background thread
        # Pass necessary variables, app instance, and cancel_event
        def run_combined_process_task(app, op_id, cv_full_path_task, cv_path_rel_task, max_pages_task, min_score_task, max_jobs_task, max_results_task, cancel_event_task):
            with app.app_context(): # Establish app context for the thread
                try:
                    # Access operation status via app extensions now that context exists
                    operation_status_ctx = app.extensions['operation_status']

                    # Update status (use op_id passed to function)
                    update_operation_progress(op_id, 5, 'processing', 'Updating settings...')

                    # Step 1: Update the settings.json file with the max_pages parameter
                    # Use config to get settings path
                    settings_path = config.get_path('settings_json')
                    if not settings_path:
                        logger.error("Configuration error: 'settings_json' path not found in config.")
                        complete_operation(op_id, 'failed', 'Scraper settings file path not configured.')
                        return
                    try:
                        with open(settings_path, 'r', encoding='utf-8') as f: settings = json.load(f)
                        settings['scraper']['max_pages'] = max_pages_task # Use passed variable
                        with open(settings_path, 'w', encoding='utf-8') as f: json.dump(settings, f, indent=4, ensure_ascii=False)
                    except Exception as settings_e:
                        logger.error(f"Error updating settings for combined run: {settings_e}")
                        complete_operation(op_id, 'failed', f'Error updating scraper settings: {settings_e}')
                        return

                    # --- Cancellation Check 1 ---
                    if cancel_event_task.is_set():
                        logger.info(f"Operation {op_id} (combined) cancelled before starting scraper.")
                        complete_operation(op_id, 'cancelled', 'Operation cancelled by user.')
                        return

                    # Update status
                    update_operation_progress(op_id, 10, 'processing', 'Starting job scraper...')

                    # Step 2: Run the job scraper
                    output_file = None
                    try:
                        # Use config to get job data acquisition path
                        job_data_acq_path = config.get_path('job_data_acquisition')
                        if not job_data_acq_path:
                             logger.error("Configuration error: 'job_data_acquisition' path not found in config.")
                             raise FileNotFoundError("Job data acquisition path not configured.")
                        app_path = job_data_acq_path / 'app.py' # Use Path object joining

                        if not app_path.is_file(): # Use Path object check
                             raise FileNotFoundError(f"Scraper app.py not found at {app_path}")
                        spec = importlib.util.spec_from_file_location("app_module", str(app_path)) # Pass path as string
                        app_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(app_module)
                        run_scraper = getattr(app_module, 'run_scraper', None)
                        if run_scraper:
                            # TODO: Consider adding cancellation support *within* run_scraper if possible
                            output_file = run_scraper() # run_scraper should return the output file path
                        else:
                             raise ModuleNotFoundError("run_scraper function not found in job-data-acquisition/app.py")
                    except Exception as scraper_e:
                         logger.error(f"Error running scraper in combined process: {scraper_e}", exc_info=True)
                         # Check cancellation status before reporting failure
                         if cancel_event_task.is_set():
                             complete_operation(op_id, 'cancelled', f'Operation cancelled during scraper run: {scraper_e}')
                         else:
                             complete_operation(op_id, 'failed', f'Job data acquisition failed: {scraper_e}')
                         return

                    # --- Cancellation Check 2 ---
                    if cancel_event_task.is_set():
                        logger.info(f"Operation {op_id} (combined) cancelled after scraper finished.")
                        complete_operation(op_id, 'cancelled', 'Operation cancelled by user.')
                        # Note: Scraper output file might exist. Cleanup?
                        return

                    if output_file is None:
                        # Check cancellation status before reporting failure
                        if cancel_event_task.is_set():
                             complete_operation(op_id, 'cancelled', 'Operation cancelled (scraper returned no output file).')
                        else:
                             complete_operation(op_id, 'failed', 'Job data acquisition failed (no output file). Check logs.')
                        return

                    # --- Insert Job Data Batch Record ---
                    job_data_batch_id = None # Initialize batch ID
                    try:
                        data_root = config.get_path('data_root')
                        if not data_root:
                            raise ValueError("Configuration error: 'data_root' path not found in config.")

                        absolute_output_path = Path(output_file)
                        # Ensure output_file path is absolute relative to data_root if needed
                        # Assuming run_scraper returns path relative to job-data-acquisition dir
                        if not absolute_output_path.is_absolute():
                            job_data_acq_path = config.get_path('job_data_acquisition')
                            if job_data_acq_path:
                                absolute_output_path = (job_data_acq_path / output_file).resolve()
                            else: # Fallback if job_data_acquisition path is missing
                                absolute_output_path = (Path(app.root_path) / 'job-data-acquisition' / output_file).resolve()


                        relative_data_filepath = str(absolute_output_path.relative_to(data_root)).replace('\\', '/')
                        batch_timestamp = datetime.now().isoformat() # Use current time

                        # Re-read settings to ensure we capture the state used for the run
                        with open(settings_path, 'r', encoding='utf-8') as f:
                            settings_for_run = json.load(f)

                        source_urls_json = json.dumps(settings_for_run.get('target_urls', []))
                        settings_used_json = json.dumps(settings_for_run.get('scraper', {}))

                        with database_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                INSERT INTO JOB_DATA_BATCHES (batch_timestamp, source_urls, data_filepath, settings_used)
                                VALUES (?, ?, ?, ?)
                            """, (batch_timestamp, source_urls_json, relative_data_filepath, settings_used_json))
                            job_data_batch_id = cursor.lastrowid # Get the ID of the inserted row
                            logger.info(f"Successfully added job data batch record (ID: {job_data_batch_id}) to database from combined run: {relative_data_filepath}") # Corrected indentation

                    except Exception as db_batch_err:
                        logger.error(f"Database error adding job data batch record from combined run for {output_file}: {db_batch_err}", exc_info=True)
                        # Check cancellation status before reporting warning/error
                        if cancel_event_task.is_set():
                            complete_operation(op_id, 'cancelled', f'Operation cancelled during batch DB insert: {db_batch_err}')
                            return # Stop processing if cancelled here
                        else:
                            # Log the error but proceed to matching if possible, the report won't be linked though.
                            update_operation_progress(op_id, 55, 'warning', 'Scraping done, but failed to record batch in DB.')

                    # --- Cancellation Check 3 ---
                    if cancel_event_task.is_set():
                        logger.info(f"Operation {op_id} (combined) cancelled before starting matcher.")
                        complete_operation(op_id, 'cancelled', 'Operation cancelled by user.')
                        return

                    # Update status
                    update_operation_progress(op_id, 60, 'processing', 'Job data acquisition completed. Starting job matcher...')

                    # Step 3: Run the job matcher with the newly acquired data
                    # Pass absolute path as string
                    # TODO: Consider adding cancellation check *within* match_jobs_with_cv if it's very long-running
                    matches = match_jobs_with_cv(str(cv_full_path_task), min_score=min_score_task, max_jobs=max_jobs_task, max_results=max_results_task) # Use passed variables

                    # --- Cancellation Check 4 ---
                    if cancel_event_task.is_set():
                        logger.info(f"Operation {op_id} (combined) cancelled after matching.")
                        complete_operation(op_id, 'cancelled', 'Operation cancelled by user.')
                        return

                    if not matches:
                        # Check cancellation status before reporting completion
                        if cancel_event_task.is_set():
                             complete_operation(op_id, 'cancelled', 'Operation cancelled (no matches found).')
                        else:
                             complete_operation(op_id, 'completed', 'No job matches found after scraping')
                        return

                    # Update status
                    update_operation_progress(op_id, 90, 'processing', 'Generating report...')

                    # Add relative cv_path for identification
                    for match in matches:
                        match['cv_path'] = cv_path_rel_task # Use passed variable

                    # --- Cancellation Check 5 ---
                    if cancel_event_task.is_set():
                        logger.info(f"Operation {op_id} (combined) cancelled before generating report.")
                        complete_operation(op_id, 'cancelled', 'Operation cancelled by user.')
                        return

                    # Step 4: Generate report
                    # TODO: Consider adding cancellation check *within* generate_report if it's long-running
                    report_file_path = generate_report(matches)
                    report_filename = os.path.basename(report_file_path) # report_file_path is absolute

                    # --- Cancellation Check 6 ---
                    if cancel_event_task.is_set():
                        logger.info(f"Operation {op_id} (combined) cancelled before report DB insertion.")
                        complete_operation(op_id, 'cancelled', 'Operation cancelled by user.')
                        # Note: Report files might exist. Cleanup?
                        return

                    # --- Database Insertion for Report ---
                    try:
                        report_timestamp = datetime.now().isoformat()
                        data_root = config.get_path('data_root') # Re-get data_root just in case
                        if not data_root:
                            raise ValueError("Configuration error: 'data_root' path not found in config.")

                        report_path_md_abs = Path(report_file_path)
                        report_path_json_abs = report_path_md_abs.with_suffix('.json')

                        report_filepath_md_rel = str(report_path_md_abs.relative_to(data_root)).replace('\\', '/')
                        report_filepath_json_rel = str(report_path_json_abs.relative_to(data_root)).replace('\\', '/')

                        parameters_used = json.dumps({
                            'max_pages': max_pages_task, # Include scraper param for combined run
                            'min_score': min_score_task,
                            'max_jobs': max_jobs_task,
                            'max_results': max_results_task
                        })
                        match_count = len(matches)

                        cv_id = None
                        # job_data_batch_id is already captured above after inserting the batch record

                        with database_connection() as conn:
                            cursor = conn.cursor()
                            # Get CV ID
                            cursor.execute("SELECT id FROM CVS WHERE original_filepath = ?", (cv_path_rel_task,))
                            cv_row = cursor.fetchone()
                            if cv_row:
                                cv_id = cv_row['id']
                            else:
                                logger.warning(f"Could not find CV ID for path: {cv_path_rel_task}")

                            # Use the captured job_data_batch_id
                            if not job_data_batch_id:
                                logger.warning("Job data batch ID was not captured successfully earlier in the combined run.")

                            # Insert report record
                            cursor.execute("""
                                INSERT INTO JOB_MATCH_REPORTS (
                                    report_timestamp, report_filepath_json, report_filepath_md,
                                    cv_id, job_data_batch_id, parameters_used, match_count
                                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (
                                report_timestamp, report_filepath_json_rel, report_filepath_md_rel,
                                cv_id, job_data_batch_id, parameters_used, match_count
                            ))
                        logger.info(f"Successfully added job match report record to database: {report_filepath_md_rel}")

                        # --- Final Cancellation Check ---
                        if cancel_event_task.is_set():
                            logger.info(f"Operation {op_id} (combined) cancelled just before final completion.")
                            complete_operation(op_id, 'cancelled', 'Operation cancelled by user.')
                            # Note: DB records inserted. Cleanup?
                            return

                        complete_operation(op_id, 'completed', f'Combined process completed and recorded. Report: {report_filename}')

                        # Store the report file in the operation status for retrieval (if needed elsewhere)
                        if op_id in operation_status_ctx:
                             operation_status_ctx[op_id]['report_file'] = report_filename # Use filename

                    except Exception as db_err:
                        logger.error(f"Database error adding job match report record for {report_filename}: {db_err}", exc_info=True)
                        # Check cancellation status before reporting error type
                        if cancel_event_task.is_set():
                            complete_operation(op_id, 'cancelled', f'Operation cancelled during report DB insert: {db_err}')
                        else:
                            # Still report completion, but mention DB error
                            complete_operation(op_id, 'completed_with_errors', f'Combined process completed, but failed to record in database. Report: {report_filename}. Error: {db_err}')
                    # --- End Database Insertion for Report ---

                except Exception as e:
                    logger.error(f'Error in combined process task: {str(e)}', exc_info=True)
                    # Check cancellation status before reporting failure
                    if cancel_event_task.is_set():
                        complete_operation(op_id, 'cancelled', f'Operation cancelled during error: {str(e)}')
                    else:
                        complete_operation(op_id, 'failed', f'Error running combined process: {str(e)}')

        # Start the background thread, passing necessary arguments including app instance and cancel_event
        # Pass absolute path as Path object
        thread_args = (app_instance, operation_id, full_cv_path, cv_path_rel, max_pages, min_score, max_jobs, max_results, cancel_event)
        thread = threading.Thread(target=run_combined_process_task, args=thread_args)
        thread.daemon = True
        thread.start()

        # Return immediately with the operation ID
        flash(f'Combined process started. Please wait. (operation_id={operation_id})')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'Error running combined process: {str(e)}')
        logger.error(f'Error running combined process: {str(e)}', exc_info=True)
        return redirect(url_for('index'))


@job_matching_bp.route('/view_results/<report_file>')
def view_results(report_file):
    """View job match results with pagination."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int) # Default 20 items per page
    except ValueError:
        abort(404) # Invalid page/per_page format

    # Secure the report filename
    secure_report_file = secure_filename(report_file)
    # Use config to get paths
    report_dir = config.get_path('job_matches')
    if not report_dir:
        flash("Configuration error: Job matches directory not found.", "error")
        logger.error("Configuration error: 'job_matches' path not found in config.")
        return redirect(url_for('index'))

    json_file = secure_report_file.replace('.md', '.json')
    json_path = report_dir / json_file # Use Path object joining

    try:
        # Get list of available CVs from DB
        available_cvs_data = []
        try:
            with database_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, original_filename, original_filepath FROM CVS ORDER BY original_filename")
                available_cvs_data = cursor.fetchall()
        except Exception as db_err:
            logger.error(f"Error fetching CVs for dropdown: {db_err}", exc_info=True)
            # Continue without CV list if DB fails

        # Load the job matches from the JSON file
        if not json_path.is_file(): # Use Path object check
            flash(f"Report JSON file not found: {json_file}")
            logger.error(f"Report JSON file not found: {json_path}")
            return redirect(url_for('index'))

        with open(json_path, 'r', encoding='utf-8') as f:
            all_matches = json.load(f) # Load all matches first

        # --- Pagination Logic ---
        total_matches = len(all_matches)
        total_pages = math.ceil(total_matches / per_page)
        start_index = (page - 1) * per_page
        end_index = start_index + per_page
        paginated_matches = all_matches[start_index:end_index]

        if page > total_pages and total_matches > 0:
             # Requested page is out of bounds
             logger.warning(f"Requested page {page} is out of bounds for report {secure_report_file} (Total pages: {total_pages})")
             abort(404) # Or redirect to last page? abort seems cleaner.
        # --- End Pagination Logic ---


        # Determine associated CV filename from the 'cv_path' stored in the *first* match (if any)
        associated_cv_rel_path = None
        associated_cv_filename = None
        # Check all_matches for the CV path, not just the paginated ones
        if all_matches and isinstance(all_matches, list) and len(all_matches) > 0 and isinstance(all_matches[0], dict) and 'cv_path' in all_matches[0]:
            associated_cv_rel_path = all_matches[0]['cv_path']
            # Find the corresponding original filename from the DB data
            for cv_data in available_cvs_data:
                if cv_data['original_filepath'] == associated_cv_rel_path:
                    associated_cv_filename = cv_data['original_filename']
                    logger.info(f"Associated CV '{associated_cv_filename}' ({associated_cv_rel_path}) for report {json_file}")
                    break
            if not associated_cv_filename:
                 logger.warning(f"Could not find original filename for CV path '{associated_cv_rel_path}' in report {json_file}")
                 # Fallback to using the path itself if filename not found
                 associated_cv_filename = associated_cv_rel_path


        # --- Check for generated files for each match ---
        letters_dir = config.get_path('motivation_letters')
        if not letters_dir:
            logger.error("Configuration error: 'motivation_letters' path not found. Cannot check generated files.")
            letters_dir = Path() # Assign empty path to prevent errors below, but checks will fail

        existing_scraped = list(letters_dir.glob('*_scraped_data.json')) if letters_dir.exists() else []

        logger.info(f"Checking for generated files in {letters_dir}: {len(existing_scraped)} scraped files found.")

        # Process only the matches for the current page
        for match in paginated_matches:
            # Normalize match_app_url (assuming 'application_url' is the key)
            match_app_url = match.get('application_url')
            if match_app_url and match_app_url != 'N/A':
                if match_app_url.startswith('/'):
                    # Assuming base URL for relative paths if needed
                    base_url = "https://www.ostjob.ch/" # Consider making this configurable
                    match_app_url = urllib.parse.urljoin(base_url, match_app_url.lstrip('/'))
            else:
                match_app_url = None

            # Initialize flags
            match.update({
                'has_motivation_letter': False,
                'motivation_letter_html_path': None, # Store relative path for URL generation
                'motivation_letter_json_path': None, # Store relative path
                'motivation_letter_docx_path': None, # Store relative path
                'has_email_text': False, # NEW: Flag for email text existence
                'has_scraped_data': False,
                'scraped_data_filename': None, # Store filename for URL generation
            })

            if not match_app_url:
                continue

            # --- URL Matching Logic (Primary Method) ---
            # Define sanitize_filename helper here or move to a shared utils module
            def sanitize_filename(name, length=30):
                # Allow alphanumeric, space, underscore, hyphen. Replace others with underscore.
                sanitized = ''.join(c if c.isalnum() or c in [' ', '_', '-'] else '_' for c in name)
                # Replace spaces with underscores
                sanitized = sanitized.replace(' ', '_')
                # Limit length
                return sanitized[:length]

            # Normalize URLs function (Improved)
            def normalize_url(url):
                """Normalizes URL for comparison: removes scheme, www., trailing slash, query params."""
                if not url: return ""
                try:
                    # Ensure scheme if missing (needed for urlparse)
                    if not url.startswith(('http://', 'https://')):
                        url = 'http://' + url # Add default scheme

                    parsed = urllib.parse.urlparse(url)
                    netloc = parsed.netloc.replace('www.', '') # Remove www.
                    path = parsed.path.rstrip('/').lower() # Lowercase path, remove trailing slash
                    # Return netloc + path, ignoring scheme and query params for robust matching
                    return f"{netloc}{path}"
                except Exception as e:
                    logger.error(f"Error normalizing URL '{url}': {e}")
                    return url # Return original on error

            norm_match_url = normalize_url(match_app_url)
            found_files_by_url = False

            for scraped_path in existing_scraped:
                try:
                    with open(scraped_path, 'r', encoding='utf-8') as f_scraped:
                        actual = json.load(f_scraped)
                    stored_url = actual.get('Application URL')
                    if stored_url and stored_url != 'N/A':
                        if stored_url.startswith('/'):
                             base_url = "https://www.ostjob.ch/" # Configurable?
                             stored_url = urllib.parse.urljoin(base_url, stored_url.lstrip('/'))

                        norm_stored_url = normalize_url(stored_url)
                        logger.debug(f"Comparing normalized URLs: Report='{norm_match_url}', ScrapedFile='{norm_stored_url}' (from {scraped_path.name})")

                        # Strict comparison after normalization
                        if norm_match_url == norm_stored_url:
                            logger.info(f"Matched normalized URLs for scraped file {scraped_path.name}")
                            match['has_scraped_data'] = True
                            match['scraped_data_filename'] = scraped_path.name # Keep filename for link

                            # --- Find corresponding letter files using the REPORT's job title ---
                            # Use the job title from the current match in the report JSON
                            title_from_report = match.get('job_title', 'unknown_job')
                            sanitized_report_title = sanitize_filename(title_from_report)
                            logger.debug(f"Looking for letter files based on sanitized report title: {sanitized_report_title}")

                            # Construct expected filenames
                            html_file = letters_dir / f"motivation_letter_{sanitized_report_title}.html"
                            json_file_check = letters_dir / f"motivation_letter_{sanitized_report_title}.json"
                            docx_file = letters_dir / f"motivation_letter_{sanitized_report_title}.docx"
                            # Also check for the scraped data file associated with *this* letter generation
                            # (Note: this assumes scraped data is saved with the same sanitized title as the letter)
                            letter_scraped_data_file = letters_dir / f"motivation_letter_{sanitized_report_title}_scraped_data.json"

                            # Use config.get_path('data_root') as the base for relative paths
                            data_root_path = config.get_path('data_root')
                            if not data_root_path:
                                logger.error("Cannot determine data_root path from config for relative paths.")
                                continue # Skip relative path generation if base is missing

                            # Check file existence
                            has_json = json_file_check.is_file()
                            has_html = html_file.is_file()
                            has_docx = docx_file.is_file()
                            # Check if the scraped data specifically for this letter exists
                            # This overrides the 'has_scraped_data' found via URL matching if this specific file exists
                            if letter_scraped_data_file.is_file():
                                match['has_scraped_data'] = True
                                match['scraped_data_filename'] = letter_scraped_data_file.name


                            if has_json: # Base check on JSON existence
                                match['has_motivation_letter'] = True # Consider letter existing if JSON exists
                                match['motivation_letter_json_path'] = str(json_file_check.relative_to(data_root_path)).replace('\\', '/')
                                # Check for email text in the found JSON
                                try:
                                    with open(json_file_check, 'r', encoding='utf-8') as f_json:
                                        letter_data = json.load(f_json)
                                    if letter_data and letter_data.get('email_text'): # Check data exists before get
                                        match['has_email_text'] = True
                                except Exception as e_json_load:
                                    logger.warning(f"Could not load or check email_text in {json_file_check.name}: {e_json_load}")

                                # Store relative paths for other existing files
                                if has_html:
                                    match['motivation_letter_html_path'] = str(html_file.relative_to(data_root_path)).replace('\\', '/')
                                if has_docx:
                                    match['motivation_letter_docx_path'] = str(docx_file.relative_to(data_root_path)).replace('\\', '/')

                            found_files_by_url = True # Mark as found based on URL match leading here
                            break # Found the corresponding scraped file via URL, assume linkage, move to next report match
                except Exception as e_load:
                    logger.error(f"Error processing scraped file {scraped_path}: {e_load}")
                    continue # Skip this scraped file

            # Log if files weren't found by URL match
            if not found_files_by_url:
                logger.warning(f"No generated files could be associated with URL {match_app_url} (Report Job Title: {match.get('job_title')}) via URL matching.")

        # Render the results template with pagination data
        return render_template(
            'results.html',
            matches=paginated_matches, # Pass only the matches for the current page
            report_file=secure_report_file,
            available_cvs=available_cvs_data,
            associated_cv_filename=associated_cv_filename,
            associated_cv_rel_path=associated_cv_rel_path,
            pagination={ # Pass pagination info
                'page': page,
                'per_page': per_page,
                'total_matches': total_matches,
                'total_pages': total_pages
            }
        )

    except json.JSONDecodeError as json_err:
        flash(f'Error reading report file {json_file}: Invalid JSON.')
        logger.error(f'Error decoding JSON from {json_path}: {json_err}')
        return redirect(url_for('index'))
    except FileNotFoundError:
         flash(f'Report file not found: {json_file}')
         logger.error(f"Report file not found: {json_path}")
         return redirect(url_for('index'))
    except Exception as e:
        flash(f'Error loading results: {e}')
        logger.error(f'Error loading results for {secure_report_file}: {e}', exc_info=True)
        return redirect(url_for('index'))


@job_matching_bp.route('/download_report/<report_file>')
def download_report(report_file):
    """Download a job match report (Markdown file)"""
    secure_report_file = secure_filename(report_file)
    # Use config to get paths
    report_dir = config.get_path('job_matches')
    if not report_dir:
        flash("Configuration error: Job matches directory not found.", "error")
        logger.error("Configuration error: 'job_matches' path not found in config.")
        return redirect(url_for('index'))
    report_path = report_dir / secure_report_file # Use Path object joining

    try:
        if not report_path.is_file(): # Use Path object check
             flash(f'Report file not found: {secure_report_file}')
             logger.error(f"Report file not found for download: {report_path}")
             return redirect(url_for('index')) # Or maybe back to results?

        return send_file(str(report_path), as_attachment=True)
    except Exception as e:
        flash(f'Error downloading report: {str(e)}')
        logger.error(f'Error downloading report {secure_report_file}: {str(e)}', exc_info=True)
        # Redirect intelligently, maybe back to the results page if possible
        # For now, redirecting to index
        return redirect(url_for('index'))

@job_matching_bp.route('/delete_report/<report_file>')
def delete_report(report_file):
    """Delete a job match report (database record and files)"""
    try:
        secure_report_file = secure_filename(report_file) # This is the MD filename
        logger.info(f"Attempting to delete report: {secure_report_file}")

        # Construct paths using config
        data_root = config.get_path('data_root')
        report_dir = config.get_path('job_matches')
        if not data_root or not report_dir:
             raise ValueError("Configuration error: 'data_root' or 'job_matches' path not found.")

        report_path_md_abs = report_dir / secure_report_file
        report_path_json_abs = report_path_md_abs.with_suffix('.json')

        # Calculate relative path for DB query
        report_filepath_md_rel = str(report_path_md_abs.relative_to(data_root)).replace('\\', '/')

        # --- Delete from database FIRST ---
        deleted_from_db = False
        try:
            with database_connection() as conn:
                cursor = conn.cursor()
                # Delete based on the relative MD path
                cursor.execute("DELETE FROM JOB_MATCH_REPORTS WHERE report_filepath_md = ?", (report_filepath_md_rel,))
                if cursor.rowcount > 0:
                    logger.info(f"Deleted job match report record from database: {report_filepath_md_rel}")
                    deleted_from_db = True
                else:
                    logger.warning(f"Job match report record not found in database for deletion: {report_filepath_md_rel}")
        except Exception as db_err:
            logger.error(f"Database error deleting job match report record {report_filepath_md_rel}: {db_err}", exc_info=True)
            flash(f'Database error deleting report record: {str(db_err)}', 'error')
            # Proceed to check files, but deletion is already problematic

        # --- Delete the files ---
        deleted_md = False
        deleted_json = False

        if report_path_md_abs.is_file():
            try:
                os.remove(report_path_md_abs)
                logger.info(f"Deleted report MD file: {report_path_md_abs}")
                deleted_md = True
            except OSError as file_err:
                logger.error(f"Error deleting report MD file {report_path_md_abs}: {file_err}", exc_info=True)
                flash(f'Error deleting report MD file: {str(file_err)}', 'error')
        else:
            logger.warning(f"Report MD file not found for deletion: {report_path_md_abs}")

        if report_path_json_abs.is_file():
            try:
                os.remove(report_path_json_abs)
                logger.info(f"Deleted report JSON file: {report_path_json_abs}")
                deleted_json = True
            except OSError as file_err:
                logger.error(f"Error deleting report JSON file {report_path_json_abs}: {file_err}", exc_info=True)
                flash(f'Error deleting report JSON file: {str(file_err)}', 'error')
        else:
            logger.warning(f"Report JSON file not found for deletion: {report_path_json_abs}")

        # Final flash message
        if deleted_from_db and (deleted_md or deleted_json):
            flash(f'Report deleted successfully: {secure_report_file}')
        elif deleted_from_db:
             flash(f'Report record deleted from DB, but associated file(s) were not found or could not be deleted: {secure_report_file}', 'warning')
        elif deleted_md or deleted_json:
             flash(f'Report file(s) deleted, but DB record was not found: {secure_report_file}', 'warning')
        elif not report_path_md_abs.exists() and not report_path_json_abs.exists():
             flash(f'Report not found: {secure_report_file}', 'error')
        # If DB error occurred, it was already flashed.

    except Exception as e:
        flash(f'An unexpected error occurred during report deletion: {str(e)}')
        logger.error(f'Error deleting report {report_file}: {str(e)}', exc_info=True)

    # Redirect back to the main dashboard after deletion
    return redirect(url_for('index'))

import os
import json
import os
import json
import logging
import threading
import importlib.util
import urllib.parse # Added
from pathlib import Path
from datetime import datetime
from flask import Blueprint, request, redirect, url_for, flash, render_template, current_app
from werkzeug.utils import secure_filename
from config import config
from utils.database_utils import database_connection

# Assuming operation tracking functions are accessible, e.g., via current_app or a shared module
# from dashboard import start_operation, update_operation_progress, complete_operation, logger # Example

job_data_bp = Blueprint('job_data', __name__, url_prefix='/job_data')

logger = logging.getLogger("dashboard.job_data") # Use a child logger

@job_data_bp.route('/run_scraper', methods=['POST'])
def run_job_scraper():
    """Run the job data acquisition component"""
    try:
        # Get max_pages parameter from the form
        max_pages = int(request.form.get('max_pages', 50))

        # Access operation tracking functions (assuming they are attached to app or imported)
        start_operation = current_app.extensions['start_operation']
        update_operation_progress = current_app.extensions['update_operation_progress']
        complete_operation = current_app.extensions['complete_operation']

        # Start tracking the operation
        operation_id = start_operation('job_scraping')

        # Define a function to run the job scraper in a background thread
        def run_job_scraper_task():
            try:
                # Update status
                update_operation_progress(operation_id, 10, 'processing', 'Updating settings...')

                # Update the settings.json file with the max_pages parameter
                # Use current_app.root_path to get the application root directory
                settings_path = os.path.join(current_app.root_path, 'job-data-acquisition', 'settings.json')

                # Read the current settings
                try:
                    with open(settings_path, 'r', encoding='utf-8') as f:
                        settings = json.load(f)
                except FileNotFoundError:
                     logger.error(f"Settings file not found at {settings_path}")
                     complete_operation(operation_id, 'failed', 'Scraper settings file not found.')
                     return
                except json.JSONDecodeError:
                     logger.error(f"Error decoding settings file at {settings_path}")
                     complete_operation(operation_id, 'failed', 'Error reading scraper settings.')
                     return


                # Update the max_pages parameter
                settings['scraper']['max_pages'] = max_pages

                # Write the updated settings back to the file
                with open(settings_path, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, indent=4, ensure_ascii=False)

                # Update status
                update_operation_progress(operation_id, 20, 'processing', 'Starting job scraper...')

                # Import the job scraper module using importlib for more robust importing
                # Get the absolute path to the app.py file relative to the application root
                app_path = os.path.join(current_app.root_path, 'job-data-acquisition', 'app.py')

                if not os.path.exists(app_path):
                    logger.error(f"Job scraper app.py not found at {app_path}")
                    complete_operation(operation_id, 'failed', 'Job scraper module not found.')
                    return

                # Load the module
                spec = importlib.util.spec_from_file_location("app_module", app_path)
                app_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(app_module)

                # Get the run_scraper function
                run_scraper = getattr(app_module, 'run_scraper', None)
                if not run_scraper:
                    logger.error(f"run_scraper function not found in {app_path}")
                    complete_operation(operation_id, 'failed', 'Job scraper function not found.')
                    return

                # Update status
                update_operation_progress(operation_id, 30, 'processing', 'Scraping job listings...')

                # Run the scraper
                output_file = run_scraper()

                if output_file is None:
                    complete_operation(operation_id, 'failed', 'Job data acquisition failed. Check the logs for details.')
                else:
                    # --- Database Insertion ---
                    try:
                        data_root = config.get_path('data_root')
                        if not data_root:
                            raise ValueError("Configuration error: 'data_root' path not found in config.")

                        absolute_output_path = Path(output_file)
                        # Ensure the output file path is absolute before making it relative
                        if not absolute_output_path.is_absolute():
                             # If run_scraper returns a relative path, make it absolute based on project root
                             absolute_output_path = Path(current_app.root_path) / output_file

                        relative_data_filepath = str(absolute_output_path.relative_to(data_root)).replace('\\', '/')
                        batch_timestamp = datetime.now().isoformat()

                        # Read settings used for this run
                        settings_path = config.get_path('settings_json')
                        if not settings_path or not settings_path.exists():
                             raise FileNotFoundError("Scraper settings file not found via config.")
                        with open(settings_path, 'r', encoding='utf-8') as f:
                            settings = json.load(f)

                        source_urls_json = json.dumps(settings.get('target_urls', []))
                        settings_used_json = json.dumps(settings.get('scraper', {}))

                        with database_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                INSERT INTO JOB_DATA_BATCHES (batch_timestamp, source_urls, data_filepath, settings_used)
                                VALUES (?, ?, ?, ?)
                            """, (batch_timestamp, source_urls_json, relative_data_filepath, settings_used_json))
                        logger.info(f"Successfully added job data batch record to database: {relative_data_filepath}")
                        complete_operation(operation_id, 'completed', f'Job data acquisition completed and recorded. Data saved to: {relative_data_filepath}')

                    except Exception as db_err:
                        logger.error(f"Database error adding job data batch record for {output_file}: {db_err}", exc_info=True)
                        # Still report completion, but mention DB error
                        complete_operation(operation_id, 'completed_with_errors', f'Job data acquisition completed, but failed to record in database. Data saved to: {output_file}. Error: {db_err}')
                    # --- End Database Insertion ---

            except Exception as e:
                logger.error(f'Error in job scraper task: {str(e)}', exc_info=True)
                complete_operation(operation_id, 'failed', f'Error running job scraper: {str(e)}')

        # Start the background thread
        thread = threading.Thread(target=run_job_scraper_task)
        thread.daemon = True
        thread.start()

        # Return immediately with the operation ID
        flash(f'Job scraper started. Please wait while the job listings are being scraped. (operation_id={operation_id})')
        return redirect(url_for('index')) # Redirect to main index
    except Exception as e:
        flash(f'Error running job scraper: {str(e)}')
        logger.error(f'Error running job scraper: {str(e)}', exc_info=True)
        return redirect(url_for('index'))

@job_data_bp.route('/delete/<path:job_data_file_rel_path>') # Changed route parameter
def delete_job_data(job_data_file_rel_path): # Changed function signature
    """Delete a job data batch (database record and file)"""
    try:
        # URL decode the path
        decoded_rel_path = urllib.parse.unquote(job_data_file_rel_path)
        logger.info(f"Attempting to delete job data batch with relative path: {decoded_rel_path}")

        # Construct absolute path using config
        data_root = config.get_path('data_root')
        if not data_root:
            raise ValueError("Configuration error: 'data_root' path not found in config.")
        absolute_data_path = data_root / decoded_rel_path

        # --- Delete from database FIRST ---
        deleted_from_db = False
        try:
            with database_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM JOB_DATA_BATCHES WHERE data_filepath = ?", (decoded_rel_path,))
                if cursor.rowcount > 0:
                    logger.info(f"Deleted job data batch record from database: {decoded_rel_path}")
                    deleted_from_db = True
                else:
                    logger.warning(f"Job data batch record not found in database for deletion: {decoded_rel_path}")
                    # Don't flash error yet, maybe file exists but DB record doesn't
        except Exception as db_err:
            logger.error(f"Database error deleting job data batch record {decoded_rel_path}: {db_err}", exc_info=True)
            flash(f'Database error deleting job data record: {str(db_err)}', 'error')
            # Proceed to check file, but deletion is already problematic

        # --- Delete the file ---
        file_deleted = False
        if absolute_data_path.is_file():
            try:
                os.remove(absolute_data_path)
                logger.info(f"Deleted job data file: {absolute_data_path}")
                file_deleted = True
            except OSError as file_err:
                logger.error(f"Error deleting job data file {absolute_data_path}: {file_err}", exc_info=True)
                flash(f'Error deleting job data file: {str(file_err)}', 'error')
        else:
            logger.warning(f"Job data file not found for deletion at path: {absolute_data_path}")
            # Only flash if DB record *was* found, otherwise it's just cleanup
            if deleted_from_db:
                 flash(f'Job data file not found: {decoded_rel_path}', 'warning')


        # Final flash message based on outcomes
        if deleted_from_db and file_deleted:
            flash(f'Job data batch deleted successfully: {decoded_rel_path}')
        elif deleted_from_db and not file_deleted:
            flash(f'Job data record deleted from DB, but file was not found or could not be deleted: {decoded_rel_path}', 'warning')
        elif not deleted_from_db and file_deleted:
             flash(f'Job data file deleted, but DB record was not found: {decoded_rel_path}', 'warning')
        elif not deleted_from_db and not absolute_data_path.exists():
             # If neither existed, maybe flash a 'not found' message
             flash(f'Job data batch not found: {decoded_rel_path}', 'error')
        # If DB error occurred, it was already flashed.

    except Exception as e:
        flash(f'An unexpected error occurred during deletion: {str(e)}')
        logger.error(f'Error deleting job data batch {job_data_file_rel_path}: {str(e)}', exc_info=True)

    return redirect(url_for('index'))

@job_data_bp.route('/view/<filename>')
def view_job_data(filename):
    """Display the contents of a specific job data JSON file."""
    try:
        # Secure the filename and construct the path using config
        secure_name = secure_filename(filename)
        # Construct path using config's data_root
        data_root = config.get_path('data_root')
        if not data_root:
             raise ValueError("Configuration error: 'data_root' path not found in config.")
        # Assuming job data files are stored in a subdirectory relative to data_root
        # Let's use the specific 'job_data' path key from config if available
        job_data_dir = config.get_path('job_data')
        if not job_data_dir:
             # Fallback or construct from data_root if 'job_data' key is missing
             logger.warning("Config path key 'job_data' not found, constructing from 'data_root'.")
             job_data_dir = data_root / 'job-data-acquisition' / 'data'

        file_path = job_data_dir / secure_name

        if not file_path.is_file():
            flash(f'Job data file not found: {secure_name} at {file_path}')
            logger.error(f"Job data file not found: {file_path}")
            return redirect(url_for('index'))

        # Load the job data
        with open(file_path, 'r', encoding='utf-8') as f:
            job_data = json.load(f)

        # Process the job data based on its structure to get a flat list
        job_listings = []
        if isinstance(job_data, list):
            if len(job_data) > 0:
                if isinstance(job_data[0], list):
                    logger.info(f"Processing list of lists structure (Total pages/outer lists: {len(job_data)})")
                    # Flatten array of arrays
                    for i, job_array in enumerate(job_data):
                        page_job_count = len(job_array) if isinstance(job_array, list) else 0
                        logger.debug(f"Page {i+1}: Found {page_job_count} jobs in this inner list.")
                        if isinstance(job_array, list):
                             job_listings.extend(job_array)
                             logger.debug(f"After extending page {i+1}, total job_listings count: {len(job_listings)}")
                        else:
                             logger.warning(f"Page {i+1}: Expected a list but found {type(job_array)}. Skipping extend.")
                    logger.info(f"Finished processing list of lists. Final job_listings count: {len(job_listings)} for file {secure_name}")
                elif isinstance(job_data[0], dict) and 'content' in job_data[0]:
                    # Structure: List of Dictionaries, each with a 'content' key containing a list of jobs
                    logger.info(f"Processing list of dicts with 'content' key structure (Total pages/outer dicts: {len(job_data)})")
                    for i, page_dict in enumerate(job_data):
                        if isinstance(page_dict, dict) and 'content' in page_dict and isinstance(page_dict['content'], list):
                            page_job_count = len(page_dict['content'])
                            logger.debug(f"Page {i+1}: Found {page_job_count} jobs in 'content' list.")
                            job_listings.extend(page_dict['content'])
                            logger.debug(f"After extending page {i+1}, total job_listings count: {len(job_listings)}")
                        else:
                            logger.warning(f"Page {i+1}: Expected a dict with a 'content' list but found {type(page_dict)}. Skipping.")
                    logger.info(f"Finished processing list of dicts structure. Final job_listings count: {len(job_listings)} for file {secure_name}")
                else:
                    # Assume flat array of job listings
                    job_listings = job_data
                    logger.info(f"Loaded flat job data structure with {len(job_listings)} jobs from {secure_name}")
        else:
             logger.warning(f"Unexpected job data structure in {secure_name}: {type(job_data)}")

        # Render the template (ensure 'job_data_view.html' exists in templates/)
        return render_template('job_data_view.html', jobs=job_listings, filename=secure_name)

    except FileNotFoundError:
        flash(f'Job data file not found: {filename}')
        logger.error(f"FileNotFoundError for job data file: {filename}")
        return redirect(url_for('index'))
    except json.JSONDecodeError:
        flash(f'Error decoding JSON from file: {filename}')
        logger.error(f"JSONDecodeError for job data file: {filename}")
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'An error occurred while viewing job data: {str(e)}')
        logger.error(f'Error in view_job_data for {filename}: {str(e)}', exc_info=True)
        return redirect(url_for('index'))

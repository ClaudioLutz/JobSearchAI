import os
import json
import logging
import threading
import importlib.util
from pathlib import Path
from flask import Blueprint, request, redirect, url_for, flash, render_template, current_app
from flask_login import login_required
from werkzeug.utils import secure_filename

# Assuming operation tracking functions are accessible, e.g., via current_app or a shared module
# from dashboard import start_operation, update_operation_progress, complete_operation, logger # Example

job_data_bp = Blueprint('job_data', __name__, url_prefix='/job_data')

logger = logging.getLogger("dashboard.job_data") # Use a child logger

@job_data_bp.route('/run_scraper', methods=['POST'])
@login_required
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
                    # Make output_file relative for the message if possible
                    try:
                        relative_output_file = Path(output_file).relative_to(current_app.root_path)
                    except ValueError:
                        relative_output_file = output_file # Keep absolute if not relative
                    complete_operation(operation_id, 'completed', f'Job data acquisition completed. Data saved to: {relative_output_file}')
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

@job_data_bp.route('/delete/<job_data_file>')
@login_required
def delete_job_data(job_data_file):
    """Delete a job data file"""
    try:
        # Construct the full path to the job data file relative to app root
        job_data_dir = Path(current_app.root_path) / 'job-data-acquisition/job-data-acquisition/data'
        # Secure the filename part only
        job_data_path = job_data_dir / secure_filename(job_data_file)

        # Check if the file exists
        if not job_data_path.is_file():
            flash(f'Job data file not found: {job_data_file}')
            logger.warning(f"Attempted to delete non-existent job data file: {job_data_path}")
            return redirect(url_for('index'))

        # Delete the file
        os.remove(job_data_path)
        flash(f'Job data file deleted: {job_data_file}')
        logger.info(f"Deleted job data file: {job_data_path}")
    except Exception as e:
        flash(f'Error deleting job data file: {str(e)}')
        logger.error(f'Error deleting job data file {job_data_file}: {str(e)}', exc_info=True)

    return redirect(url_for('index'))

@job_data_bp.route('/view/<filename>')
@login_required
def view_job_data(filename):
    """Display the contents of a specific job data JSON file."""
    try:
        # Secure the filename and construct the path relative to app root
        secure_name = secure_filename(filename)
        # Corrected path: removed extra 'job-data-acquisition' segment
        file_path = Path(current_app.root_path) / 'job-data-acquisition/data' / secure_name

        if not file_path.is_file():
            flash(f'Job data file not found: {secure_name}')
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

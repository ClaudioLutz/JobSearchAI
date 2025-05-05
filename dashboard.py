import os
import json
import logging
import threading
import uuid
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from werkzeug.utils import secure_filename
import urllib.parse

# Add the current directory to the Python path to find modules
import sys
sys.path.append('.')

import sqlite3 # Import sqlite3 for error handling
# Import the updated config object FIRST
from config import config
# Import the database initializer and connection (database_connection already imported)
from utils.database_utils import initialize_database, database_connection

# Import necessary functions used only in this file or passed to blueprints
# from job_matcher import load_latest_job_data # Keep if used in index or get_job_details

# --- Helper Functions ---
# Note: get_job_details_for_url is complex and used by multiple blueprints.
# It's kept here for now but ideally refactored into a shared utils module.
def get_job_details_for_url(job_url):
    """Get job details for a URL from the latest job data file."""
    job_details = {}
    # Use the logger defined later in create_app if possible, or a temporary one
    temp_logger = logging.getLogger("dashboard.get_job_details") # Temporary logger
    try:
        # Extract the job ID from the URL
        job_id = job_url.split('/')[-1]
        temp_logger.info(f"Extracted job ID: {job_id}")

        # Find the job data file (relative to current working directory)
        # Corrected path
        job_data_dir = Path('job-data-acquisition/data')
        temp_logger.info(f"Job data directory: {job_data_dir}")

        if job_data_dir.exists():
            # Get the latest job data file
            job_data_files = list(job_data_dir.glob('job_data_*.json'))
            temp_logger.info(f"Found {len(job_data_files)} job data files")

            if job_data_files:
                latest_job_data_file = max(job_data_files, key=os.path.getctime)
                temp_logger.info(f"Latest job data file: {latest_job_data_file}")

                # Load the job data
                with open(latest_job_data_file, 'r', encoding='utf-8') as f:
                    job_data = json.load(f)

                # Process the job data based on its structure
                job_listings = []

                # Check if the data has a nested structure
                if isinstance(job_data, list):
                    if len(job_data) > 0:
                        if isinstance(job_data[0], list):
                            # It's an array of arrays - flatten it
                            for job_array in job_data:
                                if isinstance(job_array, list): # Ensure inner item is a list
                                    job_listings.extend(job_array)
                            temp_logger.info(f"Found array of arrays structure with {len(job_listings)} total job listings")
                        elif isinstance(job_data[0], dict) and 'content' in job_data[0]:
                             # Structure: List of Dictionaries, each with a 'content' key
                             for page_dict in job_data:
                                 if isinstance(page_dict, dict) and 'content' in page_dict and isinstance(page_dict['content'], list):
                                     job_listings.extend(page_dict['content'])
                             temp_logger.info(f"Found list of dicts structure with {len(job_listings)} total job listings")
                        else:
                            # Assume it's a flat array of job listings
                            job_listings = job_data
                            temp_logger.info(f"Using flat job data structure with {len(job_listings)} job listings")
                elif isinstance(job_data, dict) and 'content' in job_data: # Handle case where root is dict with content
                     job_listings = job_data['content']
                     temp_logger.info(f"Found root dict structure with {len(job_listings)} job listings")


                temp_logger.info(f"Processed job data with {len(job_listings)} total job listings")

                # Find the job with the matching ID
                for i, job in enumerate(job_listings):
                     if not isinstance(job, dict): # Skip if item is not a dict
                         temp_logger.warning(f"Skipping non-dictionary item at index {i}")
                         continue
                     # Extract the job ID from the Application URL
                     job_application_url = job.get('Application URL', '')
                     temp_logger.info(f"Job {i+1} Application URL: {job_application_url}")

                     # More robust check for job ID within the URL path
                     if isinstance(job_application_url, str) and job_id in job_application_url.split('/')[-1]:
                         temp_logger.info(f"Found matching job: {job.get('Job Title', 'N/A')} at {job.get('Company Name', 'N/A')}")
                         job_details = job
                         break

                # If no exact match found, use the first job as a fallback (if any jobs exist)
                if not job_details and job_listings and isinstance(job_listings[0], dict):
                    temp_logger.info("No exact match found, using first job as fallback")
                    job_details = job_listings[0]
    except Exception as e:
        temp_logger.error(f'Error getting job details: {str(e)}')
        import traceback
        temp_logger.error(traceback.format_exc())

    return job_details


# --- Logging Setup ---
# Configure logging globally here or within create_app
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("dashboard.log"), # Log file in the root directory
        logging.StreamHandler()
    ]
)
# Get the root logger for the dashboard application
logger = logging.getLogger("dashboard")


# --- Application Factory ---
def create_app():
    """Creates and configures the Flask application."""
    app = Flask(__name__)
    app.secret_key = os.urandom(24)  # For flash messages

    # --- Initialize Database ---
    try:
        initialize_database()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.critical(f"CRITICAL: Database initialization failed: {e}", exc_info=True)
        # Depending on the desired behavior, you might want to exit the app here
        # or display a critical error page. For now, just log critically.

    # --- Configuration ---
    # Configure upload folder (can be overridden by instance config)
    app.config['UPLOAD_FOLDER'] = 'process_cv/cv-data/input'
    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # --- Shared State / Utilities ---
    # Progress tracking (using app context via extensions)
    app.extensions['operation_progress'] = {}
    app.extensions['operation_status'] = {}

    # --- Helper Functions attached to app context ---
    # These functions will be accessible via current_app.extensions in blueprints
    def start_operation(operation_type):
        """Start tracking a new operation"""
        operation_id = str(uuid.uuid4())
        app.extensions['operation_progress'][operation_id] = 0
        app.extensions['operation_status'][operation_id] = {
            'type': operation_type,
            'status': 'starting',
            'message': f'Starting {operation_type}...',
            'start_time': datetime.now().isoformat()
        }
        logger.info(f"Started operation {operation_id} ({operation_type})")
        return operation_id

    def update_operation_progress(operation_id, progress, status=None, message=None):
        """Update the progress of an operation"""
        if operation_id in app.extensions['operation_progress']:
            app.extensions['operation_progress'][operation_id] = progress

            if status or message:
                if operation_id in app.extensions['operation_status']:
                    op_stat = app.extensions['operation_status'][operation_id]
                    if status:
                        op_stat['status'] = status
                    if message:
                        op_stat['message'] = message
                    op_stat['updated_time'] = datetime.now().isoformat()
            current_message = app.extensions['operation_status'].get(operation_id, {}).get('message', '')
            logger.info(f"Operation {operation_id}: {progress}% complete - {message or current_message}")

    def complete_operation(operation_id, status='completed', message='Operation completed'):
        """Mark an operation as completed"""
        if operation_id in app.extensions['operation_progress']:
            app.extensions['operation_progress'][operation_id] = 100

            if operation_id in app.extensions['operation_status']:
                op_stat = app.extensions['operation_status'][operation_id]
                op_stat['status'] = status
                op_stat['message'] = message
                op_stat['completed_time'] = datetime.now().isoformat()
        logger.info(f"Operation {operation_id} {status}: {message}")

    # Attach helper functions to app extensions for blueprint access
    app.extensions['start_operation'] = start_operation
    app.extensions['update_operation_progress'] = update_operation_progress
    app.extensions['complete_operation'] = complete_operation
    # Attach the complex helper function directly to app for blueprint access via current_app
    app.get_job_details_for_url = get_job_details_for_url

    # --- Register Blueprints ---
    from blueprints.cv_routes import cv_bp
    from blueprints.job_data_routes import job_data_bp
    from blueprints.job_matching_routes import job_matching_bp
    from blueprints.motivation_letter_routes import motivation_letter_bp
    from blueprints.setup_routes import setup_bp # Import the new setup blueprint

    app.register_blueprint(cv_bp)
    app.register_blueprint(job_data_bp)
    app.register_blueprint(job_matching_bp)
    app.register_blueprint(motivation_letter_bp)
    app.register_blueprint(setup_bp) # Register the setup blueprint

    # --- Core Routes (kept in this file) ---
    @app.route('/operation_status/<operation_id>')
    def get_operation_status_route(operation_id):
        """Get the status of an operation"""
        # Access progress/status via app extensions
        op_progress = app.extensions.get('operation_progress', {})
        op_status = app.extensions.get('operation_status', {})
        if operation_id in op_progress and operation_id in op_status:
            return jsonify({
                'progress': op_progress[operation_id],
                'status': op_status[operation_id]
            })
        else:
            logger.warning(f"Operation status requested for unknown ID: {operation_id}")
            return jsonify({'error': 'Operation not found'}), 404

    @app.route('/')
    def index():
        """Render the main dashboard page, redirecting to setup if needed."""
        # --- First Run Check ---
        # Use the config object imported at the top
        if config.is_first_run():
            logger.info("First run detected, redirecting to setup wizard.")
            return redirect(url_for('setup.setup_wizard'))
        # --- End First Run Check ---

        # --- Get list of available CVs from Database ---
        cv_files_data = []
        try:
            with database_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, original_filename, original_filepath, upload_timestamp
                    FROM CVS
                    ORDER BY upload_timestamp DESC
                """)
                rows = cursor.fetchall()
                # Map database rows to the structure expected by the template
                for row in rows:
                    # Format timestamp if needed (assuming it's stored as ISO string)
                    timestamp_str = row['upload_timestamp']
                    try:
                        # Attempt to parse and format. Handle potential errors if format is unexpected.
                        dt_obj = datetime.fromisoformat(timestamp_str)
                        formatted_timestamp = dt_obj.strftime('%Y-%m-%d %H:%M')
                    except (ValueError, TypeError):
                        formatted_timestamp = timestamp_str # Fallback to original string if parsing fails

                    cv_files_data.append({
                        'id': row['id'], # Pass ID for potential future use
                        'name': row['original_filepath'], # Use relative path for display/links
                        'filename': row['original_filename'], # Original filename for display
                        'timestamp': formatted_timestamp,
                        # 'full_path' is no longer needed as we use relative path from DB
                    })
            logger.info(f"Fetched {len(cv_files_data)} CV records from database.")
        except sqlite3.Error as db_err:
            logger.error(f"Database error fetching CV list: {db_err}", exc_info=True)
            flash("Error fetching CV list from database.", "error")
        except Exception as e:
            logger.error(f"Unexpected error fetching CV list: {e}", exc_info=True)
            flash("An unexpected error occurred while fetching the CV list.", "error")
        # --- End Get list of available CVs from Database ---

        # --- Get list of available Job Data Batches from Database ---
        job_batches = []
        try:
            with database_connection() as conn:
                cursor = conn.cursor()
                # Fetch necessary columns, including the relative data_filepath
                cursor.execute("""
                    SELECT id, batch_timestamp, data_filepath
                    FROM JOB_DATA_BATCHES
                    ORDER BY batch_timestamp DESC
                """)
                job_batches = cursor.fetchall() # Fetchall returns list of Row objects
            logger.info(f"Fetched {len(job_batches)} job data batch records from database.")
        except sqlite3.Error as db_err:
            logger.error(f"Database error fetching job data batches: {db_err}", exc_info=True)
            flash("Error fetching job data batches from database.", "error")
        except Exception as e:
            logger.error(f"Unexpected error fetching job data batches: {e}", exc_info=True)
            flash("An unexpected error occurred while fetching the job data batches.", "error")
        # --- End Get list of available Job Data Batches from Database ---

        # --- Get list of available Job Match Reports from Database ---
        job_match_reports = []
        try:
            with database_connection() as conn:
                cursor = conn.cursor()
                # Fetch necessary columns for display and links
                cursor.execute("""
                    SELECT id, report_timestamp, report_filepath_md, report_filepath_json
                    FROM JOB_MATCH_REPORTS
                    ORDER BY report_timestamp DESC
                """)
                job_match_reports = cursor.fetchall() # Fetchall returns list of Row objects
            logger.info(f"Fetched {len(job_match_reports)} job match report records from database.")
        except sqlite3.Error as db_err:
            logger.error(f"Database error fetching job match reports: {db_err}", exc_info=True)
            flash("Error fetching job match reports from database.", "error")
        except Exception as e:
            logger.error(f"Unexpected error fetching job match reports: {e}", exc_info=True)
            flash("An unexpected error occurred while fetching the job match reports.", "error")
        # --- End Get list of available Job Match Reports from Database ---

        # --- Get list of generated motivation letters ---
        generated_letters_data = []
        letters_dir = config.get_path('motivation_letters') # Use config path
        if letters_dir and letters_dir.exists(): # Check if path exists
            # Helper to get relative path safely
            def get_relative_path(file_path, base_path):
                try:
                    return str(file_path.relative_to(base_path)).replace('\\', '/')
                except ValueError:
                    logger.warning(f"Could not make path relative: {file_path} to {base_path}")
                    return None # Or return absolute path as string?

            # Use sanitize_filename helper (assuming it's defined globally or imported)
            # If not, define it here or import it
            def sanitize_filename_local(name, length=30):
                 sanitized = ''.join(c if c.isalnum() or c in [' ', '_', '-'] else '_' for c in name)
                 sanitized = sanitized.replace(' ', '_')
                 return sanitized[:length]

            json_files = list(letters_dir.glob('motivation_letter_*.json'))
            logger.info(f"Found {len(json_files)} potential letter JSON files in {letters_dir}")
            for json_path in json_files:
                if "_scraped_data" in json_path.name: # Skip scraped data files
                    continue
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    # Extract info from JSON content
                    job_title = data.get('subject', 'Unknown Job Title').replace('Bewerbung als ', '') # Try to get from subject
                    if job_title == 'Unknown Job Title': # Fallback to filename guess if subject missing/wrong
                         job_title = json_path.stem.replace('motivation_letter_', '').replace('_', ' ')
                    company_name = data.get('company_name', 'Unknown Company')
                    has_email = bool(data.get('email_text')) # Check if email_text exists and is not empty

                    # Determine corresponding filenames based on the JSON filename's stem
                    base_name = json_path.stem
                    html_path = letters_dir / f"{base_name}.html"
                    docx_path = letters_dir / f"{base_name}.docx"
                    scraped_path = letters_dir / f"{base_name}_scraped_data.json"

                    # Check existence
                    has_html = html_path.is_file()
                    has_docx = docx_path.is_file()
                    has_scraped = scraped_path.is_file()

                    # Get modification time from JSON file
                    mtime = os.path.getmtime(json_path)
                    timestamp = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')

                    # Use config.get_path('data_root') as the base for relative paths
                    data_root_path = config.get_path('data_root')

                    generated_letters_data.append({
                        'job_title': job_title,
                        'company_name': company_name,
                        'timestamp': timestamp,
                        'json_filename': json_path.name, # Filename for delete action
                        'json_path': get_relative_path(json_path, data_root_path),
                        'html_path': get_relative_path(html_path, data_root_path) if has_html else None,
                        'docx_path': get_relative_path(docx_path, data_root_path) if has_docx else None,
                        'scraped_path': get_relative_path(scraped_path, data_root_path) if has_scraped else None,
                        'scraped_filename': scraped_path.name if has_scraped else None,
                        'has_html': has_html,
                        'has_docx': has_docx,
                        'has_scraped': has_scraped,
                        'has_email': has_email
                    })
                except json.JSONDecodeError:
                    logger.error(f"Error decoding JSON from letter file: {json_path.name}")
                except Exception as e:
                    logger.error(f"Error processing letter file {json_path.name}: {e}", exc_info=True)

        generated_letters_data.sort(key=lambda x: x.get('timestamp', '0'), reverse=True)
        # --- End Get list of generated motivation letters --- # THIS SECTION IS NOW REPLACED BY DB QUERY BELOW

        # --- Get list of generated motivation letters from Database ---
        motivation_letters = []
        try:
            with database_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, job_title, company_name, generation_timestamp,
                           letter_filepath_html, letter_filepath_json, letter_filepath_docx, scraped_data_filepath
                    FROM MOTIVATION_LETTERS
                    ORDER BY generation_timestamp DESC
                """)
                rows = cursor.fetchall()
                data_root_path = Path(config.get_path('data_root'))
                app_root_path = Path(app.root_path)

                for row in rows:
                    letter_data = {
                        'id': row['id'],
                        'job_title': row['job_title'],
                        'company_name': row['company_name'],
                        'timestamp': row['generation_timestamp'],
                        'html_path_ui': None,       # Path relative to app root for UI links (if needed elsewhere)
                        'html_path_db': None,       # Path relative to data root for route parameter
                        'json_path_ui': None,
                        'json_path_db': None,
                        'docx_path_ui': None,
                        'docx_path_db': None,
                        'scraped_path_ui': None,
                        'scraped_path_db': None,
                        'json_filename': None,      # Filename for delete link
                        'scraped_filename': None,   # Filename for view link
                        'has_html': False,
                        'has_json': False,
                        'has_docx': False,
                        'has_scraped': False,
                        'has_email': False          # Need to check JSON content for this
                    }

                    # Process paths and check file existence
                    if row['letter_filepath_html']:
                        abs_path = data_root_path / row['letter_filepath_html']
                        if abs_path.is_file():
                            letter_data['html_path_db'] = row['letter_filepath_html'] # Store DB relative path
                            letter_data['html_path_ui'] = str(abs_path.relative_to(app_root_path)).replace('\\', '/') # Store UI relative path
                            letter_data['has_html'] = True
                    if row['letter_filepath_json']:
                        abs_path = data_root_path / row['letter_filepath_json']
                        if abs_path.is_file():
                            letter_data['json_path_db'] = row['letter_filepath_json'] # Store DB relative path
                            letter_data['json_path_ui'] = str(abs_path.relative_to(app_root_path)).replace('\\', '/') # Store UI relative path
                            letter_data['json_filename'] = Path(row['letter_filepath_json']).name # Get filename for delete
                            letter_data['has_json'] = True
                            # Check for email text inside JSON
                            try:
                                with open(abs_path, 'r', encoding='utf-8') as f_json:
                                    json_content = json.load(f_json)
                                    if json_content.get('email_text'):
                                        letter_data['has_email'] = True
                            except Exception as json_e:
                                logger.warning(f"Could not read or parse JSON {abs_path} to check for email: {json_e}")
                    if row['letter_filepath_docx']:
                        abs_path = data_root_path / row['letter_filepath_docx']
                        if abs_path.is_file():
                            letter_data['docx_path_db'] = row['letter_filepath_docx'] # Store DB relative path
                            letter_data['docx_path_ui'] = str(abs_path.relative_to(app_root_path)).replace('\\', '/') # Store UI relative path
                            letter_data['has_docx'] = True
                    if row['scraped_data_filepath']:
                        abs_path = data_root_path / row['scraped_data_filepath']
                        if abs_path.is_file():
                            letter_data['scraped_path_db'] = row['scraped_data_filepath'] # Store DB relative path
                            letter_data['scraped_path_ui'] = str(abs_path.relative_to(app_root_path)).replace('\\', '/') # Store UI relative path
                            letter_data['scraped_filename'] = Path(row['scraped_data_filepath']).name # Get filename for view link
                            letter_data['has_scraped'] = True

                    motivation_letters.append(letter_data)

            logger.info(f"Fetched {len(motivation_letters)} motivation letter records from database.")
        except sqlite3.Error as db_err:
            logger.error(f"Database error fetching motivation letters: {db_err}", exc_info=True)
            flash("Error fetching motivation letters from database.", "error")
        except Exception as e:
            logger.error(f"Unexpected error fetching motivation letters: {e}", exc_info=True)
            flash("An unexpected error occurred while fetching the motivation letters.", "error")
        # --- End Get list of generated motivation letters from Database ---


        # Pass our custom config object and fetched data to the template context
        return render_template('index.html',
                               cv_files=cv_files_data,
                               job_batches=job_batches, # Fetched earlier
                               job_match_reports=job_match_reports, # Fetched earlier
                               generated_letters=motivation_letters, # Pass letters from DB
                               config=config) # Pass our ConfigManager instance

    @app.route('/delete_files', methods=['POST'])
    def delete_files_route():
        """Handle bulk deletion of files"""
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Invalid request format'}), 400

        file_type = data.get('file_type')
        filenames = data.get('filenames')

        if not file_type or not filenames or not isinstance(filenames, list):
            return jsonify({'success': False, 'message': 'Missing file_type or filenames'}), 400

        deleted_count = 0
        failed_count = 0
        failed_files = []
        base_dir = config.get_path('data_root') # Use config path for data root

        try:
            if file_type == 'job_data':
                target_dir = config.get_path('job_data') # Use config path
                for filename in filenames:
                    # Secure filename before joining path
                    file_path = target_dir / secure_filename(filename)
                    try:
                        if file_path.is_file():
                            os.remove(file_path)
                            deleted_count += 1
                            logger.info(f"Deleted job data file: {file_path}")
                        else:
                            logger.warning(f"Bulk delete: Job data file not found: {file_path}")
                            # Not found is not necessarily a failure in bulk delete
                    except Exception as e:
                        logger.error(f"Error deleting job data file {filename}: {str(e)}")
                        failed_count += 1
                        failed_files.append(filename)

            elif file_type == 'report':
                target_dir = config.get_path('job_matches') # Use config path
                for filename in filenames:
                    # Secure filename before joining path
                    secure_name = secure_filename(filename)
                    md_path = target_dir / secure_name
                    json_path = target_dir / secure_name.replace('.md', '.json')
                    deleted_md = False
                    deleted_json = False
                    try:
                        if md_path.is_file():
                            os.remove(md_path)
                            deleted_md = True
                            logger.info(f"Deleted report file: {md_path}")
                        if json_path.is_file():
                            os.remove(json_path)
                            deleted_json = True
                            logger.info(f"Deleted corresponding JSON report file: {json_path}")

                        if deleted_md or deleted_json:
                             deleted_count += 1
                        elif not md_path.is_file() and not json_path.is_file():
                             logger.warning(f"Bulk delete: Report files already deleted or never existed: {filename}")
                        # No explicit failure for not found

                    except Exception as e:
                        logger.error(f"Error deleting report file {filename}: {str(e)}")
                        failed_count += 1
                        failed_files.append(filename)

            elif file_type == 'cv':
                # Base directory for CV related files
                cv_base_dir = config.get_path('cv_data') # Use config path
                processed_dir = config.get_path('cv_data_processed') # Use config path
                # input_dir = config.get_path('cv_data_input') # Use config path

                for filename in filenames:
                    # Filename is expected to be the relative path from process_cv/cv-data
                    # e.g., "input/my_cv.pdf" or "my_other_cv.docx"
                    relative_path_str = filename # Keep original string for logging/errors
                    relative_path = Path(relative_path_str)

                    # Construct potential full paths relative to app root
                    cv_full_path = cv_base_dir / relative_path

                    cv_path_to_delete = None
                    if cv_full_path.is_file():
                        # Ensure it's not accidentally pointing inside 'processed'
                        # This check might be redundant if filenames are always correct relative paths
                        if 'processed' not in cv_full_path.parts:
                             cv_path_to_delete = cv_full_path
                        else:
                             logger.warning(f"Attempted to delete file inside processed dir via bulk delete: {cv_full_path}")
                    else:
                         logger.warning(f"Bulk delete: CV file not found at expected path: {cv_full_path}")
                         # If file doesn't exist, still try to delete DB record in case it's orphaned
                         cv_path_to_delete = None # Ensure it's None if file not found


                    deleted_cv = False
                    deleted_summary = False
                    deleted_db_record = False
                    try:
                        # --- Delete DB Record ---
                        # Attempt DB deletion regardless of whether file exists, based on relative path
                        try:
                            with database_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute("DELETE FROM CVS WHERE original_filepath = ?", (relative_path_str,))
                                if cursor.rowcount > 0:
                                    deleted_db_record = True
                                    logger.info(f"Bulk delete: Deleted CV record from database: {relative_path_str}")
                                else:
                                    # Don't log warning if file also didn't exist
                                    if cv_path_to_delete:
                                        logger.warning(f"Bulk delete: CV record not found in database for deletion: {relative_path_str}")
                        except Exception as db_err:
                             logger.error(f"Bulk delete: Database error deleting CV record {relative_path_str}: {db_err}", exc_info=True)
                             # Log error but continue to attempt file deletion if possible
                        # --- End Delete DB Record ---

                        # --- Delete Files ---
                        if cv_path_to_delete: # Only attempt file deletion if path was valid
                            os.remove(cv_path_to_delete)
                            deleted_cv = True
                            logger.info(f"Bulk delete: Deleted CV file: {cv_path_to_delete}")

                            # Delete corresponding summary file from processed dir
                            base_filename = cv_path_to_delete.stem # Name without extension
                            summary_filename = f"{base_filename}_summary.txt"
                            summary_path = processed_dir / summary_filename
                            if summary_path.is_file():
                                os.remove(summary_path)
                                deleted_summary = True
                                logger.info(f"Bulk delete: Deleted corresponding summary file: {summary_path}")
                        # --- End Delete Files ---

                        # Increment deleted count if either DB record or file was deleted
                        if deleted_db_record or deleted_cv or deleted_summary:
                             deleted_count += 1
                        # else: # Already logged warning if file not found and DB record not found

                    except Exception as e:
                        # This error is now primarily for file deletion errors
                        logger.error(f"Bulk delete: Error deleting CV files for {relative_path_str}: {str(e)}")
                        failed_count += 1
                        failed_files.append(relative_path_str)
            else:
                return jsonify({'success': False, 'message': f'Invalid file_type: {file_type}'}), 400

            return jsonify({
                'success': failed_count == 0,
                'message': f'Deleted {deleted_count} files. Failed to delete {failed_count} files.',
                'deleted_count': deleted_count,
                'failed_count': failed_count,
                'failed_files': failed_files
            })

        except Exception as e:
            logger.error(f"Error during bulk delete for type {file_type}: {str(e)}", exc_info=True)
            return jsonify({'success': False, 'message': f'An unexpected error occurred: {str(e)}'}), 500

    return app

# --- Main Execution ---
if __name__ == '__main__':
    app = create_app()
    # Use 127.0.0.1 instead of localhost for explicit binding
    # Set debug=False for production or testing without auto-reload
    app.run(debug=True, host='127.0.0.1', port=5000)

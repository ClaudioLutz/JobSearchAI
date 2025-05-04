import os
import json
import logging
import urllib.parse
import sqlite3 # Import sqlite3 for error handling
from pathlib import Path
from datetime import datetime # Import datetime
from flask import Blueprint, request, redirect, url_for, flash, jsonify, current_app
from werkzeug.utils import secure_filename

# Import necessary functions from other modules (adjust paths if needed)
import sys
sys.path.append('.') # Add project root to path
from process_cv.cv_processor import extract_cv_text, summarize_cv
from config import config # Import config
from utils.database_utils import database_connection # Import database context manager

# Assuming helper functions and progress tracking are accessible via current_app or imported
# from dashboard import allowed_file, logger # Example if helpers are in dashboard

cv_bp = Blueprint('cv', __name__, url_prefix='/cv')

logger = logging.getLogger("dashboard.cv") # Use a child logger

# Helper function (consider moving to a shared utils module later)
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'pdf'} # Keep this specific to CV uploads here
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@cv_bp.route('/upload', methods=['POST'])
def upload_cv():
    """Handle CV upload"""
    if 'cv_file' not in request.files:
        flash('No file part')
        return redirect(url_for('index')) # Redirect to the main index route

    file = request.files['cv_file']

    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('index'))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Get absolute path for upload directory from config
        upload_dir_path = config.get_path('cv_data_input')
        if not upload_dir_path:
            flash('Configuration error: CV input directory not found.', 'error')
            logger.error("Configuration error: 'cv_data_input' path not found in config.")
            return redirect(url_for('index'))

        upload_dir_path.mkdir(parents=True, exist_ok=True) # Ensure directory exists
        file_path = upload_dir_path / filename # Use Path object joining (file_path is now absolute)
        file.save(file_path) # Save using the absolute Path object
        logger.info(f"CV saved to absolute path: {file_path}")
        flash(f'CV uploaded successfully: {filename}')

        # Process the CV
        try:
            cv_text = extract_cv_text(file_path)
            cv_summary = summarize_cv(str(file_path)) # Pass string representation of absolute path

            # Save the processed CV summary using absolute path from config
            processed_dir_path = config.get_path('cv_data_processed')
            if not processed_dir_path:
                 flash('Configuration error: CV processed directory not found.', 'error')
                 logger.error("Configuration error: 'cv_data_processed' path not found in config.")
                 # Consider deleting the uploaded file if summary saving fails due to config error
                 return redirect(url_for('index'))

            processed_dir_path.mkdir(parents=True, exist_ok=True)
            summary_filename = f"{file_path.stem}_summary.txt" # Use stem from absolute file_path
            summary_path = processed_dir_path / summary_filename # summary_path is now absolute

            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(cv_summary)
            logger.info(f"Summary saved to absolute path: {summary_path}")

            # --- Add record to database ---
            try:
                cv_base_dir = config.get_path('cv_data') # Base path for relative calculation
                if not cv_base_dir:
                     logger.error("Configuration error: 'cv_data' path not found in config for relative path calculation.")
                     raise ValueError("Configuration error: Base CV data path not found.") # Raise to prevent DB insert

                # file_path and summary_path are now absolute Path objects
                original_rel_path = str(file_path.relative_to(cv_base_dir)).replace('\\', '/')
                summary_rel_path = str(summary_path.relative_to(cv_base_dir)).replace('\\', '/')

                upload_time = datetime.now().isoformat()
                processing_time = upload_time # Assuming processing happens immediately after upload

                with database_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO CVS (original_filename, original_filepath, summary_filepath, processing_timestamp, upload_timestamp)
                        VALUES (?, ?, ?, ?, ?)
                    """, (filename, original_rel_path, summary_rel_path, processing_time, upload_time))
                logger.info(f"Successfully added CV record to database: {original_rel_path}")
                flash(f'CV processed and recorded successfully: {filename}')
            except sqlite3.IntegrityError:
                 logger.warning(f"CV already exists in database: {original_rel_path}. Skipping DB insert.")
                 flash(f'CV {filename} already exists in the database.', 'warning')
            except Exception as db_err:
                 logger.error(f"Database error adding CV record for {filename}: {db_err}", exc_info=True)
                 flash(f'Database error recording CV: {str(db_err)}', 'error')
            # --- End Add record to database ---

        except Exception as e:
            flash(f'Error processing CV: {str(e)}')
            logger.error(f'Error processing CV {filename}: {str(e)}', exc_info=True)
    else:
        flash('Invalid file type. Only PDF files are allowed.')

    return redirect(url_for('index'))

@cv_bp.route('/delete/<path:cv_file_rel_path>')
def delete_cv(cv_file_rel_path):
    """Delete a CV file using its relative path"""
    try:
        # URL decode the path in case it contains spaces or special chars
        decoded_rel_path = urllib.parse.unquote(cv_file_rel_path)
        # Base directory for CVs relative to project root
        cv_base_dir = Path('process_cv/cv-data')
        cv_full_path = cv_base_dir / decoded_rel_path

        if not cv_full_path.is_file():
            flash(f'CV file not found: {decoded_rel_path}')
            logger.warning(f"Attempted to delete non-existent CV file: {cv_full_path}")
            return redirect(url_for('index'))

        # --- Delete from database FIRST ---
        try:
            with database_connection() as conn:
                cursor = conn.cursor()
                # Use the relative path which should be unique
                cursor.execute("DELETE FROM CVS WHERE original_filepath = ?", (decoded_rel_path,))
                if cursor.rowcount > 0:
                    logger.info(f"Deleted CV record from database: {decoded_rel_path}")
                else:
                    logger.warning(f"CV record not found in database for deletion: {decoded_rel_path}")
        except Exception as db_err:
            logger.error(f"Database error deleting CV record {decoded_rel_path}: {db_err}", exc_info=True)
            flash(f'Database error deleting CV record: {str(db_err)}', 'error')
            # Decide if we should proceed with file deletion if DB delete fails
            # For now, let's proceed but the user is warned via flash message.
        # --- End Delete from database ---

        # Delete the CV file
        os.remove(cv_full_path)
        logger.info(f"Deleted CV file: {cv_full_path}")

        # Also delete the corresponding summary file if it exists
        summary_filename = f"{cv_full_path.stem}_summary.txt"
        summary_path = Path('process_cv/cv-data/processed') / summary_filename

        if summary_path.is_file():
            os.remove(summary_path)
            logger.info(f"Deleted corresponding summary file: {summary_path}")

        flash(f'CV file deleted: {decoded_rel_path}')
    except Exception as e:
        flash(f'Error deleting CV file: {str(e)}')
        logger.error(f'Error deleting CV file {cv_file_rel_path}: {str(e)}', exc_info=True)

    return redirect(url_for('index'))

@cv_bp.route('/view_summary/<path:cv_file_rel_path>')
def view_cv_summary(cv_file_rel_path):
    """View a CV summary using its relative path"""
    try:
        # URL decode the path
        decoded_rel_path = urllib.parse.unquote(cv_file_rel_path)
        cv_base_dir = Path('process_cv/cv-data')
        cv_full_path = cv_base_dir / decoded_rel_path

        # Construct summary path using the stem of the full path
        summary_filename = f"{cv_full_path.stem}_summary.txt"
        summary_path = Path('process_cv/cv-data/processed') / summary_filename

        # Check if the summary file exists
        if not summary_path.is_file():
            logger.info(f"Summary file not found ({summary_path}), attempting to generate from CV: {cv_full_path}")
            # Ensure the original CV file exists before trying to process
            if not cv_full_path.is_file():
                 logger.error(f"Original CV file not found: {cv_full_path}")
                 return jsonify({'error': f'CV file not found: {decoded_rel_path}'}), 404

            # Process the CV to generate a summary
            cv_text = extract_cv_text(str(cv_full_path)) # Pass string path
            cv_summary = summarize_cv(cv_text)

            # Save the processed CV summary
            processed_dir = Path('process_cv/cv-data/processed')
            processed_dir.mkdir(parents=True, exist_ok=True)

            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(cv_summary)
            logger.info(f"Generated and saved summary file: {summary_path}")

        # Load the CV summary
        with open(summary_path, 'r', encoding='utf-8') as f:
            summary = f.read()

        return jsonify({'summary': summary})
    except Exception as e:
        logger.error(f"Error viewing summary for {cv_file_rel_path}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

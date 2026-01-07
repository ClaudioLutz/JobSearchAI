import os
import json
import urllib.parse
from datetime import datetime
from pathlib import Path
from flask import Blueprint, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required
from werkzeug.utils import secure_filename

# Import necessary functions from other modules (adjust paths if needed)
import sys
sys.path.append('.') # Add project root to path
from process_cv.cv_processor import extract_cv_text, summarize_cv
from utils.decorators import admin_required

# Set up logging using centralized configuration
from utils.logging_config import get_logger
logger = get_logger("dashboard.cv")

cv_bp = Blueprint('cv', __name__, url_prefix='/cv')

# Helper function (consider moving to a shared utils module later)
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'pdf'} # Keep this specific to CV uploads here
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@cv_bp.route('/upload', methods=['POST'])
@login_required
@admin_required
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
        # Use current_app.config for upload folder
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'process_cv/cv-data/input')
        # Ensure the specific upload folder exists (though the main app might do this too)
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        file.save(file_path)
        flash(f'CV uploaded successfully: {filename}')

        # Process the CV
        try:
            cv_text = extract_cv_text(file_path)
            cv_summary = summarize_cv(cv_text)

            # Save the processed CV summary
            processed_dir = Path('process_cv/cv-data/processed')
            processed_dir.mkdir(parents=True, exist_ok=True)

            # Create summary filename without any nested path
            summary_filename = os.path.splitext(os.path.basename(filename))[0] + '_summary.txt'
            summary_path = processed_dir / summary_filename

            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(cv_summary)

            flash(f'CV processed successfully. Summary saved to: {summary_path.name}') # Show only filename
        except Exception as e:
            flash(f'Error processing CV: {str(e)}')
            logger.error(f'Error processing CV {filename}: {str(e)}', exc_info=True)
    else:
        flash('Invalid file type. Only PDF files are allowed.')

    return redirect(url_for('index'))

@cv_bp.route('/delete/<path:cv_file_rel_path>')
@login_required
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
@login_required
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


import os
import json
import logging
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

# Assuming helper functions and progress tracking are accessible via current_app or imported
# from dashboard import allowed_file, logger # Example if helpers are in dashboard

cv_bp = Blueprint('cv', __name__, url_prefix='/cv')

logger = logging.getLogger("dashboard.cv") # Use a child logger

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

# DEBUG ENDPOINTS - Remove these after debugging is complete
@cv_bp.route('/debug/environment')
@login_required
@admin_required
def debug_environment():
    """Debug endpoint to check environment variables and API key loading"""
    import openai as debug_openai
    
    debug_info = {
        'timestamp': str(datetime.now()),
        'openai_api_key_present': bool(os.getenv('OPENAI_API_KEY')),
        'openai_api_key_length': len(os.getenv('OPENAI_API_KEY', '')),
        'openai_api_key_prefix': os.getenv('OPENAI_API_KEY', '')[:15] + '...' if os.getenv('OPENAI_API_KEY') else None,
        'env_vars_with_key_or_api': [k for k in os.environ.keys() if 'API' in k or 'KEY' in k],
        'working_directory': os.getcwd(),
        'dotenv_path_exists': os.path.exists(Path(__file__).resolve().parent.parent / 'process_cv' / '.env'),
        'openai_version': debug_openai.__version__
    }
    
    # Test OpenAI client initialization
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            client = debug_openai.OpenAI(api_key=api_key)
            models = client.models.list()
            debug_info['openai_client_test'] = 'SUCCESS'
            debug_info['available_models_count'] = len(models.data)
        else:
            debug_info['openai_client_test'] = 'FAILED - No API key'
    except Exception as e:
        debug_info['openai_client_test'] = f'FAILED - {str(e)}'
    
    return jsonify(debug_info)

@cv_bp.route('/debug/pdf_extraction/<filename>')
@login_required
@admin_required
def debug_pdf_extraction(filename):
    """Debug endpoint to test PDF text extraction"""
    from datetime import datetime
    
    try:
        # Construct file path
        cv_path = Path('process_cv/cv-data/input') / filename
        
        debug_info = {
            'timestamp': str(datetime.now()),
            'filename': filename,
            'full_path': str(cv_path),
            'file_exists': cv_path.exists(),
            'file_size': cv_path.stat().st_size if cv_path.exists() else None
        }
        
        if cv_path.exists():
            # Test text extraction
            extracted_text = extract_cv_text(str(cv_path))
            debug_info['text_extraction'] = 'SUCCESS'
            debug_info['extracted_length'] = len(extracted_text)
            debug_info['text_preview'] = extracted_text[:500] + '...' if len(extracted_text) > 500 else extracted_text
        else:
            debug_info['text_extraction'] = 'FAILED - File not found'
            
    except Exception as e:
        debug_info['text_extraction'] = f'FAILED - {str(e)}'
        debug_info['exception_type'] = type(e).__name__
    
    return jsonify(debug_info)

@cv_bp.route('/debug/summarization_test')
@login_required
@admin_required
def debug_summarization_test():
    """Debug endpoint to test OpenAI summarization with sample text"""
    from datetime import datetime
    
    sample_text = """
    Lutz Claudio
    Software Engineer
    
    Berufserfahrung:
    2020-2023: Senior Developer bei TechCorp
    - Entwicklung von Web-Anwendungen mit Python und JavaScript
    - Team-Leadership für 5 Entwickler
    
    2018-2020: Junior Developer bei StartupXYZ
    - Frontend-Entwicklung mit React
    - Backend APIs mit Node.js
    
    Ausbildung:
    2014-2018: Bachelor Informatik, ETH Zürich
    
    Fähigkeiten: Python, JavaScript, React, Node.js, Docker, Kubernetes
    """
    
    debug_info = {
        'timestamp': str(datetime.now()),
        'sample_text_length': len(sample_text),
        'sample_text': sample_text
    }
    
    try:
        summary = summarize_cv(sample_text)
        debug_info['summarization'] = 'SUCCESS'
        debug_info['summary_length'] = len(summary)
        debug_info['summary_content'] = summary
        debug_info['summary_is_error'] = summary.startswith('Error:')
        
    except Exception as e:
        debug_info['summarization'] = f'FAILED - {str(e)}'
        debug_info['exception_type'] = type(e).__name__
    
    return jsonify(debug_info)

@cv_bp.route('/debug/file_operations')
@login_required 
@admin_required
def debug_file_operations():
    """Debug endpoint to test file I/O operations"""
    from datetime import datetime
    
    debug_info = {
        'timestamp': str(datetime.now()),
        'working_directory': os.getcwd()
    }
    
    # Test directory structure
    cv_dirs = {
        'input': Path('process_cv/cv-data/input'),
        'processed': Path('process_cv/cv-data/processed')
    }
    
    for dir_name, dir_path in cv_dirs.items():
        debug_info[f'{dir_name}_dir_exists'] = dir_path.exists()
        if dir_path.exists():
            debug_info[f'{dir_name}_dir_files'] = list(dir_path.glob('*'))
            debug_info[f'{dir_name}_dir_permissions'] = oct(dir_path.stat().st_mode)[-3:]
    
    # Test file write/read
    test_file = Path('process_cv/cv-data/processed/debug_test.txt')
    test_content = f"Debug test at {datetime.now()}"
    
    try:
        # Test write
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(test_content)
        debug_info['file_write'] = 'SUCCESS'
        
        # Test read
        with open(test_file, 'r', encoding='utf-8') as f:
            read_content = f.read()
        debug_info['file_read'] = 'SUCCESS'
        debug_info['content_match'] = read_content == test_content
        
        # Clean up
        test_file.unlink()
        debug_info['file_cleanup'] = 'SUCCESS'
        
    except Exception as e:
        debug_info['file_operations'] = f'FAILED - {str(e)}'
        debug_info['exception_type'] = type(e).__name__
    
    return jsonify(debug_info)

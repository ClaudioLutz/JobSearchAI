import logging
import json
from pathlib import Path
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required
from services.linkedin_generator import generate_linkedin_messages
from job_details_utils import get_job_details
from utils.decorators import admin_required

linkedin_bp = Blueprint('linkedin', __name__, url_prefix='/linkedin')
logger = logging.getLogger("dashboard.linkedin")

@linkedin_bp.route('/generate', methods=['POST'])
@login_required
@admin_required
def generate_messages():
    """
    Generate LinkedIn messages for a specific job.
    Expects JSON payload with 'job_url' and 'cv_filename'.
    """
    try:
        data = request.get_json()
        job_url = data.get('job_url')
        cv_filename = data.get('cv_filename')
        
        if not job_url or not cv_filename:
            return jsonify({'success': False, 'error': 'Missing job_url or cv_filename'}), 400
            
        # 1. Get Job Details
        job_details = get_job_details(job_url)
        if not job_details:
             return jsonify({'success': False, 'error': 'Could not fetch job details'}), 404

        # 2. Get CV Summary
        # Assuming standard path structure as in motivation_letter_routes
        summary_path = Path(current_app.root_path) / 'process_cv/cv-data/processed' / f"{cv_filename}_summary.txt"
        if not summary_path.exists():
            return jsonify({'success': False, 'error': f'CV summary not found: {summary_path}'}), 404
            
        with open(summary_path, 'r', encoding='utf-8') as f:
            cv_summary = f.read()
            
        # 3. Generate Messages
        messages = generate_linkedin_messages(cv_summary, job_details)
        
        if messages:
            return jsonify({'success': True, 'data': messages})
        else:
            return jsonify({'success': False, 'error': 'Failed to generate messages'}), 500
            
    except Exception as e:
        logger.error(f"Error in /linkedin/generate: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

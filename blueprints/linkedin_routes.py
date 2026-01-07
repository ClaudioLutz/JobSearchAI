import json
from pathlib import Path
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required
from services.linkedin_generator import generate_linkedin_messages
from job_details_utils import get_job_details
from utils.decorators import admin_required

# Set up logging using centralized configuration
from utils.logging_config import get_logger
logger = get_logger("dashboard.linkedin")

linkedin_bp = Blueprint('linkedin', __name__, url_prefix='/linkedin')

@linkedin_bp.route('/generate', methods=['POST'])
@login_required
@admin_required
def generate_messages():
    """
    Generate LinkedIn messages for a specific job.
    Expects JSON payload with 'job_url' and 'cv_filename'.
    Returns JSON with 'success' and either 'data' or 'error'.
    """
    try:
        data = request.get_json(silent=True)
        if not data or not isinstance(data, dict):
            logger.warning("Validation failed: invalid or missing JSON payload")
            return jsonify({'success': False, 'error': 'Invalid JSON payload'}), 400

        job_url = (data.get('job_url') or '').strip()
        cv_filename = (data.get('cv_filename') or '').strip()

        if not job_url or not cv_filename:
            logger.warning(f"Validation failed: Missing fields. job_url='{job_url}', cv_filename='{cv_filename}'")
            return jsonify({'success': False, 'error': 'Missing job_url or cv_filename'}), 400

        logger.info(f"Requested LinkedIn generation for job_url='{job_url}', cv_filename='{cv_filename}'")

        # 1. Get Job Details
        job_details = get_job_details(job_url)
        # Treat default/fallback values as failed fetch to satisfy acceptance criteria
        could_not_fetch = (
            not job_details or
            (
                isinstance(job_details, dict) and
                (job_details.get('Job Description') in (None, '', 'No description available')) and
                (job_details.get('Company Name') in (None, 'Unknown_Company')) and
                (job_details.get('Job Title') in (None, 'Unknown_Job'))
            )
        )
        if could_not_fetch:
            logger.warning(f"Job details fetch failed for URL: {job_url}")
            return jsonify({'success': False, 'error': 'Could not fetch job details'}), 404

        # 2. Get CV Summary
        summary_path = Path(current_app.root_path) / 'process_cv/cv-data/processed' / f"{cv_filename}_summary.txt"
        if not summary_path.exists():
            logger.warning(f"CV summary not found at path: {summary_path}")
            return jsonify({'success': False, 'error': f'CV summary not found: {summary_path}'}), 404

        logger.info(f"Reading CV summary from: {summary_path}")
        with open(summary_path, 'r', encoding='utf-8') as f:
            cv_summary = f.read()

        # 3. Generate Messages
        messages = generate_linkedin_messages(cv_summary, job_details)

        if messages:
            logger.info(f"LinkedIn messages generated successfully for URL: {job_url}")
            return jsonify({'success': True, 'data': messages}), 200
        else:
            logger.error("Message generation returned None/empty result")
            return jsonify({'success': False, 'error': 'Failed to generate messages'}), 500

    except Exception as e:
        logger.error(f"Error in /linkedin/generate: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

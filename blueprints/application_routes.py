"""
Application Routes Blueprint

Provides API endpoints for managing job application statuses.
Part of Epic 9: Job Stage Classification
Story 9.2: API & Route Integration
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required
from services.application_service import (
    update_application_status,
    get_application_status,
    get_application_by_job_match_id
)
from models.application_status import ApplicationStatus

# Set up logging using centralized configuration
from utils.logging_config import get_logger
logger = get_logger("dashboard.application")

application_bp = Blueprint('application', __name__, url_prefix='/api/applications')

@application_bp.route('/status', methods=['POST'])
@login_required
def update_status():
    """Update the status of a job application."""
    try:
        data = request.get_json()
        
        # Validate input
        if not data or 'job_match_id' not in data or 'status' not in data:
            return jsonify({
                'success': False,
                'message': 'Missing required fields: job_match_id, status'
            }), 400
        
        job_match_id = data['job_match_id']
        new_status = data['status'].upper()
        notes = data.get('notes')
        
        # Validate status
        if not ApplicationStatus.is_valid(new_status):
            valid_statuses = ApplicationStatus.get_all_values()
            return jsonify({
                'success': False,
                'message': f'Invalid status. Valid options: {", ".join(valid_statuses)}'
            }), 400
        
        # Get old status for logging
        old_status = get_application_status(job_match_id)
        
        # Update status
        success = update_application_status(job_match_id, new_status, notes)
        
        if success:
            logger.info(f"Status updated for job_match_id {job_match_id}: {old_status} -> {new_status}")
            return jsonify({
                'success': True,
                'new_status': new_status,
                'previous_status': old_status,
                'message': f'Status updated to {new_status}'
            }), 200
        else:
            logger.error(f"Failed to update status for job_match_id {job_match_id}")
            return jsonify({
                'success': False,
                'message': 'Failed to update status. Job may not exist.'
            }), 404
            
    except Exception as e:
        logger.exception(f"Error updating application status: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500

@application_bp.route('', methods=['GET'])
@login_required
def get_applications():
    """Get application records."""
    try:
        job_match_id = request.args.get('job_match_id', type=int)
        
        if job_match_id:
            # Get specific application
            app = get_application_by_job_match_id(job_match_id)
            if app:
                return jsonify({'success': True, 'application': app}), 200
            else:
                return jsonify({
                    'success': False,
                    'message': 'Application not found'
                }), 404
        else:
            # Get all applications (could be extended with pagination)
            # For now, this endpoint may not be heavily used
            return jsonify({
                'success': True,
                'message': 'Use job_match_id parameter to fetch specific application'
            }), 200
            
    except Exception as e:
        logger.exception(f"Error fetching applications: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500

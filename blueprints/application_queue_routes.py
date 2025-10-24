"""
Application Queue Routes Blueprint
Manages the application queue dashboard and email sending functionality.
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from flask import Blueprint, render_template, jsonify, request, current_app
from flask_login import login_required
from werkzeug.utils import secure_filename

from utils.email_sender import EmailSender
from utils.queue_validation import ApplicationValidator

# Create blueprint
queue_bp = Blueprint('queue', __name__, url_prefix='/queue')

# Configure logging
logger = logging.getLogger(__name__)


def _ensure_directories():
    """Ensure required directories exist for application storage."""
    base_dir = Path(current_app.root_path) / 'job_matches'
    directories = ['pending', 'sent', 'failed']
    
    for dir_name in directories:
        dir_path = base_dir / dir_name
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured directory exists: {dir_path}")


def _get_application_path(application_id: str, status: str = 'pending') -> Path:
    """
    Get the full path for an application file.
    
    Args:
        application_id: Application ID (filename without extension)
        status: Application status (pending/sent/failed)
    
    Returns:
        Path object for the application file
    """
    base_dir = Path(current_app.root_path) / 'job_matches' / status
    filename = secure_filename(f"{application_id}.json")
    return base_dir / filename


def _load_applications(status: str = 'pending') -> list:
    """
    Load all applications from the specified status folder.
    
    Args:
        status: Application status folder (pending/sent/failed)
    
    Returns:
        List of application dictionaries with validation results
    """
    _ensure_directories()
    
    applications = []
    base_dir = Path(current_app.root_path) / 'job_matches' / status
    
    if not base_dir.exists():
        return applications
    
    for json_file in base_dir.glob('*.json'):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                app_data = json.load(f)
            
            # Add application ID from filename
            app_data['id'] = json_file.stem
            
            # Run validation using queue validator
            is_valid, errors = ApplicationValidator.validate_for_queue(app_data)
            completeness = ApplicationValidator.validate_field_completeness(app_data)
            
            # Build validation result in expected format
            app_data['validation'] = {
                'is_valid': is_valid,
                'errors': errors,
                'completeness_score': completeness['completeness_score'],
                'missing_required': completeness['missing_required'],
                'missing_recommended': completeness['missing_recommended'],
                'validated_at': datetime.now().isoformat()
            }
            
            applications.append(app_data)
            
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {json_file}: {e}")
        except Exception as e:
            logger.error(f"Error loading application {json_file}: {e}")
    
    # Sort by created_at (most recent first)
    applications.sort(
        key=lambda x: x.get('created_at', ''),
        reverse=True
    )
    
    return applications


def _move_application(application_id: str, from_status: str, to_status: str) -> bool:
    """
    Move an application file from one status folder to another.
    
    Args:
        application_id: Application ID
        from_status: Source status folder
        to_status: Destination status folder
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        source_path = _get_application_path(application_id, from_status)
        dest_path = _get_application_path(application_id, to_status)
        
        if not source_path.exists():
            logger.error(f"Source file not found: {source_path}")
            return False
        
        # Ensure destination directory exists
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Move the file
        source_path.rename(dest_path)
        logger.info(f"Moved application {application_id} from {from_status} to {to_status}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error moving application {application_id}: {e}")
        return False


@queue_bp.route('/')
@login_required
def queue_dashboard():
    """
    Display the application queue dashboard.
    
    Shows all pending applications with validation status,
    completeness scores, and action buttons.
    """
    try:
        # Load all pending applications
        applications = _load_applications('pending')
        
        # Calculate counts for summary
        ready_count = sum(1 for app in applications if app['validation']['is_valid'])
        review_count = sum(1 for app in applications if not app['validation']['is_valid'])
        
        # Load sent applications for "Sent" tab
        sent_applications = _load_applications('sent')
        
        logger.info(f"Queue dashboard loaded: {len(applications)} pending, {len(sent_applications)} sent")
        
        return render_template(
            'application_queue.html',
            applications=applications,
            sent_applications=sent_applications,
            ready_count=ready_count,
            review_count=review_count,
            total_count=len(applications)
        )
        
    except Exception as e:
        logger.error(f"Error loading queue dashboard: {e}", exc_info=True)
        return render_template(
            'application_queue.html',
            applications=[],
            sent_applications=[],
            ready_count=0,
            review_count=0,
            total_count=0,
            error=str(e)
        )


@queue_bp.route('/send/<application_id>', methods=['POST'])
@login_required
def send_application(application_id):
    """
    Send a single application via email.
    
    Args:
        application_id: ID of the application to send
    
    Returns:
        JSON response with success status and message
    """
    try:
        # Load application data
        app_path = _get_application_path(application_id, 'pending')
        
        if not app_path.exists():
            return jsonify({
                'success': False,
                'message': f'Application not found: {application_id}'
            }), 404
        
        with open(app_path, 'r', encoding='utf-8') as f:
            app_data = json.load(f)
        
        # Validate application before sending
        is_valid, errors = ApplicationValidator.validate_for_queue(app_data)
        
        if not is_valid:
            return jsonify({
                'success': False,
                'message': 'Application validation failed',
                'details': {'errors': errors}
            }), 400
        
        # Send email
        email_sender = EmailSender()
        success, message = email_sender.send_application(
            recipient_email=app_data['recipient_email'],
            recipient_name=app_data['recipient_name'],
            subject=app_data['subject_line'],
            motivation_letter=app_data['motivation_letter'],
            job_title=app_data['job_title'],
            company_name=app_data['company_name']
        )
        
        if success:
            # Update application data
            app_data['status'] = 'sent'
            app_data['sent_at'] = datetime.now().isoformat()
            
            # Save updated data to sent folder
            sent_path = _get_application_path(application_id, 'sent')
            with open(sent_path, 'w', encoding='utf-8') as f:
                json.dump(app_data, f, indent=2, ensure_ascii=False)
            
            # Remove from pending
            app_path.unlink()
            
            logger.info(f"Application {application_id} sent successfully")
            
            return jsonify({
                'success': True,
                'message': message,
                'details': {'sent_at': app_data['sent_at']}
            })
        else:
            # Move to failed folder
            app_data['status'] = 'failed'
            app_data['failed_at'] = datetime.now().isoformat()
            app_data['error_message'] = message
            
            failed_path = _get_application_path(application_id, 'failed')
            with open(failed_path, 'w', encoding='utf-8') as f:
                json.dump(app_data, f, indent=2, ensure_ascii=False)
            
            # Remove from pending
            app_path.unlink()
            
            logger.error(f"Application {application_id} failed to send: {message}")
            
            return jsonify({
                'success': False,
                'message': message,
                'details': {'failed_at': app_data['failed_at']}
            }), 500
        
    except Exception as e:
        logger.error(f"Error sending application {application_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Internal error: {str(e)}'
        }), 500


@queue_bp.route('/send-batch', methods=['POST'])
@login_required
def send_batch():
    """
    Send multiple applications in batch.
    
    Expects JSON body with 'application_ids' array.
    
    Returns:
        JSON response with results for each application
    """
    try:
        data = request.get_json()
        application_ids = data.get('application_ids', [])
        
        if not application_ids:
            return jsonify({
                'success': False,
                'message': 'No application IDs provided'
            }), 400
        
        results = []
        
        for app_id in application_ids:
            try:
                # Load application
                app_path = _get_application_path(app_id, 'pending')
                
                if not app_path.exists():
                    results.append({
                        'id': app_id,
                        'success': False,
                        'message': 'Application not found'
                    })
                    continue
                
                with open(app_path, 'r', encoding='utf-8') as f:
                    app_data = json.load(f)
                
                # Validate
                is_valid, errors = ApplicationValidator.validate_for_queue(app_data)
                
                if not is_valid:
                    results.append({
                        'id': app_id,
                        'success': False,
                        'message': f'Validation failed: {", ".join(errors[:2])}'  # Show first 2 errors
                    })
                    continue
                
                # Send email
                email_sender = EmailSender()
                success, message = email_sender.send_application(
                    recipient_email=app_data['recipient_email'],
                    recipient_name=app_data['recipient_name'],
                    subject=app_data['subject_line'],
                    motivation_letter=app_data['motivation_letter'],
                    job_title=app_data['job_title'],
                    company_name=app_data['company_name']
                )
                
                if success:
                    # Move to sent
                    app_data['status'] = 'sent'
                    app_data['sent_at'] = datetime.now().isoformat()
                    
                    sent_path = _get_application_path(app_id, 'sent')
                    with open(sent_path, 'w', encoding='utf-8') as f:
                        json.dump(app_data, f, indent=2, ensure_ascii=False)
                    
                    app_path.unlink()
                    
                    results.append({
                        'id': app_id,
                        'success': True,
                        'message': 'Sent successfully'
                    })
                else:
                    # Move to failed
                    app_data['status'] = 'failed'
                    app_data['failed_at'] = datetime.now().isoformat()
                    app_data['error_message'] = message
                    
                    failed_path = _get_application_path(app_id, 'failed')
                    with open(failed_path, 'w', encoding='utf-8') as f:
                        json.dump(app_data, f, indent=2, ensure_ascii=False)
                    
                    app_path.unlink()
                    
                    results.append({
                        'id': app_id,
                        'success': False,
                        'message': message
                    })
                
            except Exception as e:
                logger.error(f"Error processing application {app_id} in batch: {e}")
                results.append({
                    'id': app_id,
                    'success': False,
                    'message': str(e)
                })
        
        # Count successes
        success_count = sum(1 for r in results if r['success'])
        
        logger.info(f"Batch send completed: {success_count}/{len(results)} successful")
        
        return jsonify({
            'success': True,
            'message': f'Batch send completed: {success_count}/{len(results)} successful',
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error in batch send: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'message': f'Batch send error: {str(e)}'
        }), 500

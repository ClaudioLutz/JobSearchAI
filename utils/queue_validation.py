"""
Queue Application Validation Utilities
Validates applications before queuing to prevent silent failures.

Part of Story 1.4: Application Queue Integration Bridge
"""

from typing import List, Tuple
import re


class ApplicationValidator:
    """
    Validates queue applications before saving.
    
    Architectural Pattern: Fail Fast
    Prevents silent failures by validating all required fields.
    """
    
    # Required fields that MUST be present and non-empty
    REQUIRED_FIELDS = [
        'id',
        'job_title',
        'company_name',
        'subject_line',
        'motivation_letter',
        'application_url',
        'status'
    ]
    
    # Recommended fields (can be empty but should exist)
    RECOMMENDED_FIELDS = [
        'recipient_email',
        'recipient_name'
    ]
    
    @classmethod
    def validate_for_queue(cls, app_data: dict) -> Tuple[bool, List[str]]:
        """
        Validate application data before queuing.
        
        Args:
            app_data: Application dictionary to validate
            
        Returns:
            tuple: (is_valid, list_of_errors)
                  is_valid is False if ANY required field fails
                  errors include both errors and warnings
        """
        errors = []
        
        # Check required fields exist and are not None/empty
        for field in cls.REQUIRED_FIELDS:
            if field not in app_data:
                errors.append(f"Missing required field: {field}")
            elif app_data[field] is None or app_data[field] == '':
                errors.append(f"Required field is empty: {field}")
        
        # Check recommended fields exist
        for field in cls.RECOMMENDED_FIELDS:
            if field not in app_data:
                errors.append(f"Warning: Missing recommended field: {field}")
        
        # Validate email format if present and non-empty
        if app_data.get('recipient_email'):
            if not cls.is_valid_email(app_data['recipient_email']):
                errors.append(f"Invalid email format: {app_data['recipient_email']}")
        
        # Validate ID format (should be app-{uuid})
        if 'id' in app_data and app_data['id']:
            if not app_data['id'].startswith('app-'):
                errors.append(f"Invalid ID format: {app_data['id']} (should start with 'app-')")
        
        # Validate status value
        valid_statuses = ['pending', 'sent', 'failed']
        if 'status' in app_data and app_data['status'] not in valid_statuses:
            errors.append(f"Invalid status: {app_data['status']} (must be one of {valid_statuses})")
        
        # Validate URL format (basic check)
        if 'application_url' in app_data and app_data['application_url']:
            url = app_data['application_url']
            if not (url.startswith('http://') or url.startswith('https://') or url.startswith('/')):
                errors.append(f"Invalid URL format: {url}")
        
        # Determine if valid (no critical errors, warnings are OK)
        critical_errors = [e for e in errors if not e.startswith('Warning:')]
        is_valid = len(critical_errors) == 0
        
        return is_valid, errors
    
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """
        Validate email format.
        
        Args:
            email: Email address to validate
            
        Returns:
            bool: True if email format is valid
        """
        if not email or not isinstance(email, str):
            return False
            
        # Basic email regex pattern
        # Matches: user@domain.com, user.name@domain.co.uk, etc.
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email.strip()))
    
    @classmethod
    def validate_field_completeness(cls, app_data: dict) -> dict:
        """
        Check completeness of application data.
        
        Returns:
            dict: {
                'complete': bool,
                'missing_required': List[str],
                'missing_recommended': List[str],
                'completeness_score': float (0-1)
            }
        """
        missing_required = []
        missing_recommended = []
        
        # Check required fields
        for field in cls.REQUIRED_FIELDS:
            if field not in app_data or not app_data[field]:
                missing_required.append(field)
        
        # Check recommended fields
        for field in cls.RECOMMENDED_FIELDS:
            if field not in app_data or not app_data[field]:
                missing_recommended.append(field)
        
        # Calculate completeness score
        total_fields = len(cls.REQUIRED_FIELDS) + len(cls.RECOMMENDED_FIELDS)
        present_fields = total_fields - len(missing_required) - len(missing_recommended)
        completeness_score = present_fields / total_fields if total_fields > 0 else 0.0
        
        return {
            'complete': len(missing_required) == 0,
            'missing_required': missing_required,
            'missing_recommended': missing_recommended,
            'completeness_score': completeness_score
        }

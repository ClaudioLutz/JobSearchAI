"""
Data Validation Module for JobSearchAI
Validates job application data completeness and correctness.
"""

from typing import Dict, List, Any
from email_validator import validate_email, EmailNotValidError


class ApplicationValidator:
    """
    Validates job application data for completeness and correctness.
    
    Validates required fields, minimum character lengths, email format,
    and calculates a completeness score (0-100%).
    """
    
    # Required field definitions
    REQUIRED_FIELDS = [
        'recipient_email',
        'recipient_name',
        'company_name',
        'job_title',
        'job_description',
        'motivation_letter',
        'subject_line'
    ]
    
    # Minimum length requirements (in characters)
    MIN_LENGTHS = {
        'job_description': 50,
        'motivation_letter': 200,
        'recipient_name': 2,
        'company_name': 2,
        'job_title': 5,
        'subject_line': 10
    }
    
    def __init__(self):
        """Initialize ApplicationValidator."""
        pass
    
    def validate_application(self, application: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate job application data for completeness and correctness.
        
        Args:
            application: Dictionary containing application data with keys:
                - recipient_email (str): Recipient's email address
                - recipient_name (str): Recipient's name
                - company_name (str): Company name
                - job_title (str): Job position title
                - job_description (str): Job description text
                - motivation_letter (str): Motivation letter content
                - subject_line (str, optional): Email subject line
                - job_url (str, optional): Job posting URL
        
        Returns:
            Dict containing validation results:
                - is_valid (bool): True if all validations pass
                - completeness_score (int): Score from 0-100
                - missing_fields (List[str]): List of missing required fields
                - invalid_fields (Dict[str, str]): Field names with error messages
                - warnings (List[str]): Non-critical issues
        
        Example:
            >>> validator = ApplicationValidator()
            >>> app_data = {
            ...     'recipient_email': 'hr@company.com',
            ...     'recipient_name': 'Frau Müller',
            ...     'company_name': 'TechCorp',
            ...     'job_title': 'Software Engineer',
            ...     'job_description': 'A' * 60,  # 60 chars
            ...     'motivation_letter': 'B' * 250  # 250 chars
            ... }
            >>> result = validator.validate_application(app_data)
            >>> print(result['is_valid'])
            True
        """
        missing_fields: List[str] = []
        invalid_fields: Dict[str, str] = {}
        warnings: List[str] = []
        
        # Generate subject_line if missing
        if 'subject_line' not in application or not application.get('subject_line'):
            job_title = application.get('job_title', '')
            company_name = application.get('company_name', '')
            if job_title and company_name:
                application['subject_line'] = f"Bewerbung als {job_title} bei {company_name}"
        
        # Check for missing required fields
        for field in self.REQUIRED_FIELDS:
            value = application.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing_fields.append(field)
        
        # Validate minimum lengths for fields that exist
        for field, min_length in self.MIN_LENGTHS.items():
            value = application.get(field)
            if value and isinstance(value, str):
                actual_length = len(value.strip())
                if actual_length < min_length:
                    invalid_fields[field] = (
                        f"Minimum length {min_length} characters required "
                        f"(current: {actual_length} characters)"
                    )
        
        # Validate email format
        recipient_email = application.get('recipient_email')
        if recipient_email and recipient_email not in missing_fields:
            try:
                # Validate email format using email-validator library
                validate_email(recipient_email, check_deliverability=False)
            except EmailNotValidError as e:
                invalid_fields['recipient_email'] = f"Invalid email format: {str(e)}"
        
        # Check for optional but recommended fields
        if not application.get('job_url'):
            warnings.append(
                "job_url is missing - including the job posting URL is recommended "
                "for tracking and reference"
            )
        
        # Calculate completeness score (0-100%)
        total_fields = len(self.REQUIRED_FIELDS)
        completed_fields = total_fields - len(missing_fields)
        
        # Adjust score based on invalid fields (each invalid field reduces score)
        invalid_penalty = len(invalid_fields) * 10  # 10% penalty per invalid field
        
        # Base score from field completion
        base_score = int((completed_fields / total_fields) * 100)
        
        # Final score with penalties
        completeness_score = max(0, base_score - invalid_penalty)
        
        # Determine overall validity
        is_valid = (
            len(missing_fields) == 0 and
            len(invalid_fields) == 0
        )
        
        return {
            'is_valid': is_valid,
            'completeness_score': completeness_score,
            'missing_fields': missing_fields,
            'invalid_fields': invalid_fields,
            'warnings': warnings
        }
    
    def get_validation_summary(self, validation_result: Dict[str, Any]) -> str:
        """
        Generate a human-readable summary of validation results.
        
        Args:
            validation_result: Result dictionary from validate_application()
        
        Returns:
            str: Formatted validation summary
        """
        lines = []
        
        if validation_result['is_valid']:
            lines.append("✓ Application is valid and ready to send")
            lines.append(f"  Completeness: {validation_result['completeness_score']}%")
        else:
            lines.append("✗ Application has validation errors")
            lines.append(f"  Completeness: {validation_result['completeness_score']}%")
        
        if validation_result['missing_fields']:
            lines.append(f"\nMissing fields ({len(validation_result['missing_fields'])}):")
            for field in validation_result['missing_fields']:
                lines.append(f"  - {field}")
        
        if validation_result['invalid_fields']:
            lines.append(f"\nInvalid fields ({len(validation_result['invalid_fields'])}):")
            for field, error in validation_result['invalid_fields'].items():
                lines.append(f"  - {field}: {error}")
        
        if validation_result['warnings']:
            lines.append(f"\nWarnings ({len(validation_result['warnings'])}):")
            for warning in validation_result['warnings']:
                lines.append(f"  - {warning}")
        
        return "\n".join(lines)


# Example usage (for manual testing)
if __name__ == "__main__":
    validator = ApplicationValidator()
    
    # Test Case 1: Complete valid application
    print("=" * 60)
    print("Test Case 1: Complete Valid Application")
    print("=" * 60)
    
    valid_app = {
        'recipient_email': 'hr@techcorp.com',
        'recipient_name': 'Frau Müller',
        'company_name': 'TechCorp GmbH',
        'job_title': 'Senior Software Engineer',
        'job_description': 'A' * 100,  # 100 characters
        'motivation_letter': 'B' * 250,  # 250 characters
        'subject_line': 'Bewerbung als Senior Software Engineer',
        'job_url': 'https://techcorp.com/jobs/12345'
    }
    
    result = validator.validate_application(valid_app)
    print(validator.get_validation_summary(result))
    
    # Test Case 2: Missing fields
    print("\n" + "=" * 60)
    print("Test Case 2: Missing Fields")
    print("=" * 60)
    
    incomplete_app = {
        'recipient_email': 'hr@company.com',
        'company_name': 'TestCorp'
    }
    
    result = validator.validate_application(incomplete_app)
    print(validator.get_validation_summary(result))
    
    # Test Case 3: Invalid email format
    print("\n" + "=" * 60)
    print("Test Case 3: Invalid Email Format")
    print("=" * 60)
    
    invalid_email_app = {
        'recipient_email': 'not-an-email',
        'recipient_name': 'Test User',
        'company_name': 'TestCorp',
        'job_title': 'Software Engineer',
        'job_description': 'A' * 100,
        'motivation_letter': 'B' * 250,
        'subject_line': 'Test Application'
    }
    
    result = validator.validate_application(invalid_email_app)
    print(validator.get_validation_summary(result))
    
    # Test Case 4: Minimum length violations
    print("\n" + "=" * 60)
    print("Test Case 4: Minimum Length Violations")
    print("=" * 60)
    
    short_content_app = {
        'recipient_email': 'hr@company.com',
        'recipient_name': 'A',  # Too short (min 2)
        'company_name': 'TestCorp',
        'job_title': 'Dev',  # Too short (min 5)
        'job_description': 'Short',  # Too short (min 50)
        'motivation_letter': 'Also short',  # Too short (min 200)
        'subject_line': 'Test'  # Too short (min 10)
    }
    
    result = validator.validate_application(short_content_app)
    print(validator.get_validation_summary(result))

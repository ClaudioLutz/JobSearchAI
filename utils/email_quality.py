"""
Email Quality Assessment Utilities
Detects generic emails that are likely to be filtered by spam systems.

Part of Story 1.4: Application Queue Integration Bridge
Critical Safety Fix #3: Generic Email Warnings
"""

from typing import Dict, Any


class EmailQualityChecker:
    """
    Assess email quality before sending to prevent spam filtering.
    
    Architectural Pattern: Quality Gate
    Prevents 30-70% failure rate from generic email addresses.
    """
    
    # Generic email patterns that are commonly filtered
    GENERIC_PATTERNS = [
        'jobs@',
        'jobs.',  # jobs.team@, etc
        'hr@',
        'hr.',  # hr.team@, hr.department@, etc
        'careers@',
        'recruiting@',
        'bewerbung@',
        'bewerbungen@',  # German plural
        'application@',
        'info@',
        'contact@',
        'office@',
        'admin@'
    ]
    
    # Patterns that indicate personal email
    PERSONAL_INDICATORS = [
        '.',  # e.g., john.doe@
        '_',  # e.g., john_doe@
        '-',  # e.g., john-doe@
    ]
    
    @classmethod
    def assess_email(cls, email: str) -> Dict[str, Any]:
        """
        Assess email quality and provide recommendations.
        
        Args:
            email: Email address to assess
            
        Returns:
            dict: {
                'is_generic': bool,
                'confidence': float (0-1),
                'recommendation': str,
                'severity': str ('ok'|'warning'|'error'),
                'pattern_matched': str or None,
                'has_personal_indicators': bool
            }
        """
        # Handle None or empty
        if email is None or (isinstance(email, str) and not email.strip()):
            return {
                'is_generic': False,
                'confidence': 1.0,
                'recommendation': 'No email address provided. Manual input required.',
                'severity': 'error',
                'pattern_matched': None,
                'has_personal_indicators': False
            }
        
        email_lower = email.lower().strip()
        
        # Validate email format (basic check)
        if '@' not in email_lower or '.' not in email_lower.split('@')[-1]:
            return {
                'is_generic': False,
                'confidence': 1.0,
                'recommendation': 'Invalid email format. Please verify address.',
                'severity': 'error',
                'pattern_matched': None,
                'has_personal_indicators': False
            }
        
        # Extract local part for analysis
        local_part = email_lower.split('@')[0]
        
        # Check for generic patterns FIRST (takes precedence over personal indicators)
        for pattern in cls.GENERIC_PATTERNS:
            if pattern in email_lower:
                return {
                    'is_generic': True,
                    'confidence': 0.9,
                    'recommendation': f'Generic email ({pattern}) detected. High risk of spam filtering. Try to find personal contact.',
                    'severity': 'warning',
                    'pattern_matched': pattern,
                    'has_personal_indicators': False
                }
        
        # Check for personal name indicators
        has_personal_indicator = any(
            indicator in local_part for indicator in cls.PERSONAL_INDICATORS
        )
        
        # Personal email indicators found
        if has_personal_indicator:
            return {
                'is_generic': False,
                'confidence': 0.8,
                'recommendation': 'Appears to be personal email. Good delivery chance.',
                'severity': 'ok',
                'pattern_matched': None,
                'has_personal_indicators': True
            }
        
        # Unclear - could be personal or generic
        return {
            'is_generic': False,
            'confidence': 0.5,
            'recommendation': 'Email format unclear. Consider verifying contact.',
            'severity': 'warning',
            'pattern_matched': None,
            'has_personal_indicators': False
        }
    
    @classmethod
    def batch_assess(cls, emails: list) -> Dict[str, Any]:
        """
        Assess multiple email addresses.
        
        Args:
            emails: List of email addresses
            
        Returns:
            dict: {
                'total': int,
                'generic_count': int,
                'personal_count': int,
                'unclear_count': int,
                'assessments': List[dict]
            }
        """
        assessments = []
        generic_count = 0
        personal_count = 0
        unclear_count = 0
        
        for email in emails:
            assessment = cls.assess_email(email)
            assessments.append({
                'email': email,
                **assessment
            })
            
            if assessment['severity'] == 'critical' or assessment['is_generic']:
                generic_count += 1
            elif assessment['severity'] == 'ok':
                personal_count += 1
            else:
                unclear_count += 1
        
        return {
            'total': len(emails),
            'generic_count': generic_count,
            'personal_count': personal_count,
            'unclear_count': unclear_count,
            'assessments': assessments
        }
    
    @staticmethod
    def get_quality_color(severity: str) -> str:
        """
        Get Bootstrap color class for severity level.
        
        Args:
            severity: 'ok', 'warning', or 'critical'
            
        Returns:
            str: Bootstrap color class
        """
        color_map = {
            'ok': 'success',
            'warning': 'warning',
            'critical': 'danger'
        }
        return color_map.get(severity, 'secondary')
    
    @staticmethod
    def get_quality_icon(severity: str) -> str:
        """
        Get icon for severity level.
        
        Args:
            severity: 'ok', 'warning', or 'critical'
            
        Returns:
            str: Icon name/emoji
        """
        icon_map = {
            'ok': '✓',
            'warning': '⚠️',
            'critical': '❌'
        }
        return icon_map.get(severity, '?')

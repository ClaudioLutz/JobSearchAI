"""
Application Context Data Structure
Intermediate format for bridge transformation.

Part of Story 1.4: Application Queue Integration Bridge
"""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
import uuid


@dataclass
class ApplicationContext:
    """
    Intermediate representation combining data from multiple sources.
    
    This is a transient data structure used only during bridge transformation
    to aggregate match data, letter data, and scraped data into a unified format.
    
    Architectural Pattern: Adapter/Transformer
    """
    
    # From Match JSON (required fields)
    job_title: str
    company_name: str
    application_url: str  # Full URL (normalized)
    match_score: int
    cv_path: str
    
    # From Letter JSON (required fields)
    subject_line: str
    letter_html: str
    
    # From Match JSON (optional fields)
    location: Optional[str] = None
    
    # From Letter JSON (optional fields)
    letter_text: Optional[str] = None
    email_text: Optional[str] = None
    
    # From Scraped Data JSON (optional fields)
    contact_person: Optional[str] = None
    recipient_email: Optional[str] = None
    job_description: Optional[str] = None
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_queue_application(self) -> dict:
        """
        Transform ApplicationContext to queue application JSON format.
        
        Returns:
            dict: Application in queue format ready to be saved to pending/
            
        Queue Application Format:
            {
                "id": "app-{uuid}",
                "job_title": str,
                "company_name": str,
                "recipient_email": str,
                "recipient_name": str,
                "subject_line": str,
                "motivation_letter": str,
                "email_text": str (optional),
                "application_url": str,
                "match_score": int,
                "location": str (optional),
                "created_at": str (ISO format),
                "status": "pending",
                "requires_manual_email": bool
            }
        """
        # Generate unique ID using UUID (prevents race conditions)
        app_id = f"app-{uuid.uuid4()}"
        
        # Determine recipient name (fallback chain)
        recipient_name = self.contact_person or "Hiring Team"
        
        # Check if manual email input is required
        requires_manual_email = not bool(self.recipient_email)
        
        # Build queue application
        queue_app = {
            'id': app_id,
            'job_title': self.job_title,
            'company_name': self.company_name,
            'recipient_email': self.recipient_email or '',
            'recipient_name': recipient_name,
            'subject_line': self.subject_line,
            'motivation_letter': self.letter_html,
            'application_url': self.application_url,
            'match_score': self.match_score,
            'created_at': self.created_at.isoformat(),
            'status': 'pending',
            'requires_manual_email': requires_manual_email
        }
        
        # Add optional fields if present
        if self.email_text:
            queue_app['email_text'] = self.email_text
        
        if self.location:
            queue_app['location'] = self.location
        
        if self.job_description:
            queue_app['job_description'] = self.job_description
            
        if self.letter_text:
            queue_app['letter_text'] = self.letter_text
        
        return queue_app
    
    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate that context has required fields for transformation.
        
        Returns:
            tuple: (is_valid, list of error messages)
        """
        errors = []
        
        # Required fields from match
        if not self.job_title:
            errors.append("Missing job_title")
        if not self.company_name:
            errors.append("Missing company_name")
        if not self.application_url:
            errors.append("Missing application_url")
        if not self.cv_path:
            errors.append("Missing cv_path")
        
        # Required fields from letter
        if not self.subject_line:
            errors.append("Missing subject_line")
        if not self.letter_html:
            errors.append("Missing letter_html (motivation letter)")
        
        # Match score validation
        if not isinstance(self.match_score, int) or self.match_score < 0 or self.match_score > 10:
            errors.append("Invalid match_score (must be 0-10)")
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def __str__(self) -> str:
        """String representation for debugging"""
        return (
            f"ApplicationContext("
            f"job_title='{self.job_title}', "
            f"company='{self.company_name}', "
            f"match={self.match_score}, "
            f"has_email={bool(self.recipient_email)})"
        )

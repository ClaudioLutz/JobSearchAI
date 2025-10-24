"""
Email Sender Module for JobSearchAI
Handles email sending via Gmail SMTP for job application submissions.
"""

import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from pathlib import Path
from typing import Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmailSender:
    """
    Handles sending job application emails via Gmail SMTP.
    
    Requires environment variables:
    - GMAIL_ADDRESS: Gmail account email address
    - GMAIL_APP_PASSWORD: 16-character Gmail app password
    """
    
    def __init__(self):
        """
        Initialize EmailSender with credentials from environment variables.
        
        Raises:
            ValueError: If required environment variables are missing
        """
        gmail_address = os.getenv('GMAIL_ADDRESS')
        gmail_app_password = os.getenv('GMAIL_APP_PASSWORD')
        
        if not gmail_address or not gmail_app_password:
            raise ValueError(
                "Missing Gmail credentials. Please set GMAIL_ADDRESS and "
                "GMAIL_APP_PASSWORD environment variables."
            )
        
        # Type assertion: after validation, these are guaranteed to be str
        self.gmail_address: str = gmail_address
        self.gmail_app_password: str = gmail_app_password
        
        self.smtp_server = 'smtp.gmail.com'
        self.smtp_port = 587
        self.timeout = 30
        
        logger.info(f"EmailSender initialized for account: {self.gmail_address}")
    
    def send_application(
        self,
        recipient_email: str,
        recipient_name: str,
        subject: str,
        motivation_letter: str,
        job_title: str,
        company_name: str
    ) -> Tuple[bool, str]:
        """
        Send job application email via Gmail SMTP.
        
        Args:
            recipient_email: Recipient's email address
            recipient_name: Recipient's name for greeting
            subject: Email subject line
            motivation_letter: Main body content (motivation letter)
            job_title: Job position title
            company_name: Company name
        
        Returns:
            Tuple[bool, str]: (success, message) where:
                - success: True if email sent successfully, False otherwise
                - message: Success confirmation or detailed error message
        
        Example:
            >>> sender = EmailSender()
            >>> success, msg = sender.send_application(
            ...     recipient_email="hr@company.com",
            ...     recipient_name="Frau Müller",
            ...     subject="Bewerbung als Software Engineer",
            ...     motivation_letter="Sehr geehrte Frau Müller,...",
            ...     job_title="Software Engineer",
            ...     company_name="TechCorp"
            ... )
            >>> if success:
            ...     print(f"Email sent successfully: {msg}")
        """
        try:
            # Create message container
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.gmail_address
            msg['To'] = recipient_email
            
            # Determine greeting based on language detection (simple heuristic)
            if 'Sehr geehrte' in motivation_letter or 'Sehr geehrter' in motivation_letter:
                greeting = f"Sehr geehrte/r {recipient_name},"
            else:
                greeting = f"Dear {recipient_name},"
            
            # Create plain text version
            text_content = f"""{greeting}

{motivation_letter}

Mit freundlichen Grüßen / Best regards,
[Your Name]

---
Position: {job_title}
Company: {company_name}
"""
            
            # Create HTML version
            html_content = f"""
<html>
<body>
<p>{greeting}</p>

<div style="white-space: pre-wrap;">{motivation_letter}</div>

<p>Mit freundlichen Grüßen / Best regards,<br>
[Your Name]</p>

<hr>
<p style="color: #666; font-size: 12px;">
<strong>Position:</strong> {job_title}<br>
<strong>Company:</strong> {company_name}
</p>
</body>
</html>
"""
            
            # Attach both plain text and HTML versions
            part_text = MIMEText(text_content, 'plain', 'utf-8')
            part_html = MIMEText(html_content, 'html', 'utf-8')
            
            msg.attach(part_text)
            msg.attach(part_html)
            
            # Connect to Gmail SMTP server with TLS encryption
            logger.info(f"Connecting to {self.smtp_server}:{self.smtp_port}")
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=self.timeout) as server:
                # Enable TLS encryption
                server.starttls()
                logger.info("TLS encryption enabled")
                
                # Authenticate
                server.login(self.gmail_address, self.gmail_app_password)
                logger.info("SMTP authentication successful")
                
                # Send email
                server.send_message(msg)
                
                success_message = (
                    f"Email sent successfully to {recipient_email} "
                    f"(Subject: {subject})"
                )
                logger.info(success_message)
                
                return True, success_message
        
        except smtplib.SMTPAuthenticationError as e:
            error_message = (
                f"SMTP Authentication failed. Please verify Gmail credentials. "
                f"Error: {str(e)}"
            )
            logger.error(error_message)
            return False, error_message
        
        except smtplib.SMTPException as e:
            error_message = (
                f"SMTP error occurred while sending email to {recipient_email}. "
                f"Error: {str(e)}"
            )
            logger.error(error_message)
            return False, error_message
        
        except Exception as e:
            error_message = (
                f"Unexpected error while sending email to {recipient_email}. "
                f"Error: {type(e).__name__}: {str(e)}"
            )
            logger.error(error_message)
            return False, error_message
    
    def send_application_with_attachments(
        self,
        recipient_email: str,
        subject: str,
        body_text: str,
        attachment_paths: list[str],
        job_title: str = "",
        company_name: str = ""
    ) -> Tuple[bool, str]:
        """
        Send job application email with PDF attachments.
        
        Args:
            recipient_email: Recipient's email address
            subject: Email subject line
            body_text: Email body text (plain text)
            attachment_paths: List of file paths to attach (PDFs)
            job_title: Job position title (optional, for logging)
            company_name: Company name (optional, for logging)
        
        Returns:
            Tuple[bool, str]: (success, message) where:
                - success: True if email sent successfully, False otherwise
                - message: Success confirmation or detailed error message
        
        Example:
            >>> sender = EmailSender()
            >>> success, msg = sender.send_application_with_attachments(
            ...     recipient_email="hr@company.com",
            ...     subject="Bewerbung als Software Engineer",
            ...     body_text="Sehr geehrte Damen und Herren...",
            ...     attachment_paths=["bewerbung.pdf", "lebenslauf.pdf"]
            ... )
        """
        try:
            # Validate attachments exist and check size
            MAX_ATTACHMENT_SIZE = 25 * 1024 * 1024  # 25 MB Gmail limit
            total_size = 0
            
            for path in attachment_paths:
                if not Path(path).is_file():
                    return False, f"Attachment file not found: {path}"
                file_size = Path(path).stat().st_size
                total_size += file_size
                
            if total_size > MAX_ATTACHMENT_SIZE:
                return False, f"Total attachment size ({total_size / (1024*1024):.1f} MB) exceeds 25 MB Gmail limit"
            
            # Create message
            msg = MIMEMultipart()
            msg['Subject'] = subject
            msg['From'] = self.gmail_address
            msg['To'] = recipient_email
            
            # Attach body text
            msg.attach(MIMEText(body_text, 'plain', 'utf-8'))
            
            # Attach files
            for file_path in attachment_paths:
                with open(file_path, 'rb') as f:
                    part = MIMEApplication(f.read(), Name=Path(file_path).name)
                    part['Content-Disposition'] = f'attachment; filename="{Path(file_path).name}"'
                    msg.attach(part)
                logger.info(f"Attached file: {Path(file_path).name}")
            
            # Send via SMTP
            logger.info(f"Connecting to {self.smtp_server}:{self.smtp_port}")
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=self.timeout) as server:
                # Enable TLS encryption
                server.starttls()
                logger.info("TLS encryption enabled")
                
                # Authenticate
                server.login(self.gmail_address, self.gmail_app_password)
                logger.info("SMTP authentication successful")
                
                # Send email
                server.send_message(msg)
                
                success_message = (
                    f"Email sent successfully to {recipient_email} with {len(attachment_paths)} attachment(s). "
                    f"Subject: {subject}"
                )
                logger.info(success_message)
                
                return True, success_message
                
        except smtplib.SMTPAuthenticationError as e:
            error_message = (
                f"SMTP Authentication failed. Please verify Gmail credentials. "
                f"Error: {str(e)}"
            )
            logger.error(error_message)
            return False, error_message
        
        except smtplib.SMTPException as e:
            error_message = (
                f"SMTP error occurred while sending email to {recipient_email}. "
                f"Error: {str(e)}"
            )
            logger.error(error_message)
            return False, error_message
        
        except Exception as e:
            error_message = f"Error sending email with attachments: {type(e).__name__}: {str(e)}"
            logger.error(error_message)
            return False, error_message


# Example usage (for manual testing)
if __name__ == "__main__":
    # This block is for manual testing only
    # Ensure GMAIL_ADDRESS and GMAIL_APP_PASSWORD are set in environment
    
    try:
        sender = EmailSender()
        
        # Test data
        test_data = {
            'recipient_email': 'test@example.com',
            'recipient_name': 'Test Recipient',
            'subject': 'Test Application - Software Engineer',
            'motivation_letter': 'This is a test motivation letter...',
            'job_title': 'Software Engineer',
            'company_name': 'Test Company'
        }
        
        success, message = sender.send_application(**test_data)
        
        if success:
            print(f"✓ SUCCESS: {message}")
        else:
            print(f"✗ FAILURE: {message}")
    
    except Exception as e:
        print(f"✗ ERROR: {type(e).__name__}: {str(e)}")

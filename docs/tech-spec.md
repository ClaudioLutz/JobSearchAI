# JobSearchAI - Technical Specification
**MVP Email Automation Feature**

**Author:** Claudio
**Date:** 2025-10-15
**Project Level:** 1 - Coherent Feature
**Project Type:** Web Application
**Development Context:** Brownfield - Enhancing existing JobSearchAI automation pipeline

---

## Source Tree Structure

### New Files to Create

```
blueprints/application_queue_routes.py    # New Flask blueprint for queue management
templates/application_queue.html          # Queue dashboard UI
templates/application_detail.html         # Individual application review modal
utils/email_sender.py                     # Email sending module using smtplib
utils/validation.py                       # Data validation module
static/css/queue_styles.css               # Queue-specific styling
static/js/queue.js                        # Queue interaction JavaScript
tests/test_email_sender.py                # Email sender unit tests
tests/test_validation.py                  # Validation unit tests
```

### Files to Modify

```
dashboard.py                              # Register new blueprint
requirements.txt                          # Add email-validator==2.1.0
.env.example                             # Document new environment variables
README.md                                 # Update with new features documentation
```

### Existing Files Referenced (No Changes)

```
models/user.py                            # Existing user model
utils/decorators.py                       # Existing auth decorators
job_matcher.py                            # Existing AI matching logic
motivation_letter_generator.py            # Existing Bewerbung generation
```

---

## Technical Approach

### Component 1: Email Sending (smtplib)

**Implementation Strategy:**
Use Python's built-in `smtplib` library with Gmail SMTP server. This is the simplest, most reliable approach with zero external dependencies beyond what's already in Python standard library.

**Key Design Decisions:**
- Gmail App Password authentication (not OAuth2 - simpler for MVP)
- TLS encryption on port 587 (industry standard)
- HTML email format for professional appearance
- Synchronous sending (async defer to post-MVP)
- Detailed error logging for debugging
- No retry logic in MVP (fail fast, user notified)

**Technical Flow:**
1. Load credentials from environment variables
2. Create SMTP_SSL connection to smtp.gmail.com:587
3. Authenticate using app password
4. Compose MIME multipart message (HTML + text fallback)
5. Send via SMTP, capture response
6. Log result (success/failure)
7. Close connection
8. Return status to caller

### Component 2: Data Validation

**Validation Strategy:**
Create comprehensive validation module that checks application completeness before allowing send. Validation runs automatically when applications enter queue and again before send button enables.

**Validation Rules (Definitive):**
```python
REQUIRED_FIELDS = {
    'recipient_email': 'Must be valid email format',
    'recipient_name': 'Must be non-empty string',
    'company_name': 'Must be non-empty string',
    'job_title': 'Must be non-empty string',
    'job_description': 'Minimum 50 characters',
    'motivation_letter': 'Minimum 200 characters',
    'subject_line': 'Must be non-empty string'
}

OPTIONAL_FIELDS = {
    'job_url': 'URL format if present',
    'salary_range': 'String, no validation',
    'application_deadline': 'Date format if present'
}
```

**Validation Output:**
```python
{
    'is_valid': boolean,
    'completeness_score': int (0-100),
    'missing_fields': list[str],
    'invalid_fields': dict[str, str],  # field: reason
    'warnings': list[str]
}
```

**Design Principles:**
- Fail-safe: Invalid applications cannot be sent
- Clear feedback: Specific reasons for each validation failure
- Quantifiable: Completeness score for progress indication
- Extensible: Easy to add new validation rules

### Component 3: Application Queue UI

**UI Architecture:**
Single-page Flask route serving queue dashboard with AJAX for dynamic updates. No JavaScript frameworks - vanilla JS + Fetch API for simplicity.

**Page Structure:**
```
Application Queue Dashboard
├── Header: Count summary (10 ready, 3 need review)
├── Filter Tabs: All | Ready | Needs Review | Sent
├── Application List (Cards)
│   ├── Card per application
│   │   ├── Status badge (✅ Ready | ⚠️ Review | 📧 Sent)
│   │   ├── Company + Job Title
│   │   ├── Completeness bar (0-100%)
│   │   ├── Preview snippet
│   │   └── Action buttons
│   └── ...
└── Batch Actions: Send All Ready button
```

**Interaction Flow:**
1. User opens `/queue` route
2. Server loads all pending applications from filesystem
3. Each application validated, scores calculated
4. Rendered as cards with status indicators
5. User clicks "Review" → Modal shows full details
6. User clicks "Send" → Confirmation dialog
7. AJAX POST to `/queue/send/<id>`
8. Email sent, UI updated without page reload
9. Application moved to "Sent" status

---

## Implementation Stack

### Core Technologies (Already in Use)

- **Python:** 3.11.5 (existing version)
- **Flask:** 2.3.3 (existing version)
- **Playwright:** 1.40.0 (existing version)
- **OpenAI:** 1.3.5 (existing version)

### New Dependencies

```txt
email-validator==2.1.0    # Email format validation
```

### Email Configuration

```python
# SMTP Settings (Definitive)
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SMTP_USE_TLS = True
SMTP_TIMEOUT = 30  # seconds

# From .env file
GMAIL_ADDRESS = os.getenv('GMAIL_ADDRESS')
GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD')
```

### Database/Storage

**MVP Approach:** File-based JSON storage (existing pattern)
```
job_matches/
  ├── pending/           # Applications in queue
  │   ├── app_001.json
  │   ├── app_002.json
  │   └── ...
  ├── sent/             # Sent applications archive
  └── failed/           # Failed send attempts
```

**JSON Structure:**
```json
{
  "id": "app_001",
  "status": "pending|sent|failed",
  "created_at": "2025-10-15T10:00:00Z",
  "sent_at": "2025-10-15T11:00:00Z",
  "job": {
    "title": "Senior Python Developer",
    "company": "TechCorp AG",
    "url": "https://ostjob.ch/...",
    "description": "..."
  },
  "recipient": {
    "email": "hr@techcorp.ch",
    "name": "HR Department"
  },
  "motivation_letter": "Sehr geehrte Damen und Herren...",
  "validation": {
    "is_valid": true,
    "completeness_score": 100,
    "validated_at": "2025-10-15T10:30:00Z"
  }
}
```

---

## Technical Details

### Module 1: Email Sender (`utils/email_sender.py`)

```python
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Tuple
import logging

class EmailSender:
    """Send job applications via Gmail SMTP"""
    
    def __init__(self):
        self.smtp_server = 'smtp.gmail.com'
        self.smtp_port = 587
        self.sender_email = os.getenv('GMAIL_ADDRESS')
        self.sender_password = os.getenv('GMAIL_APP_PASSWORD')
        
        if not self.sender_email or not self.sender_password:
            raise ValueError("Gmail credentials not configured in .env")
    
    def send_application(self, 
                        recipient_email: str,
                        recipient_name: str,
                        subject: str,
                        motivation_letter: str,
                        job_title: str,
                        company_name: str) -> Tuple[bool, str]:
        """
        Send job application email
        
        Returns: (success: bool, message: str)
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.sender_email
            msg['To'] = recipient_email
            msg['Subject'] = subject
            
            # HTML body
            html_body = f"""
            <html>
              <body>
                <p>Sehr geehrte/r {recipient_name},</p>
                <p>{motivation_letter.replace('\n', '<br>')}</p>
                <p>Mit freundlichen Grüssen,<br>
                Claudio Lutz</p>
              </body>
            </html>
            """
            
            # Plain text fallback
            text_body = f"Sehr geehrte/r {recipient_name},\n\n{motivation_letter}\n\nMit freundlichen Grüssen,\nClaudio Lutz"
            
            msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send via SMTP
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(msg)
            
            logging.info(f"Email sent successfully to {recipient_email} for {job_title} at {company_name}")
            return True, "Email sent successfully"
            
        except smtplib.SMTPAuthenticationError:
            logging.error("Gmail authentication failed")
            return False, "Authentication failed - check Gmail app password"
        except smtplib.SMTPException as e:
            logging.error(f"SMTP error: {str(e)}")
            return False, f"Email sending failed: {str(e)}"
        except Exception as e:
            logging.error(f"Unexpected error: {str(e)}")
            return False, f"Unexpected error: {str(e)}"
```

### Module 2: Data Validation (`utils/validation.py`)

```python
from email_validator import validate_email, EmailNotValidError
from typing import Dict, List, Optional
import re

class ApplicationValidator:
    """Validate job application completeness and correctness"""
    
    REQUIRED_FIELDS = {
        'recipient_email': 'Recipient email address',
        'recipient_name': 'Recipient name',
        'company_name': 'Company name',
        'job_title': 'Job title',
        'job_description': 'Job description',
        'motivation_letter': 'Motivation letter'
    }
    
    MIN_LENGTHS = {
        'job_description': 50,
        'motivation_letter': 200,
        'recipient_name': 2,
        'company_name': 2,
        'job_title': 5
    }
    
    def validate_application(self, application: Dict) -> Dict:
        """
        Validate application data
        
        Returns:
        {
            'is_valid': bool,
            'completeness_score': int (0-100),
            'missing_fields': list[str],
            'invalid_fields': dict[str, str],
            'warnings': list[str]
        }
        """
        missing_fields = []
        invalid_fields = {}
        warnings = []
        
        # Check required fields exist
        for field, description in self.REQUIRED_FIELDS.items():
            value = application.get(field)
            if not value or (isinstance(value, str) and not value.strip()):
                missing_fields.append(description)
        
        # Validate email format
        if 'recipient_email' in application:
            try:
                validate_email(application['recipient_email'])
            except EmailNotValidError as e:
                invalid_fields['recipient_email'] = str(e)
        
        # Check minimum lengths
        for field, min_length in self.MIN_LENGTHS.items():
            value = application.get(field, '')
            if value and len(value) < min_length:
                invalid_fields[field] = f"Minimum {min_length} characters required (found {len(value)})"
        
        # Optional warnings
        if not application.get('job_url'):
            warnings.append("Job URL missing - recommended for reference")
        
        # Calculate completeness score
        total_checks = len(self.REQUIRED_FIELDS) + len(self.MIN_LENGTHS)
        passed_checks = total_checks - len(missing_fields) - len(invalid_fields)
        completeness_score = int((passed_checks / total_checks) * 100)
        
        is_valid = len(missing_fields) == 0 and len(invalid_fields) == 0
        
        return {
            'is_valid': is_valid,
            'completeness_score': completeness_score,
            'missing_fields': missing_fields,
            'invalid_fields': invalid_fields,
            'warnings': warnings
        }
```

### Module 3: Queue Routes (`blueprints/application_queue_routes.py`)

```python
from flask import Blueprint, render_template, request, jsonify
from utils.validation import ApplicationValidator
from utils.email_sender import EmailSender
from utils.decorators import login_required
import os
import json
from datetime import datetime

queue_bp = Blueprint('queue', __name__, url_prefix='/queue')
validator = ApplicationValidator()
email_sender = EmailSender()

@queue_bp.route('/')
@login_required
def queue_dashboard():
    """Render application queue dashboard"""
    applications = load_pending_applications()
    
    # Validate each application
    for app in applications:
        validation_result = validator.validate_application(app)
        app['validation'] = validation_result
    
    # Count by status
    ready_count = sum(1 for app in applications if app['validation']['is_valid'])
    review_count = len(applications) - ready_count
    
    return render_template('application_queue.html',
                         applications=applications,
                         ready_count=ready_count,
                         review_count=review_count)

@queue_bp.route('/send/<application_id>', methods=['POST'])
@login_required
def send_application(application_id):
    """Send a single application via email"""
    try:
        app = load_application(application_id)
        
        # Validate before sending
        validation = validator.validate_application(app)
        if not validation['is_valid']:
            return jsonify({
                'success': False,
                'error': 'Application validation failed',
                'details': validation
            }), 400
        
        # Send email
        success, message = email_sender.send_application(
            recipient_email=app['recipient_email'],
            recipient_name=app['recipient_name'],
            subject=f"Bewerbung als {app['job_title']} bei {app['company_name']}",
            motivation_letter=app['motivation_letter'],
            job_title=app['job_title'],
            company_name=app['company_name']
        )
        
        if success:
            # Move to sent folder
            move_to_sent(application_id, app)
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'error': message}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@queue_bp.route('/send-batch', methods=['POST'])
@login_required
def send_batch():
    """Send all ready applications"""
    data = request.get_json()
    application_ids = data.get('application_ids', [])
    
    results = []
    for app_id in application_ids:
        # Send each application
        response = send_application(app_id)
        results.append({
            'id': app_id,
            'success': response.status_code == 200
        })
    
    return jsonify({'results': results})

def load_pending_applications():
    """Load all pending applications from filesystem"""
    pending_dir = 'job_matches/pending'
    applications = []
    
    if os.path.exists(pending_dir):
        for filename in os.listdir(pending_dir):
            if filename.endswith('.json'):
                with open(os.path.join(pending_dir, filename), 'r') as f:
                    applications.append(json.load(f))
    
    return applications

def move_to_sent(application_id, application_data):
    """Move application from pending to sent folder"""
    application_data['status'] = 'sent'
    application_data['sent_at'] = datetime.utcnow().isoformat()
    
    # Remove from pending
    os.remove(f'job_matches/pending/{application_id}.json')
    
    # Save to sent
    os.makedirs('job_matches/sent', exist_ok=True)
    with open(f'job_matches/sent/{application_id}.json', 'w') as f:
        json.dump(application_data, f, indent=2)
```

---

## Development Setup

### Environment Variables (.env)

```bash
# Existing variables
OPENAI_API_KEY=sk-...
FLASK_SECRET_KEY=...

# New variables for email
GMAIL_ADDRESS=your.email@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx  # 16-character app password
```

### Gmail App Password Setup

1. Go to Google Account settings
2. Security → 2-Step Verification (must be enabled)
3. App passwords → Generate new app password
4. Select "Mail" and device type
5. Copy 16-character password to .env file

### Directory Structure

```bash
mkdir -p job_matches/pending
mkdir -p job_matches/sent
mkdir -p job_matches/failed
mkdir -p tests
```

### Dependencies Installation

```bash
pip install email-validator==2.1.0
pip freeze > requirements.txt
```

---

## Implementation Guide

### Step 1: Email Sender Module (2-3 hours)

**Tasks:**
1. Create `utils/email_sender.py` with EmailSender class
2. Implement send_application() method with error handling
3. Add Gmail credentials to .env
4. Create test script to send test email
5. Verify email delivery and formatting
6. Add logging for debugging

**Acceptance Criteria:**
- Test email successfully delivered to Gmail inbox
- HTML formatting renders correctly
- Error handling logs useful messages
- Credentials loaded from environment variables

### Step 2: Data Validation Module (2-3 hours)

**Tasks:**
1. Create `utils/validation.py` with ApplicationValidator class
2. Implement validate_application() method
3. Add email-validator dependency
4. Write unit tests for validation rules
5. Test with sample application data
6. Document validation rules

**Acceptance Criteria:**
- All required fields checked correctly
- Email validation works
- Minimum length checks functional
- Completeness score calculated accurately
- Unit tests pass 100%

### Step 3: Application Queue UI (4-6 hours)

**Tasks:**
1. Create `/queue` Flask route in new blueprint
2. Create `templates/application_queue.html`
3. Implement application loading from filesystem
4. Add validation calls for each application
5. Create card-based UI with status indicators
6. Implement "Send" button with AJAX
7. Add confirmation dialogs
8. Create `static/css/queue_styles.css`
9. Create `static/js/queue.js` for interactions
10. Register blueprint in dashboard.py
11. Add navigation link to main dashboard

**Acceptance Criteria:**
- Queue page loads all pending applications
- Validation status displayed correctly
- "Send" button calls email sender
- AJAX updates UI without reload
- Error messages displayed clearly
- Applications move to sent folder after sending

### Integration Testing (1-2 hours)

**End-to-End Test:**
1. Manually trigger job scrape (existing functionality)
2. Open application queue
3. Verify applications appear with validation status
4. Click "Review" to see full details
5. Click "Send" on ready application
6. Confirm email delivered to recipient
7. Verify application moved to sent folder
8. Check for any errors in logs

---

## Testing Approach

### Unit Tests

**test_email_sender.py:**
```python
def test_email_sender_initialization()
def test_send_application_success()
def test_send_application_auth_failure()
def test_send_application_invalid_recipient()
def test_email_formatting()
```

**test_validation.py:**
```python
def test_validate_complete_application()
def test_validate_missing_required_fields()
def test_validate_email_format()
def test_validate_minimum_lengths()
def test_completeness_score_calculation()
```

### Manual Testing Checklist

- [ ] Send test email to personal address
- [ ] Verify HTML rendering in Gmail
- [ ] Test with missing required fields
- [ ] Test with invalid email format
- [ ] Test with minimum length violations
- [ ] Load queue with multiple applications
- [ ] Click each button and verify behavior
- [ ] Test error handling (disconnect WiFi mid-send)
- [ ] Verify sent applications archived correctly
- [ ] Check logs for proper error messages

### Integration Testing

**Full Pipeline Test:**
1. Run scraper to generate pending applications
2. Open queue dashboard
3. Verify validation runs automatically
4. Send one application
5. Verify email delivery
6. Check sent folder contains application
7. Confirm pending folder no longer has it

---

## Deployment Strategy

### Local Development Deployment

**Prerequisites:**
- Python 3.11+ environment active
- Gmail app password configured
- All dependencies installed
- Environment variables set in .env

**Deployment Steps:**

```bash
# 1. Install new dependencies
pip install email-validator==2.1.0

# 2. Create required directories
mkdir -p job_matches/{pending,sent,failed}

# 3. Configure Gmail credentials
echo "GMAIL_ADDRESS=your.email@gmail.com" >> .env
echo "GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx" >> .env

# 4. Run database migrations (if any)
# None required for MVP - using file storage

# 5. Start Flask development server
python dashboard.py

# 6. Access application queue
# Navigate to http://localhost:5000/queue
```

### Configuration Validation

**Pre-deployment Checklist:**
- [ ] .env file contains GMAIL_ADDRESS
- [ ] .env file contains GMAIL_APP_PASSWORD
- [ ] job_matches/pending directory exists
- [ ] job_matches/sent directory exists
- [ ] email-validator installed
- [ ] Test email successfully sent
- [ ] Flask server starts without errors

### Rollback Plan

If issues arise:
1. Remove new blueprint registration from dashboard.py
2. Delete utils/email_sender.py and utils/validation.py
3. Remove queue templates
4. Restart Flask server
5. System reverts to previous working state

### Monitoring

**What to Monitor:**
- Flask application logs for email sending errors
- job_matches/failed/ directory for failed send attempts
- Gmail "Sent Mail" folder to verify delivery
- Application queue count (shouldn't grow indefinitely)

**Log Locations:**
```
logs/flask.log           # Flask application logs
logs/email_sender.log    # Email sending specific logs
```

---

_This tech spec provides definitive implementation guidance for the 3 MVP features (email sending, data validation, application queue UI). All technical decisions are concrete with no ambiguity. Ready for direct implementation._

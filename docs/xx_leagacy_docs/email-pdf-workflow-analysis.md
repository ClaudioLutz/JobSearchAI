# Email & PDF Attachment Workflow - Implementation Plan
**Date:** October 16, 2025  
**Updated By:** Development Team (Party Mode Discussion)  
**For:** Claudio  
**Project:** JobSearchAI

## Executive Summary

Following clarification with Claudio, the workflow is much simpler than initially analyzed. The user wants to maintain manual control over document editing and PDF conversion, which actually **simplifies the implementation significantly**. No automatic PDF conversion is needed.

**Estimated Implementation Time:** 4-6 hours (not days!)

## Clarified Requirements

### User's Desired Workflow

1. **Generate** Bewerbungsschreiben (motivation letter) as Word document (✅ Already works)
2. **Download** the Word document (✅ Already works)
3. **Edit** the Word document in Microsoft Office locally (✅ User handles)
4. **Save as PDF** locally in Microsoft Office (✅ User handles)
5. **Upload** the PDF back to the application (❌ **Need to add**)
6. **Review & Edit** generated email text (❌ **Need to add**)
7. **Send email** with:
   - Short email text (generated, but user can edit)
   - Bewerbungsschreiben PDF (uploaded by user)
   - Lebenslauf PDF (static file, auto-attached) (❌ **Need to add**)

## Current System Status

### ✅ What Already Works

1. **Motivation Letter Word Generation**
   - File: `word_template_generator.py`
   - Route: `blueprints/motivation_letter_routes.py` (line 134-139)
   - Generates `.docx` files successfully using `docxtpl`
   - Template: `motivation_letters/template/motivation_letter_template.docx`

2. **Word Document Download**
   - Route: `/motivation_letter/download_docx` (lines 428-446)
   - Returns `.docx` file for download
   - Works reliably

3. **Email Text Generation**
   - Function: `generate_email_text_only()` in `letter_generation_utils.py`
   - Already generates short email text
   - Stored in JSON files alongside motivation letters

4. **Basic Email Sending**
   - File: `utils/email_sender.py`
   - Class: `EmailSender` with `send_application()` method
   - Can send text/HTML emails via Gmail SMTP
   - ⚠️ **Does NOT support attachments yet**

5. **Static CV**
   - Location: `process_cv/cv-data/input/Lebenslauf_-_Lutz_Claudio.pdf`
   - ✅ File exists and is ready to attach

### ❌ What Needs to Be Added

1. **PDF Upload Functionality** (NEW)
2. **Email Attachment Support** (MODIFY existing)
3. **Send Application UI/Workflow** (NEW)

## Implementation Plan

### Task 1: Add Email Attachment Support ⏱️ 2-3 hours

**File to Modify:** `utils/email_sender.py`

**Changes Needed:**

1. **Import additional MIME type:**
```python
from email.mime.application import MIMEApplication
from pathlib import Path
```

2. **Add new method `send_application_with_attachments`:**
```python
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
        Tuple[bool, str]: (success, message)
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
        with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=self.timeout) as server:
            server.starttls()
            server.login(self.gmail_address, self.gmail_app_password)
            server.send_message(msg)
            
            success_message = (
                f"Email sent successfully to {recipient_email} with {len(attachment_paths)} attachment(s). "
                f"Subject: {subject}"
            )
            logger.info(success_message)
            return True, success_message
            
    except Exception as e:
        error_message = f"Error sending email with attachments: {type(e).__name__}: {str(e)}"
        logger.error(error_message)
        return False, error_message
```

**Testing:**
- Create unit test in `tests/test_email_sender.py`
- Test with sample PDF files
- Test file size validation
- Test missing file handling

---

### Task 2: Add PDF Upload & Send Application Workflow ⏱️ 2-3 hours

**File to Modify:** `blueprints/motivation_letter_routes.py`

**Changes Needed:**

#### 2.1: Add PDF Upload Endpoint

```python
@motivation_letter_bp.route('/upload_pdf', methods=['POST'])
@login_required
def upload_bewerbungsschreiben_pdf():
    """Upload Bewerbungsschreiben PDF for sending"""
    try:
        if 'pdf_file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        
        file = request.files['pdf_file']
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'success': False, 'error': 'Only PDF files are allowed'}), 400
        
        # Secure filename and save
        job_title = request.form.get('job_title', 'application')
        sanitized_title = sanitize_filename(job_title)
        filename = f"Bewerbungsschreiben_{sanitized_title}.pdf"
        
        # Save to ready_to_send directory
        upload_dir = Path(current_app.root_path) / 'motivation_letters/ready_to_send'
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = upload_dir / filename
        file.save(str(file_path))
        
        logger.info(f"Uploaded Bewerbungsschreiben PDF: {file_path}")
        
        return jsonify({
            'success': True,
            'file_path': str(file_path.relative_to(current_app.root_path)),
            'filename': filename
        })
    
    except Exception as e:
        logger.error(f'Error uploading PDF: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
```

#### 2.2: Add Send Application Endpoint

```python
@motivation_letter_bp.route('/send_application', methods=['POST'])
@login_required
def send_application_email():
    """Send job application email with PDF attachments"""
    try:
        data = request.get_json()
        
        recipient_email = data.get('recipient_email')
        subject = data.get('subject')
        email_text = data.get('email_text')
        bewerbungsschreiben_pdf_path = data.get('bewerbungsschreiben_pdf_path')
        job_title = data.get('job_title', '')
        company_name = data.get('company_name', '')
        
        # Validate required fields
        if not all([recipient_email, subject, email_text, bewerbungsschreiben_pdf_path]):
            return jsonify({
                'success': False,
                'error': 'Missing required fields'
            }), 400
        
        # Build attachment paths
        bewerbungsschreiben_full_path = Path(current_app.root_path) / bewerbungsschreiben_pdf_path
        lebenslauf_full_path = Path(current_app.root_path) / 'process_cv/cv-data/input/Lebenslauf_-_Lutz_Claudio.pdf'
        
        # Validate both files exist
        if not bewerbungsschreiben_full_path.is_file():
            return jsonify({
                'success': False,
                'error': 'Bewerbungsschreiben PDF not found'
            }), 400
        
        if not lebenslauf_full_path.is_file():
            return jsonify({
                'success': False,
                'error': 'Lebenslauf PDF not found. Please ensure CV is at process_cv/cv-data/input/Lebenslauf_-_Lutz_Claudio.pdf'
            }), 400
        
        # Send email with attachments
        sender = EmailSender()
        success, message = sender.send_application_with_attachments(
            recipient_email=recipient_email,
            subject=subject,
            body_text=email_text,
            attachment_paths=[
                str(bewerbungsschreiben_full_path),
                str(lebenslauf_full_path)
            ],
            job_title=job_title,
            company_name=company_name
        )
        
        if success:
            logger.info(f"Application sent successfully to {recipient_email} for {job_title} at {company_name}")
        
        return jsonify({
            'success': success,
            'message': message
        })
    
    except Exception as e:
        logger.error(f'Error sending application: {str(e)}', exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Error sending application: {str(e)}'
        }), 500
```

#### 2.3: Add Prepare Send UI View

```python
@motivation_letter_bp.route('/prepare_send/<job_title>')
@login_required
def prepare_send_application(job_title):
    """Show the send application page with email text and upload form"""
    try:
        # Load the email text from JSON
        sanitized_title = sanitize_filename(job_title)
        json_path = Path(current_app.root_path) / 'motivation_letters' / f'motivation_letter_{sanitized_title}.json'
        
        email_text = ""
        job_details = {}
        
        if json_path.is_file():
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                email_text = data.get('email_text', '')
                # Load job details from the JSON
                job_details = {
                    'Job Title': data.get('job_title_source', job_title),
                    'Company Name': data.get('company_name', ''),
                    'Application Email': data.get('contact_email', ''),
                    'Application URL': data.get('job_url', '')
                }
        
        return render_template(
            'send_application.html',
            job_title=job_title,
            email_text=email_text,
            job_details=job_details
        )
    
    except Exception as e:
        flash(f'Error preparing send application: {str(e)}')
        logger.error(f'Error in prepare_send_application: {str(e)}', exc_info=True)
        return redirect(url_for('index'))
```

---

### Task 3: Create Send Application UI Template ⏱️ 1-2 hours

**New File:** `templates/send_application.html`

```html
{% extends "index.html" %}
{% block content %}

<div class="container mt-4">
    <h2>📧 Send Job Application</h2>
    <h4>{{ job_details.get('Job Title', 'Job Application') }}</h4>
    <p class="text-muted">{{ job_details.get('Company Name', '') }}</p>
    
    <div class="card mb-3">
        <div class="card-header">
            <h5>✅ Pre-Send Checklist</h5>
        </div>
        <div class="card-body">
            <div class="form-check">
                <input class="form-check-input" type="checkbox" id="check-email-text">
                <label class="form-check-label" for="check-email-text">
                    Email text reviewed and edited
                </label>
            </div>
            <div class="form-check">
                <input class="form-check-input" type="checkbox" id="check-bewerbung-pdf">
                <label class="form-check-label" for="check-bewerbung-pdf">
                    Bewerbungsschreiben PDF uploaded (edited & converted from Word)
                </label>
            </div>
            <div class="form-check">
                <input class="form-check-input" type="checkbox" id="check-lebenslauf">
                <label class="form-check-label" for="check-lebenslauf">
                    Lebenslauf will be auto-attached (Lebenslauf_-_Lutz_Claudio.pdf)
                </label>
            </div>
            <div class="form-check">
                <input class="form-check-input" type="checkbox" id="check-recipient">
                <label class="form-check-label" for="check-recipient">
                    Recipient email verified
                </label>
            </div>
        </div>
    </div>
    
    <form id="send-application-form">
        <!-- Recipient Email -->
        <div class="mb-3">
            <label for="recipient-email" class="form-label">Recipient Email *</label>
            <input type="email" class="form-control" id="recipient-email" 
                   value="{{ job_details.get('Application Email', '') }}" required>
        </div>
        
        <!-- Subject -->
        <div class="mb-3">
            <label for="email-subject" class="form-label">Subject *</label>
            <input type="text" class="form-control" id="email-subject" 
                   value="Bewerbung - {{ job_details.get('Job Title', '') }}" required>
        </div>
        
        <!-- Email Text -->
        <div class="mb-3">
            <label for="email-text" class="form-label">Email Text * (Editable)</label>
            <textarea class="form-control" id="email-text" rows="10" required>{{ email_text }}</textarea>
            <small class="form-text text-muted">You can edit this text before sending</small>
        </div>
        
        <!-- PDF Upload -->
        <div class="mb-3">
            <label for="pdf-file" class="form-label">Upload Bewerbungsschreiben PDF *</label>
            <input type="file" class="form-control" id="pdf-file" accept=".pdf" required>
            <small class="form-text text-muted">Upload your edited and PDF-converted Bewerbungsschreiben</small>
            <div id="upload-status" class="mt-2"></div>
        </div>
        
        <!-- Hidden field for uploaded PDF path -->
        <input type="hidden" id="bewerbungsschreiben-pdf-path">
        
        <!-- Send Button -->
        <button type="submit" class="btn btn-primary btn-lg" id="send-btn" disabled>
            📤 Send Application
        </button>
        <a href="{{ url_for('index') }}" class="btn btn-secondary">Cancel</a>
    </form>
    
    <div id="send-result" class="mt-3"></div>
</div>

<script>
document.getElementById('pdf-file').addEventListener('change', async function(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('pdf_file', file);
    formData.append('job_title', '{{ job_title }}');
    
    document.getElementById('upload-status').innerHTML = '<span class="text-info">Uploading...</span>';
    
    try {
        const response = await fetch('/motivation_letter/upload_pdf', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            document.getElementById('upload-status').innerHTML = 
                '<span class="text-success">✓ PDF uploaded successfully</span>';
            document.getElementById('bewerbungsschreiben-pdf-path').value = result.file_path;
            document.getElementById('check-bewerbung-pdf').checked = true;
            checkFormReady();
        } else {
            document.getElementById('upload-status').innerHTML = 
                '<span class="text-danger">✗ Upload failed: ' + result.error + '</span>';
        }
    } catch (error) {
        document.getElementById('upload-status').innerHTML = 
            '<span class="text-danger">✗ Upload error: ' + error.message + '</span>';
    }
});

function checkFormReady() {
    const allChecked = 
        document.getElementById('check-email-text').checked &&
        document.getElementById('check-bewerbung-pdf').checked &&
        document.getElementById('check-lebenslauf').checked &&
        document.getElementById('check-recipient').checked;
    
    const pdfUploaded = document.getElementById('bewerbungsschreiben-pdf-path').value !== '';
    
    document.getElementById('send-btn').disabled = !(allChecked && pdfUploaded);
}

// Enable checkboxes to be manually checked
document.querySelectorAll('.form-check-input').forEach(checkbox => {
    checkbox.addEventListener('change', checkFormReady);
});

document.getElementById('send-application-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const sendBtn = document.getElementById('send-btn');
    sendBtn.disabled = true;
    sendBtn.innerHTML = 'Sending...';
    
    const data = {
        recipient_email: document.getElementById('recipient-email').value,
        subject: document.getElementById('email-subject').value,
        email_text: document.getElementById('email-text').value,
        bewerbungsschreiben_pdf_path: document.getElementById('bewerbungsschreiben-pdf-path').value,
        job_title: '{{ job_details.get("Job Title", "") }}',
        company_name: '{{ job_details.get("Company Name", "") }}'
    };
    
    try {
        const response = await fetch('/motivation_letter/send_application', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            document.getElementById('send-result').innerHTML = 
                '<div class="alert alert-success">✓ Application sent successfully!</div>';
            setTimeout(() => {
                window.location.href = '/';
            }, 2000);
        } else {
            document.getElementById('send-result').innerHTML = 
                '<div class="alert alert-danger">✗ Error: ' + result.message + '</div>';
            sendBtn.disabled = false;
            sendBtn.innerHTML = '📤 Send Application';
        }
    } catch (error) {
        document.getElementById('send-result').innerHTML = 
            '<div class="alert alert-danger">✗ Error: ' + error.message + '</div>';
        sendBtn.disabled = false;
        sendBtn.innerHTML = '📤 Send Application';
    }
});
</script>

{% endblock %}
```

---

### Task 4: Add "Send Application" Button to Existing UI ⏱️ 30 minutes

**Files to Modify:**
- `templates/results.html` (or wherever motivation letters are displayed)
- `templates/motivation_letter.html`

**Add Button After Download Buttons:**

```html
<a href="{{ url_for('motivation_letter.prepare_send_application', job_title=job_details['Job Title']) }}" 
   class="btn btn-success">
   📧 Send Application
</a>
```

---

## File Structure After Implementation

```
JobSearchAI/
├── utils/
│   └── email_sender.py                    [MODIFIED - Add attachment support]
├── blueprints/
│   └── motivation_letter_routes.py        [MODIFIED - Add upload & send routes]
├── templates/
│   └── send_application.html              [NEW - Send application UI]
├── motivation_letters/
│   ├── ready_to_send/                     [NEW - Uploaded PDFs]
│   └── ... (existing files)
├── process_cv/
│   └── cv-data/
│       └── input/
│           └── Lebenslauf_-_Lutz_Claudio.pdf  [MUST EXIST]
└── tests/
    └── test_email_sender.py               [MODIFIED - Add attachment tests]
```

---

## Complete User Workflow

### Step-by-Step Process

1. **User matches jobs** (existing functionality)
2. **User generates motivation letter** as Word document (existing functionality)
3. **User downloads Word document** (existing functionality)
4. **User opens Word in Microsoft Office** ✏️ (manual, offline)
5. **User edits the document** ✏️ (manual, offline)
6. **User saves as PDF** ✏️ (manual, offline, e.g., "Save As" → PDF)
7. **User returns to app** and clicks "Send Application" button (NEW)
8. **App shows send form** with:
   - Pre-filled recipient email (from job details)
   - Pre-filled subject line
   - Generated email text (editable textarea)
   - PDF upload field
   - Checklist
9. **User uploads the PDF** they just created
10. **User reviews/edits email text**
11. **User checks all checklist items**
12. **User clicks "Send Application"**
13. **App sends email with**:
    - Email text (as entered by user)
    - Bewerbungsschreiben PDF (uploaded)
    - Lebenslauf PDF (auto-attached from `process_cv/cv-data/input/`)

---

## Technical Architecture

### Advantages of This Approach

✅ **No External Dependencies**
- No PDF conversion libraries needed
- No MS Office/LibreOffice installation required on server
- Works on any platform (Windows, Linux, Mac)

✅ **User Control**
- User sees exactly what they're sending
- Can make last-minute edits to email text
- Verifies PDF before sending
- No "black box" automation

✅ **Simple Error Handling**
- No PDF conversion failures
- Clear upload validation
- Explicit file size checks

✅ **Stateless Server**
- No temporary files to manage
- No session state for "edit then convert" workflow
- Clean separation of concerns

✅ **Security**
- File upload validation (PDF only)
- File size limits enforced
- Secure filename handling
- Gmail SMTP with app password

### Email Sending Flow

```
┌─────────────────────────────────────────────────────────────┐
│ User clicks "Send Application"                              │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Show send_application.html with:                            │
│ - Pre-filled recipient email                                │
│ - Pre-filled subject                                        │
│ - Generated email text (editable)                           │
│ - PDF upload field                                          │
│ - Checklist                                                 │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ User uploads Bewerbungsschreiben PDF                        │
│ → POST /motivation_letter/upload_pdf                        │
│ → Saves to motivation_letters/ready_to_send/                │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ User reviews checklist and clicks "Send"                    │
│ → POST /motivation_letter/send_application                  │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Backend validates:                                          │
│ - All required fields present                               │
│ - Bewerbungsschreiben PDF exists                           │
│ - Lebenslauf PDF exists                                    │
│ - Total file size < 25MB                                   │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ EmailSender.send_application_with_attachments()            │
│ - Creates MIMEMultipart message                            │
│ - Attaches email text                                      │
│ - Attaches Bewerbungsschreiben PDF                        │
│ - Attaches Lebenslauf PDF                                 │
│ - Sends via Gmail SMTP                                     │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Success! Show confirmation and redirect to home            │
└─────────────────────────────────────────────────────────────┘
```

---

## Testing Strategy

### Unit Tests

**File:** `tests/test_email_sender.py`

```python
def test_send_application_with_attachments_success():
    """Test successful email sending with PDF attachments"""
    # Test with mock SMTP and real PDF files
    pass

def test_send_application_missing_attachment():
    """Test error handling when attachment file is missing"""
    pass

def test_send_application_file_too_large():
    """Test file size validation (>25MB)"""
    pass

def test_send_application_invalid_file_type():
    """Test that non-PDF files are rejected"""
    pass
```

### Integration Tests

1. **Upload PDF Test:**
   - Upload valid PDF → Should save to `ready_to_send/`
   - Upload non-PDF → Should reject
   - Upload file >25MB → Should reject

2. **Send Application Test:**
   - Send with both PDFs → Should succeed
   - Send with missing CV → Should fail gracefully
   - Send with missing Bewerbungsschreiben → Should fail gracefully

3. **End-to-End Test:**
   - Generate Word → Download → Upload PDF → Send
   - Verify email received with 2 attachments

### Manual Testing Checklist

- [ ] Generate motivation letter Word document
- [ ] Download Word document successfully
- [ ] Edit Word document in Microsoft Office (manual)
- [ ] Save as PDF (manual)
- [ ] Click "Send Application" button
- [ ] Upload edited PDF
- [ ] Verify email text is pre-filled and editable
- [ ] Verify recipient email is pre-filled from job details
- [ ] Check all checklist items
- [ ] Click "Send Application"
- [ ] Verify email arrives with:
  - [ ] Correct email text
  - [ ] Bewerbungsschreiben PDF attached
  - [ ] Lebenslauf PDF attached
  - [ ] Both PDFs open correctly
- [ ] Verify UI shows success message
- [ ] Verify proper error handling for missing files

---

## Error Handling

### Common Errors & Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| "Attachment file not found" | PDF not uploaded or path incorrect | Verify upload was successful before sending |
| "Total attachment size exceeds 25 MB" | PDFs too large | Compress PDFs or reduce quality |
| "Lebenslauf PDF not found" | CV missing from expected location | Ensure CV exists at `process_cv/cv-data/input/Lebenslauf_-_Lutz_Claudio.pdf` |
| "SMTP Authentication failed" | Gmail credentials invalid | Check GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env |
| "Only PDF files are allowed" | User tried to upload non-PDF | Only accept .pdf files in upload form |

---

## Dependencies

### No New Dependencies Required! 🎉

All necessary libraries are already in `requirements.txt`:
- ✅ `Flask` (web framework)
- ✅ `python-dotenv` (environment variables)
- ✅ `docxtpl` (Word document generation)
- ✅ Email libraries are Python standard library:
  - `email.mime.text`
  - `email.mime.multipart`
  - `email.mime.application` ← Standard library
  - `smtplib` ← Standard library

**Zero new dependencies to install!**

---

## Security Considerations

### File Upload Security

1. **File Type Validation**
   - Only accept `.pdf` files
   - Check file extension and MIME type
   - Reject executables and scripts

2. **File Size Limits**
   - Maximum 25 MB (Gmail limit)
   - Validate before accepting upload
   - Display clear error messages

3. **Filename Sanitization**
   - Use `sanitize_filename()` helper
   - Remove special characters
   - Prevent directory traversal attacks

### Email Security

1. **Gmail App Password**
   - Use app-specific password, not main password
   - Store in `.env` file (not committed to git)
   - Rotate periodically

2. **Recipient Validation**
   - Validate email format
   - Confirm recipient before sending
   - Log all sent emails

3. **Attachment Validation**
   - Verify files exist before sending
   - Check file sizes

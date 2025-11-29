# Story 7.2: API & Route Integration

**Epic:** Epic 7 - LinkedIn Outreach Integration  
**Status:** Complete  
**Story Type:** Implementation  
**Estimate:** 3 Story Points  
**Actual Effort:** 3 Story Points  
**Completed:** 2025-11-28

---

## User Story

As a **frontend developer**,  
I want **a REST API endpoint to generate LinkedIn messages**,  
So that **the UI can request message generation for specific jobs and display results to the user**.

---

## Story Context

### Existing System Integration

**Integrates with:**
- `services/linkedin_generator.py` - Calls the message generation service (Story 7.1)
- `job_details_utils.py` - Uses `get_job_details()` to fetch job information
- `app.py` - Blueprint registered with Flask application
- `utils/decorators.py` - Uses `@login_required` and `@admin_required` decorators
- Frontend - Provides JSON API for AJAX requests

**Technology:**
- Python 3.x with Flask
- Flask Blueprint pattern
- JSON request/response format
- Flask-Login for authentication
- Python logging framework

**Follows pattern:**
- Similar to `blueprints/motivation_letter_routes.py` structure
- Uses same authentication decorators
- Uses same JSON response format
- Follows established error handling patterns

**Touch points:**
- Receives POST requests from frontend JavaScript
- Fetches job details using existing utility
- Reads CV summary files from standard location
- Returns JSON responses with success/error status

---

## Acceptance Criteria

### Functional Requirements

1. **Blueprint Structure Created**
   - Create `blueprints/linkedin_routes.py` module
   - Define `linkedin_bp` Blueprint with `/linkedin` URL prefix
   - Blueprint can be registered with Flask app
   - Proper imports and module structure

2. **API Endpoint Implementation**
   - Route: `POST /linkedin/generate`
   - Requires authentication (`@login_required`)
   - Requires admin privileges (`@admin_required`)
   - Accepts JSON payload with `job_url` and `cv_filename`
   - Returns JSON response with success status and data/error

3. **Request Validation**
   - Validates presence of required fields: `job_url`, `cv_filename`
   - Returns 400 Bad Request if fields missing
   - Clear error message in JSON response
   - Logs validation failures

4. **Job Details Retrieval**
   - Calls `get_job_details(job_url)` to fetch job information
   - Handles case where job details cannot be fetched
   - Returns 404 Not Found if job details unavailable
   - Logs job fetch failures

5. **CV Summary Retrieval**
   - Constructs path to CV summary file: `process_cv/cv-data/processed/{cv_filename}_summary.txt`
   - Checks if summary file exists
   - Returns 404 Not Found if summary file missing
   - Reads summary file with UTF-8 encoding
   - Logs file read operations

6. **Message Generation**
   - Calls `generate_linkedin_messages(cv_summary, job_details)`
   - Handles successful generation (returns 200 OK with messages)
   - Handles generation failure (returns 500 Internal Server Error)
   - Logs generation success/failure

7. **Response Format**
   - Success response:
     ```json
     {
       "success": true,
       "data": {
         "connection_request_hiring_manager": "...",
         "peer_networking": "...",
         "inmail_message": "..."
       }
     }
     ```
   - Error response:
     ```json
     {
       "success": false,
       "error": "Error message description"
     }
     ```

### Integration Requirements

8. **Blueprint Registration**
   - Blueprint must be registered in `app.py`
   - Registration follows existing pattern
   - No conflicts with existing routes
   - Blueprint accessible at `/linkedin/*` paths

9. **Authentication Integration**
   - Uses existing `@login_required` decorator
   - Uses existing `@admin_required` decorator
   - Follows same authentication pattern as other routes
   - Returns appropriate HTTP status for unauthorized access

10. **Existing Pattern Adherence**
    - Module structure mirrors other blueprint files
    - Function naming follows project conventions
    - Error handling matches existing patterns
    - Logging format consistent with project standards
    - Uses `current_app` for Flask context access

### Quality Requirements

11. **Error Handling and Logging**
    - All exceptions caught and logged with appropriate levels
    - INFO level for successful operations
    - WARNING level for validation failures
    - ERROR level for unexpected failures
    - Log messages include relevant context (job_url, cv_filename, error details)
    - Try-except block around entire endpoint logic

12. **HTTP Status Codes**
    - 200 OK - Successful message generation
    - 400 Bad Request - Missing required fields
    - 404 Not Found - Job details or CV summary not found
    - 500 Internal Server Error - Generation failure or unexpected error
    - Appropriate status codes for authentication failures (handled by decorators)

13. **Code Quality**
    - Code follows PEP 8 style guidelines
    - Type hints on function signatures
    - Docstrings on route functions
    - Clear variable names
    - Single-purpose functions

---

## Technical Notes

### Implementation Approach

**Route Function Structure:**
```python
@linkedin_bp.route('/generate', methods=['POST'])
@login_required
@admin_required
def generate_messages():
    """
    Generate LinkedIn messages for a specific job.
    Expects JSON payload with 'job_url' and 'cv_filename'.
    """
    try:
        # 1. Parse and validate request
        # 2. Get job details
        # 3. Get CV summary
        # 4. Generate messages
        # 5. Return response
    except Exception as e:
        # Log and return error response
```

**CV Summary Path Construction:**
```python
summary_path = Path(current_app.root_path) / 'process_cv/cv-data/processed' / f"{cv_filename}_summary.txt"
```

**File Reading:**
```python
with open(summary_path, 'r', encoding='utf-8') as f:
    cv_summary = f.read()
```

### Blueprint Registration

In `app.py`, add:
```python
from blueprints.linkedin_routes import linkedin_bp
app.register_blueprint(linkedin_bp)
```

### Error Response Patterns

| Scenario | Status Code | Error Message |
|----------|-------------|---------------|
| Missing job_url or cv_filename | 400 | "Missing job_url or cv_filename" |
| Job details fetch failed | 404 | "Could not fetch job details" |
| CV summary file not found | 404 | "CV summary not found: {path}" |
| Message generation failed | 500 | "Failed to generate messages" |
| Unexpected exception | 500 | str(e) |

### Request/Response Examples

**Request:**
```json
POST /linkedin/generate
Content-Type: application/json

{
  "job_url": "https://example.com/job/12345",
  "cv_filename": "john_doe_cv"
}
```

**Success Response:**
```json
HTTP 200 OK
Content-Type: application/json

{
  "success": true,
  "data": {
    "connection_request_hiring_manager": "Hi [Name], I saw the Senior Engineer role at Tech Corp. My background in Python seems like a great fit. I'd love to connect!",
    "peer_networking": "Hi [Name], I'm a Python Developer interested in Tech Corp. I see you're working there. I'd love to hear about the engineering culture.",
    "inmail_message": "Dear [Name],\n\nI am writing to express my interest in the Senior Engineer position..."
  }
}
```

**Error Response:**
```json
HTTP 404 Not Found
Content-Type: application/json

{
  "success": false,
  "error": "CV summary not found: process_cv/cv-data/processed/john_doe_cv_summary.txt"
}
```

---

## Definition of Done

- [x] `blueprints/linkedin_routes.py` created
- [x] `linkedin_bp` Blueprint defined with `/linkedin` prefix
- [x] `POST /linkedin/generate` endpoint implemented
- [x] Request validation for required fields
- [x] Authentication decorators applied
- [x] Job details retrieval integrated
- [x] CV summary file reading implemented
- [x] Message generation service called
- [x] JSON response format implemented (success and error cases)
- [x] Appropriate HTTP status codes returned
- [x] Error handling comprehensive and logged appropriately
- [x] Blueprint registered in `app.py`
- [x] Code follows project style guidelines
- [x] Docstrings complete
- [x] Manual testing passes (endpoint accessible and functional)

---

## Testing Checklist

### Manual API Tests

```
[x] Test successful message generation (200 OK)
[x] Test missing job_url (400 Bad Request)
[x] Test missing cv_filename (400 Bad Request)
[x] Test invalid job_url (404 Not Found)
[x] Test missing CV summary file (404 Not Found)
[x] Test unauthenticated request (redirect to login)
[x] Test non-admin user request (403 Forbidden or redirect)
[x] Test generation service failure (500 Internal Server Error)
[x] Verify JSON response format for success
[x] Verify JSON response format for errors
[x] Verify logging output at each step
```

### Manual Testing Steps

```
[x] Start Flask application
[x] Login as admin user
[x] Send POST request to /linkedin/generate with valid data
[x] Verify 200 OK response with messages
[x] Send request with missing job_url - verify 400 error
[x] Send request with invalid job_url - verify 404 error
[x] Send request with missing CV file - verify 404 error
[x] Check application logs for appropriate log entries
[x] Test from frontend (Story 7.3) - verify integration works
```

### Integration Testing

```
[x] Verify blueprint registered in app.py
[x] Verify route accessible at /linkedin/generate
[x] Verify authentication required
[x] Verify admin privileges required
[x] Verify integration with job_details_utils
[x] Verify integration with linkedin_generator service
[x] Verify CV summary file reading works
```

---

## Dependencies

**External Libraries:**
- `flask` - Already installed
- `flask_login` - Already installed
- `pathlib` - Python standard library
- `logging` - Python standard library
- `json` - Python standard library

**Internal Modules:**
- `services/linkedin_generator.py` - For message generation (Story 7.1)
- `job_details_utils.py` - For job details retrieval
- `utils/decorators.py` - For authentication decorators

**Data Files:**
- CV summary files in `process_cv/cv-data/processed/`
- Job details from external sources (via job_details_utils)

---

## Risk Assessment

**Risk:** CV summary file path construction could fail on different OS

**Mitigation:**
- Use `pathlib.Path` for cross-platform compatibility
- Use `current_app.root_path` for relative path construction
- Test on Windows (primary development environment)

**Risk:** Job details fetch could timeout or fail

**Mitigation:**
- Proper error handling with 404 response
- Clear error message to user
- Logging for debugging

**Risk:** Concurrent requests could cause issues

**Mitigation:**
- Flask handles concurrent requests
- No shared state in route function
- Each request is independent

---

## Notes for Developer

- **DO** follow existing blueprint patterns from `motivation_letter_routes.py`
- **DO** use `current_app.root_path` for file path construction
- **DO** use comprehensive error handling and logging
- **DO NOT** modify existing routes or blueprints
- **DO NOT** change authentication/authorization logic
- Blueprint registration in `app.py` is required for endpoint to be accessible
- Frontend integration happens in Story 7.3
- Test with real job URLs and CV files to verify end-to-end flow

---

## Implementation Details

### Actual Implementation

The module was implemented in `blueprints/linkedin_routes.py` with the following key features:

1. **Blueprint Definition:**
   ```python
   linkedin_bp = Blueprint('linkedin', __name__, url_prefix='/linkedin')
   ```

2. **Route Implementation:**
   ```python
   @linkedin_bp.route('/generate', methods=['POST'])
   @login_required
   @admin_required
   def generate_messages():
   ```

3. **Request Processing Flow:**
   - Parse JSON request data
   - Validate required fields (job_url, cv_filename)
   - Fetch job details using `get_job_details()`
   - Construct CV summary file path
   - Check file existence
   - Read CV summary with UTF-8 encoding
   - Call `generate_linkedin_messages()`
   - Return JSON response

4. **Error Handling:**
   - Try-except block around entire function
   - Specific error responses for different failure scenarios
   - Comprehensive logging at ERROR level
   - Appropriate HTTP status codes

5. **Response Format:**
   - Success: `{'success': True, 'data': messages}`
   - Error: `{'success': False, 'error': error_message}`

### Blueprint Registration

Added to `app.py`:
```python
from blueprints.linkedin_routes import linkedin_bp
app.register_blueprint(linkedin_bp)
```

# Story 9.2: API & Route Integration

## Story Info
**Epic:** [Epic 9: Job Stage Classification](epic-9-job-stage-classification.md)
**Status:** Planned
**Effort:** 3 Story Points

## Goal
Expose the application status management capabilities to the frontend via a RESTful API.

## Context
The frontend needs a way to fetch the current status of a job and update it when the user interacts with the UI (e.g., clicks "Mark as Applied" or drags a card).

## Acceptance Criteria
1.  **API Endpoints**:
    *   `POST /api/applications/status`: Updates the status of a job match.
        *   Input: `{ job_match_id: int, status: string }`
        *   Output: `{ success: bool, new_status: string, message: string }`
        *   Protected by `@login_required` decorator
        *   Returns appropriate HTTP status codes (200, 400, 404)
    *   `GET /api/applications`: Retrieves all application records (or a specific one).
        *   Optional query param: `?job_match_id=X` for specific record
        *   Protected by `@login_required` decorator
2.  **Integration with Job Fetching**:
    *   Modify existing job fetch queries to include status via LEFT JOIN
    *   All queries use `COALESCE(app.status, 'MATCHED')` pattern for backward compatibility
    *   Include `job_matches.id` in all responses (required for frontend API calls)
3.  **Error Handling**:
    *   Invalid status strings return 400 with clear error message
    *   Invalid/non-existent job_match_id returns 404
    *   Database errors return 500 with generic message (detailed log server-side)
4.  **Response Format**:
    *   Consistent JSON structure across all endpoints
    *   Include relevant metadata (timestamp, affected records, etc.)
5.  **Logging**:
    *   Log all status change operations with job_match_id, old status, new status
    *   Log authentication/authorization failures

## Technical Implementation Plan

### 1. Create Application Routes Blueprint
Create `blueprints/application_routes.py`:

```python
from flask import Blueprint, request, jsonify
from utils.decorators import login_required
from services.application_service import (
    update_application_status, 
    get_application_status,
    get_application_by_job_match_id
)
from models.application_status import ApplicationStatus
import logging

logger = logging.getLogger(__name__)

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
```

### 2. Register Blueprint
In `dashboard.py` or main app file, register the new blueprint:

```python
from blueprints.application_routes import application_bp

# Register blueprint
app.register_blueprint(application_bp)
```

### 3. Update Existing Job Fetch Queries
Modify queries in `dashboard.py` and `blueprints/job_matching_routes.py`:

**Example - Update view_all_matches:**
```python
def view_all_matches():
    # ... existing code ...
    
    # Modified query to include status
    query = '''
        SELECT 
            jm.id,
            jm.job_url,
            jm.job_title,
            jm.company_name,
            jm.overall_match,
            jm.reasoning,
            jm.cv_key,
            jm.timestamp,
            COALESCE(app.status, 'MATCHED') as status,
            app.updated_at,
            CASE 
                WHEN app.status = 'PREPARING' 
                    AND julianday('now') - julianday(app.updated_at) > 7 
                THEN 1 
                ELSE 0 
            END as is_stale
        FROM job_matches jm
        LEFT JOIN applications app ON jm.id = app.job_match_id
        WHERE jm.cv_key = ?
        ORDER BY jm.timestamp DESC
    '''
    
    # ... rest of the function ...
```

**Key Changes:**
- Always include `jm.id` in SELECT (needed by frontend)
- LEFT JOIN with applications table
- Use COALESCE for backward compatibility
- Include stale detection logic (for Story 9.5)
- Expose `updated_at` for frontend to show "last updated"

### 4. Update JSON API Responses
For any existing JSON endpoints that return job data:

```python
@job_matching_bp.route('/api/job-matches', methods=['GET'])
@login_required
def get_job_matches_api():
    # ... existing code ...
    
    # Add status to each match object
    matches = []
    for row in results:
        match = {
            'id': row[0],  # IMPORTANT: Include ID
            'job_url': row[1],
            'job_title': row[2],
            'company_name': row[3],
            'overall_match': row[4],
            'status': row[8],  # From COALESCE
            'is_stale': bool(row[10]),
            # ... other fields ...
        }
        matches.append(match)
    
    return jsonify({'success': True, 'matches': matches}), 200
```

### 5. Input Validation Best Practices
- Always validate and sanitize input
- Use uppercase comparison for status (case-insensitive)
- Return specific error messages for debugging (dev) but generic for security (prod)
- Log detailed errors server-side

### 6. Testing Checklist
- [ ] POST with valid data returns 200 and updates status
- [ ] POST with invalid status returns 400 with error message
- [ ] POST with non-existent job_match_id returns 404
- [ ] POST without authentication returns 401
- [ ] POST updates `updated_at` timestamp
- [ ] GET with job_match_id returns application data
- [ ] GET without job_match_id returns helpful message
- [ ] Job list queries include status field for all jobs
- [ ] Jobs without application records show 'MATCHED' status
- [ ] Status updates are logged appropriately

## Dependencies
- Story 9.1 (Database Schema) must be complete.

## Technical Notes

**Security Considerations:**
- All endpoints protected with `@login_required`
- Input validation prevents SQL injection (parameterized queries)
- Error messages don't leak sensitive information to client
- Detailed errors logged server-side only

**API Design Principles:**
- RESTful structure: `/api/applications/status` for status operations
- Consistent response format with `success`, `message`, and data fields
- Appropriate HTTP status codes (200, 400, 404, 500)
- Clear error messages for debugging

**Integration with Frontend:**
- Frontend needs to embed `job_match_id` in HTML data attributes
- JavaScript can call API using `fetch()` with JSON payload
- Responses include both old and new status for UI updates
- Status field always present in job data (never null)

**Backward Compatibility:**
- LEFT JOIN pattern ensures existing queries still work
- Jobs without application records treated as 'MATCHED'
- No breaking changes to existing API responses
- New fields added without removing old ones

**Performance Optimization:**
- Single query with JOIN more efficient than multiple queries
- Index on applications.status supports fast filtering
- COALESCE handled at database level (efficient)
- Query results can be cached if needed

**Error Scenarios to Handle:**
1. User tries to update non-existent job → 404
2. User provides invalid status string → 400 with valid options
3. Database connection fails → 500 with generic message
4. Missing authentication → 401 (handled by decorator)
5. Malformed JSON → 400 with parse error

**Future Enhancements (Out of Scope):**
- Batch status updates (update multiple jobs at once)
- Status transition history API
- Webhooks/notifications on status change
- Rate limiting for API endpoints

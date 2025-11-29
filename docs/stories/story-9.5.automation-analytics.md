# Story 9.5: Automation & Analytics

## Story Info
**Epic:** [Epic 9: Job Stage Classification](epic-9-job-stage-classification.md)
**Status:** Planned
**Effort:** 3 Story Points

## Goal
Implement smart automations to reduce manual effort and provide basic analytics on the job search progress.

## Context
To make the system feel "smart", it should infer status changes where possible (e.g., generating a letter implies "Preparing"). Users also need feedback on their funnel (e.g., how many jobs are in each stage).

## Acceptance Criteria
1.  **Auto-Transition on Letter Generation**:
    *   When user generates a motivation letter, status automatically updates to `PREPARING`.
    *   Only updates if current status is `MATCHED` or `INTERESTED` (doesn't override more advanced states).
    *   Update happens immediately on letter generation request (not on completion).
    *   Logged appropriately for audit trail.
2.  **Stale Detection**:
    *   Jobs in `PREPARING` status for > 7 days are visually flagged.
    *   Flag appears in both list view and Kanban board.
    *   Uses warning icon (⚠️) or clock icon with "Stale" tooltip.
    *   Calculation based on `updated_at` timestamp (accurate to the day).
3.  **Dashboard Analytics Widget**:
    *   Summary widget displays counts for each stage.
    *   Shows: MATCHED, INTERESTED, PREPARING, APPLIED, INTERVIEW, OFFER counts.
    *   Optional: Display REJECTED/ARCHIVED separately or as total.
    *   Updates on page load (no real-time required for MVP).
    *   Clean, compact design fits existing dashboard layout.
4.  **Data Accuracy**:
    *   Counts include jobs without application records (treated as MATCHED).
    *   Uses same LEFT JOIN pattern as other queries for consistency.
    *   Single efficient query for all counts.

## Technical Implementation Plan

### 1. Auto-Transition on Letter Generation

**Modify Motivation Letter Route (blueprints/motivation_letter_routes.py):**

```python
from services.application_service import update_application_status, get_application_status

@motivation_letter_bp.route('/generate', methods=['POST'])
@login_required
def generate_letter():
    """Generate motivation letter and auto-update status."""
    try:
        # ... existing letter generation code ...
        job_url = request.form.get('job_url')
        cv_filename = request.form.get('cv_filename')
        
        # Get job_match_id from job_url and cv
        db = JobMatchDatabase()
        db.create_connection()
        cursor = db.conn.cursor()
        
        # Query to find the job match
        cursor.execute('''
            SELECT id FROM job_matches 
            WHERE job_url = ? AND cv_key = ?
        ''', (job_url, cv_key))
        
        result = cursor.fetchone()
        db.close_connection()
        
        if result:
            job_match_id = result[0]
            
            # Check current status
            current_status = get_application_status(job_match_id)
            
            # Only update if in early stages
            if current_status in ['MATCHED', 'INTERESTED']:
                success = update_application_status(job_match_id, 'PREPARING')
                if success:
                    logger.info(f"Auto-transitioned job {job_match_id} to PREPARING on letter generation")
                else:
                    logger.warning(f"Failed to auto-transition job {job_match_id}")
        
        # ... continue with letter generation ...
        
    except Exception as e:
        logger.exception(f"Error in letter generation: {str(e)}")
        # Don't fail letter generation if status update fails
```

**Key Implementation Notes:**
- Update happens immediately when user clicks "Generate Letter"
- Doesn't block or fail if status update fails (letter generation continues)
- Only updates early-stage applications (respects workflow)
- Logged for debugging and audit purposes

### 2. Stale Detection Implementation

**Already implemented in Story 9.2 query pattern. Ensure it's used consistently:**

```sql
-- Example from job fetch query
SELECT 
    jm.id,
    jm.job_title,
    jm.company_name,
    jm.overall_match,
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
```

**Frontend already handles stale indicator (from Story 9.3):**
```html
{% if match.is_stale %}
<span class="text-warning ms-1" title="No updates in 7+ days">
    <i class="bi bi-clock-history"></i>
</span>
{% endif %}
```

**No additional work needed** - stale detection is built into the query pattern.

### 3. Dashboard Analytics Widget

**Create Analytics Function (in services/application_service.py or dashboard.py):**

```python
def get_application_pipeline_stats(cv_key=None):
    """
    Get count of jobs in each status stage.
    If cv_key is provided, filter by that CV.
    """
    db = JobMatchDatabase()
    db.create_connection()
    cursor = db.conn.cursor()
    
    # Query with LEFT JOIN to include jobs without application records
    query = '''
        SELECT 
            COALESCE(app.status, 'MATCHED') as status,
            COUNT(*) as count
        FROM job_matches jm
        LEFT JOIN applications app ON jm.id = app.job_match_id
    '''
    
    params = []
    if cv_key:
        query += ' WHERE jm.cv_key = ?'
        params.append(cv_key)
    
    query += ' GROUP BY COALESCE(app.status, "MATCHED")'
    
    cursor.execute(query, params)
    results = cursor.fetchall()
    db.close_connection()
    
    # Convert to dictionary
    stats = {
        'MATCHED': 0,
        'INTERESTED': 0,
        'PREPARING': 0,
        'APPLIED': 0,
        'INTERVIEW': 0,
        'OFFER': 0,
        'REJECTED': 0,
        'ARCHIVED': 0
    }
    
    for row in results:
        status, count = row
        if status in stats:
            stats[status] = count
    
    # Calculate totals
    stats['TOTAL_ACTIVE'] = (
        stats['MATCHED'] + 
        stats['INTERESTED'] + 
        stats['PREPARING'] + 
        stats['APPLIED'] + 
        stats['INTERVIEW'] + 
        stats['OFFER']
    )
    stats['TOTAL_CLOSED'] = stats['REJECTED'] + stats['ARCHIVED']
    stats['TOTAL_ALL'] = stats['TOTAL_ACTIVE'] + stats['TOTAL_CLOSED']
    
    return stats
```

**Update Dashboard Route:**

```python
@app.route('/dashboard')
@login_required
def dashboard():
    # ... existing code ...
    
    # Get selected CV
    selected_cv = session.get('selected_cv') or get_default_cv()
    
    # Get pipeline statistics
    pipeline_stats = get_application_pipeline_stats(selected_cv)
    
    return render_template(
        'index.html',
        # ... existing variables ...
        pipeline_stats=pipeline_stats
    )
```

**Create Widget Template Partial (templates/widgets/pipeline_stats.html):**

```html
<div class="card mb-3">
    <div class="card-header">
        <h5 class="mb-0">
            <i class="bi bi-bar-chart"></i> Application Pipeline
        </h5>
    </div>
    <div class="card-body">
        <div class="row text-center">
            <!-- Active Stages -->
            <div class="col-md-2 col-sm-4 mb-3">
                <div class="stat-box">
                    <div class="stat-number text-secondary">{{ pipeline_stats.MATCHED }}</div>
                    <div class="stat-label">Matched</div>
                </div>
            </div>
            <div class="col-md-2 col-sm-4 mb-3">
                <div class="stat-box">
                    <div class="stat-number text-primary">{{ pipeline_stats.INTERESTED }}</div>
                    <div class="stat-label">Interested</div>
                </div>
            </div>
            <div class="col-md-2 col-sm-4 mb-3">
                <div class="stat-box">
                    <div class="stat-number text-warning">{{ pipeline_stats.PREPARING }}</div>
                    <div class="stat-label">Preparing</div>
                </div>
            </div>
            <div class="col-md-2 col-sm-4 mb-3">
                <div class="stat-box">
                    <div class="stat-number text-success">{{ pipeline_stats.APPLIED }}</div>
                    <div class="stat-label">Applied</div>
                </div>
            </div>
            <div class="col-md-2 col-sm-4 mb-3">
                <div class="stat-box">
                    <div class="stat-number" style="color: #6f42c1;">{{ pipeline_stats.INTERVIEW }}</div>
                    <div class="stat-label">Interview</div>
                </div>
            </div>
            <div class="col-md-2 col-sm-4 mb-3">
                <div class="stat-box">
                    <div class="stat-number" style="color: #20c997;">{{ pipeline_stats.OFFER }}</div>
                    <div class="stat-label">Offer</div>
                </div>
            </div>
        </div>
        
        <!-- Summary Row -->
        <div class="row text-center border-top pt-3 mt-2">
            <div class="col-4">
                <strong>Active:</strong> {{ pipeline_stats.TOTAL_ACTIVE }}
            </div>
            <div class="col-4">
                <strong>Closed:</strong> {{ pipeline_stats.TOTAL_CLOSED }}
            </div>
            <div class="col-4">
                <strong>Total:</strong> {{ pipeline_stats.TOTAL_ALL }}
            </div>
        </div>
    </div>
</div>
```

**Include Widget in Dashboard (templates/index.html):**

```html
<!-- After existing dashboard content -->
{% include 'widgets/pipeline_stats.html' %}
```

**Add CSS for Stats Widget (static/css/styles.css):**

```css
.stat-box {
    padding: 1rem;
}

.stat-number {
    font-size: 2rem;
    font-weight: bold;
    line-height: 1;
    margin-bottom: 0.5rem;
}

.stat-label {
    font-size: 0.875rem;
    color: #6c757d;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* Mobile responsive */
@media (max-width: 576px) {
    .stat-number {
        font-size: 1.5rem;
    }
    
    .stat-label {
        font-size: 0.75rem;
    }
}
```

### 4. Testing Checklist
- [ ] Generate letter for MATCHED job → status becomes PREPARING
- [ ] Generate letter for INTERESTED job → status becomes PREPARING
- [ ] Generate letter for APPLIED job → status stays APPLIED (no downgrade)
- [ ] Letter generation succeeds even if status update fails
- [ ] Status change is logged appropriately
- [ ] Jobs in PREPARING for 7+ days show stale indicator (list view)
- [ ] Jobs in PREPARING for 7+ days show stale indicator (Kanban view)
- [ ] Dashboard widget displays accurate counts for all statuses
- [ ] Dashboard counts include jobs without application records
- [ ] Widget updates after status changes (on page reload)
- [ ] Widget displays correctly on mobile devices
- [ ] Stale calculation is accurate (test with manipulated dates)

## Dependencies
- Story 9.1 (Database Schema) must be complete.
- Story 9.2 (API Integration) must be complete.
- Story 9.3 (Frontend Controls) should be complete for consistent stale indicators.

## Technical Notes

**Auto-Transition Strategy:**
- **Trigger Point**: On user request to generate letter (not on completion)
- **Non-Blocking**: Status update failure doesn't prevent letter generation
- **State Guards**: Only transitions from MATCHED/INTERESTED to PREPARING
- **Rationale**: User generating letter is clear signal of preparation intent

**Why Not Update on Letter Completion:**
- Letter generation is background task (may take time)
- User expects immediate feedback
- Completion timing unpredictable (could fail, timeout)
- Simpler to update on user action than background thread completion

**Guard Against Status Downgrades:**
```python
# Only update if in early stages
if current_status in ['MATCHED', 'INTERESTED']:
    update_application_status(job_match_id, 'PREPARING')
# Otherwise, leave status unchanged
```

**This prevents scenarios like:**
- User already marked as APPLIED, generates another version of letter
- Status should remain APPLIED, not downgrade to PREPARING
- Guard ensures workflow integrity

**Stale Detection Algorithm:**
```sql
julianday('now') - julianday(app.updated_at) > 7
```
- Uses SQLite's `julianday()` function for date math
- Returns difference in days (floating point)
- Comparison > 7 means "more than 7 days old"
- Only applies to PREPARING status (could extend to others)

**Why 7 Days:**
- Reasonable timeframe to prepare/submit application
- Not too aggressive (won't nag after 2-3 days)
- Not too lenient (14 days is too long)
- Configurable in future if needed

**Analytics Performance:**
- Single query with GROUP BY is efficient
- LEFT JOIN ensures all jobs counted (even without app records)
- COALESCE handles missing records as MATCHED
- Result size small (max 8 rows, one per status)
- Can be cached if needed (refresh on page load is fine)

**Widget Design Principles:**
- Minimal, glanceable information
- Color-coded to match status badges
- Active vs Closed distinction clear
- Mobile-responsive layout
- Doesn't clutter dashboard

**Future Enhancements (Out of Scope):**
- Auto-transition to APPLIED when application actually sent
- Email reminders for stale applications
- Trend charts (applications over time)
- Conversion rates (MATCHED → APPLIED → INTERVIEW)
- Time-in-stage analytics
- Configurable stale threshold (per user)

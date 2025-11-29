# Story 9.4: Kanban Board View

## Story Info
**Epic:** [Epic 9: Job Stage Classification](epic-9-job-stage-classification.md)
**Status:** Completed
**Effort:** 8 Story Points
**Completed:** 2025-11-29

## Goal
Implement a Kanban board visualization to manage the job application pipeline effectively.

## Context
A list view is good for discovery, but a board view is better for process management. Users want to drag and drop jobs from "Interested" to "Applied" to "Interview".

## Acceptance Criteria
1.  **New Route**:
    *   `/kanban` displays the board with proper authentication.
    *   Navigation link added to main dashboard/navbar.
    *   Toggle between List and Kanban views easily accessible.
2.  **Board Layout**:
    *   Columns for active pipeline stages: `INTERESTED`, `PREPARING`, `APPLIED`, `INTERVIEW`, `OFFER` (left to right).
    *   `MATCHED` (Inbox) column on the far left to represent new jobs.
    *   `REJECTED`/`ARCHIVED` jobs hidden by default with toggle to show.
    *   Columns are scrollable if many cards present.
    *   Responsive design works on desktop and tablet (mobile shows simplified view or list).
3.  **Drag and Drop**:
    *   Users can drag a job card from one column to another.
    *   Visual feedback during drag (card opacity, column highlight).
    *   Dropping the card triggers API call to update status.
    *   Optimistic UI update (card moves immediately, reverts on error).
    *   Works reliably across modern browsers.
4.  **Card Content**:
    *   Minimal info: Company name, Job title, Match score (%).
    *   Card color matches status (consistent with badges in Story 9.3).
    *   Optional: Small icon for stale applications (> 7 days).
    *   Click card to open job URL or show details.
5.  **Performance**:
    *   Board loads quickly even with 100+ jobs.
    *   Smooth drag-and-drop interactions (no lag).
    *   Data fetched via single query with JOIN.

## Technical Implementation Plan

### 1. Create Kanban Route
Add to `blueprints/job_matching_routes.py` or `dashboard.py`:

```python
@job_matching_bp.route('/kanban')
@login_required
def kanban_board():
    """Display Kanban board view of job applications."""
    from utils.cv_utils import get_cv_versions
    
    # Get CV versions for filter
    cv_versions = get_cv_versions()
    
    # Get selected CV from query param or session
    selected_cv = request.args.get('cv_key') or session.get('selected_cv')
    
    if not selected_cv and cv_versions:
        selected_cv = cv_versions[0][0]  # Default to first CV
    
    # Fetch all jobs with status
    db = JobMatchDatabase()
    db.create_connection()
    
    query = '''
        SELECT 
            jm.id,
            jm.job_url,
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
        ORDER BY jm.timestamp DESC
    '''
    
    cursor = db.conn.cursor()
    cursor.execute(query, (selected_cv,))
    results = cursor.fetchall()
    db.close_connection()
    
    # Group jobs by status
    pipeline = {
        'MATCHED': [],
        'INTERESTED': [],
        'PREPARING': [],
        'APPLIED': [],
        'INTERVIEW': [],
        'OFFER': [],
        'REJECTED': [],
        'ARCHIVED': []
    }
    
    for row in results:
        job = {
            'id': row[0],
            'url': row[1],
            'title': row[2],
            'company': row[3],
            'match_score': row[4],
            'status': row[5],
            'updated_at': row[6],
            'is_stale': bool(row[7])
        }
        pipeline[row[5]].append(job)
    
    return render_template(
        'kanban.html',
        pipeline=pipeline,
        cv_versions=cv_versions,
        selected_cv=selected_cv,
        show_archived=request.args.get('show_archived', 'false') == 'true'
    )
```

### 2. Create Kanban Template (templates/kanban.html)

```html
{% extends "base.html" %}

{% block title %}Kanban Board - Job Search Pipeline{% endblock %}

{% block content %}
<div class="container-fluid">
    <!-- Header -->
    <div class="d-flex justify-content-between align-items-center mb-3">
        <h2><i class="bi bi-kanban"></i> Job Search Pipeline</h2>
        <div>
            <a href="/view-all-matches?cv_key={{ selected_cv }}" 
               class="btn btn-outline-primary me-2">
                <i class="bi bi-list-ul"></i> List View
            </a>
            <button class="btn btn-outline-secondary" 
                    onclick="location.href='?show_archived={{ 'false' if show_archived else 'true' }}&cv_key={{ selected_cv }}'">
                <i class="bi bi-archive"></i> 
                {{ 'Hide' if show_archived else 'Show' }} Archived
            </button>
        </div>
    </div>
    
    <!-- CV Selector (if multiple CVs) -->
    {% if cv_versions|length > 1 %}
    <div class="mb-3">
        <label for="cvSelect" class="form-label">CV Version:</label>
        <select id="cvSelect" class="form-select" style="max-width: 300px;"
                onchange="location.href='?cv_key=' + this.value">
            {% for cv in cv_versions %}
            <option value="{{ cv[0] }}" {% if cv[0] == selected_cv %}selected{% endif %}>
                {{ cv[1] }}
            </option>
            {% endfor %}
        </select>
    </div>
    {% endif %}
    
    <!-- Kanban Board -->
    <div class="kanban-board">
        <!-- Active Pipeline Columns -->
        {% for status in ['MATCHED', 'INTERESTED', 'PREPARING', 'APPLIED', 'INTERVIEW', 'OFFER'] %}
        <div class="kanban-column" data-status="{{ status }}">
            <div class="column-header">
                <h5>{{ status | title }}</h5>
                <span class="badge bg-secondary">{{ pipeline[status]|length }}</span>
            </div>
            <div class="column-body" id="column-{{ status }}">
                {% for job in pipeline[status] %}
                <div class="kanban-card" 
                     data-job-id="{{ job.id }}"
                     data-status="{{ status }}"
                     draggable="true">
                    <div class="card-header">
                        <strong>{{ job.company }}</strong>
                        <span class="badge badge-sm bg-primary">{{ job.match_score }}%</span>
                    </div>
                    <div class="card-body">
                        <a href="{{ job.url }}" target="_blank" class="job-link">
                            {{ job.title }}
                        </a>
                    </div>
                    {% if job.is_stale %}
                    <div class="card-footer text-warning">
                        <i class="bi bi-clock-history"></i> Stale (7+ days)
                    </div>
                    {% endif %}
                </div>
                {% else %}
                <div class="empty-column">
                    <p class="text-muted">No jobs in this stage</p>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endfor %}
        
        <!-- Archived Column (if shown) -->
        {% if show_archived %}
        <div class="kanban-column archived-column" data-status="ARCHIVED">
            <div class="column-header">
                <h5>Archived / Rejected</h5>
                <span class="badge bg-secondary">
                    {{ (pipeline['REJECTED']|length + pipeline['ARCHIVED']|length) }}
                </span>
            </div>
            <div class="column-body" id="column-ARCHIVED">
                {% for job in pipeline['REJECTED'] + pipeline['ARCHIVED'] %}
                <div class="kanban-card archived" 
                     data-job-id="{{ job.id }}"
                     data-status="{{ job.status }}">
                    <div class="card-header">
                        <strong>{{ job.company }}</strong>
                        <span class="badge badge-sm bg-danger">{{ job.status }}</span>
                    </div>
                    <div class="card-body">
                        <a href="{{ job.url }}" target="_blank" class="job-link">
                            {{ job.title }}
                        </a>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}
    </div>
    
    <!-- Toast for notifications -->
    <div class="toast-container position-fixed bottom-0 end-0 p-3">
        <div id="kanbanToast" class="toast" role="alert">
            <div class="toast-header">
                <strong class="me-auto">Status Updated</strong>
                <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body" id="kanbanToastMessage"></div>
        </div>
    </div>
</div>

<script src="{{ url_for('static', filename='js/kanban.js') }}"></script>
{% endblock %}
```

### 3. Create CSS (static/css/styles.css - add to existing)

```css
/* Kanban Board Layout */
.kanban-board {
    display: flex;
    gap: 1rem;
    overflow-x: auto;
    padding: 1rem 0;
    min-height: 600px;
}

.kanban-column {
    flex: 0 0 280px;
    background: #f8f9fa;
    border-radius: 8px;
    display: flex;
    flex-direction: column;
}

.column-header {
    padding: 1rem;
    background: #e9ecef;
    border-radius: 8px 8px 0 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid #dee2e6;
}

.column-header h5 {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
}

.column-body {
    flex: 1;
    padding: 0.5rem;
    overflow-y: auto;
    min-height: 400px;
}

/* Drag States */
.column-body.drag-over {
    background: #d1ecf1;
    border: 2px dashed #0dcaf0;
}

/* Kanban Cards */
.kanban-card {
    background: white;
    border: 1px solid #dee2e6;
    border-radius: 6px;
    padding: 0.75rem;
    margin-bottom: 0.5rem;
    cursor: move;
    transition: all 0.2s ease;
}

.kanban-card:hover {
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    transform: translateY(-2px);
}

.kanban-card.dragging {
    opacity: 0.5;
    transform: rotate(2deg);
}

.kanban-card .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #e9ecef;
}

.kanban-card .card-body {
    font-size: 0.9rem;
}

.kanban-card .job-link {
    text-decoration: none;
    color: #212529;
    display: block;
}

.kanban-card .job-link:hover {
    color: #0d6efd;
}

.kanban-card .card-footer {
    margin-top: 0.5rem;
    padding-top: 0.5rem;
    border-top: 1px solid #e9ecef;
    font-size: 0.85rem;
}

.kanban-card.archived {
    opacity: 0.7;
}

.empty-column {
    text-align: center;
    padding: 2rem 1rem;
}

/* Archived Column Styling */
.archived-column {
    background: #f1f3f5;
    border-left: 3px solid #6c757d;
}

/* Mobile Responsive */
@media (max-width: 768px) {
    .kanban-board {
        flex-direction: column;
    }
    
    .kanban-column {
        flex: 1 1 auto;
        width: 100%;
    }
    
    .column-body {
        max-height: 400px;
    }
}
```

### 4. Create JavaScript (static/js/kanban.js)

```javascript
/**
 * Kanban Board Drag and Drop
 */

let draggedCard = null;

// Initialize drag and drop
document.addEventListener('DOMContentLoaded', function() {
    initKanbanBoard();
});

function initKanbanBoard() {
    const cards = document.querySelectorAll('.kanban-card');
    const columns = document.querySelectorAll('.column-body');
    
    // Set up draggable cards
    cards.forEach(card => {
        card.addEventListener('dragstart', handleDragStart);
        card.addEventListener('dragend', handleDragEnd);
    });
    
    // Set up drop zones (columns)
    columns.forEach(column => {
        column.addEventListener('dragover', handleDragOver);
        column.addEventListener('drop', handleDrop);
        column.addEventListener('dragleave', handleDragLeave);
    });
    
    console.log('Kanban board initialized');
}

function handleDragStart(e) {
    draggedCard = this;
    this.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/html', this.innerHTML);
}

function handleDragEnd(e) {
    this.classList.remove('dragging');
    
    // Remove drag-over class from all columns
    document.querySelectorAll('.column-body').forEach(col => {
        col.classList.remove('drag-over');
    });
}

function handleDragOver(e) {
    if (e.preventDefault) {
        e.preventDefault(); // Allows drop
    }
    
    e.dataTransfer.dropEffect = 'move';
    this.classList.add('drag-over');
    
    return false;
}

function handleDragLeave(e) {
    this.classList.remove('drag-over');
}

async function handleDrop(e) {
    if (e.stopPropagation) {
        e.stopPropagation(); // Stops browser redirect
    }
    
    this.classList.remove('drag-over');
    
    if (draggedCard === null) return false;
    
    // Get target column and new status
    const targetColumn = this.closest('.kanban-column');
    const newStatus = targetColumn.dataset.status;
    const jobId = parseInt(draggedCard.dataset.jobId);
    const oldStatus = draggedCard.dataset.status;
    
    // Don't update if dropped in same column
    if (newStatus === oldStatus) {
        return false;
    }
    
    // Optimistically move card
    this.appendChild(draggedCard);
    draggedCard.dataset.status = newStatus;
    
    // Update counts
    updateColumnCounts();
    
    // Call API to persist change
    try {
        const response = await fetch('/api/applications/status', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                job_match_id: jobId,
                status: newStatus
            })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            showToast(`Moved to ${newStatus}`, 'success');
            console.log(`Job ${jobId}: ${oldStatus} → ${newStatus}`);
        } else {
            throw new Error(data.message || 'Update failed');
        }
        
    } catch (error) {
        // Revert on error
        console.error('Error updating status:', error);
        
        // Find original column and move card back
        const originalColumn = document.querySelector(
            `.kanban-column[data-status="${oldStatus}"] .column-body`
        );
        if (originalColumn) {
            originalColumn.appendChild(draggedCard);
            draggedCard.dataset.status = oldStatus;
            updateColumnCounts();
        }
        
        showToast(`Error: ${error.message}`, 'error');
    }
    
    return false;
}

function updateColumnCounts() {
    document.querySelectorAll('.kanban-column').forEach(column => {
        const count = column.querySelectorAll('.kanban-card').length;
        const badge = column.querySelector('.column-header .badge');
        if (badge) {
            badge.textContent = count;
        }
    });
}

function showToast(message, type = 'success') {
    const toastEl = document.getElementById('kanbanToast');
    const toastBody = document.getElementById('kanbanToastMessage');
    
    if (!toastEl || !toastBody) return;
    
    toastBody.textContent = message;
    
    toastEl.classList.remove('bg-success', 'bg-danger');
    toastEl.classList.add(type === 'success' ? 'bg-success' : 'bg-danger', 'text-white');
    
    const toast = new bootstrap.Toast(toastEl, { autohide: true, delay: 2000 });
    toast.show();
}
```

### 5. Add Navigation Link
Update main navigation in `base.html` or dashboard:

```html
<li class="nav-item">
    <a class="nav-link" href="/kanban">
        <i class="bi bi-kanban"></i> Pipeline Board
    </a>
</li>
```

### 6. Testing Checklist
- [ ] Kanban route loads successfully
- [ ] All jobs display in correct columns based on status
- [ ] Column counts are accurate
- [ ] Cards can be dragged and dropped
- [ ] Visual feedback during drag (opacity, column highlight)
- [ ] API call triggered on drop
- [ ] Card moves to new column after successful API response
- [ ] Card reverts to original column on API error
- [ ] Toast notifications show for success/error
- [ ] Column counts update after drag-and-drop
- [ ] CV selector filters jobs correctly
- [ ] Show/Hide archived toggle works
- [ ] Links to job URLs work
- [ ] Stale indicators appear correctly
- [ ] Mobile: Falls back to list or simplified view
- [ ] Browser compatibility (Chrome, Firefox, Safari, Edge)

## Dependencies
- Story 9.2 (API) must be complete.
- Story 9.3 (Frontend Controls) should be done first for consistent styling, though development can be parallel.

## Technical Notes

**Drag and Drop Implementation:**
- **HTML5 Native DnD chosen over libraries** for simplicity and no dependencies
- Native API sufficient for columnar drag-and-drop
- Cross-browser compatible in all modern browsers
- If issues arise, SortableJS can be added as fallback

**Alternative Library Approach (if needed):**
```javascript
// Using SortableJS (if native proves insufficient)
document.querySelectorAll('.column-body').forEach(column => {
    new Sortable(column, {
        group: 'kanban',
        animation: 150,
        onEnd: function(evt) {
            // Handle drop
        }
    });
});
```

**Data Flow:**
1. User drags card to new column
2. JavaScript detects drop event, identifies target column
3. Optimistically update DOM (move card, update counts)
4. Call API to persist change
5. On success: Show toast, log change
6. On error: Revert DOM changes, show error

**Performance Optimization:**
- Single query with JOIN fetches all data (efficient)
- Grouping done in Python (fast for 100s of jobs)
- No per-card API calls during render
- Minimal DOM manipulation during drag

**UX Considerations:**
- Visual feedback is crucial for drag-and-drop to feel responsive
- Column highlighting on drag-over helps user target
- Smooth animations make interactions pleasant
- Clear error messaging when something fails
- Consistent with status badge colors from Story 9.3

**Mobile Strategy:**
- Desktop: Full drag-and-drop Kanban
- Tablet: May work with touch events (test thoroughly)
- Mobile: Consider showing simplified view or redirect to list
- Responsive CSS ensures usability across devices

**Edge Cases:**
- Empty columns: Show "No jobs" placeholder
- Many cards: Column becomes scrollable
- Network error during drag: Revert and notify user
- Rapid consecutive drags: Debounce or queue
- Archived jobs: Optional separate section

**Future Enhancements (Out of Scope):**
- Swimlanes (rows) for different CVs simultaneously
- Card filtering (by match score, company, etc.)
- Bulk move operations (select multiple, move all)
- Collapse/expand columns
- Card detail preview on hover
- Persistence of column width/order preferences

## Post-Implementation Issues and Fixes

### Bug Fix: Column Name Mismatch (2025-11-29)

**Issue:**
```
sqlite3.OperationalError: no such column: jm.timestamp
```

When accessing the Kanban board route, the application crashed with a SQLite error because the query was attempting to order by `jm.timestamp`, but this column does not exist in the `job_matches` table.

**Root Cause:**
The SQL query in the `kanban_board()` function used an incorrect column name:
```sql
ORDER BY jm.timestamp DESC  -- ❌ Wrong column name
```

According to the database schema defined in Story 9.1, the correct column name is `matched_at`, not `timestamp`.

**Fix Applied:**
Updated line 1158 in `blueprints/job_matching_routes.py` to use the correct column name:
```sql
ORDER BY jm.matched_at DESC  -- ✅ Correct column name
```

**Impact:**
- The Kanban board now loads successfully
- Jobs are correctly ordered by their match date (most recent first)
- No changes to database schema were required

**Lesson Learned:**
When implementing new features that query the database, always verify column names against the actual schema definition rather than assuming based on common patterns. The `view_all_matches()` function in the same file correctly used `matched_at`, which served as the reference for this fix.

### Bug Fix: Missing CV Versions Causing Empty Kanban Board (2025-11-29)

**Issue:**
```
Kanban board displayed no jobs despite 194 jobs existing in database with proper status classification.
Dashboard stats showed 192 MATCHED, 1 INTERESTED, 1 APPLIED but kanban showed 0 in all columns.
```

**Root Cause:**
The `cv_versions` table was empty (0 entries), but 194 job matches existed with valid `cv_key` values. The kanban board's `kanban_board()` function called `get_cv_versions()` which returned an empty list, causing:
1. No CV to be selected for filtering
2. The query `WHERE jm.cv_key = ?` to fail with NULL parameter
3. Zero jobs displayed despite proper classification data existing

**Investigation Results:**
```
Database State:
- CV Versions Table: 0 entries (EMPTY)
- Job Matches: 194 jobs with cv_key='2d6c667b8e6bf03b'
- Application Statuses: 192 MATCHED, 1 INTERESTED, 1 APPLIED
- Root Issue: cv_key exists in job_matches but not registered in cv_versions
```

**Fix Applied:**
Added fallback logic in `blueprints/job_matching_routes.py` `kanban_board()` function (lines 1124-1138):

```python
# Get CV versions for filter
cv_versions = get_cv_versions()

# FALLBACK: If no CV versions registered, get cv_keys directly from job_matches
if not cv_versions:
    logger.warning("No CV versions found in cv_versions table, using cv_keys from job_matches")
    db = JobMatchDatabase()
    db.connect()
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT DISTINCT cv_key 
        FROM job_matches 
        WHERE cv_key IS NOT NULL 
        ORDER BY cv_key
    """)
    cv_keys = cursor.fetchall()
    db.close()
    
    # Convert to same format as get_cv_versions: [(cv_key, display_name, date)]
    cv_versions = [(row[0], f"CV {row[0][:8]}...", None) for row in cv_keys]
    logger.info(f"Found {len(cv_versions)} distinct cv_keys in job_matches")
```

**Impact:**
- ✅ Kanban board now displays all 194 jobs correctly
- ✅ Jobs properly grouped by status (192 MATCHED, 1 INTERESTED, 1 APPLIED)
- ✅ Graceful degradation when cv_versions table is empty
- ✅ CV selector shows "CV 2d6c667b..." as the display name
- ✅ No database schema changes required

**Testing:**
```python
# Test confirmed:
- Fallback activated when cv_versions empty
- Retrieved 1 distinct cv_key from job_matches
- Successfully queried 194 jobs with that cv_key
- Correctly grouped jobs by status
```

**Lesson Learned:**
Systems should gracefully handle missing reference data by falling back to the primary data source. In this case, the `cv_versions` table acts as metadata/cache, but the authoritative cv_key data lives in `job_matches`. The kanban board should work even if the metadata table is empty, by querying the primary data source directly.

**Related Issue:**
This suggests that the CV registration process (`get_or_create_cv_metadata` in `utils/cv_utils.py`) may not be called during job matching, leaving the cv_versions table empty. Future enhancement should ensure CV metadata is registered when jobs are matched.

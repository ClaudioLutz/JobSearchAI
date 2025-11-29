# Story 9.3: Frontend UI - Status Controls

## Story Info
**Epic:** [Epic 9: Job Stage Classification](epic-9-job-stage-classification.md)
**Status:** Planned
**Effort:** 5 Story Points

## Goal
Update the existing Job List and Job Detail views to display the current application status and allow users to change it.

## Context
Users currently see a list of matches. They need to see which ones they've already applied to or are preparing for. They also need a quick way to update this status without leaving the page.

## Acceptance Criteria
1.  **Status Display**:
    *   Each Job Card in the main list displays a color-coded status badge.
    *   Badge colors follow consistent theme: Grey (MATCHED), Blue (INTERESTED), Yellow (PREPARING), Green (APPLIED), Purple (INTERVIEW), Teal (OFFER), Red (REJECTED), Dark Grey (ARCHIVED).
    *   Job Detail modal (reasoning) displays current status prominently at the top.
    *   Status badge includes `job_match_id` in data attribute for JavaScript access.
2.  **Status Update Control**:
    *   Clean dropdown menu in Actions column for changing status (avoids UI clutter).
    *   Common transitions prioritized: One-click "Mark as Applied" button for MATCHED/INTERESTED states.
    *   Dropdown shows all available statuses for flexibility.
    *   Control is intuitive and accessible (keyboard navigation, tooltips).
3.  **Visual Feedback**:
    *   Optimistic UI update: Badge changes immediately on click.
    *   Toast notification confirms successful update (Bootstrap toast or similar).
    *   Error handling: Revert badge and show error message if API call fails.
    *   Loading state: Subtle indicator during API call (optional spinner).
4.  **Mobile Responsiveness**:
    *   Status badge wraps gracefully on smaller screens.
    *   Dropdown menu remains accessible on touch devices.
    *   Table layout adapts or provides horizontal scroll.
5.  **Data Attributes**:
    *   All job rows include `data-job-match-id` attribute.
    *   Status badge includes `data-current-status` attribute for easy updates.

## Technical Implementation Plan

### 1. Update Templates (all_matches.html or similar)

**Add Status Column to Table:**
```html
<table class="table table-hover">
    <thead>
        <tr>
            <th>Status</th>
            <th>Job Title</th>
            <th>Company</th>
            <th>Match %</th>
            <th>Actions</th>
        </tr>
    </thead>
    <tbody>
        {% for match in matches %}
        <tr data-job-match-id="{{ match.id }}">
            <!-- Status Badge Column -->
            <td>
                <span class="badge status-badge" 
                      data-current-status="{{ match.status }}"
                      data-job-match-id="{{ match.id }}">
                    {{ match.status | title }}
                </span>
                {% if match.is_stale %}
                <span class="text-warning ms-1" 
                      title="No updates in 7+ days">
                    <i class="bi bi-clock-history"></i>
                </span>
                {% endif %}
            </td>
            
            <!-- Job Title Column -->
            <td>
                <a href="{{ match.job_url }}" target="_blank">
                    {{ match.job_title }}
                </a>
            </td>
            
            <!-- Other columns... -->
            
            <!-- Actions Column -->
            <td>
                <div class="dropdown">
                    <button class="btn btn-sm btn-outline-secondary dropdown-toggle" 
                            type="button" 
                            data-bs-toggle="dropdown">
                        Actions
                    </button>
                    <ul class="dropdown-menu">
                        <!-- Quick Actions for Common Transitions -->
                        {% if match.status in ['MATCHED', 'INTERESTED'] %}
                        <li>
                            <a class="dropdown-item quick-action" 
                               href="#"
                               onclick="updateStatus({{ match.id }}, 'APPLIED'); return false;">
                                <i class="bi bi-check-circle"></i> Mark as Applied
                            </a>
                        </li>
                        <li><hr class="dropdown-divider"></li>
                        {% endif %}
                        
                        <!-- Status Change Submenu -->
                        <li class="dropend">
                            <a class="dropdown-item dropdown-toggle" href="#">
                                Change Status
                            </a>
                            <ul class="dropdown-menu status-dropdown">
                                <li><a class="dropdown-item" href="#" 
                                       onclick="updateStatus({{ match.id }}, 'INTERESTED'); return false;">
                                    Interested
                                </a></li>
                                <li><a class="dropdown-item" href="#" 
                                       onclick="updateStatus({{ match.id }}, 'PREPARING'); return false;">
                                    Preparing
                                </a></li>
                                <li><a class="dropdown-item" href="#" 
                                       onclick="updateStatus({{ match.id }}, 'APPLIED'); return false;">
                                    Applied
                                </a></li>
                                <li><a class="dropdown-item" href="#" 
                                       onclick="updateStatus({{ match.id }}, 'INTERVIEW'); return false;">
                                    Interview
                                </a></li>
                                <li><a class="dropdown-item" href="#" 
                                       onclick="updateStatus({{ match.id }}, 'OFFER'); return false;">
                                    Offer
                                </a></li>
                                <li><hr class="dropdown-divider"></li>
                                <li><a class="dropdown-item text-danger" href="#" 
                                       onclick="updateStatus({{ match.id }}, 'REJECTED'); return false;">
                                    Rejected
                                </a></li>
                                <li><a class="dropdown-item text-muted" href="#" 
                                       onclick="updateStatus({{ match.id }}, 'ARCHIVED'); return false;">
                                    Archive
                                </a></li>
                            </ul>
                        </li>
                        
                        <!-- Other existing actions -->
                        <li><hr class="dropdown-divider"></li>
                        <li><a class="dropdown-item" href="#" onclick="viewReasoning(...)">
                            View Reasoning
                        </a></li>
                        <!-- ... other actions ... -->
                    </ul>
                </div>
            </td>
        </tr>
        {% endfor %}
    </tbody>
</table>

<!-- Toast Container for Notifications -->
<div class="toast-container position-fixed bottom-0 end-0 p-3">
    <div id="statusToast" class="toast" role="alert">
        <div class="toast-header">
            <strong class="me-auto">Status Updated</strong>
            <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
        </div>
        <div class="toast-body" id="toastMessage">
            <!-- Dynamic message -->
        </div>
    </div>
</div>
```

### 2. CSS Styling (static/css/styles.css)

**Status Badge Colors:**
```css
/* Status Badge Base Styles */
.status-badge {
    font-weight: 500;
    font-size: 0.85rem;
    padding: 0.35em 0.65em;
    cursor: pointer;
    transition: all 0.2s ease;
}

.status-badge:hover {
    opacity: 0.8;
    transform: scale(1.05);
}

/* Status-Specific Colors */
.status-badge[data-current-status="MATCHED"] {
    background-color: #6c757d;
    color: white;
}

.status-badge[data-current-status="INTERESTED"] {
    background-color: #0d6efd;
    color: white;
}

.status-badge[data-current-status="PREPARING"] {
    background-color: #ffc107;
    color: #000;
}

.status-badge[data-current-status="APPLIED"] {
    background-color: #198754;
    color: white;
}

.status-badge[data-current-status="INTERVIEW"] {
    background-color: #6f42c1;
    color: white;
}

.status-badge[data-current-status="OFFER"] {
    background-color: #20c997;
    color: white;
}

.status-badge[data-current-status="REJECTED"] {
    background-color: #dc3545;
    color: white;
}

.status-badge[data-current-status="ARCHIVED"] {
    background-color: #343a40;
    color: white;
}

/* Loading State */
.status-badge.updating {
    opacity: 0.6;
    pointer-events: none;
}

.status-badge.updating::after {
    content: " ...";
    animation: dots 1s infinite;
}

@keyframes dots {
    0%, 20% { content: " ."; }
    40% { content: " .."; }
    60%, 100% { content: " ..."; }
}

/* Mobile Responsiveness */
@media (max-width: 768px) {
    .status-badge {
        font-size: 0.75rem;
        padding: 0.25em 0.5em;
    }
    
    .dropdown-menu.status-dropdown {
        max-height: 300px;
        overflow-y: auto;
    }
}
```

### 3. JavaScript Implementation (static/js/status_management.js)

**Create new JS file or add to existing:**
```javascript
/**
 * Status Management Functions
 */

// Status color mapping (for dynamic updates)
const STATUS_COLORS = {
    'MATCHED': '#6c757d',
    'INTERESTED': '#0d6efd',
    'PREPARING': '#ffc107',
    'APPLIED': '#198754',
    'INTERVIEW': '#6f42c1',
    'OFFER': '#20c997',
    'REJECTED': '#dc3545',
    'ARCHIVED': '#343a40'
};

/**
 * Update job application status
 * @param {number} jobMatchId - The job match ID
 * @param {string} newStatus - The new status to set
 */
async function updateStatus(jobMatchId, newStatus) {
    const badge = document.querySelector(
        `.status-badge[data-job-match-id="${jobMatchId}"]`
    );
    
    if (!badge) {
        console.error('Badge not found for job:', jobMatchId);
        return;
    }
    
    const oldStatus = badge.dataset.currentStatus;
    
    // Optimistic UI update
    badge.textContent = newStatus.charAt(0) + newStatus.slice(1).toLowerCase();
    badge.dataset.currentStatus = newStatus;
    badge.classList.add('updating');
    
    try {
        const response = await fetch('/api/applications/status', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                job_match_id: jobMatchId,
                status: newStatus
            })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            // Success - update complete
            badge.classList.remove('updating');
            showToast(`Status updated to ${newStatus}`, 'success');
            
            // Log for debugging
            console.log(`Status updated: ${oldStatus} → ${newStatus}`);
        } else {
            // API returned error
            throw new Error(data.message || 'Failed to update status');
        }
        
    } catch (error) {
        // Revert on error
        console.error('Error updating status:', error);
        badge.textContent = oldStatus.charAt(0) + oldStatus.slice(1).toLowerCase();
        badge.dataset.currentStatus = oldStatus;
        badge.classList.remove('updating');
        
        showToast(`Error: ${error.message}`, 'error');
    }
}

/**
 * Show toast notification
 * @param {string} message - Message to display
 * @param {string} type - Type of notification ('success' or 'error')
 */
function showToast(message, type = 'success') {
    const toastEl = document.getElementById('statusToast');
    const toastBody = document.getElementById('toastMessage');
    
    if (!toastEl || !toastBody) {
        console.warn('Toast elements not found');
        return;
    }
    
    // Update message
    toastBody.textContent = message;
    
    // Update styling based on type
    toastEl.classList.remove('bg-success', 'bg-danger');
    if (type === 'success') {
        toastEl.classList.add('bg-success', 'text-white');
    } else {
        toastEl.classList.add('bg-danger', 'text-white');
    }
    
    // Show toast
    const toast = new bootstrap.Toast(toastEl, {
        autohide: true,
        delay: 3000
    });
    toast.show();
}

/**
 * Initialize status management on page load
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('Status management initialized');
    
    // Optional: Add tooltips to status badges
    const badges = document.querySelectorAll('.status-badge');
    badges.forEach(badge => {
        badge.setAttribute('title', 'Click to change status');
        badge.style.cursor = 'help';
    });
});
```

### 4. Template Integration Points

**Include JavaScript in template:**
```html
<!-- At bottom of all_matches.html -->
<script src="{{ url_for('static', filename='js/status_management.js') }}"></script>
```

**Add to Job Detail Modal (if exists):**
```html
<!-- In reasoning modal or job detail modal -->
<div class="modal-header">
    <h5 class="modal-title">
        Job Details
        <span class="badge status-badge ms-2" 
              data-current-status="{{ job.status }}"
              data-job-match-id="{{ job.id }}">
            {{ job.status | title }}
        </span>
    </h5>
</div>
```

### 5. Testing Checklist
- [ ] Status badges display correctly with proper colors
- [ ] Clicking "Mark as Applied" updates status immediately
- [ ] Dropdown menu shows all status options
- [ ] Status change triggers API call with correct payload
- [ ] Optimistic UI update works (badge changes immediately)
- [ ] Success toast appears after successful update
- [ ] Error toast appears and badge reverts on failure
- [ ] Status persists after page refresh
- [ ] Multiple jobs can have status updated independently
- [ ] Stale indicator shows for jobs in PREPARING > 7 days
- [ ] Mobile: Dropdown works on touch devices
- [ ] Mobile: Status badge wraps or truncates appropriately
- [ ] Keyboard navigation works for dropdowns
- [ ] Console logs show no errors

## Dependencies
- Story 9.2 (API) must be complete.

## Technical Notes

**UI/UX Design Principles:**
- **Consistency**: Same color scheme across all views (list, Kanban, modals)
- **Clarity**: Status always visible without requiring interaction
- **Efficiency**: Common actions (Mark as Applied) require single click
- **Flexibility**: All statuses accessible via dropdown for edge cases
- **Feedback**: Immediate visual response + confirmation toast

**Implementation Strategy:**
1. Start with basic badge display (read-only)
2. Add dropdown with status options
3. Implement API call with optimistic updates
4. Add error handling and revert logic
5. Polish with animations and toasts

**Common Pitfalls to Avoid:**
- Don't clutter every row with multiple buttons
- Don't require multiple clicks for common actions
- Don't hide status behind modal/tooltip only
- Don't forget mobile users (touch-friendly)
- Don't skip error handling (network failures)

**Accessibility Considerations:**
- Use semantic HTML (proper button/link elements)
- Include ARIA labels for screen readers
- Ensure keyboard navigation works
- Provide text alternatives for icons
- Maintain sufficient color contrast

**Browser Compatibility:**
- Use `fetch()` API (supported in all modern browsers)
- Bootstrap 5 dropdowns work cross-browser
- CSS Grid/Flexbox for responsive layout
- Test on Chrome, Firefox, Safari, Edge

**Performance Considerations:**
- Batch DOM updates if updating multiple statuses
- Debounce rapid clicks to prevent duplicate API calls
- Use event delegation for dynamic content
- Minimize reflows/repaints during updates

**Future Enhancements (Out of Scope):**
- Keyboard shortcuts for status changes (e.g., Ctrl+A for Applied)
- Bulk status update (select multiple jobs, change all)
- Status change confirmation dialog for REJECTED
- Undo/redo for status changes
- Custom status colors per user preference

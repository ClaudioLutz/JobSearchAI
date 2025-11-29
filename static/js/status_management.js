/**
 * Status Management Functions
 * Part of Epic 9: Job Stage Classification
 * Story 9.3: Frontend UI - Status Controls
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
    badge.textContent = formatStatusText(newStatus);
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
            showToast(`Status updated to ${formatStatusText(newStatus)}`, 'success');
            
            // Log for debugging
            console.log(`Status updated: ${oldStatus} → ${newStatus}`);
        } else {
            // API returned error
            throw new Error(data.message || 'Failed to update status');
        }
        
    } catch (error) {
        // Revert on error
        console.error('Error updating status:', error);
        badge.textContent = formatStatusText(oldStatus);
        badge.dataset.currentStatus = oldStatus;
        badge.classList.remove('updating');
        
        showToast(`Error: ${error.message}`, 'error');
    }
}

/**
 * Format status text for display
 * @param {string} status - Status string
 * @returns {string} Formatted status text
 */
function formatStatusText(status) {
    return status.charAt(0) + status.slice(1).toLowerCase();
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
    toastEl.classList.remove('bg-success', 'bg-danger', 'text-white');
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
        badge.setAttribute('title', 'Current application status');
    });
});

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

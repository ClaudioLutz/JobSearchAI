/**
 * Search Term Manager
 * 
 * Manages search terms in the dashboard via REST API
 * Provides functionality to add, edit, and delete search terms
 */

// State management
let searchTerms = [];
let baseUrl = '';

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeSearchTermManager();
    populateCombinedSearchTermDropdown();
});

/**
 * Initialize the search term manager
 */
async function initializeSearchTermManager() {
    // Check if the search term manager section exists
    const managerSection = document.getElementById('search-term-manager');
    if (!managerSection) {
        return; // Not on the dashboard page
    }

    // Set up event listeners
    const addButton = document.getElementById('btn-add-term');
    if (addButton) {
        addButton.addEventListener('click', showAddForm);
    }

    const cancelButton = document.getElementById('btn-cancel-add');
    if (cancelButton) {
        cancelButton.addEventListener('click', hideAddForm);
    }

    const saveButton = document.getElementById('btn-save-term');
    if (saveButton) {
        saveButton.addEventListener('click', saveSearchTerm);
    }

    const templateSelect = document.getElementById('term-template');
    if (templateSelect) {
        templateSelect.addEventListener('change', applyTemplate);
    }

    const termInput = document.getElementById('term-input');
    if (termInput) {
        termInput.addEventListener('input', updatePreview);
    }

    // Load initial search terms
    await loadSearchTerms();
}

/**
 * Load search terms from API
 */
async function loadSearchTerms() {
    try {
        const response = await fetch('/api/settings/search_terms');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        searchTerms = data.search_terms || [];
        baseUrl = data.base_url || '';
        
        renderSearchTerms();
    } catch (error) {
        console.error('Error loading search terms:', error);
        showToast('Failed to load search terms', 'error');
    }
}

/**
 * Render search terms in the DOM
 */
function renderSearchTerms() {
    const container = document.getElementById('search-terms-list');
    if (!container) return;

    if (searchTerms.length === 0) {
        container.innerHTML = '<p class="text-muted">No search terms configured. Add one to get started.</p>';
        return;
    }

    let html = '<div class="search-terms-container">';
    
    searchTerms.forEach((term, index) => {
        const previewUrl = baseUrl.replace('{search_term}', escapeHtml(term)) + '1';
        
        html += `
            <div class="search-term-item" data-index="${index}">
                <span class="term-label">${escapeHtml(term)}</span>
                <div class="term-actions">
                    <button class="btn-icon" onclick="editSearchTerm(${index})" title="Edit term">
                        ✏️
                    </button>
                    <button class="btn-icon" onclick="deleteSearchTerm(${index})" title="Delete term">
                        🗑️
                    </button>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

/**
 * Show the add term form
 */
function showAddForm() {
    const form = document.getElementById('add-term-form');
    const button = document.getElementById('btn-add-term');
    
    if (form) {
        form.style.display = 'block';
    }
    if (button) {
        button.style.display = 'none';
    }
    
    // Clear form
    const termInput = document.getElementById('term-input');
    const templateSelect = document.getElementById('term-template');
    
    if (termInput) {
        termInput.value = '';
    }
    if (templateSelect) {
        templateSelect.value = '';
    }
    
    updatePreview();
}

/**
 * Hide the add term form
 */
function hideAddForm() {
    const form = document.getElementById('add-term-form');
    const button = document.getElementById('btn-add-term');
    
    if (form) {
        form.style.display = 'none';
    }
    if (button) {
        button.style.display = 'block';
    }
}

/**
 * Apply a template to the term input
 */
function applyTemplate() {
    const templateSelect = document.getElementById('term-template');
    const termInput = document.getElementById('term-input');
    
    if (!templateSelect || !termInput) return;
    
    const template = templateSelect.value;
    
    if (template) {
        // For templates with placeholders, provide sensible defaults
        let filledTemplate = template;
        
        // Replace common placeholders
        filledTemplate = filledTemplate.replace('{role}', 'Software-Engineer');
        filledTemplate = filledTemplate.replace('{percentage}', '80-bis-100');
        
        termInput.value = filledTemplate;
    }
    
    updatePreview();
}

/**
 * Update the URL preview
 */
function updatePreview() {
    const termInput = document.getElementById('term-input');
    const preview = document.getElementById('term-placeholder');
    
    if (!termInput || !preview) return;
    
    const term = termInput.value.trim() || '[term]';
    preview.textContent = escapeHtml(term);
}

/**
 * Save a new search term
 */
async function saveSearchTerm() {
    const termInput = document.getElementById('term-input');
    if (!termInput) return;
    
    const term = termInput.value.trim();
    
    if (!term) {
        showToast('Please enter a search term', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/settings/search_terms', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ search_term: term })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            showToast('Search term added successfully', 'success');
            hideAddForm();
            await loadSearchTerms();
        } else {
            showToast(data.error || 'Failed to add search term', 'error');
        }
    } catch (error) {
        console.error('Error saving search term:', error);
        showToast('Failed to save search term', 'error');
    }
}

/**
 * Edit a search term
 * @param {number} index - Index of the term to edit
 */
async function editSearchTerm(index) {
    if (index < 0 || index >= searchTerms.length) return;
    
    const currentTerm = searchTerms[index];
    const newTerm = prompt('Edit search term:', currentTerm);
    
    if (newTerm === null || newTerm.trim() === '') {
        return; // User cancelled or entered empty string
    }
    
    if (newTerm.trim() === currentTerm) {
        return; // No change
    }
    
    await updateSearchTerm(index, newTerm.trim());
}

/**
 * Update a search term
 * @param {number} index - Index of the term to update
 * @param {string} newTerm - New term value
 */
async function updateSearchTerm(index, newTerm) {
    try {
        const response = await fetch(`/api/settings/search_terms/${index}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ search_term: newTerm })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            showToast('Search term updated successfully', 'success');
            await loadSearchTerms();
        } else {
            showToast(data.error || 'Failed to update search term', 'error');
        }
    } catch (error) {
        console.error('Error updating search term:', error);
        showToast('Failed to update search term', 'error');
    }
}

/**
 * Delete a search term
 * @param {number} index - Index of the term to delete
 */
async function deleteSearchTerm(index) {
    if (index < 0 || index >= searchTerms.length) return;
    
    const term = searchTerms[index];
    
    if (!confirm(`Are you sure you want to delete "${term}"?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/settings/search_terms/${index}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            showToast('Search term deleted successfully', 'success');
            await loadSearchTerms();
        } else {
            showToast(data.error || 'Failed to delete search term', 'error');
        }
    } catch (error) {
        console.error('Error deleting search term:', error);
        showToast('Failed to delete search term', 'error');
    }
}

/**
 * Show a toast notification
 * @param {string} message - Message to display
 * @param {string} type - Type of toast (success, error, info)
 */
function showToast(message, type = 'info') {
    // Remove any existing toasts
    const existingToasts = document.querySelectorAll('.toast');
    existingToasts.forEach(toast => toast.remove());
    
    // Create new toast
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    // Trigger animation
    setTimeout(() => {
        toast.classList.add('show');
    }, 10);
    
    // Remove after 3 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 3000);
}

/**
 * Escape HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Populate the combined process search term dropdown
 */
async function populateCombinedSearchTermDropdown() {
    const dropdown = document.getElementById('combined_search_term');
    if (!dropdown) {
        return; // Not on the combined process form
    }

    try {
        const response = await fetch('/api/settings/search_terms');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        const terms = data.search_terms || [];
        
        // Clear existing options except the placeholder
        dropdown.innerHTML = '<option value="">Select a search term</option>';
        
        // Add search terms as options
        terms.forEach(term => {
            const option = document.createElement('option');
            option.value = term;
            option.textContent = term;
            dropdown.appendChild(option);
        });
        
        // If no terms available, show message
        if (terms.length === 0) {
            const option = document.createElement('option');
            option.value = '';
            option.textContent = 'No search terms configured - add one in Setup & Data tab';
            option.disabled = true;
            dropdown.appendChild(option);
        }
    } catch (error) {
        console.error('Error loading search terms for combined process:', error);
        const option = document.createElement('option');
        option.value = '';
        option.textContent = 'Error loading search terms';
        option.disabled = true;
        dropdown.appendChild(option);
    }
}

// Make functions globally available
window.editSearchTerm = editSearchTerm;
window.deleteSearchTerm = deleteSearchTerm;
window.showAddForm = showAddForm;
window.hideAddForm = hideAddForm;
window.saveSearchTerm = saveSearchTerm;
window.applyTemplate = applyTemplate;
window.populateCombinedSearchTermDropdown = populateCombinedSearchTermDropdown;

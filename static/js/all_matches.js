// All Matches View JavaScript
// Handles filtering, pagination, selection, and export features

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
    updateBulkActions();
});

function setupEventListeners() {
    // Select all checkbox in header
    const selectAllHeader = document.getElementById('select-all-header');
    if (selectAllHeader) {
        selectAllHeader.addEventListener('change', toggleAllCheckboxes);
    }
    
    // Individual job checkboxes
    document.querySelectorAll('.job-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', updateBulkActions);
    });
}

function toggleAllCheckboxes() {
    const selectAll = document.getElementById('select-all-header').checked;
    document.querySelectorAll('.job-checkbox').forEach(checkbox => {
        checkbox.checked = selectAll;
    });
    updateBulkActions();
}

function selectAll() {
    document.querySelectorAll('.job-checkbox').forEach(checkbox => {
        checkbox.checked = true;
    });
    const headerCheckbox = document.getElementById('select-all-header');
    if (headerCheckbox) {
        headerCheckbox.checked = true;
    }
    updateBulkActions();
}

function deselectAll() {
    document.querySelectorAll('.job-checkbox').forEach(checkbox => {
        checkbox.checked = false;
    });
    const headerCheckbox = document.getElementById('select-all-header');
    if (headerCheckbox) {
        headerCheckbox.checked = false;
    }
    updateBulkActions();
}

function updateBulkActions() {
    const checkboxes = document.querySelectorAll('.job-checkbox:checked');
    const generateButton = document.getElementById('btn-generate-letters');
    
    if (generateButton) {
        generateButton.disabled = checkboxes.length === 0;
        generateButton.textContent = `Generate Letters for Selected (${checkboxes.length})`;
    }
    
    // Update header checkbox state
    const allCheckboxes = document.querySelectorAll('.job-checkbox');
    const headerCheckbox = document.getElementById('select-all-header');
    if (headerCheckbox && allCheckboxes.length > 0) {
        headerCheckbox.checked = checkboxes.length === allCheckboxes.length;
    }
}

function getSelectedJobs() {
    const selected = [];
    document.querySelectorAll('.job-checkbox:checked').forEach(checkbox => {
        selected.push(checkbox.value);
    });
    return selected;
}

function viewDetails(jobUrl) {
    // Open job URL in new tab
    window.open(jobUrl, '_blank');
}

function generateSingle(jobUrl) {
    // Navigate to letter generation with job URL
    window.location.href = `/motivation_letter/generate?job_url=${encodeURIComponent(jobUrl)}`;
}

function generateLetters() {
    const selectedJobs = getSelectedJobs();
    if (selectedJobs.length === 0) {
        alert('Please select at least one job');
        return;
    }
    
    // Navigate to bulk letter generation
    const jobUrls = selectedJobs.join(',');
    window.location.href = `/motivation_letter/generate_bulk?job_urls=${encodeURIComponent(jobUrls)}`;
}

function exportToCSV() {
    const table = document.querySelector('.results-table');
    if (!table) {
        alert('No results to export');
        return;
    }
    
    // Build CSV content
    let csv = [];
    
    // Headers (skip checkbox column)
    const headers = [];
    table.querySelectorAll('thead th').forEach((th, index) => {
        if (index > 0) { // Skip checkbox column
            headers.push(th.textContent.trim());
        }
    });
    csv.push(headers.join(','));
    
    // Data rows
    table.querySelectorAll('tbody tr').forEach(row => {
        const values = [];
        row.querySelectorAll('td').forEach((td, index) => {
            if (index === 0) return; // Skip checkbox column
            
            let text = td.textContent.trim();
            // Clean up the text
            text = text.replace(/\s+/g, ' '); // Replace multiple spaces with single space
            text = text.replace(/\n/g, ' '); // Replace newlines with space
            
            // Escape commas and quotes
            if (text.includes(',') || text.includes('"') || text.includes('\n')) {
                text = `"${text.replace(/"/g, '""')}"`;
            }
            values.push(text);
        });
        if (values.length > 0) {
            csv.push(values.join(','));
        }
    });
    
    // Create download
    const csvContent = csv.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    const csvTimestamp = new Date().toISOString().split('T')[0];
    link.setAttribute('href', url);
    link.setAttribute('download', `job_matches_${csvTimestamp}.csv`);
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function exportToMarkdown() {
    const table = document.querySelector('.results-table');
    if (!table) {
        alert('No results to export');
        return;
    }
    
    // Build Markdown content
    let markdown = ['# Job Matches Report\n'];
    const timestamp = new Date().toLocaleString();
    markdown.push(`Generated: ${timestamp}\n`);
    
    // Get summary info
    const summaryText = document.querySelector('.results-summary p')?.textContent || 'No summary available';
    markdown.push(`${summaryText}\n\n`);
    
    // Table headers (skip checkbox column)
    const headers = [];
    table.querySelectorAll('thead th').forEach((th, index) => {
        if (index > 0) { // Skip checkbox column
            headers.push(th.textContent.trim());
        }
    });
    markdown.push('| ' + headers.join(' | ') + ' |');
    markdown.push('|' + headers.map(() => '---').join('|') + '|');
    
    // Table rows
    table.querySelectorAll('tbody tr').forEach(row => {
        const values = [];
        row.querySelectorAll('td').forEach((td, index) => {
            if (index === 0) return; // Skip checkbox column
            
            let text = td.textContent.trim();
            // Clean up text for markdown
            text = text.replace(/\s+/g, ' '); // Replace multiple spaces
            text = text.replace(/\|/g, '\\|'); // Escape pipes
            values.push(text);
        });
        if (values.length > 0) {
            markdown.push('| ' + values.join(' | ') + ' |');
        }
    });
    
    // Create download
    const mdContent = markdown.join('\n');
    const blob = new Blob([mdContent], { type: 'text/markdown;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    const mdTimestamp = new Date().toISOString().split('T')[0];
    link.setAttribute('href', url);
    link.setAttribute('download', `job_matches_${mdTimestamp}.md`);
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function resetFilters() {
    // Clear all filter inputs
    document.getElementById('search_term').value = '';
    document.getElementById('cv_key').value = '';
    document.getElementById('min_score').value = '0';
    document.getElementById('location').value = '';
    document.getElementById('date_from').value = '';
    document.getElementById('date_to').value = '';
    document.getElementById('sort_by').value = 'overall_match DESC';
    
    // Submit form to reload without filters
    document.getElementById('filter-form').submit();
}

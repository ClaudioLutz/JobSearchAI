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

function viewReasoning(jobUrl) {
    // Fetch reasoning from database and show in modal
    fetch(`/job_matching/api/job-reasoning?url=${encodeURIComponent(jobUrl)}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Populate modal with reasoning
                document.getElementById('reasoning-job-title').textContent = 
                    `${data.job_title} - ${data.company_name}`;
                document.getElementById('reasoning-content').textContent = data.reasoning;
                // Show modal
                const modal = new bootstrap.Modal(document.getElementById('reasoningModal'));
                modal.show();
            } else {
                alert('Failed to load reasoning: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error fetching reasoning:', error);
            alert('Failed to load reasoning');
        });
}

function generateLetter(jobUrl, cvFilename) {
    // Validate CV filename
    if (!cvFilename) {
        alert('Unable to determine CV filename. Please try again.');
        return;
    }
    
    // Create form and submit with POST
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/motivation_letter/generate';
    
    const urlInput = document.createElement('input');
    urlInput.type = 'hidden';
    urlInput.name = 'job_url';
    urlInput.value = jobUrl;
    form.appendChild(urlInput);
    
    const cvInput = document.createElement('input');
    cvInput.type = 'hidden';
    cvInput.name = 'cv_filename';
    cvInput.value = cvFilename;
    form.appendChild(cvInput);
    
    document.body.appendChild(form);
    form.submit();
}

function generateLetterManual(jobUrl, cvFilename) {
    // Validate CV filename
    if (!cvFilename) {
        alert('Unable to determine CV filename. Please try again.');
        return;
    }
    
    // Show manual text input modal
    document.getElementById('manualJobUrl').value = jobUrl;
    document.getElementById('manualCvFilename').value = cvFilename;
    document.getElementById('manualJobTextInput').value = '';
    const modal = new bootstrap.Modal(document.getElementById('manualTextModal'));
    modal.show();
}

// Handle manual text submission
document.addEventListener('DOMContentLoaded', function() {
    const submitBtn = document.getElementById('submitManualTextBtn');
    if (submitBtn) {
        submitBtn.addEventListener('click', function() {
            const jobUrl = document.getElementById('manualJobUrl').value;
            const cvFilename = document.getElementById('manualCvFilename').value;
            const manualText = document.getElementById('manualJobTextInput').value;
            
            if (!manualText.trim()) {
                alert('Please enter job description text');
                return;
            }
            
            if (!cvFilename) {
                alert('CV filename is missing');
                return;
            }
            
            // Create form and submit
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = '/motivation_letter/generate';
            
            const urlInput = document.createElement('input');
            urlInput.type = 'hidden';
            urlInput.name = 'job_url';
            urlInput.value = jobUrl;
            form.appendChild(urlInput);
            
            const cvInput = document.createElement('input');
            cvInput.type = 'hidden';
            cvInput.name = 'cv_filename';
            cvInput.value = cvFilename;
            form.appendChild(cvInput);
            
            const textInput = document.createElement('input');
            textInput.type = 'hidden';
            textInput.name = 'manual_job_text';
            textInput.value = manualText;
            form.appendChild(textInput);
            
            document.body.appendChild(form);
            form.submit();
        });
    }
});

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

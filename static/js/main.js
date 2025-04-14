/**
 * JobsearchAI Dashboard JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // Handle CV summary view buttons
    const viewCvButtons = document.querySelectorAll('.view-cv-btn');
    const cvSummaryModal = new bootstrap.Modal(document.getElementById('cvSummaryModal'));
    const cvSummaryContent = document.getElementById('cv-summary-content');
    const cvSummaryModalLabel = document.getElementById('cvSummaryModalLabel');
    
    viewCvButtons.forEach(button => {
        button.addEventListener('click', function() {
            const cvFile = this.getAttribute('data-cv-file');
            
            // Update modal title
            if (cvSummaryModalLabel) {
                cvSummaryModalLabel.textContent = `CV Summary: ${cvFile}`;
            }
            
            // Show loading message
            if (cvSummaryContent) {
                cvSummaryContent.innerHTML = '<div class="text-center"><div class="spinner-border text-primary" role="status"></div><p class="mt-2">Loading CV summary...</p></div>';
            }
            
            // Show the modal
            cvSummaryModal.show();
            
            // Fetch CV summary
            fetch(`/view_cv_summary/${encodeURIComponent(cvFile)}`)
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        cvSummaryContent.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
                    } else {
                        // Format the summary with line breaks
                        const formattedSummary = data.summary.replace(/\n/g, '<br>');
                        cvSummaryContent.innerHTML = formattedSummary;
                    }
                })
                .catch(error => {
                    console.error('Error fetching CV summary:', error);
                    cvSummaryContent.innerHTML = `<div class="alert alert-danger">Error loading CV summary: ${error.message}</div>`;
                });
        });
    });
    
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Add confirmation for job scraper button
    const jobScraperForm = document.querySelector('form[action="/run_job_scraper"]');
    if (jobScraperForm) {
        jobScraperForm.addEventListener('submit', function(event) {
            if (!confirm('Running the job scraper may take several minutes. Do you want to continue?')) {
                event.preventDefault();
            }
        });
    }
    
    // Add form validation for job matcher
    const jobMatcherForm = document.querySelector('form[action="/run_job_matcher"]');
    if (jobMatcherForm) {
        jobMatcherForm.addEventListener('submit', function(event) {
            const cvPath = document.getElementById('cv_path').value;
            const minScore = document.getElementById('min_score').value;
            const maxResults = document.getElementById('max_results').value;
            
            if (!cvPath) {
                event.preventDefault();
                alert('Please select a CV');
                return;
            }
            
            if (minScore < 1 || minScore > 10) {
                event.preventDefault();
                alert('Minimum score must be between 1 and 10');
                return;
            }
            
            if (maxResults < 1 || maxResults > 50) {
                event.preventDefault();
                alert('Maximum results must be between 1 and 50');
                return;
            }
        });
    }
    
    // Add confirmation for job data delete buttons
    const deleteJobDataButtons = document.querySelectorAll('.delete-job-data-btn');
    deleteJobDataButtons.forEach(button => {
        button.addEventListener('click', function(event) {
            const jobDataFile = this.getAttribute('data-job-data-file');
            if (!confirm(`Are you sure you want to delete the job data file: ${jobDataFile}?`)) {
                event.preventDefault();
            }
        });
    });
    
    // Add confirmation for report delete buttons
    const deleteReportButtons = document.querySelectorAll('.delete-report-btn');
    deleteReportButtons.forEach(button => {
        button.addEventListener('click', function(event) {
            const reportFile = this.getAttribute('data-report-file');
            if (!confirm(`Are you sure you want to delete the report file: ${reportFile}?`)) {
                event.preventDefault();
            }
        });
    });
    
    // Add confirmation for CV delete buttons
    const deleteCvButtons = document.querySelectorAll('.delete-cv-btn');
    deleteCvButtons.forEach(button => {
        button.addEventListener('click', function(event) {
            const cvFile = this.getAttribute('data-cv-file');
            if (!confirm(`Are you sure you want to delete the CV file: ${cvFile}?`)) {
                event.preventDefault();
            }
        });
    });
});

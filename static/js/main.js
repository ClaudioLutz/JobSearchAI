/**
 * JobsearchAI Dashboard JavaScript
 */

// Function to set button loading state
function setButtonLoading(button, isLoading) {
  if (isLoading) {
    // Store original text
    button.setAttribute('data-original-text', button.innerHTML);
    // Replace with loading spinner + text
    button.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Processing...';
    button.disabled = true;
  } else {
    // Restore original text
    button.innerHTML = button.getAttribute('data-original-text');
    button.disabled = false;
  }
}

// Function to check operation status
function checkOperationStatus(operationId, onComplete) {
    const statusUrl = `/operation_status/${operationId}`;
    
    // Create progress modal if it doesn't exist
    let progressModal = document.getElementById('progressModal');
    if (!progressModal) {
        const modalHtml = `
            <div class="modal fade" id="progressModal" tabindex="-1" aria-labelledby="progressModalLabel" aria-hidden="true">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="progressModalLabel">Operation in Progress</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <div class="progress mb-3">
                                <div id="operationProgressBar" class="progress-bar" role="progressbar" style="width: 0%;" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">0%</div>
                            </div>
                            <p id="operationStatusMessage">Starting operation...</p>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        progressModal = document.getElementById('progressModal');
    }
    
    // Show the progress modal
    const bsProgressModal = new bootstrap.Modal(progressModal);
    bsProgressModal.show();
    
    // Get the progress bar and status message elements
    const progressBar = document.getElementById('operationProgressBar');
    const statusMessage = document.getElementById('operationStatusMessage');
    
    // Function to update the progress modal
    function updateProgressModal(progress, message) {
        progressBar.style.width = `${progress}%`;
        progressBar.setAttribute('aria-valuenow', progress);
        progressBar.textContent = `${progress}%`;
        
        if (message) {
            statusMessage.textContent = message;
        }
    }
    
    // Start polling for status updates
    const pollInterval = setInterval(() => {
        fetch(statusUrl)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    clearInterval(pollInterval);
                    updateProgressModal(100, `Error: ${data.error}`);
                    return;
                }
                
                const progress = data.progress;
                const status = data.status;
                
                // Update the progress modal
                updateProgressModal(progress, status.message);
                
                // Check if the operation is complete
                if (progress === 100 || status.status === 'completed' || status.status === 'failed') {
                    clearInterval(pollInterval);
                    
                    // Call the onComplete callback if provided
                    if (onComplete && typeof onComplete === 'function') {
                        onComplete(status);
                    }
                }
            })
            .catch(error => {
                console.error('Error checking operation status:', error);
                clearInterval(pollInterval);
                updateProgressModal(100, `Error checking status: ${error.message}`);
            });
    }, 1000); // Poll every second
    
    // Return the poll interval so it can be cleared if needed
    return pollInterval;
}

document.addEventListener('DOMContentLoaded', function() {
    // Apply loading state to all form submissions
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            const submitButton = this.querySelector('button[type="submit"]');
            
            // Check if this is a long-running operation form
            const isJobMatcher = form.action.includes('/run_job_matcher');
            const isJobScraper = form.action.includes('/run_job_scraper');
            const isCombinedProcess = form.action.includes('/run_combined_process');
            const isMotivationLetter = form.action.includes('/generate_motivation_letter');
            
            if (isJobMatcher || isJobScraper || isCombinedProcess || isMotivationLetter) {
                // For long operations, we'll handle the form submission manually
                event.preventDefault();
                
                if (submitButton) {
                    setButtonLoading(submitButton, true);
                }
                
                // Submit the form using fetch
                fetch(form.action, {
                    method: 'POST',
                    body: new FormData(form)
                })
                .then(response => response.text())
                .then(html => {
                    // Parse the HTML to extract the operation ID from the flash message
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(html, 'text/html');
                    const flashMessages = doc.querySelectorAll('.alert');
                    
                    // Look for an operation ID in the flash messages
                    let operationId = null;
                    flashMessages.forEach(message => {
                        const match = message.textContent.match(/operation_id=([a-f0-9-]+)/i);
                        if (match && match[1]) {
                            operationId = match[1];
                        }
                    });
                    
                    if (operationId) {
                        // Start checking the operation status
                        checkOperationStatus(operationId, (status) => {
                            // When the operation is complete, redirect to the appropriate page
                            if (status.status === 'completed') {
                                if (status.report_file) {
                                    // Redirect to the results page
                                    window.location.href = `/view_results/${status.report_file}`;
                                } else {
                                    // Reload the current page
                                    window.location.reload();
                                }
                            }
                        });
                    } else {
                        // If no operation ID was found, just reload the page
                        window.location.reload();
                    }
                })
                .catch(error => {
                    console.error('Error submitting form:', error);
                    if (submitButton) {
                        setButtonLoading(submitButton, false);
                    }
                    alert(`Error: ${error.message}`);
                });
            } else {
                // For regular forms, just set the button to loading state
                if (submitButton) {
                    setButtonLoading(submitButton, true);
                }
            }
        });
    });
    
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

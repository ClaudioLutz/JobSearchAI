console.log("main.js loaded"); // Add this line at the top

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
        
        if (message && statusMessage.innerHTML.indexOf('<br>') === -1) {
            // Only update the text content if it doesn't contain HTML (which would indicate we've already
            // formatted it with the completion message)
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
                    
                    // Update modal title and message based on operation status
                    const progressModalLabel = document.getElementById('progressModalLabel');
                    const statusMessage = document.getElementById('operationStatusMessage');
                    
                    if (status.status === 'failed') {
                        // Handle failed operations
                        if (progressModalLabel) {
                            progressModalLabel.textContent = 'Operation Failed';
                        }
                        if (statusMessage) {
                            statusMessage.innerHTML = `${status.message}<br><br><strong>Operation failed.</strong>`;
                        }
                        // Change progress bar color to red for failed operations
                        if (progressBar) {
                            progressBar.classList.remove('bg-success');
                            progressBar.classList.add('bg-danger');
                        }
                    } else if (status.status === 'completed') {
                        // Handle completed operations
                        if (progressModalLabel) {
                            progressModalLabel.textContent = 'Operation Completed';
                        }
                        // Change progress bar color to green for completed operations
                        if (progressBar) {
                            progressBar.classList.remove('bg-danger');
                            progressBar.classList.add('bg-success');
                        }
                    }
                    
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

// Main DOMContentLoaded listener
document.addEventListener('DOMContentLoaded', function() {
    console.log("Main DOMContentLoaded fired.");

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
                                // When the operation is complete, add a "View Results" button instead of auto-redirecting
                                if (status.status === 'completed') {
                                    const statusMessage = document.getElementById('operationStatusMessage');
                                    const modalFooter = document.querySelector('#progressModal .modal-footer');
                                    
                                    // Update status message
                                    if (statusMessage) {
                                        statusMessage.innerHTML = `${status.message}<br><br><strong>Operation completed successfully.</strong>`;
                                    }
                                    
                                    // Add a "View Results" button to the modal footer
                                    if (modalFooter) {
                                        // Remove any existing view results button
                                        const existingButton = modalFooter.querySelector('.btn-primary');
                                        if (existingButton) {
                                            existingButton.remove();
                                        }
                                        
                                        // Create and add the new button
                                        const viewResultsButton = document.createElement('button');
                                        viewResultsButton.type = 'button';
                                        viewResultsButton.className = 'btn btn-primary';
                                        
                                        if (status.type === 'motivation_letter_generation') {
                                            viewResultsButton.textContent = 'View Motivation Letter';
                                            viewResultsButton.addEventListener('click', () => {
                                                window.location.href = `/view_motivation_letter/${operationId}`;
                                            });
                                        } else if (status.report_file) {
                                            viewResultsButton.textContent = 'View Results';
                                            viewResultsButton.addEventListener('click', () => {
                                                window.location.href = `/view_results/${status.report_file}`;
                                            });
                                        } else {
                                            viewResultsButton.textContent = 'Reload Page';
                                            viewResultsButton.addEventListener('click', () => {
                                                window.location.reload();
                                            });
                                        }
                                        
                                        modalFooter.prepend(viewResultsButton);
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
    
    // Handle CV summary view buttons (only if the modal exists on the page)
    const cvSummaryModalElement = document.getElementById('cvSummaryModal');
    if (cvSummaryModalElement) {
        const viewCvButtons = document.querySelectorAll('.view-cv-btn');
        const cvSummaryModal = new bootstrap.Modal(cvSummaryModalElement);
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
                            if (cvSummaryContent) {
                                 cvSummaryContent.innerHTML = `<div class="alert alert-danger">Error loading CV summary: ${error.message}</div>`;
                            }
                });
            });
        });
    } // End if (cvSummaryModalElement)

    // --- Handle Generate Letter Link Clicks (New for Dropdown) ---
    document.body.addEventListener('click', function(event) {
        if (event.target.classList.contains('generate-letter-link')) {
            event.preventDefault(); // Prevent default link behavior

            const link = event.target;
            const jobUrl = link.dataset.jobUrl;
            // const cvFilename = link.dataset.cvFilename; // No longer read from link
            const reportFile = link.dataset.reportFile;
            const jobTitle = link.dataset.jobTitle; // Optional, for potential status messages

            // Get selected CV from dropdown
            const cvSelectElement = document.getElementById('cv-select');
            if (!cvSelectElement) {
                console.error('CV select dropdown (#cv-select) not found.');
                alert('Error: CV selection dropdown is missing.');
                return;
            }
            const cvFilename = cvSelectElement.value;

            if (!jobUrl || !cvFilename || !reportFile) {
                console.error('Missing data for generate letter link:', { jobUrl, cvFilename, reportFile });
                alert('Error: Could not get necessary data (Job URL, CV Filename, Report File) to generate letter.');
                return;
            }

            // Temporarily disable link to prevent multiple clicks (optional)
            link.classList.add('disabled');
            link.style.pointerEvents = 'none'; // Make it visually disabled

            // Create FormData
            const formData = new FormData();
            formData.append('cv_filename', cvFilename);
            formData.append('job_url', jobUrl);
            formData.append('report_file', reportFile);
            formData.append('job_title', jobTitle); // Send job title too

            // Submit using fetch (similar to existing form logic)
            fetch('/generate_motivation_letter', { // Use the correct endpoint
                method: 'POST',
                body: formData
            })
            .then(response => response.text()) // Get response as text to parse HTML
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
                    // Start checking the operation status using the existing function
                    checkOperationStatus(operationId, (status) => {
                        // Re-enable link when operation completes (success or fail)
                        link.classList.remove('disabled');
                        link.style.pointerEvents = 'auto';

                        // Existing completion logic from checkOperationStatus will handle modal updates
                        if (status.status === 'completed') {
                             // Optionally add specific success handling here if needed
                             console.log(`Letter generation completed for ${jobTitle}`);
                             // Maybe update the dropdown item? e.g., change text to "View Letter"
                             // This would require more complex DOM manipulation. For now, rely on modal.
                        } else if (status.status === 'failed') {
                             // Optionally add specific failure handling here
                             console.error(`Letter generation failed for ${jobTitle}`);
                             alert(`Failed to generate letter for ${jobTitle}. Check logs for details.`);
                        }
                    });
                } else {
                    // If no operation ID was found, handle error
                    console.error('Could not find operation_id in response for generate_motivation_letter');
                    alert('Error starting letter generation process. Please check the console or server logs.');
                    // Re-enable link on error
                    link.classList.remove('disabled');
                    link.style.pointerEvents = 'auto';
                }
            })
            .catch(error => {
                console.error('Error submitting generate letter request:', error);
                alert(`Error generating letter: ${error.message}`);
                // Re-enable link on error
                link.classList.remove('disabled');
                link.style.pointerEvents = 'auto';
            });
        }
    });
    // --- End Handle Generate Letter Link Clicks ---

    // --- Handle Manual Text Input Modal ---
    const manualTextModalElement = document.getElementById('manualTextModal');
    if (manualTextModalElement) {
        const manualTextModal = new bootstrap.Modal(manualTextModalElement);
        const manualTextForm = document.getElementById('manualTextForm');
        const manualJobTextInput = document.getElementById('manualJobTextInput');
        const submitManualTextBtn = document.getElementById('submitManualTextBtn');
        const manualTextModalLabel = document.getElementById('manualTextModalLabel');

        // Listener for dropdown links that trigger the modal
        document.body.addEventListener('click', function(event) {
            if (event.target.classList.contains('manual-text-trigger')) {
                event.preventDefault();
                const link = event.target;

                // Get data from the clicked link
                const jobUrl = link.dataset.jobUrl;
                const reportFile = link.dataset.reportFile;
                const jobTitle = link.dataset.jobTitle;

                // Get selected CV from dropdown
                const cvSelectElement = document.getElementById('cv-select');
                if (!cvSelectElement) {
                    console.error('CV select dropdown (#cv-select) not found.');
                    alert('Error: CV selection dropdown is missing.');
                    return;
                }
                const cvFilename = cvSelectElement.value;

                if (!jobUrl || !reportFile || !cvFilename || !jobTitle) {
                    alert('Error: Missing necessary data to open manual input modal.');
                    return;
                }

                // Populate hidden fields and modal title
                document.getElementById('manualTextJobUrl').value = jobUrl;
                document.getElementById('manualTextReportFile').value = reportFile;
                document.getElementById('manualTextCvFilename').value = cvFilename;
                document.getElementById('manualTextJobTitle').value = jobTitle; // Store job title if needed later
                manualTextModalLabel.textContent = `Manual Job Text Input for: ${jobTitle}`;
                manualJobTextInput.value = ''; // Clear previous text

                // Show the modal (handled by data-bs-toggle/target, but ensure it's ready)
                // manualTextModal.show(); // Usually not needed if using data attributes correctly
            }
        });

        // Listener for the modal's submit button
        if (submitManualTextBtn) {
            submitManualTextBtn.addEventListener('click', function() {
                const manualText = manualJobTextInput.value.trim();
                if (!manualText) {
                    alert('Please paste the job announcement text into the text area.');
                    manualJobTextInput.focus();
                    return;
                }

                // Retrieve data from hidden fields
                const jobUrl = document.getElementById('manualTextJobUrl').value;
                const reportFile = document.getElementById('manualTextReportFile').value;
                const cvFilename = document.getElementById('manualTextCvFilename').value;
                const jobTitle = document.getElementById('manualTextJobTitle').value; // Retrieve job title

                // Create FormData
                const formData = new FormData();
                formData.append('cv_filename', cvFilename);
                formData.append('job_url', jobUrl);
                formData.append('report_file', reportFile);
                formData.append('job_title', jobTitle); // Include job title if needed by backend
                formData.append('manual_job_text', manualText); // Add the manual text

                // Close the modal
                manualTextModal.hide();

                // Show loading state (optional, maybe use the global progress modal)
                console.log("Submitting manual text for letter generation...");

                // Submit using fetch to the standard generate endpoint
                fetch('/motivation_letter/generate', {
                    method: 'POST',
                    body: formData
                })
                .then(response => { // Expect JSON response now
                    if (!response.ok) {
                        // Try to parse error from JSON, otherwise use status text
                        return response.json().then(errData => {
                            throw new Error(errData.error || `Server error: ${response.statusText}`);
                        }).catch(() => {
                            throw new Error(`Server error: ${response.statusText}`);
                        });
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.success && data.operation_id) {
                        // Start checking the operation status using the existing function
                        checkOperationStatus(data.operation_id, (status) => {
                            // Existing completion logic from checkOperationStatus will handle modal updates
                            if (status.status === 'completed') {
                                console.log(`Manual text letter generation completed for ${jobTitle}`);
                            } else if (status.status === 'failed') {
                                console.error(`Manual text letter generation failed for ${jobTitle}`);
                                // The error message from the backend should be displayed by checkOperationStatus
                            }
                        });
                    } else {
                        console.error('Could not find operation_id in response for manual text generation');
                        alert('Error starting letter generation process from manual text. Please check logs.');
                    }
                })
                .catch(error => {
                    console.error('Error submitting manual text generate request:', error);
                    alert(`Error generating letter from manual text: ${error.message}`);
                });
            });
        }
    }
    // --- End Handle Manual Text Input Modal ---

    // --- Bulk Delete Functionality ---
    const fileSections = [
        { listId: 'cv-list', checkboxClass: 'cv-checkbox', buttonSelector: '.bulk-delete-btn[data-file-type="cv"]', fileType: 'cv' },
        { listId: 'job-data-list', checkboxClass: 'job-data-checkbox', buttonSelector: '.bulk-delete-btn[data-file-type="job_data"]', fileType: 'job_data' },
        { listId: 'report-list', checkboxClass: 'report-checkbox', buttonSelector: '.bulk-delete-btn[data-file-type="report"]', fileType: 'report' }
    ];

    fileSections.forEach(section => {
        const listElement = document.getElementById(section.listId);
        const bulkDeleteButton = document.querySelector(section.buttonSelector);

        if (listElement && bulkDeleteButton) {
            // Event listener for checkboxes within this section
            listElement.addEventListener('change', (event) => {
                if (event.target.classList.contains(section.checkboxClass)) {
                    const checkedCheckboxes = listElement.querySelectorAll(`.${section.checkboxClass}:checked`);
                    bulkDeleteButton.style.display = checkedCheckboxes.length > 0 ? 'inline-block' : 'none';
                }
            });

            // Event listener for the bulk delete button
            bulkDeleteButton.addEventListener('click', () => {
                const checkedCheckboxes = listElement.querySelectorAll(`.${section.checkboxClass}:checked`);
                const selectedFilenames = Array.from(checkedCheckboxes).map(cb => cb.value);

                if (selectedFilenames.length === 0) {
                    alert('Please select at least one file to delete.');
                    return;
                }

                const fileTypeLabel = section.fileType.replace('_', ' '); // e.g., 'job data'
                if (confirm(`Are you sure you want to delete the ${selectedFilenames.length} selected ${fileTypeLabel} file(s)? This action cannot be undone.`)) {
                    // Send request to backend
                    fetch('/delete_files', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            file_type: section.fileType,
                            filenames: selectedFilenames
                        })
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            alert(data.message || `Successfully deleted ${data.deleted_count} file(s).`);
                            // Remove deleted items from the list
                            checkedCheckboxes.forEach(checkbox => {
                                checkbox.closest('li').remove();
                            });
                            // Hide button again
                            bulkDeleteButton.style.display = 'none';
                            // If list becomes empty, show the 'No files' message (optional enhancement)
                            if (listElement.querySelectorAll('li').length === 0) {
                                const noFilesMessage = listElement.closest('.card-body').querySelector('p');
                                if (noFilesMessage) noFilesMessage.style.display = 'block';
                                listElement.style.display = 'none'; // Hide the empty ul
                                bulkDeleteButton.remove(); // Remove the button entirely if list is empty
                            }
                        } else {
                            alert(`Error deleting files: ${data.message || 'Unknown error'}`);
                        }
                    })
                    .catch(error => {
                        console.error('Error during bulk delete:', error);
                        alert(`An error occurred while trying to delete files: ${error.message}`);
                    });
                }
            });
        }
    });
     // --- End Bulk Delete Functionality ---

    // --- Generate Letters for Selected Jobs ---
    console.log("Checking for multi-letter button elements."); // Debug log A
    const generateSelectedBtn = document.getElementById('generate-selected-letters-btn');
    const selectedStatusSpan = document.getElementById('selected-status');

    if (generateSelectedBtn && selectedStatusSpan) {
        console.log("Attempting to attach listener to #generate-selected-letters-btn"); // Debug log 1
        generateSelectedBtn.addEventListener('click', function() {
            console.log("#generate-selected-letters-btn clicked!"); // Debug log 2
            const selectedCheckboxes = document.querySelectorAll('.job-select-checkbox:checked');
            console.log(`Found ${selectedCheckboxes.length} selected checkboxes.`); // Debug log 3
            // const cvFilename = this.getAttribute('data-cv-filename'); // No longer read from button

            // Get selected CV from dropdown
            const cvSelectElement = document.getElementById('cv-select');
             if (!cvSelectElement) {
                console.error('CV select dropdown (#cv-select) not found.');
                alert('Error: CV selection dropdown is missing.');
                return;
            }
            const cvFilename = cvSelectElement.value;

            if (!cvFilename) {
                alert('Error: No CV selected in the dropdown.');
                console.error("CV filename is empty from dropdown.");
                return;
            }

            if (selectedCheckboxes.length === 0) {
                alert('Please select at least one job to generate letters for.');
                return;
            }

            const jobUrls = Array.from(selectedCheckboxes).map(cb => cb.value);
            const jobTitles = Array.from(selectedCheckboxes).map(cb => cb.getAttribute('data-job-title')); // For status messages
            console.log("Selected Job URLs:", jobUrls); // Debug log 4
            console.log("CV Filename:", cvFilename); // Debug log 5

            setButtonLoading(this, true);
            selectedStatusSpan.textContent = `Generating ${jobUrls.length} letter(s)...`;
            selectedStatusSpan.className = 'ms-2 text-info'; // Reset class

            console.log("Initiating fetch to /motivation_letter/generate_multiple"); // Debug log 6 - Updated URL
            fetch('/motivation_letter/generate_multiple', { // Use the correct blueprint endpoint
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    job_urls: jobUrls,
                    cv_filename: cvFilename // Send CV filename directly
                })
            })
            .then(response => {
                if (!response.ok) {
                    // Try to get error message from response body if possible
                    return response.json().then(errData => {
                        throw new Error(errData.error || `Server error: ${response.statusText}`);
                    }).catch(() => {
                        // Fallback if response body is not JSON or empty
                        throw new Error(`Server error: ${response.statusText}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                console.log("Backend response:", data); // Log response for debugging
                let message = `Generated ${data.success_count}/${jobUrls.length} letters.`;
                if (data.errors && data.errors.length > 0) {
                    // Find job titles for failed URLs
                    const failedTitles = data.errors.map(errorUrl => {
                        const index = jobUrls.indexOf(errorUrl);
                        return index !== -1 ? jobTitles[index] : errorUrl; // Show title or URL if title not found
                    });
                    message += ` Failed for: ${failedTitles.join(', ')}.`;
                    selectedStatusSpan.className = 'ms-2 text-warning';
                } else {
                    selectedStatusSpan.className = 'ms-2 text-success';
                }
                selectedStatusSpan.textContent = message;
                // Optional: Reload or update UI after success? For now, just show status.
                // Consider refreshing the page or updating the specific rows after a delay.
                // setTimeout(() => window.location.reload(), 3000); // Example: Reload after 3 seconds
            })
            .catch(error => {
                console.error('Error generating multiple letters:', error);
                selectedStatusSpan.textContent = `Error: ${error.message}`;
                selectedStatusSpan.className = 'ms-2 text-danger';
            })
            .finally(() => {
                setButtonLoading(this, false);
            });
        });
        console.log("Listener attached to #generate-selected-letters-btn"); // Debug log 7
    } else {
        // Only log error if we expect the button to be present (e.g., on results page)
        // We can check the URL or presence of another element unique to the results page
        if (document.querySelector('.job-matches-table')) { // Assuming results table has this class
             console.error("#generate-selected-letters-btn or #selected-status not found on results page!"); // Debug log B
        }
    }
    // --- End Generate Letters for Selected Jobs ---

    // --- Generate Email Texts for Selected Jobs ---
    console.log("Checking for multi-email button elements.");
    const generateSelectedEmailsBtn = document.getElementById('generate-selected-emails-btn');
    // Use the same status span as the letter generation
    // const selectedStatusSpan = document.getElementById('selected-status'); // Already defined above

    if (generateSelectedEmailsBtn && selectedStatusSpan) {
        console.log("Attempting to attach listener to #generate-selected-emails-btn");
        generateSelectedEmailsBtn.addEventListener('click', function() {
            console.log("#generate-selected-emails-btn clicked!");
            const selectedCheckboxes = document.querySelectorAll('.job-select-checkbox:checked');
            console.log(`Found ${selectedCheckboxes.length} selected checkboxes for email generation.`);

            // Get selected CV from dropdown
            const cvSelectElement = document.getElementById('cv-select');
            if (!cvSelectElement) {
                console.error('CV select dropdown (#cv-select) not found.');
                alert('Error: CV selection dropdown is missing.');
                return;
            }
            const cvFilename = cvSelectElement.value;

            if (!cvFilename) {
                alert('Error: No CV selected in the dropdown.');
                console.error("CV filename is empty from dropdown for email generation.");
                return;
            }

            if (selectedCheckboxes.length === 0) {
                alert('Please select at least one job to generate email texts for.');
                return;
            }

            const jobUrls = Array.from(selectedCheckboxes).map(cb => cb.value);
            const jobTitles = Array.from(selectedCheckboxes).map(cb => cb.getAttribute('data-job-title')); // For status messages
            console.log("Selected Job URLs for email:", jobUrls);
            console.log("CV Filename for email:", cvFilename);

            setButtonLoading(this, true);
            selectedStatusSpan.textContent = `Generating ${jobUrls.length} email text(s)...`;
            selectedStatusSpan.className = 'ms-2 text-info'; // Reset class

            console.log("Initiating fetch to /motivation_letter/generate_multiple_emails");
            fetch('/motivation_letter/generate_multiple_emails', { // Call the new endpoint
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    job_urls: jobUrls,
                    cv_filename: cvFilename
                })
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(errData => {
                        throw new Error(errData.error || `Server error: ${response.statusText}`);
                    }).catch(() => {
                        throw new Error(`Server error: ${response.statusText}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                console.log("Backend response (email generation):", data);
                let message = `Generated/Updated ${data.success_count}/${jobUrls.length} email texts.`;
                if (data.errors && data.errors.length > 0) {
                    // Extract reasons or URLs for failed jobs
                    const failedDetails = data.errors.map(err => err.url || 'Unknown URL').join(', ');
                    message += ` Failed for: ${failedDetails}.`;
                    selectedStatusSpan.className = 'ms-2 text-warning';
                } else {
                    selectedStatusSpan.className = 'ms-2 text-success';
                }
                selectedStatusSpan.textContent = message;
                // Optional: Reload or update UI. Reload might be simplest to show new "View Email Text" links.
                // setTimeout(() => window.location.reload(), 3000);
            })
            .catch(error => {
                console.error('Error generating multiple email texts:', error);
                selectedStatusSpan.textContent = `Error: ${error.message}`;
                selectedStatusSpan.className = 'ms-2 text-danger';
            })
            .finally(() => {
                setButtonLoading(this, false);
            });
        });
        console.log("Listener attached to #generate-selected-emails-btn");
    } else {
        if (document.querySelector('.job-matches-table')) { // Check if on results page
             console.error("#generate-selected-emails-btn or #selected-status not found on results page!");
        }
    }
    // --- End Generate Email Texts for Selected Jobs ---

    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            // Check if the alert still exists before trying to close it
            if (alert.parentNode) {
                 const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
                 bsAlert.close();
            }
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

}); // End of main DOMContentLoaded listener

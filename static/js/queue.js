/**
 * Application Queue JavaScript
 * Handles AJAX interactions, modal management, and UI updates
 */

(function() {
    'use strict';

    // Parse application data from hidden div
    let applicationsData = [];
    try {
        const dataElement = document.getElementById('applicationData');
        if (dataElement && dataElement.textContent) {
            applicationsData = JSON.parse(dataElement.textContent);
        }
    } catch (e) {
        console.error('Error parsing application data:', e);
    }

    // Current application being viewed in modal
    let currentApplicationId = null;

    // Toast instances
    const successToast = new bootstrap.Toast(document.getElementById('successToast'));
    const errorToast = new bootstrap.Toast(document.getElementById('errorToast'));

    /**
     * Show success toast notification
     */
    function showSuccess(message) {
        document.getElementById('successMessage').textContent = message;
        successToast.show();
    }

    /**
     * Show error toast notification
     */
    function showError(message) {
        document.getElementById('errorMessage').textContent = message;
        errorToast.show();
    }

    /**
     * Find application by ID
     */
    function findApplication(appId) {
        return applicationsData.find(app => app.id === appId);
    }

    /**
     * Remove application card from DOM
     */
    function removeApplicationCard(appId) {
        const card = document.querySelector(`[data-app-id="${appId}"]`);
        if (card) {
            card.style.transition = 'opacity 0.3s';
            card.style.opacity = '0';
            setTimeout(() => {
                card.remove();
                // Update counts
                updateCounts();
            }, 300);
        }
    }

    /**
     * Update header counts
     */
    function updateCounts() {
        // Count remaining applications
        const remainingCards = document.querySelectorAll('[data-app-id]').length;
        const readyCards = document.querySelectorAll('[data-valid="true"]').length;
        const reviewCards = document.querySelectorAll('[data-valid="false"]').length;

        // Counts updated - page reload recommended for accuracy
    }

    /**
     * Populate modal with application details
     */
    function populateModal(app) {
        if (!app) return;

        currentApplicationId = app.id;

        // Job Info Tab
        document.getElementById('modal-job-title').textContent = app.job_title || 'N/A';
        document.getElementById('modal-company').textContent = app.company_name || 'N/A';
        document.getElementById('modal-recipient-name').textContent = app.recipient_name || 'N/A';
        document.getElementById('modal-recipient-email').textContent = app.recipient_email || 'N/A';
        document.getElementById('modal-subject').textContent = app.subject_line || 'N/A';
        document.getElementById('modal-job-description').textContent = app.job_description || 'No description available';

        // Motivation Letter Tab - Fixed: Use innerHTML to render HTML content
        const motivationDiv = document.getElementById('modal-motivation-letter');
        if (app.motivation_letter) {
            // Render HTML content properly (motivation letters contain HTML formatting)
            motivationDiv.innerHTML = app.motivation_letter;
        } else {
            motivationDiv.textContent = 'No motivation letter available';
        }

        // Email Preview Tab
        document.getElementById('preview-to').textContent = app.recipient_email || 'N/A';
        document.getElementById('preview-subject').textContent = app.subject_line || 'N/A';
        
        const greeting = app.motivation_letter && app.motivation_letter.includes('Sehr geehrte') 
            ? `Sehr geehrte/r ${app.recipient_name || 'N/A'},`
            : `Dear ${app.recipient_name || 'N/A'},`;
        
        const previewBody = `${greeting}\n\n${app.motivation_letter || ''}\n\nMit freundlichen Grüßen / Best regards,\n[Your Name]`;
        document.getElementById('preview-body').textContent = previewBody;

        // Validation Status
        const validationDiv = document.getElementById('modal-validation-status');
        if (app.validation) {
            let validationHTML = '';
            
            if (app.validation.is_valid) {
                validationHTML = '<div class="alert alert-success"><i class="bi bi-check-circle"></i> Application is valid and ready to send</div>';
            } else {
                validationHTML = '<div class="alert alert-warning"><i class="bi bi-exclamation-triangle"></i> Application has validation issues</div>';
                
                if (app.validation.missing_fields && app.validation.missing_fields.length > 0) {
                    validationHTML += '<p><strong>Missing fields:</strong></p><ul>';
                    app.validation.missing_fields.forEach(field => {
                        validationHTML += `<li>${field}</li>`;
                    });
                    validationHTML += '</ul>';
                }
                
                if (app.validation.invalid_fields && Object.keys(app.validation.invalid_fields).length > 0) {
                    validationHTML += '<p><strong>Invalid fields:</strong></p><ul>';
                    Object.entries(app.validation.invalid_fields).forEach(([field, error]) => {
                        validationHTML += `<li>${field}: ${error}</li>`;
                    });
                    validationHTML += '</ul>';
                }
            }
            
            validationHTML += `<p><strong>Completeness Score:</strong> ${app.validation.completeness_score}%</p>`;
            validationDiv.innerHTML = validationHTML;
        }

        // Update modal Send button state
        const modalSendBtn = document.getElementById('modalSendBtn');
        if (app.validation && app.validation.is_valid) {
            modalSendBtn.disabled = false;
        } else {
            modalSendBtn.disabled = true;
        }
    }

    /**
     * Send a single application via AJAX
     */
    function sendApplication(appId, onSuccess, onError) {
        // Disable button and show loading
        const button = document.querySelector(`[data-app-id="${appId}"] .send-btn`);
        if (button) {
            button.disabled = true;
            button.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Sending...';
        }

        fetch(`/queue/send/${appId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                if (onSuccess) onSuccess(data);
                showSuccess(data.message || 'Application sent successfully!');
                removeApplicationCard(appId);
            } else {
                if (onError) onError(data);
                showError(data.message || 'Failed to send application');
                // Re-enable button
                if (button) {
                    button.disabled = false;
                    button.innerHTML = '<i class="bi bi-send"></i> Send';
                }
            }
        })
        .catch(error => {
            console.error('Error sending application:', error);
            if (onError) onError(error);
            showError('Network error: Failed to send application');
            // Re-enable button
            if (button) {
                button.disabled = false;
                button.innerHTML = '<i class="bi bi-send"></i> Send';
            }
        });
    }

    /**
     * Send all ready applications
     */
    function sendAllReady() {
        const readyApps = applicationsData.filter(app => app.validation && app.validation.is_valid);
        
        if (readyApps.length === 0) {
            showError('No ready applications to send');
            return;
        }

        if (!confirm(`Are you sure you want to send ${readyApps.length} application(s)?`)) {
            return;
        }

        const appIds = readyApps.map(app => app.id);
        
        // Disable button and show loading
        const button = document.getElementById('sendAllReadyBtn');
        button.disabled = true;
        button.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Sending...';

        fetch('/queue/send-batch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ application_ids: appIds })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showSuccess(data.message);
                
                // Remove successfully sent applications
                if (data.results) {
                    data.results.forEach(result => {
                        if (result.success) {
                            removeApplicationCard(result.id);
                        }
                    });
                }
                
                // Reload page after short delay to update counts
                setTimeout(() => {
                    window.location.reload();
                }, 2000);
            } else {
                showError(data.message || 'Batch send failed');
                button.disabled = false;
                button.innerHTML = `<i class="bi bi-send-check"></i> Send All Ready (${readyApps.length})`;
            }
        })
        .catch(error => {
            console.error('Error in batch send:', error);
            showError('Network error: Batch send failed');
            button.disabled = false;
            button.innerHTML = `<i class="bi bi-send-check"></i> Send All Ready (${readyApps.length})`;
        });
    }

    // Event Listeners

    // Review button clicks (open modal)
    document.addEventListener('click', function(e) {
        if (e.target.closest('.review-btn')) {
            const button = e.target.closest('.review-btn');
            const appId = button.dataset.appId;
            const app = findApplication(appId);
            
            if (app) {
                populateModal(app);
                const modal = new bootstrap.Modal(document.getElementById('applicationModal'));
                modal.show();
            }
        }
    });

    // Send button clicks (with confirmation)
    document.addEventListener('click', function(e) {
        if (e.target.closest('.send-btn')) {
            const button = e.target.closest('.send-btn');
            const appId = button.dataset.appId;
            const app = findApplication(appId);
            
            if (app && confirm(`Send application for ${app.job_title} at ${app.company_name}?`)) {
                sendApplication(appId);
            }
        }
    });

    // Modal Send Now button
    const modalSendBtn = document.getElementById('modalSendBtn');
    if (modalSendBtn) {
        modalSendBtn.addEventListener('click', function() {
            if (currentApplicationId) {
                const app = findApplication(currentApplicationId);
                if (app && confirm(`Send application for ${app.job_title} at ${app.company_name}?`)) {
                    sendApplication(currentApplicationId, function() {
                        // Close modal on success
                        const modal = bootstrap.Modal.getInstance(document.getElementById('applicationModal'));
                        if (modal) modal.hide();
                    });
                }
            }
        });
    }

    // Send All Ready button
    const sendAllReadyBtn = document.getElementById('sendAllReadyBtn');
    if (sendAllReadyBtn) {
            sendAllReadyBtn.addEventListener('click', sendAllReady);
    }
})();

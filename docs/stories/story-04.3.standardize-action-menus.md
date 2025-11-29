# Story 4.3: Standardize Action Menus Across Views

## Status
Approved

## Story
**As a** JobSearchAI user,
**I want** the same comprehensive action menu in All Job Matches view as in Job Match Results view,
**so that** I have consistent functionality across all views and don't need to switch views to access key features.

## Acceptance Criteria
1. Action dropdown in all_matches.html matches results.html structure
2. All action items functional (View Reasoning, Generate Letter, etc.)
3. Backend checks for file existence (docx, scraped data, email)
4. Conditional display of menu items based on file availability
5. Modal for View Reasoning implemented
6. JavaScript handlers for all actions working
7. No broken links or non-functional buttons
8. Consistent styling across both views

## Tasks / Subtasks

- [ ] Task 1: Update All Job Matches Actions Column (AC: 1, 8)
  - [ ] Replace simple buttons with Bootstrap dropdown in templates/all_matches.html
  - [ ] Add all 8 action menu items from results.html
  - [ ] Use same CSS classes and structure
  - [ ] Add dividers between action groups

- [ ] Task 2: Backend File Existence Checks (AC: 3, 4)
  - [ ] Update view_all_matches route in blueprints/job_matching_routes.py
  - [ ] Add has_motivation_letter check for each result
  - [ ] Add has_docx check for each result
  - [ ] Add has_scraped_data check for each result
  - [ ] Add has_email_text check for each result
  - [ ] Reuse existing file-checking logic from view_results route

- [ ] Task 3: View Reasoning Modal (AC: 2, 5)
  - [ ] Add modal HTML to templates/all_matches.html
  - [ ] Create API endpoint GET /api/job-reasoning in blueprints/job_matching_routes.py
  - [ ] Implement JavaScript handler to fetch and display reasoning
  - [ ] Test modal opening and content display

- [ ] Task 4: JavaScript Action Handlers (AC: 2, 6)
  - [ ] Create/update static/js/all_matches.js
  - [ ] Implement viewReasoning(jobUrl) function
  - [ ] Implement generateLetter(jobUrl) function
  - [ ] Implement generateLetterManual(jobUrl) function
  - [ ] Add manual text input modal if needed
  - [ ] Test all handlers

- [ ] Task 5: Conditional Menu Items (AC: 4)
  - [ ] Update template to conditionally show Download Word
  - [ ] Update template to conditionally show View Scraped Data
  - [ ] Update template to conditionally show View Email Text
  - [ ] Test with jobs that have/don't have these files

- [ ] Task 6: Integration Testing (AC: 7)
  - [ ] Test View Reasoning for multiple jobs
  - [ ] Test View Job Ad (external links)
  - [ ] Test Generate Letter redirect
  - [ ] Test Generate Letter (Manual) modal
  - [ ] Test Download Word link
  - [ ] Test View Scraped Data link
  - [ ] Test View Email Text link
  - [ ] Verify no broken links or console errors

## Dev Notes

### Relevant Source Tree
```
templates/
├── all_matches.html                 # All Job Matches view (needs update)
├── results.html                     # Job Match Results view (reference)
blueprints/
├── job_matching_routes.py          # Contains view_all_matches and view_results routes
static/
├── js/
│   └── all_matches.js              # JavaScript for All Job Matches (create/update)
utils/
├── url_utils.py                    # URL normalization utilities
```

### Integration Points
- **All Job Matches Template**: `templates/all_matches.html` actions column
- **Results Template (Reference)**: `templates/results.html` full dropdown structure
- **Backend Route**: `blueprints/job_matching_routes.py` view_all_matches function
- **API Endpoint**: New `/api/job-reasoning` endpoint for modal data
- **JavaScript**: `static/js/all_matches.js` action handlers
- **File Checking**: Reuse logic from view_results route

### Key Implementation Notes

#### Current Actions in results.html (Reference)
```html
<div class="dropdown">
    <button class="btn btn-secondary btn-sm dropdown-toggle" type="button">
        Actions
    </button>
    <ul class="dropdown-menu">
        <li><a class="dropdown-item" href="#" data-bs-toggle="modal">View Reasoning</a></li>
        <li><a class="dropdown-item" href="{{ full_job_url }}" target="_blank">View Job Ad</a></li>
        <li><hr class="dropdown-divider"></li>
        <li><a class="dropdown-item generate-letter-link" href="#">Generate Letter</a></li>
        <li><a class="dropdown-item manual-text-trigger" href="#">Generate Letter (Manual Text)</a></li>
        <li><a class="dropdown-item" href="#">Download Word</a></li>
        <li><a class="dropdown-item" href="#">View Scraped Data</a></li>
        <li><a class="dropdown-item" href="#">View Email Text</a></li>
    </ul>
</div>
```

#### Target Actions Dropdown Structure
```html
<!-- templates/all_matches.html -->
<td>
    <div class="dropdown">
        <button class="btn btn-secondary btn-sm dropdown-toggle" type="button" 
                id="actionsDropdown{{ loop.index }}" 
                data-bs-toggle="dropdown" 
                aria-expanded="false">
            Actions
        </button>
        <ul class="dropdown-menu" aria-labelledby="actionsDropdown{{ loop.index }}">
            <!-- View Actions -->
            <li><a class="dropdown-item" href="#" 
                   onclick="viewReasoning('{{ match.job_url }}'); return false;">
                View Reasoning
            </a></li>
            <li><a class="dropdown-item" href="{{ match.job_url }}" 
                   target="_blank" rel="noopener noreferrer">
                View Job Ad <i class="bi bi-box-arrow-up-right"></i>
            </a></li>
            <li><hr class="dropdown-divider"></li>
            
            <!-- Generation Actions -->
            <li><a class="dropdown-item" href="#" 
                   onclick="generateLetter('{{ match.job_url }}'); return false;">
                Generate Letter
            </a></li>
            <li><a class="dropdown-item" href="#" 
                   onclick="generateLetterManual('{{ match.job_url }}'); return false;">
                Generate Letter (Manual Text)
            </a></li>
            
            <!-- Document Actions (conditional) -->
            {% if match.has_docx %}
            <li><a class="dropdown-item" href="{{ url_for('motivation_letter.download_docx', job_url=match.job_url) }}">
                Download Word
            </a></li>
            {% endif %}
            
            {% if match.has_scraped_data %}
            <li><a class="dropdown-item" href="{{ url_for('job_data.view_scraped_data', job_url=match.job_url) }}">
                View Scraped Data
            </a></li>
            {% endif %}
            
            {% if match.has_email_text %}
            <li><a class="dropdown-item" href="{{ url_for('motivation_letter.view_email_text', job_url=match.job_url) }}">
                View Email Text
            </a></li>
            {% endif %}
        </ul>
    </div>
</td>
```

#### Backend File Checking Implementation
```python
# blueprints/job_matching_routes.py - view_all_matches function
def check_for_generated_files(job_url):
    """
    Reusable helper function to check for generated files
    Extract from view_results and share with view_all_matches
    """
    from pathlib import Path
    from utils.url_utils import URLNormalizer
    
    letters_dir = Path(current_app.root_path) / 'motivation_letters'
    
    # URL normalization
    job_url = URLNormalizer.clean_malformed_url(job_url)
    norm_job_url = URLNormalizer.normalize_for_comparison(job_url)
    
    # Check for files
    has_motivation_letter = False
    has_docx = False
    has_scraped_data = False
    has_email_text = False
    
    # Implementation: Check for matching files
    # ... (similar to results.html logic)
    
    return {
        'has_motivation_letter': has_motivation_letter,
        'has_docx': has_docx,
        'has_scraped_data': has_scraped_data,
        'has_email_text': has_email_text
    }

# In view_all_matches route:
for result in results:
    file_checks = check_for_generated_files(result['job_url'])
    result.update(file_checks)
```

#### JavaScript Implementation
```javascript
// static/js/all_matches.js
function viewReasoning(jobUrl) {
    // Fetch reasoning from database and show in modal
    fetch(`/api/job-reasoning?url=${encodeURIComponent(jobUrl)}`)
        .then(response => response.json())
        .then(data => {
            // Populate modal with reasoning
            document.getElementById('reasoningModalTitle').textContent = data.job_title;
            document.getElementById('reasoningModalBody').textContent = data.reasoning;
            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('reasoningModal'));
            modal.show();
        })
        .catch(error => {
            console.error('Error fetching reasoning:', error);
            alert('Failed to load reasoning');
        });
}

function generateLetter(jobUrl) {
    // Redirect to letter generation
    window.location.href = `/motivation_letter/generate?job_url=${encodeURIComponent(jobUrl)}`;
}

function generateLetterManual(jobUrl) {
    // Show manual text input modal
    document.getElementById('manualJobUrl').value = jobUrl;
    const modal = new bootstrap.Modal(document.getElementById('manualTextModal'));
    modal.show();
}
```

### Important Context from Previous Stories
- Story 3.3 implemented the All Job Matches unified view with filtering
- Results.html already has full action dropdown implemented
- File checking logic exists in view_results route
- URL normalization utilities available in utils/url_utils.py
- Bootstrap 5 dropdowns and modals already used throughout application

### Testing

#### Test Standards
- **Manual Testing**: UI/UX verification required
- **Integration Testing**: Action functionality testing
- **Backend Testing**: File existence check accuracy

#### Testing Framework
- Manual browser testing for dropdown and modals
- JavaScript console for debugging handlers
- Flask test client for API endpoints
- Verify URL normalization works correctly

#### Specific Testing Requirements
1. Test all 8 action menu items display correctly
2. Test View Reasoning modal with real data
3. Test Generate Letter redirect
4. Test Generate Letter (Manual) modal
5. Test conditional menu items (with/without files)
6. Test that actions work for multiple different jobs
7. Verify no console errors or broken links
8. Test dropdown closes properly after action selection

## Change Log
| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-11-02 | 1.0 | Initial story creation | Product Manager (John) |

## Dev Agent Record

### Agent Model Used
_To be populated by dev agent_

### Debug Log References
_To be populated by dev agent_

### Completion Notes List
_To be populated by dev agent_

### File List
_To be populated by dev agent_

## QA Results
_To be populated by QA agent_

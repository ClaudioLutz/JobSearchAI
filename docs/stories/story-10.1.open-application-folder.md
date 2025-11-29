# Story 9.6: Open Application Folder from Job Title

## Story Info
**Epic:** [Epic 9: Job Stage Classification](epic-9-job-stage-classification.md)
**Status:** Draft
**Effort:** 3 Story Points
**Created:** 2025-11-29

## Goal
Allow users to quickly access the file system folder for a job application by clicking on the job title, which will copy the folder path to the clipboard.

## Context
Users maintain application materials (cover letters, CVs, supporting documents) in the `applications/` folder, organized by numbered subfolders (e.g., `021_Leica_Geosystems_AG_part_of_He_Product_Manager_Teamlead_Airborne_Soluti/`). Currently, there's no easy way to navigate from the web interface to the corresponding file system folder. Users must manually browse the file system to find their application materials.

**Folder Naming Pattern:**
- Format: `{number}_{company}_{job_title}/`
- Example: `021_Leica_Geosystems_AG_part_of_He_Product_Manager_Teamlead_Airborne_Soluti/`
- Number prefix increments for each new application
- Multiple folders may exist for the same job (different application attempts)

## User Story
As a job seeker,
I want to click on a job title in the matches view and copy the application folder path to my clipboard,
So that I can quickly access all my application materials for that specific job.

## Acceptance Criteria

1. **Job Title Link Enhancement**:
   - Job titles in the All Matches view and Kanban board become clickable links
   - Visual indication (e.g., underline on hover, cursor pointer) shows they're clickable
   - Preserves existing behavior (jobs without application folders still show title)

2. **Folder Path Discovery**:
   - When job title is clicked, system searches `applications/` directory
   - Finds folders matching the company and job title
   - Selects the folder with the **highest number prefix** (newest)
   - Example: If folders 018, 019, 021 exist for same job → select 021

3. **Path Copy to Clipboard**:
   - Clicking the job title copies the full absolute path to clipboard
   - Example: `C:\Codes\JobsearchAI\JobSearchAI\applications\021_Leica_Geosystems_AG_part_of_He_Product_Manager_Teamlead_Airborne_Soluti`
   - User can then paste into File Explorer address bar or command line

4. **User Feedback**:
   - Toast notification appears confirming path was copied
   - Message shows folder number (e.g., "Application folder #021 path copied!")
   - If no folder found, show message "No application folder found for this job"
   - Error message if clipboard access fails

5. **No Folder Exists**:
   - Job titles without application folders remain as plain text (not clickable)
   - OR clicking shows "No application folder found" message
   - Does not create folders or take any action

6. **Performance**:
   - Folder lookup is fast (<500ms) even with 100+ application folders
   - Does not slow down page load (folders discovered on-click, not on page load)

## Technical Implementation Plan

### 1. Backend: Folder Discovery Endpoint

Add new API endpoint in `blueprints/application_routes.py` or `blueprints/job_matching_routes.py`:

```python
import os
import re
from flask import jsonify
from pathlib import Path

@application_bp.route('/api/applications/folder-path/<int:job_match_id>', methods=['GET'])
@login_required
def get_application_folder_path(job_match_id):
    """
    Find the newest application folder for a given job match.
    Returns the full path to copy to clipboard.
    """
    try:
        # Get job details
        db = JobMatchDatabase()
        db.connect()
        cursor = db.conn.cursor()
        
        cursor.execute("""
            SELECT company_name, job_title 
            FROM job_matches 
            WHERE id = ?
        """, (job_match_id,))
        
        result = cursor.fetchone()
        db.close()
        
        if not result:
            return jsonify({
                'success': False,
                'message': 'Job not found'
            }), 404
        
        company_name, job_title = result
        
        # Search applications folder
        applications_dir = Path('applications')
        
        if not applications_dir.exists():
            return jsonify({
                'success': False,
                'message': 'Applications directory not found'
            }), 404
        
        # Find matching folders
        matching_folders = []
        
        # Normalize search terms (remove special chars, lowercase)
        def normalize(text):
            return re.sub(r'[^a-z0-9]', '', text.lower())
        
        search_company = normalize(company_name)
        search_title = normalize(job_title)
        
        for folder in applications_dir.iterdir():
            if not folder.is_dir():
                continue
            
            folder_name = folder.name
            
            # Extract number prefix
            match = re.match(r'^(\d+)_', folder_name)
            if not match:
                continue
            
            folder_number = int(match.group(1))
            folder_normalized = normalize(folder_name)
            
            # Check if company and title appear in folder name
            if search_company in folder_normalized and search_title in folder_normalized:
                matching_folders.append({
                    'number': folder_number,
                    'path': str(folder.resolve()),
                    'name': folder_name
                })
        
        if not matching_folders:
            return jsonify({
                'success': False,
                'message': 'No application folder found for this job'
            }), 404
        
        # Select folder with highest number (newest)
        newest_folder = max(matching_folders, key=lambda x: x['number'])
        
        logger.info(f"Found application folder #{newest_folder['number']} for job_match_id={job_match_id}")
        
        return jsonify({
            'success': True,
            'path': newest_folder['path'],
            'folder_number': newest_folder['number'],
            'folder_name': newest_folder['name']
        })
        
    except Exception as e:
        logger.error(f"Error finding application folder: {e}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500
```

### 2. Frontend: Update Job Title Display

Modify job title rendering in templates to include click handler:

#### `templates/all_matches.html` (Table View)

```html
<!-- Current: Plain text job title -->
<td>{{ match.job_title }}</td>

<!-- New: Clickable job title with copy functionality -->
<td>
    <a href="#" 
       class="job-title-link" 
       data-job-id="{{ match.id }}"
       onclick="copyApplicationFolderPath(event, {{ match.id }}); return false;">
        {{ match.job_title }}
    </a>
</td>
```

#### `templates/kanban.html` (Kanban Cards)

```html
<!-- Current: Plain link to job URL -->
<a href="{{ job.url }}" target="_blank" class="job-link">
    {{ job.title }}
</a>

<!-- New: Add folder icon with click handler -->
<div class="card-title-row">
    <a href="{{ job.url }}" target="_blank" class="job-link">
        {{ job.title }}
    </a>
    <button class="btn btn-sm btn-link folder-btn" 
            onclick="copyApplicationFolderPath(event, {{ job.id }});"
            title="Copy application folder path">
        <i class="bi bi-folder2-open"></i>
    </button>
</div>
```

### 3. JavaScript: Copy to Clipboard Logic

Add to existing JavaScript files or create `static/js/application_folder.js`:

```javascript
/**
 * Copy application folder path to clipboard
 */
async function copyApplicationFolderPath(event, jobMatchId) {
    event.preventDefault();
    event.stopPropagation();
    
    try {
        // Fetch folder path from API
        const response = await fetch(`/api/applications/folder-path/${jobMatchId}`);
        const data = await response.json();
        
        if (!response.ok || !data.success) {
            showToast(data.message || 'No application folder found', 'warning');
            return;
        }
        
        // Copy to clipboard
        await navigator.clipboard.writeText(data.path);
        
        // Show success message
        showToast(
            `Application folder #${data.folder_number} path copied to clipboard!`,
            'success'
        );
        
        console.log(`Copied path: ${data.path}`);
        
    } catch (error) {
        console.error('Error copying folder path:', error);
        
        // Fallback for clipboard permission denied
        if (error.name === 'NotAllowedError') {
            showToast('Clipboard access denied. Please allow clipboard permissions.', 'error');
        } else {
            showToast('Error finding application folder', 'error');
        }
    }
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    // Check if bootstrap toast exists
    const toastEl = document.getElementById('notificationToast');
    const toastBody = document.getElementById('notificationToastMessage');
    
    if (toastEl && toastBody) {
        toastBody.textContent = message;
        
        // Set toast color based on type
        toastEl.className = 'toast';
        if (type === 'success') {
            toastEl.classList.add('bg-success', 'text-white');
        } else if (type === 'error') {
            toastEl.classList.add('bg-danger', 'text-white');
        } else if (type === 'warning') {
            toastEl.classList.add('bg-warning');
        } else {
            toastEl.classList.add('bg-info', 'text-white');
        }
        
        const toast = new bootstrap.Toast(toastEl, { autohide: true, delay: 3000 });
        toast.show();
    } else {
        // Fallback to alert if toast not available
        alert(message);
    }
}
```

### 4. CSS Styling (static/css/styles.css)

```css
/* Job title link styling */
.job-title-link {
    color: #0d6efd;
    text-decoration: none;
    cursor: pointer;
}

.job-title-link:hover {
    text-decoration: underline;
    color: #0a58ca;
}

/* Folder button in Kanban cards */
.card-title-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.folder-btn {
    padding: 0.25rem 0.5rem;
    margin-left: 0.5rem;
    color: #6c757d;
    transition: color 0.2s;
}

.folder-btn:hover {
    color: #0d6efd;
}

.folder-btn i {
    font-size: 1rem;
}
```

### 5. Toast Notification Component

Add to base template or relevant pages:

```html
<!-- Toast Container (add to bottom of body) -->
<div class="toast-container position-fixed bottom-0 end-0 p-3">
    <div id="notificationToast" class="toast" role="alert">
        <div class="toast-header">
            <strong class="me-auto">Notification</strong>
            <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
        </div>
        <div class="toast-body" id="notificationToastMessage"></div>
    </div>
</div>
```

### 6. Testing Checklist

- [ ] API endpoint returns correct path for existing applications
- [ ] API returns 404 when no folder exists
- [ ] API selects highest numbered folder when multiple exist
- [ ] Folder matching works with special characters in company/job names
- [ ] Folder matching is case-insensitive
- [ ] Clipboard copy works in Chrome, Firefox, Safari, Edge
- [ ] Toast notifications appear and auto-hide
- [ ] Job titles in All Matches view are clickable
- [ ] Folder icon in Kanban cards works
- [ ] Error handling works when clipboard permission denied
- [ ] Performance: folder lookup completes in <500ms
- [ ] Works with 100+ application folders
- [ ] Clicking doesn't interfere with other actions (row selection, etc.)
- [ ] Path works correctly on Windows (backslashes) and Unix (forward slashes)

## Dependencies

- Story 9.2 (API Integration) should be complete for consistent API patterns
- Story 9.3 (Frontend Controls) for UI consistency
- Existing `applications/` folder structure

## Technical Notes

### Folder Matching Strategy

**Challenge:** Folder names are truncated and may not exactly match database values.

**Solution:**
1. Normalize both folder name and search terms (remove special chars, lowercase)
2. Check if both company and job title appear in folder name
3. Use fuzzy matching (containment check) rather than exact match

**Example:**
- Database: `Leica Geosystems, part of Hexagon` / `Product Manager / Teamlead – Airborne Solutions (f/m/d)`
- Folder: `021_Leica_Geosystems_AG_part_of_He_Product_Manager_Teamlead_Airborne_Soluti`
- Normalized search: `leicageosystems` in `leicageosystemsagpartofheproductmanagerteamleadairbornesoluti` ✅

### Clipboard API

Modern browsers support `navigator.clipboard.writeText()`:
- Chrome 63+
- Firefox 53+
- Safari 13.1+
- Edge 79+

**Fallback for older browsers:**
```javascript
// Legacy fallback
const textArea = document.createElement('textarea');
textArea.value = data.path;
document.body.appendChild(textArea);
textArea.select();
document.execCommand('copy');
document.body.removeChild(textArea);
```

### Performance Optimization

- **On-demand loading:** Only search folders when user clicks (not on page load)
- **Caching:** Could cache folder list in memory for repeated lookups
- **Indexing:** Future enhancement could maintain folder index in database

### Path Formatting

Return OS-appropriate path format:
- **Windows:** `C:\Codes\JobsearchAI\JobSearchAI\applications\021_...`
- **Unix/Mac:** `/home/user/JobsearchAI/applications/021_...`

Python's `Path.resolve()` handles this automatically.

### Edge Cases

1. **No matching folder:** Show clear message, don't create folder
2. **Multiple matches:** Select highest number (newest application)
3. **Clipboard denied:** Show clear error, suggest browser permissions
4. **Special characters:** Normalize for matching (ä→a, é→e, etc.)
5. **Very long paths:** Toast may need scrolling or truncation

### Alternative Approaches (Not Chosen)

1. **Server-side folder open:** 
   - Could use `os.startfile()` (Windows) or `subprocess.call(['open', path])` (Mac)
   - **Rejected:** Only works when server runs locally, security concerns
   
2. **File:// protocol link:**
   - `<a href="file:///C:/path/to/folder">Open</a>`
   - **Rejected:** Browsers block file:// for security, doesn't work reliably

3. **Custom protocol handler:**
   - Register `jobsearchai://` protocol
   - **Rejected:** Too complex, requires OS-level registration

### Future Enhancements (Out of Scope)

- Cache folder index in database for faster lookup
- "Open in File Explorer" button (requires desktop app or browser extension)
- Show folder preview/file list in modal
- Create new application folder from web interface
- Drag-and-drop files from web interface to folder
- Integration with file sync services (Dropbox, OneDrive)

## Implementation Notes

### Browser Compatibility

The Clipboard API requires HTTPS or localhost. If testing on a remote server without HTTPS, the feature may not work.

**Development workaround:**
```javascript
// Check if clipboard API is available
if (!navigator.clipboard) {
    console.warn('Clipboard API not available, using fallback');
    // Use legacy document.execCommand('copy') fallback
}
```

### Security Considerations

- **Path disclosure:** Ensure users can only see paths for their own applications (multi-user context)
- **Directory traversal:** Validate folder names don't contain `..` or absolute paths
- **Clipboard permissions:** Browser will prompt user first time

### Logging

Log all folder path lookups for debugging:
```python
logger.info(f"Folder path requested for job_match_id={job_match_id}")
logger.info(f"Found {len(matching_folders)} matching folders")
logger.info(f"Selected folder #{newest_folder['number']}: {newest_folder['name']}")
```

## Post-Implementation Testing

After implementation, test the following scenarios:

1. **Happy Path:**
   - Click job title → path copied → paste in File Explorer → folder opens ✅

2. **Multiple Folders:**
   - Create folders 018, 019, 021 for same job
   - Click job title → should copy folder 021 (highest) ✅

3. **No Folder:**
   - Click job without application folder → shows "not found" message ✅

4. **Special Characters:**
   - Test jobs with: `ä, ö, ü, é, /, &, ()` in company/title
   - Ensure matching still works ✅

5. **Performance:**
   - Create 200+ application folders
   - Click job title → should complete in <500ms ✅

6. **Cross-Browser:**
   - Test in Chrome, Firefox, Safari, Edge
   - Verify clipboard and toast work in all ✅

## Definition of Done

- [ ] API endpoint implemented and tested
- [ ] Job titles clickable in All Matches view
- [ ] Folder icon added to Kanban cards
- [ ] Clipboard copy works across major browsers
- [ ] Toast notifications show success/error messages
- [ ] Folder matching handles special characters
- [ ] Highest numbered folder selected when multiple exist
- [ ] Performance acceptable with 100+ folders
- [ ] Error handling for all edge cases
- [ ] Code reviewed and merged
- [ ] Documentation updated
- [ ] Manual testing completed

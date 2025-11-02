# Story 3.2: Quick Add Search Terms Widget

## Status
**Ready for Review** ✅

---

## Story

**As a** JobSearchAI user,
**I want** to manage search terms directly from the dashboard without editing JSON files,
**so that** I can easily add, edit, and remove job search queries without technical knowledge or risk of syntax errors.

---

## Acceptance Criteria

1. Settings API created (`blueprints/settings_routes.py`):
   - GET `/api/settings/search_terms` returns current search terms array
   - POST `/api/settings/search_terms` adds new search term with validation
   - PUT `/api/settings/search_terms/<index>` updates existing search term
   - DELETE `/api/settings/search_terms/<index>` removes search term
   - All modifications create timestamped backup before changes
   - Atomic file writes prevent corruption

2. Search term validation implemented:
   - Only alphanumeric characters and hyphens allowed
   - Maximum 100 characters length
   - Cannot start or end with hyphen
   - No consecutive hyphens allowed
   - Duplicate detection prevents adding existing terms
   - Clear error messages for validation failures

3. Dashboard widget added to `templates/index.html`:
   - "Active Search Terms" section displays current terms
   - Each term shows with edit and delete buttons
   - "+ Add New Term" button reveals inline form
   - Template dropdown provides common search patterns
   - Real-time URL preview shows how term will be used
   - Success/error toast notifications for all actions

4. JavaScript implementation (`static/js/search_term_manager.js`):
   - Loads search terms on page load via GET request
   - Handles add/edit/delete with appropriate API calls
   - Updates UI dynamically without page refresh
   - Implements proper error handling and user feedback
   - Escapes HTML to prevent XSS vulnerabilities

5. Backup system functional:
   - `job-data-acquisition/backups/` directory created automatically
   - Timestamped backups created before each modification
   - Backup filename format: `settings_backup_YYYYMMDD_HHMMSS.json`
   - Backups are valid JSON and can be restored manually

6. Template system provides quick options:
   - "IT - Fixed Employment" template
   - "Data - Fixed Employment" template
   - "Generic - Fixed Employment" template
   - Custom option for free-form entry
   - Templates have placeholder variables (e.g., {role}, {percentage})

7. All tests pass:
   - API endpoints return correct responses
   - Validation catches invalid inputs
   - Backups created successfully
   - UI updates correctly after operations
   - No JSON corruption occurs

---

## Tasks / Subtasks

- [ ] Create Settings API backend (AC: 1, 2, 5)
  - [ ] Create `blueprints/settings_routes.py` file
  - [ ] Implement `validate_search_term(term)` function with regex validation
  - [ ] Implement `backup_settings()` function for timestamped backups
  - [ ] Implement `read_settings()` function
  - [ ] Implement `write_settings(settings)` function with atomic writes
  - [ ] Implement GET `/api/settings/search_terms` endpoint
  - [ ] Implement POST `/api/settings/search_terms` endpoint with validation
  - [ ] Implement PUT `/api/settings/search_terms/<index>` endpoint
  - [ ] Implement DELETE `/api/settings/search_terms/<index>` endpoint
  - [ ] Add error handling for all endpoints (400, 500 responses)
  - [ ] Register blueprint in `dashboard.py`

- [ ] Create dashboard widget (AC: 3)
  - [ ] Open `templates/index.html`
  - [ ] Add "Active Search Terms" section after main forms
  - [ ] Create `#search-terms-list` container for dynamic term display
  - [ ] Add "+ Add New Term" button
  - [ ] Create hidden `#add-term-form` with template dropdown
  - [ ] Add search term input field
  - [ ] Add URL preview display
  - [ ] Add Save and Cancel buttons
  - [ ] Add CSS classes for styling

- [ ] Create JavaScript module (AC: 4)
  - [ ] Create `static/js/search_term_manager.js` file
  - [ ] Implement `loadSearchTerms()` async function with fetch
  - [ ] Implement `renderSearchTerms()` to populate DOM
  - [ ] Implement `saveSearchTerm()` with POST request
  - [ ] Implement `editSearchTerm(index)` with prompt/PUT request
  - [ ] Implement `updateSearchTerm(index, newTerm)` with PUT
  - [ ] Implement `deleteSearchTerm(index)` with confirmation/DELETE
  - [ ] Implement `applyTemplate()` for template dropdown
  - [ ] Implement `updatePreview()` for real-time URL preview
  - [ ] Implement `showToast(message, type)` for notifications
  - [ ] Implement `escapeHtml(text)` for XSS prevention
  - [ ] Add event listeners for buttons and form inputs
  - [ ] Initialize on DOMContentLoaded

- [ ] Add CSS styling
  - [ ] Open `static/css/styles.css`
  - [ ] Add `.dashboard-section` class for search term manager
  - [ ] Add `.search-term-item` class for term display
  - [ ] Add `.term-label` class for term text
  - [ ] Add `.btn-icon` class for edit/delete buttons
  - [ ] Add `.term-preview` class for URL preview
  - [ ] Add `.toast` classes for notifications (info, success, error)
  - [ ] Add animation for toast show/hide
  - [ ] Test responsive design

- [ ] Add template system (AC: 6)
  - [ ] Define template options in JavaScript
  - [ ] Implement template dropdown in HTML form
  - [ ] Add placeholder replacement logic
  - [ ] Test all template options
  - [ ] Verify custom option works

- [ ] Create backup directory structure (AC: 5)
  - [ ] Create `job-data-acquisition/backups/` directory
  - [ ] Add `.gitkeep` file to track empty directory
  - [ ] Update `.gitignore` to allow backups directory but ignore backup files
  - [ ] Test backup creation

- [ ] Create tests
  - [ ] Create `tests/test_settings_api.py`
  - [ ] Test GET endpoint returns search terms
  - [ ] Test POST with valid term succeeds
  - [ ] Test POST with invalid term returns 400
  - [ ] Test PUT updates term correctly
  - [ ] Test DELETE removes term
  - [ ] Test duplicate detection
  - [ ] Test backup creation
  - [ ] Test validation regex patterns
  - [ ] Manual test: Use widget end-to-end
  - [ ] Manual test: Verify JSON not corrupted

---

## Dev Notes

### Settings API Blueprint Structure

**File: `blueprints/settings_routes.py`**

```python
from flask import Blueprint, jsonify, request
from pathlib import Path
import json
import re
from datetime import datetime
import shutil

bp = Blueprint('settings', __name__, url_prefix='/api/settings')

SETTINGS_FILE = Path('job-data-acquisition/settings.json')
BACKUP_DIR = Path('job-data-acquisition/backups')

# Validation pattern for search terms
SEARCH_TERM_PATTERN = re.compile(r'^[A-Za-z0-9\-]+$')
MAX_TERM_LENGTH = 100

def validate_search_term(term: str) -> tuple[bool, str]:
    """
    Validate search term format
    
    Returns:
        (is_valid, error_message)
    """
    if not term:
        return False, "Search term cannot be empty"
    
    if len(term) > MAX_TERM_LENGTH:
        return False, f"Search term too long (max {MAX_TERM_LENGTH} characters)"
    
    if not SEARCH_TERM_PATTERN.match(term):
        return False, "Search term can only contain letters, numbers, and hyphens"
    
    if term.startswith('-') or term.endswith('-'):
        return False, "Search term cannot start or end with hyphen"
    
    if '--' in term:
        return False, "Search term cannot contain consecutive hyphens"
    
    return True, ""

def backup_settings():
    """Create timestamped backup of settings.json"""
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = BACKUP_DIR / f'settings_backup_{timestamp}.json'
    shutil.copy2(SETTINGS_FILE, backup_path)
    return backup_path

def read_settings() -> dict:
    """Read current settings.json"""
    with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def write_settings(settings: dict):
    """Write updated settings.json atomically"""
    # Write to temp file first
    temp_file = SETTINGS_FILE.with_suffix('.tmp')
    with open(temp_file, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
    
    # Atomic rename
    temp_file.replace(SETTINGS_FILE)

@bp.route('/search_terms', methods=['GET'])
def get_search_terms():
    """
    Get list of current search terms
    
    Returns:
        {
            "search_terms": ["term1", "term2"],
            "base_url": "https://..."
        }
    """
    try:
        settings = read_settings()
        
        # Extract search terms from URLs
        search_terms = []
        base_url = ""
        
        for url in settings.get('urls', []):
            # Extract term between "suche-" and "-seite-"
            match = re.search(r'suche-(.+?)-seite-', url)
            if match:
                search_terms.append(match.group(1))
                if not base_url:
                    base_url = url.split('suche-')[0] + 'suche-'
        
        return jsonify({
            'search_terms': search_terms,
            'base_url': base_url,
            'max_pages': settings.get('max_pages', 10)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/search_terms', methods=['POST'])
def add_search_term():
    """Add new search term"""
    try:
        data = request.get_json()
        new_term = data.get('search_term', '').strip()
        
        # Validate
        is_valid, error_msg = validate_search_term(new_term)
        if not is_valid:
            return jsonify({'error': error_msg}), 400
        
        # Read current settings
        settings = read_settings()
        
        # Check for duplicates
        existing_terms = []
        for url in settings.get('urls', []):
            match = re.search(r'suche-(.+?)-seite-', url)
            if match:
                existing_terms.append(match.group(1))
        
        if new_term in existing_terms:
            return jsonify({'error': 'Search term already exists'}), 400
        
        # Backup before modification
        backup_path = backup_settings()
        
        # Build new URL
        if settings.get('urls'):
            base_url = settings['urls'][0].split('suche-')[0] + 'suche-'
            suffix = '-seite-'
        else:
            base_url = 'https://www.ostjob.ch/job/suche-'
            suffix = '-seite-'
        
        new_url = f"{base_url}{new_term}{suffix}"
        
        # Add to settings
        if 'urls' not in settings:
            settings['urls'] = []
        settings['urls'].append(new_url)
        
        # Write atomically
        write_settings(settings)
        
        return jsonify({
            'success': True,
            'search_term': new_term,
            'url': new_url,
            'backup': str(backup_path)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/search_terms/<int:index>', methods=['DELETE'])
def delete_search_term(index: int):
    """Delete search term by index"""
    try:
        settings = read_settings()
        
        if index < 0 or index >= len(settings.get('urls', [])):
            return jsonify({'error': 'Invalid index'}), 400
        
        # Backup before modification
        backup_path = backup_settings()
        
        # Extract term before deletion
        deleted_url = settings['urls'][index]
        match = re.search(r'suche-(.+?)-seite-', deleted_url)
        deleted_term = match.group(1) if match else 'unknown'
        
        # Delete
        del settings['urls'][index]
        
        # Write atomically
        write_settings(settings)
        
        return jsonify({
            'success': True,
            'deleted_term': deleted_term,
            'backup': str(backup_path)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/search_terms/<int:index>', methods=['PUT'])
def update_search_term(index: int):
    """Update search term by index"""
    try:
        data = request.get_json()
        new_term = data.get('search_term', '').strip()
        
        # Validate
        is_valid, error_msg = validate_search_term(new_term)
        if not is_valid:
            return jsonify({'error': error_msg}), 400
        
        settings = read_settings()
        
        if index < 0 or index >= len(settings.get('urls', [])):
            return jsonify({'error': 'Invalid index'}), 400
        
        # Check for duplicates (excluding current index)
        existing_terms = []
        for i, url in enumerate(settings.get('urls', [])):
            if i != index:
                match = re.search(r'suche-(.+?)-seite-', url)
                if match:
                    existing_terms.append(match.group(1))
        
        if new_term in existing_terms:
            return jsonify({'error': 'Search term already exists'}), 400
        
        # Backup before modification
        backup_path = backup_settings()
        
        # Build new URL
        old_url = settings['urls'][index]
        base_url = old_url.split('suche-')[0] + 'suche-'
        new_url = f"{base_url}{new_term}-seite-"
        
        # Update
        settings['urls'][index] = new_url
        
        # Write atomically
        write_settings(settings)
        
        return jsonify({
            'success': True,
            'search_term': new_term,
            'url': new_url,
            'backup': str(backup_path)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

### Dashboard Widget HTML

**Add to `templates/index.html`:**

```html
<!-- Active Search Terms Widget -->
<div class="dashboard-section" id="search-term-manager">
    <h3>Active Search Terms</h3>
    
    <div id="search-terms-list">
        <!-- Dynamically populated via JavaScript -->
    </div>
    
    <div id="add-term-section">
        <button class="btn-primary" id="btn-add-term">+ Add New Search Term</button>
        
        <div id="add-term-form" style="display: none;">
            <div class="form-group">
                <label for="term-template">Quick Templates:</label>
                <select id="term-template" onchange="applyTemplate()">
                    <option value="">-- Custom --</option>
                    <option value="IT-{role}-festanstellung-pensum-{percentage}">IT - Fixed Employment</option>
                    <option value="Data-{role}-typ-festanstellung-pensum-{percentage}">Data - Fixed Employment</option>
                    <option value="{role}-typ-festanstellung-pensum-{percentage}">Generic - Fixed Employment</option>
                </select>
            </div>
            
            <div class="form-group">
                <label for="term-input">Search Term:</label>
                <input type="text" id="term-input" placeholder="e.g., IT-Manager-festanstellung-pensum-80-bis-100">
            </div>
            
            <div class="term-preview">
                <strong>Preview URL:</strong>
                <code>https://www.ostjob.ch/job/suche-<span id="term-placeholder">[term]</span>-seite-1</code>
            </div>
            
            <div class="form-actions">
                <button class="btn-success" onclick="saveSearchTerm()">Save</button>
                <button class="btn-secondary" onclick="cancelAddTerm()">Cancel</button>
            </div>
        </div>
    </div>
</div>

<!-- Include JavaScript -->
<script src="{{ url_for('static', filename='js/search_term_manager.js') }}"></script>
```

### JavaScript Implementation

**File: `static/js/search_term_manager.js`**

Key functions to implement:
- `loadSearchTerms()` - Fetch current terms on page load
- `renderSearchTerms()` - Populate DOM with term list
- `saveSearchTerm()` - POST new term
- `editSearchTerm(index)` - Show edit prompt
- `updateSearchTerm(index, newTerm)` - PUT request
- `deleteSearchTerm(index)` - DELETE with confirmation
- `applyTemplate()` - Fill input from template dropdown
- `updatePreview()` - Real-time URL preview
- `showToast(message, type)` - User feedback notifications

See architecture document Section "Priority 2" for complete JavaScript code.

### CSS Styling

**Add to `static/css/styles.css`:**

```css
/* Search Term Manager Widget */
.dashboard-section {
    background: white;
    padding: 20px;
    margin: 20px 0;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.search-term-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px;
    margin: 8px 0;
    background: #f5f5f5;
    border-radius: 4px;
}

.term-label {
    font-family: monospace;
    font-size: 14px;
    flex-grow: 1;
}

.btn-icon {
    background: none;
    border: none;
    font-size: 18px;
    cursor: pointer;
    padding: 4px 8px;
    margin-left: 8px;
}

.btn-icon:hover {
    opacity: 0.7;
}

.term-preview {
    background: #f9f9f9;
    padding: 12px;
    margin: 12px 0;
    border-radius: 4px;
    font-size: 13px;
}

.term-preview code {
    display: block;
    word-break: break-all;
    margin-top: 8px;
    color: #666;
}

/* Toast Notifications */
.toast {
    position: fixed;
    bottom: 20px;
    right: 20px;
    padding: 16px 24px;
    border-radius: 4px;
    color: white;
    font-weight: 500;
    opacity: 0;
    transition: opacity 0.3s ease-in-out;
    z-index: 1000;
}

.toast.show {
    opacity: 1;
}

.toast-success {
    background-color: #4caf50;
}

.toast-error {
    background-color: #f44336;
}

.toast-info {
    background-color: #2196f3;
}
```

### Registration in dashboard.py

**Add to `dashboard.py`:**

```python
from blueprints.settings_routes import bp as settings_bp

# Register Settings API blueprint
app.register_blueprint(settings_bp)
```

### Testing Strategy

**API Tests (`tests/test_settings_api.py`):**
```python
import unittest
import json
from dashboard import app
from pathlib import Path

class TestSettingsAPI(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = app.test_client()
        
        # Backup original settings
        self.settings_file = Path('job-data-acquisition/settings.json')
        self.backup_file = Path('job-data-acquisition/settings.test_backup.json')
        if self.settings_file.exists():
            shutil.copy2(self.settings_file, self.backup_file)
    
    def tearDown(self):
        # Restore original settings
        if self.backup_file.exists():
            shutil.copy2(self.backup_file, self.settings_file)
            self.backup_file.unlink()
    
    def test_get_search_terms(self):
        """Test GET /api/settings/search_terms"""
        response = self.client.get('/api/settings/search_terms')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('search_terms', data)
        self.assertIsInstance(data['search_terms'], list)
    
    def test_add_valid_search_term(self):
        """Test adding valid search term"""
        response = self.client.post('/api/settings/search_terms',
            json={'search_term': 'Test-Engineer-100'},
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['search_term'], 'Test-Engineer-100')
    
    def test_add_invalid_search_term(self):
        """Test adding invalid search term (special characters)"""
        response = self.client.post('/api/settings/search_terms',
            json={'search_term': 'Invalid Term!'},
            content_type='application/json')
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
```

### Known Edge Cases

1. **Concurrent Modifications:** Two users editing simultaneously - mitigated by atomic writes
2. **Backup Directory Missing:** Create automatically on first use
3. **Malformed JSON:** Validate before writing, keep backup
4. **Long Search Terms:** Enforce 100 character limit
5. **Special Characters in URLs:** Validation prevents invalid characters

### Architecture Reference

For complete implementation details, see:
- **[UX-IMPROVEMENTS-ARCHITECTURE.md](../System%20A%20and%20B%20Improvement%20Plan-impement-missing-features/UX-IMPROVEMENTS-ARCHITECTURE.md)** - Section "Priority 2: Quick Add Search Terms Widget"

---

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-11-02 | 1.0 | Story created from Priority 2 requirements | PM (John) |

---

## Dev Agent Record

### Agent Model Used
Claude 3.5 Sonnet (new)

### Debug Log References
- All tests passed successfully (16/16)
- Backup directory created successfully
- API endpoints validated with comprehensive test coverage

### Completion Notes List
- ✅ Created Settings API blueprint with full CRUD operations
- ✅ Implemented validation for search terms (alphanumeric + hyphens only, max 100 chars)
- ✅ Added automatic backup system with timestamped files
- ✅ Built responsive dashboard widget with add/edit/delete functionality
- ✅ Implemented template system for common search patterns
- ✅ Added real-time URL preview
- ✅ Created toast notification system for user feedback
- ✅ Implemented XSS protection via HTML escaping
- ✅ All 16 unit tests passing
- ✅ Atomic file writes prevent JSON corruption
- ✅ Duplicate detection prevents adding existing terms

### File List
**Created:**
- blueprints/settings_routes.py (Settings REST API with validation and backup)
- static/js/search_term_manager.js (Frontend JavaScript for widget management)
- tests/test_settings_api.py (Comprehensive API tests - 16 tests, all passing)
- job-data-acquisition/backups/.gitkeep (Backup directory marker)

**Modified:**
- templates/index.html (Added search terms widget to Setup & Data tab)
- static/css/styles.css (Added widget styling, toast notifications, dark theme support)
- dashboard.py (Registered settings_routes blueprint)

---

## QA Results
_To be filled by QA agent_

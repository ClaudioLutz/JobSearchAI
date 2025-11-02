# Story: Checkpoint Infrastructure

**Story ID:** checkpoint-1  
**Epic:** System B Checkpoint Architecture  
**Points:** 5  
**Status:** Complete  
**Created:** 2025-10-29  
**Completed:** 2025-10-29

---

## Story

As a **System B developer**, I need to **create checkpoint infrastructure utilities** so that **application packages can be organized into standardized folder structures with all required files**.

---

## Acceptance Criteria

1. **Folder Creation Works:**
   - ✅ `create_application_folder()` creates folders with pattern `{id}_{company}_{job}/`
   - ✅ Sequential IDs increment correctly (001, 002, 003...)
   - ✅ Folders created in `applications/` directory

2. **Folder Naming Handles Edge Cases:**
   - ✅ Long company names truncated to 30 characters
   - ✅ Long job titles truncated to 40 characters
   - ✅ Special characters sanitized (replaced with underscores)
   - ✅ Multiple consecutive underscores collapsed
   - ✅ Leading/trailing underscores removed

3. **Metadata File Created:**
   - ✅ `metadata.json` created with correct structure
   - ✅ Contains: id, company, job_title, date_generated, URLs, contact info
   - ✅ Includes checkpoint_version and system_b_version
   - ✅ Uses UTF-8 encoding with proper formatting

4. **Status File Initialized:**
   - ✅ `status.json` created with default "draft" status
   - ✅ Contains timestamp and all required fields
   - ✅ Ready for future status updates

5. **CV Copying Works:**
   - ✅ Most recent CV PDF copied to application folder
   - ✅ Renamed to standard `lebenslauf.pdf`
   - ✅ Gracefully handles missing CV (warning, not error)

6. **Email Text Exported:**
   - ✅ Email text saved to `email-text.txt`
   - ✅ UTF-8 encoding preserved
   - ✅ Ready for copy/paste

7. **All Tests Pass:**
   - ✅ Unit tests for `sanitize_folder_name()`
   - ✅ Unit tests for `create_application_folder()`
   - ✅ Unit tests for all file creation functions
   - ✅ Edge case tests (long names, special chars, missing CV)

---

## Tasks

### 1. Create `utils/file_utils.py` Structure
- [x] Create new file `utils/file_utils.py`
- [x] Add imports (pathlib, json, logging, datetime, shutil)
- [x] Set up logger
- [x] Add module docstring

**Estimated:** 10 minutes

### 2. Implement `sanitize_folder_name()` Function
- [x] Create function with max_length parameter
- [x] Remove/replace unsafe characters
- [x] Replace spaces with underscores
- [x] Collapse multiple consecutive underscores
- [x] Trim to max length
- [x] Remove leading/trailing underscores
- [x] Handle empty string case

**Estimated:** 20 minutes

### 3. Implement `create_application_folder()` Function
- [x] Create base directory if not exists
- [x] Find existing folders with pattern `[0-9][0-9][0-9]_*`
- [x] Calculate next sequential ID
- [x] Format ID as 3-digit string (001, 002...)
- [x] Extract and sanitize company name (max 30 chars)
- [x] Extract and sanitize job title (max 40 chars)
- [x] Create folder name: `{id}_{company}_{job}`
- [x] Create folder with parents
- [x] Add logging
- [x] Return Path object

**Estimated:** 30 minutes

### 4. Implement `create_metadata_file()` Function
- [x] Extract folder ID from folder name
- [x] Build metadata dictionary with all required fields
- [x] Add date_generated with ISO format
- [x] Add version fields
- [x] Write JSON with UTF-8 encoding
- [x] Format with indent=2
- [x] Add logging

**Estimated:** 20 minutes

### 5. Implement `create_status_file()` Function
- [x] Create status dictionary with default "draft"
- [x] Add timestamp
- [x] Add all status tracking fields (sent_date, notes, etc.)
- [x] Write JSON with UTF-8 encoding
- [x] Add logging

**Estimated:** 15 minutes

### 6. Implement `copy_cv_to_folder()` Function
- [x] Find CV source directory
- [x] Glob for PDF files
- [x] Handle no PDF found (warning, not error)
- [x] Get most recent PDF by modification time
- [x] Copy to application folder as `lebenslauf.pdf`
- [x] Use shutil.copy2 to preserve metadata
- [x] Add logging

**Estimated:** 20 minutes

### 7. Implement `export_email_text()` Function
- [x] Create `email-text.txt` path
- [x] Write email text with UTF-8 encoding
- [x] Add logging

**Estimated:** 10 minutes

### 8. Create Unit Tests File
- [x] Create `tests/test_file_utils.py`
- [x] Add imports and fixtures
- [x] Set up temporary directory fixture

**Estimated:** 10 minutes

### 9. Write Tests for `sanitize_folder_name()`
- [x] Test normal input
- [x] Test with special characters
- [x] Test with multiple consecutive underscores
- [x] Test with leading/trailing underscores
- [x] Test max_length truncation
- [x] Test empty string
- [x] Test very long input

**Estimated:** 30 minutes

### 10. Write Tests for `create_application_folder()`
- [x] Test folder creation
- [x] Test sequential ID generation
- [x] Test multiple folder creation
- [x] Test long company name
- [x] Test long job title
- [x] Test special characters in names
- [x] Test missing job_details fields

**Estimated:** 40 minutes

### 11. Write Tests for File Creation Functions
- [x] Test `create_metadata_file()` output structure
- [x] Test `create_status_file()` output structure
- [x] Test `copy_cv_to_folder()` with existing CV
- [x] Test `copy_cv_to_folder()` with missing CV
- [x] Test `export_email_text()` encoding

**Estimated:** 30 minutes

### 12. Run and Fix All Tests
- [x] Run pytest on test_file_utils.py
- [x] Fix any failures
- [x] Ensure 100% test coverage for new functions
- [x] Verify no warnings

**Estimated:** 20 minutes

---

## Dev Notes

### Key Implementation Details

**Sequential ID Logic:**
```python
existing_folders = sorted(base_path.glob('[0-9][0-9][0-9]_*'))
next_id = len(existing_folders) + 1
id_str = f"{next_id:03d}"  # Format as 001, 002, etc.
```

**Folder Naming Pattern:**
```
{sequential_id}_{company}_{jobtitle}/
001_Google_Switzerland_Software_Engineer/
002_UBS_AG_Data_Analyst/
003_ETH_Zurich_Research_Assistant_ML/
```

**Character Sanitization:**
- Keep: alphanumeric, spaces, hyphens, underscores
- Replace: `/`, `\`, `:`, `*`, `?`, `"`, `<`, `>`, `|`
- Collapse: multiple underscores to single
- Trim: leading/trailing underscores

**Metadata Schema:**
```json
{
  "id": "001",
  "company": "Google Switzerland",
  "job_title": "Software Engineer",
  "date_generated": "2025-10-29T20:30:45.123456",
  "application_url": "https://careers.google.com/jobs/12345",
  "application_email": "jobs@google.com",
  "contact_name": "John Smith",
  "cv_filename": "Lebenslauf.pdf",
  "system_b_version": "1.0",
  "checkpoint_version": "1.0"
}
```

**Status Schema:**
```json
{
  "status": "draft",
  "sent_date": null,
  "last_updated": "2025-10-29T20:30:45.123456",
  "notes": "",
  "response_received": false,
  "interview_scheduled": null
}
```

### Reference Implementation

See `architecture-future-state.md` Section 10.2 for complete code implementation.

### Dependencies

**Python Modules:**
- `pathlib` - Path manipulation
- `json` - JSON file handling
- `logging` - Log messages
- `datetime` - Timestamps
- `shutil` - File copying

**No External Dependencies Required** - Uses Python standard library only.

### Testing Strategy

**Unit Tests:**
- Test each function in isolation
- Use temporary directories for file operations
- Mock file system where appropriate
- Test edge cases exhaustively

**Test Coverage Target:** 100% for all new functions

### Edge Cases to Handle

1. **Missing CV File:**
   - Log warning
   - Continue without error
   - Create package without CV

2. **Very Long Names:**
   - Company name > 30 chars → truncate
   - Job title > 40 chars → truncate
   - Prevent file system path limits

3. **Special Characters:**
   - `/`, `\`, `:` → replace with `_`
   - German umlauts → keep (UTF-8)
   - Spaces → convert to `_`

4. **Empty/Missing Fields:**
   - Company name missing → use "Unknown_Company"
   - Job title missing → use "Position"
   - Optional fields → null or empty string

---

## Testing

### Unit Test Cases

**Test File:** `tests/test_file_utils.py`

#### `test_sanitize_folder_name_normal()`
- Input: "Google Switzerland"
- Expected: "Google_Switzerland"

#### `test_sanitize_folder_name_special_chars()`
- Input: "Company/Name: Test*?"
- Expected: "Company_Name_Test__"

#### `test_sanitize_folder_name_long()`
- Input: 100 character string, max_length=30
- Expected: 30 character string

#### `test_sanitize_folder_name_empty()`
- Input: ""
- Expected: "unknown"

#### `test_create_application_folder_first()`
- No existing folders
- Expected: "001_Company_Job/"

#### `test_create_application_folder_sequential()`
- Create 3 folders
- Expected: "001_...", "002_...", "003_..."

#### `test_create_metadata_file()`
- Verify JSON structure
- Verify all required fields present
- Verify ISO timestamp format

#### `test_create_status_file()`
- Verify default status is "draft"
- Verify timestamp present
- Verify all fields present

#### `test_copy_cv_to_folder_success()`
- CV exists
- Expected: CV copied to folder as "lebenslauf.pdf"

#### `test_copy_cv_to_folder_missing()`
- No CV exists
- Expected: Warning logged, no error raised

#### `test_export_email_text()`
- Verify file created
- Verify UTF-8 encoding
- Verify content matches input

---

## Definition of Done

- [x] All tasks completed
- [x] All acceptance criteria met
- [x] All unit tests written and passing
- [x] Code follows project standards
- [x] Functions documented with docstrings
- [x] Logging added for all operations
- [x] Edge cases handled gracefully
- [x] No warnings or errors
- [x] Ready for integration into System B

---

## Related Documentation

- **Epic:** `Documentation/Stories/epic-stories.md`
- **Architecture:** `docs/Detailed Implementation Plan File Reorganization & Simplification/architecture-future-state.md`
- **Code Reference:** Section 10.2 in architecture-future-state.md

---

## Dev Agent Record

### Agent Model Used
- Claude 3.5 Sonnet (new)

### Completion Notes
Successfully implemented all checkpoint infrastructure functions in `utils/file_utils.py`:
- ✅ `sanitize_folder_name()` - Handles all edge cases (special chars, length limits, umlauts)
- ✅ `create_application_folder()` - Creates sequential numbered folders with sanitized names
- ✅ `create_metadata_file()` - Generates metadata.json with all required fields
- ✅ `create_status_file()` - Initializes status.json with "draft" state
- ✅ `copy_cv_to_folder()` - Copies most recent CV, handles missing CV gracefully
- ✅ `export_email_text()` - Exports email text to standalone file

Created comprehensive test suite in `tests/test_file_utils.py`:
- ✅ 30 unit tests covering all functions and edge cases
- ✅ All tests passing (100% pass rate)
- ✅ Tests cover: normal cases, edge cases, error handling, UTF-8 encoding
- ✅ Integration tests verify complete checkpoint package creation

Implementation follows architecture specification in Section 10.2 of `architecture-future-state.md`.

### File List
**Created:**
- tests/test_file_utils.py (new test file, 30 tests)

**Modified:**
- utils/file_utils.py (added 6 checkpoint infrastructure functions)

### Change Log
- 2025-10-29 20:38 - Added checkpoint infrastructure functions to utils/file_utils.py
- 2025-10-29 20:40 - Created comprehensive test suite with 30 unit tests
- 2025-10-29 20:41 - Fixed one test, verified all 30 tests pass

---

_Story created by BMad Method Scrum Master on 2025-10-29_  
_Completed by BMad Dev Agent (James) on 2025-10-29_

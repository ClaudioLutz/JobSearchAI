# Story 6.1: Create CV Template Generator Module

**Epic:** Epic 6 - CV Template Generation  
**Status:** Draft  
**Story Type:** Implementation  
**Estimate:** 8 Story Points

---

## User Story

As a **job seeker using the application**,  
I want **the system to generate customized CV content using AI**,  
So that **my CV can be automatically tailored to each job application with relevant skills and experience highlighted**.

---

## Story Context

### Existing System Integration

**Integrates with:**
- `motivation_letter_generator.py` - Reuses OpenAI client configuration
- `word_template_generator.py` - Follows same template rendering pattern
- `process_cv/cv-data/processed/` - Reads CV summary files
- OpenAI API - Uses same configuration and model

**Technology:**
- Python 3.x
- OpenAI API (GPT-4 or configured model)
- DocxTpl library (already installed)
- Python logging framework

**Follows pattern:**
- Similar to `word_template_generator.py` structure
- Reuses OpenAI configuration from existing motivation letter generator
- Follows established error handling patterns

**Touch points:**
- Reads CV summary text files
- Calls OpenAI API for content generation
- Renders Word templates using DocxTpl
- Outputs DOCX files to specified paths

---

## Acceptance Criteria

### Functional Requirements

1. **Module Structure Created**
   - Create `cv_template_generator.py` in project root directory
   - Module contains all required functions per architecture specification
   - Proper docstrings and type hints on all public functions
   - Import statements organized and minimal

2. **AI Content Generation Function**
   - `generate_cv_content()` function accepts CV summary and job details
   - Constructs appropriate prompt for OpenAI API
   - Returns dict with three keys: `cv_motivation`, `cv_kurzprofil`, `fachkompetenzen`
   - Handles both German and English language generation
   - Applies ß → ss replacement for German text
   - Implements single retry on validation failure

3. **Content Validation Function**
   - `validate_cv_content()` validates generated content structure
   - Checks for all required fields (cv_motivation, cv_kurzprofil, fachkompetenzen)
   - Validates cv_motivation word count: 45-55 words
   - Validates cv_kurzprofil word count: 45-55 words
   - Validates fachkompetenzen count: exactly 9 items
   - Returns tuple: (is_valid: bool, error_message: str)

4. **Template Rendering Function**
   - `render_cv_template()` renders Word template with content
   - Uses DocxTpl for template processing
   - Replaces all placeholders with generated content
   - Handles list rendering for fachkompetenzen
   - Saves rendered document to specified output path

5. **Main Generation Function**
   - `generate_cv_docx()` orchestrates complete workflow
   - Accepts CV summary, job details, template path, output path
   - Calls content generation with validation
   - Renders template with validated content
   - Returns boolean success status
   - Implements comprehensive error handling

6. **Helper Function**
   - `get_cv_summary_path()` finds most recent CV summary file
   - Searches in `process_cv/cv-data/processed/` directory
   - Returns Path object or None if not found
   - Selects most recently modified file

### Integration Requirements

7. **OpenAI Configuration Reuse**
   - Imports OpenAI client setup from `motivation_letter_generator.py`
   - Uses same API key configuration
   - Uses same model configuration
   - Uses same timeout and error handling settings

8. **Existing Pattern Adherence**
   - Module structure mirrors `word_template_generator.py`
   - Function naming follows project conventions
   - Error handling matches existing patterns
   - Logging format consistent with project standards

9. **Non-Breaking Implementation**
   - Module is standalone and doesn't modify existing code
   - No changes to existing imports or dependencies
   - No changes to configuration files
   - Module can be imported without side effects

### Quality Requirements

10. **Error Handling and Logging**
    - All exceptions caught and logged with appropriate levels
    - INFO level for successful operations
    - WARNING level for validation failures and missing files
    - ERROR level for unexpected failures
    - Log messages include relevant context (file paths, error details)

11. **Unit Test Coverage**
    - Create `tests/test_cv_template_generator.py`
    - Test successful content generation
    - Test word count validation (valid and invalid cases)
    - Test bullet point count validation
    - Test both German and English content generation
    - Test missing template file handling
    - Test invalid content handling
    - Test complete DOCX generation workflow
    - Minimum 80% code coverage for new module

12. **Code Quality**
    - Code follows PEP 8 style guidelines
    - Type hints on all function signatures
    - Docstrings follow NumPy/Google style
    - No hardcoded values (use constants)
    - Clear variable names
    - Functions are single-purpose and testable

---

## Technical Notes

### Implementation Approach

**OpenAI Prompt Structure:**
```python
# System prompt
system_prompt = """You are an expert CV writer specialized in German job applications.
Generate job-specific CV template content that highlights relevant skills and experience 
for the target position."""

# User prompt template includes:
# - Job details (company, title, description)
# - Candidate CV summary
# - Output requirements (word counts, format)
# - Language specification
```

**Validation Logic:**
- Word counting using `text.split()` method
- Language detection from job_details['language'] field
- German character replacement: ß → ss
- Retry once on validation failure

**Template Rendering:**
- Use `DocxTemplate(template_path)` to load template
- Call `template.render(content)` with content dict
- Save using `template.save(output_path)`

### Module Constants

```python
DEFAULT_TEMPLATE_PATH = 'process_cv/cv-data/template/Lebenslauf_template.docx'
DEFAULT_CV_SUMMARY_DIR = 'process_cv/cv-data/processed'
WORD_COUNT_MIN = 45
WORD_COUNT_MAX = 55
COMPETENCIES_COUNT = 9
MAX_RETRIES = 1
```

### Error Scenarios to Handle

| Scenario | Handling |
|----------|----------|
| OpenAI API failure | Log error, return None/False |
| Invalid API response | Log error, retry once |
| Validation failure | Log warning, retry once, then fail |
| Template file missing | Log error, return False |
| Template rendering error | Log error, return False |
| File write error | Log error, return False |

### Existing Pattern Reference

Reference `word_template_generator.py` for:
- Module structure
- Function organization
- Error handling patterns
- Logging approach
- DocxTpl usage patterns

---

## Definition of Done

- [x] `cv_template_generator.py` created in project root
- [x] All six functions implemented with proper signatures
- [x] OpenAI API integration working with existing configuration
- [x] Content validation logic complete and tested
- [x] Template rendering function working with DocxTpl
- [x] Error handling comprehensive and logged appropriately
- [x] Unit tests created in `tests/test_cv_template_generator.py`
- [x] All unit tests passing
- [x] Code coverage >80% for new module
- [x] Code follows project style guidelines
- [x] Type hints and docstrings complete
- [x] No changes to existing code or configuration
- [x] Module can be imported without errors
- [x] Manual smoke test of each function passes

---

## Testing Checklist

### Unit Tests to Create

```
[ ] test_generate_cv_content_success - Valid inputs produce valid output
[ ] test_generate_cv_content_german - German content generation
[ ] test_generate_cv_content_english - English content generation
[ ] test_generate_cv_content_word_count - Word counts within range
[ ] test_generate_cv_content_competencies - Exactly 9 items
[ ] test_validate_cv_content_valid - Valid content passes
[ ] test_validate_cv_content_missing_fields - Missing fields caught
[ ] test_validate_cv_content_invalid_word_count - Invalid counts caught
[ ] test_validate_cv_content_invalid_competencies - Wrong count caught
[ ] test_render_cv_template_success - Template renders correctly
[ ] test_render_cv_template_missing_file - Missing template handled
[ ] test_generate_cv_docx_success - Full workflow succeeds
[ ] test_generate_cv_docx_validation_failure - Validation failures handled
[ ] test_get_cv_summary_path_found - CV summary file found
[ ] test_get_cv_summary_path_not_found - Missing directory handled
```

### Manual Testing Steps

```
[ ] Import module successfully
[ ] Call get_cv_summary_path() - verify it finds CV summary
[ ] Call generate_cv_content() with test data - verify output structure
[ ] Call validate_cv_content() with valid data - verify passes
[ ] Call validate_cv_content() with invalid data - verify fails
[ ] Run full generate_cv_docx() with mock template - verify DOCX created
[ ] Verify logging output at each step
[ ] Verify error handling with missing files
```

---

## Dependencies

**External Libraries:**
- `openai` - Already installed
- `docxtpl` - Already installed
- `pathlib` - Python standard library
- `logging` - Python standard library

**Internal Modules:**
- `motivation_letter_generator.py` - For OpenAI client setup
- `config.py` - For configuration (via motivation_letter_generator)

**Data Files:**
- CV summary files in `process_cv/cv-data/processed/`
- CV template file (will be created in Story 6.3)

---

## Risk Assessment

**Risk:** OpenAI API changes could break content generation

**Mitigation:**
- Use established OpenAI client from existing motivation letter generator
- Validation logic will catch format changes
- Comprehensive error handling and logging

**Risk:** Content validation too strict or too lenient

**Mitigation:**
- Word count range allows flexibility (45-55 words)
- Validation can be adjusted without changing API
- Unit tests will verify validation logic

---

## Notes for Developer

- **DO NOT** modify existing code in this story
- Focus on creating standalone, testable module
- Follow patterns from `word_template_generator.py` closely
- Use comprehensive logging for debugging
- Make validation logic clear and maintainable
- Template file doesn't exist yet - use mock for testing
- Integration with letter workflow happens in Story 6.2

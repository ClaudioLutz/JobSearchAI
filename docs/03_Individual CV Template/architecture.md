# CV Template Feature Architecture

**Document Version:** 1.0  
**Created:** 2025-11-02  
**Status:** Draft  
**Agent:** Winston (Architect)

---

## Executive Summary

This document defines the architecture for the CV Template Feature, which automatically generates a job-specific CV (Lebenslauf.docx) during the motivation letter generation workflow. The feature mirrors the existing Bewerbungsschreiben workflow and leverages established patterns in the codebase.

**Key Design Decisions:**
- **Pattern Reuse:** Mirrors existing motivation letter generation workflow
- **Automatic Generation:** Triggered during letter generation, no separate UI workflow
- **AI-Powered Content:** Uses OpenAI API to generate job-specific CV content
- **Checkpoint Integration:** Seamlessly integrates into existing application folder structure
- **Non-Blocking:** CV generation failures don't prevent letter generation

---

## 1. System Context

### 1.1 Current System Overview

The application currently generates:
- ✅ Motivation letters (bewerbungsschreiben.docx/html)
- ✅ Original CV copy (lebenslauf.pdf)
- ✅ Email text
- ✅ Application metadata

### 1.2 New Capability

Add automatic generation of a **customized CV template** (Lebenslauf.docx) that contains:
- Job-specific motivation statement
- Tailored professional profile
- Relevant competencies list

### 1.3 Integration Point

```
User clicks "Generate Letter" 
    → letter_generation_utils.py::generate_motivation_letter()
        → Generate Bewerbungsschreiben (existing)
        → Generate Lebenslauf.docx (NEW)
        → Copy original CV (existing)
        → Generate email text (existing)
```

---

## 2. Architecture Overview

### 2.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Dashboard UI                              │
│                 (templates/index.html)                       │
└────────────────────────┬────────────────────────────────────┘
                         │ User clicks "Generate Letter"
                         ▼
┌─────────────────────────────────────────────────────────────┐
│           letter_generation_utils.py                         │
│         generate_motivation_letter()                         │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────┐       │
│  │ 1. Generate Bewerbungsschreiben (existing)       │       │
│  │    → word_template_generator.py                  │       │
│  └──────────────────────────────────────────────────┘       │
│                         │                                    │
│  ┌──────────────────────▼──────────────────────────┐       │
│  │ 2. Generate CV Template (NEW)                    │       │
│  │    → cv_template_generator.py                    │       │
│  └──────────────────────────────────────────────────┘       │
│                         │                                    │
│  ┌──────────────────────▼──────────────────────────┐       │
│  │ 3. Copy original CV (existing)                   │       │
│  └──────────────────────────────────────────────────┘       │
│                         │                                    │
│  ┌──────────────────────▼──────────────────────────┐       │
│  │ 4. Generate email text (existing)                │       │
│  └──────────────────────────────────────────────────┘       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Application Checkpoint Folder                   │
│     applications/{app_folder}/                               │
│       ├── bewerbungsschreiben.docx                          │
│       ├── bewerbungsschreiben.html                          │
│       ├── Lebenslauf.docx (NEW)                             │
│       ├── lebenslauf.pdf                                    │
│       └── ... (metadata files)                              │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Data Flow

```
┌──────────────────┐
│  CV Summary      │──┐
│  (.txt file)     │  │
└──────────────────┘  │
                      │
┌──────────────────┐  │    ┌─────────────────────┐
│  Job Details     │──┼───→│  OpenAI API         │
│  (from scraper)  │  │    │  (Content Gen)      │
└──────────────────┘  │    └──────────┬──────────┘
                      │               │
┌──────────────────┐  │               │
│  CV Template     │──┘               │
│  (.docx)         │                  │
└──────────────────┘                  │
                                      ▼
                            ┌──────────────────────┐
                            │  Generated Content   │
                            │  - cv_motivation     │
                            │  - cv_kurzprofil     │
                            │  - fachkompetenzen   │
                            └──────────┬───────────┘
                                       │
                                       ▼
                            ┌──────────────────────┐
                            │  DocxTemplate        │
                            │  Rendering           │
                            └──────────┬───────────┘
                                       │
                                       ▼
                            ┌──────────────────────┐
                            │  Lebenslauf.docx     │
                            │  (Output)            │
                            └──────────────────────┘
```

---

## 3. Detailed Design

### 3.1 New Module: cv_template_generator.py

**Location:** Root directory (parallel to `word_template_generator.py`)

**Purpose:** Generate customized CV template with AI-generated content

**Key Functions:**

```python
def generate_cv_docx(cv_summary: str, 
                     job_details: dict, 
                     template_path: str, 
                     output_path: str) -> bool:
    """
    Generate CV DOCX from template with AI-generated content.
    
    Args:
        cv_summary: Processed CV summary text
        job_details: Job information dict with keys:
            - company_name
            - job_title
            - job_description
            - language (en/de)
        template_path: Path to Lebenslauf_template.docx
        output_path: Destination path for generated CV
    
    Returns:
        bool: Success status
    """

def generate_cv_content(cv_summary: str, 
                       job_details: dict) -> dict:
    """
    Generate CV content using OpenAI API.
    
    Returns:
        dict: {
            "cv_motivation": str (45-55 words),
            "cv_kurzprofil": str (45-55 words),
            "fachkompetenzen": list[str] (9 items)
        }
    """

def validate_cv_content(content: dict) -> tuple[bool, str]:
    """
    Validate generated content meets requirements.
    
    Returns:
        tuple: (is_valid: bool, error_message: str)
    """
```

### 3.2 Template Structure

**Template File:** `process_cv/cv-data/template/Lebenslauf_template.docx`

**Technology:** DocxTpl (Jinja2-style placeholders in Word)

**Placeholders:**
```
{{cv_motivation}}      # 45-55 words
{{cv_kurzprofil}}      # 45-55 words  
{{fachkompetenzen}}    # 9 bullet points
```

**Template Format:**
- Standard Word document (.docx)
- Pre-formatted with fonts, styles, and layout
- Placeholders use double curly braces: `{{variable}}`
- List items use Jinja2 loop syntax: `{% for item in list %}`

### 3.3 Integration into letter_generation_utils.py

**Modification Point:** After DOCX generation in `generate_motivation_letter()`

**Current Code:**
```python
# Around line 450-460
docx_result = json_to_docx(
    motivation_letter_json, 
    output_path=str(docx_file_path)
)
if not docx_result:
    logger.error(f"Failed to generate DOCX at {docx_file_path}")
    return None
```

**New Code:**
```python
# Generate Bewerbungsschreiben DOCX (existing)
docx_result = json_to_docx(
    motivation_letter_json, 
    output_path=str(docx_file_path)
)
if not docx_result:
    logger.error(f"Failed to generate DOCX at {docx_file_path}")
    return None

# Generate CV Template DOCX (NEW)
from cv_template_generator import generate_cv_docx

cv_docx_path = app_folder / 'Lebenslauf.docx'
cv_template_path = 'process_cv/cv-data/template/Lebenslauf_template.docx'

# Get CV summary path
cv_summary_path = get_cv_summary_path()  # Helper function
if cv_summary_path and cv_summary_path.exists():
    with open(cv_summary_path, 'r', encoding='utf-8') as f:
        cv_summary = f.read()
    
    cv_result = generate_cv_docx(
        cv_summary=cv_summary,
        job_details=job_details,
        template_path=cv_template_path,
        output_path=str(cv_docx_path)
    )
    
    if not cv_result:
        logger.warning(f"Failed to generate CV template at {cv_docx_path}")
        # Continue execution - non-blocking
else:
    logger.warning("CV summary not found, skipping CV template generation")
```

### 3.4 Application Folder Structure

**Before (Current):**
```
applications/001_Company_Name_Job_Title/
├── bewerbungsschreiben.docx    # Generated letter
├── bewerbungsschreiben.html    # HTML version
├── lebenslauf.pdf              # Original CV copy
├── application-data.json       # Letter content
├── job-details.json            # Job information
├── metadata.json               # Application metadata
├── status.json                 # Status tracking
└── email-text.txt              # Email draft
```

**After (With CV Template):**
```
applications/001_Company_Name_Job_Title/
├── bewerbungsschreiben.docx    # Generated letter
├── bewerbungsschreiben.html    # HTML version
├── Lebenslauf.docx             # ✨ NEW: CV template
├── lebenslauf.pdf              # Original CV copy
├── application-data.json       # Letter content
├── job-details.json            # Job information
├── metadata.json               # Application metadata
├── status.json                 # Status tracking
└── email-text.txt              # Email draft
```

---

## 4. AI Content Generation

### 4.1 OpenAI API Integration

**Model:** Same as motivation letter generation (GPT-4 or configured model)

**System Prompt:**
```
You are an expert CV writer specialized in German job applications.
Generate job-specific CV template content that highlights relevant 
skills and experience for the target position.
```

**User Prompt Template:**
```python
prompt = f"""
Generate CV template content in {language} for this job application:

JOB DETAILS:
Company: {company_name}
Position: {job_title}
Description: {job_description}

CANDIDATE CV SUMMARY:
{cv_summary}

OUTPUT REQUIREMENTS:
Generate JSON with exactly these fields:

1. cv_motivation (45-55 words):
   - Explain why applying for THIS specific job
   - Be authentic and enthusiastic
   - Connect candidate's background to role

2. cv_kurzprofil (45-55 words):
   - Professional introduction focused on THIS job
   - Highlight most relevant experience
   - Show value proposition for employer

3. fachkompetenzen (exactly 9 items):
   - List most relevant professional competencies
   - Prioritize skills matching job requirements
   - Be specific and concrete
   - Format as bullet points

OUTPUT FORMAT:
{{
  "cv_motivation": "...",
  "cv_kurzprofil": "...",
  "fachkompetenzen": [
    "Competency 1",
    "Competency 2",
    ...
    "Competency 9"
  ]
}}
"""
```

### 4.2 Content Validation

**Validation Rules:**
1. **Word Count:** 
   - cv_motivation: 45-55 words
   - cv_kurzprofil: 45-55 words
   
2. **Bullet Points:**
   - fachkompetenzen: exactly 9 items
   
3. **Language:**
   - Match job description language (de/en)
   - Use proper German characters (ü, ö, ä)
   - Apply ß → ss replacement per convention
   
4. **Content Quality:**
   - No placeholders like [Company Name]
   - No generic phrases
   - Specific to job and candidate

**Validation Function:**
```python
def validate_cv_content(content: dict) -> tuple[bool, str]:
    """Validate generated CV content."""
    errors = []
    
    # Check required fields
    required = ['cv_motivation', 'cv_kurzprofil', 'fachkompetenzen']
    for field in required:
        if field not in content:
            errors.append(f"Missing field: {field}")
    
    # Word count validation
    if 'cv_motivation' in content:
        words = len(content['cv_motivation'].split())
        if not (45 <= words <= 55):
            errors.append(f"cv_motivation: {words} words (expected 45-55)")
    
    if 'cv_kurzprofil' in content:
        words = len(content['cv_kurzprofil'].split())
        if not (45 <= words <= 55):
            errors.append(f"cv_kurzprofil: {words} words (expected 45-55)")
    
    # Bullet point count
    if 'fachkompetenzen' in content:
        count = len(content['fachkompetenzen'])
        if count != 9:
            errors.append(f"fachkompetenzen: {count} items (expected 9)")
    
    if errors:
        return False, "; ".join(errors)
    return True, ""
```

---

## 5. Error Handling & Resilience

### 5.1 Non-Blocking Design

**Principle:** CV template generation MUST NOT prevent motivation letter generation.

**Implementation:**
```python
try:
    cv_result = generate_cv_docx(...)
    if not cv_result:
        logger.warning("CV template generation failed")
        # Continue with workflow
except Exception as e:
    logger.error(f"CV template generation error: {e}")
    # Continue with workflow
```

### 5.2 Failure Scenarios

| Scenario | Handling | User Impact |
|----------|----------|-------------|
| Template file missing | Log warning, skip CV generation | No CV template, workflow continues |
| CV summary not found | Log warning, skip CV generation | No CV template, workflow continues |
| OpenAI API error | Log error with details, skip CV generation | No CV template, workflow continues |
| Invalid content (validation fails) | Log warning, regenerate once | Retry once, then skip if still fails |
| Template rendering error | Log error, skip CV generation | No CV template, workflow continues |
| File write error | Log error, skip CV generation | No CV template, workflow continues |

### 5.3 Retry Logic

**Strategy:** Single retry on content validation failure

```python
MAX_RETRIES = 1
for attempt in range(MAX_RETRIES + 1):
    content = generate_cv_content(cv_summary, job_details)
    is_valid, error = validate_cv_content(content)
    
    if is_valid:
        break
    
    if attempt < MAX_RETRIES:
        logger.warning(f"Validation failed: {error}, retrying...")
    else:
        logger.error(f"Failed after {MAX_RETRIES + 1} attempts: {error}")
        return False
```

### 5.4 Logging Strategy

**Log Levels:**
- `INFO`: Successful CV generation
- `WARNING`: Skipped generation (missing files, validation failures)
- `ERROR`: Unexpected errors during generation

**Log Format:**
```python
logger.info(f"CV template generated successfully: {output_path}")
logger.warning(f"CV summary not found at {cv_summary_path}, skipping CV generation")
logger.error(f"Failed to generate CV template: {error_message}")
```

---

## 6. Testing Strategy

### 6.1 Unit Tests

**Test File:** `tests/test_cv_template_generator.py`

**Test Cases:**
```python
def test_generate_cv_content_success():
    """Test successful content generation with valid inputs."""
    
def test_generate_cv_content_word_count():
    """Verify word counts are within 45-55 range."""
    
def test_generate_cv_content_bullet_points():
    """Verify exactly 9 competencies are generated."""
    
def test_generate_cv_content_language_german():
    """Test German content generation."""
    
def test_generate_cv_content_language_english():
    """Test English content generation."""
    
def test_validate_cv_content_valid():
    """Test validation passes for valid content."""
    
def test_validate_cv_content_invalid_word_count():
    """Test validation fails for invalid word counts."""
    
def test_validate_cv_content_invalid_bullet_count():
    """Test validation fails for wrong number of competencies."""
    
def test_generate_cv_docx_success():
    """Test complete DOCX generation workflow."""
    
def test_generate_cv_docx_missing_template():
    """Test handling of missing template file."""
    
def test_generate_cv_docx_invalid_content():
    """Test handling of content validation failures."""
```

### 6.2 Integration Tests

**Test Scenarios:**
1. **Full Workflow:** Generate letter → verify CV template created
2. **Missing CV Summary:** Verify workflow continues without CV template
3. **Template Rendering:** Verify placeholders correctly replaced
4. **File Structure:** Verify CV template in correct location
5. **Non-Blocking:** Verify letter generation succeeds even if CV fails

### 6.3 Manual Testing Checklist

```
[ ] CV template file generated in application folder
[ ] Placeholders correctly replaced with content
[ ] Word counts within 45-55 range
[ ] Exactly 9 competencies listed
[ ] Content language matches job description
[ ] German special characters handled correctly
[ ] Template formatting preserved
[ ] Workflow continues if CV generation fails
[ ] Appropriate log messages generated
[ ] No regression in motivation letter generation
```

---

## 7. Configuration

### 7.1 File Paths

**Configuration Pattern:** Follow existing conventions

```python
# In cv_template_generator.py
DEFAULT_TEMPLATE_PATH = 'process_cv/cv-data/template/Lebenslauf_template.docx'
DEFAULT_CV_SUMMARY_DIR = 'process_cv/cv-data/processed'

def get_cv_summary_path() -> Optional[Path]:
    """Get path to most recent CV summary file."""
    summary_dir = Path(DEFAULT_CV_SUMMARY_DIR)
    if not summary_dir.exists():
        return None
    
    summary_files = list(summary_dir.glob('*_summary.txt'))
    if not summary_files:
        return None
    
    # Return most recent
    return max(summary_files, key=lambda p: p.stat().st_mtime)
```

### 7.2 OpenAI Configuration

**Reuse Existing Configuration:**
- Use same API key from `config.py`
- Use same model configuration
- Use same timeout settings
- Use same error handling patterns

```python
# Import from existing motivation letter generator
from motivation_letter_generator import get_openai_client, get_model_config

def generate_cv_content(cv_summary: str, job_details: dict) -> dict:
    client = get_openai_client()
    model_config = get_model_config()
    
    # Use same temperature, max_tokens as letter generation
    # ...
```

### 7.3 Template Requirements

**Template Structure:**
- Professional CV design
- Clear section headers
- Placeholder locations marked
- List formatting for competencies
- Compatible with DocxTpl library

**Delivery:**
- Template file must be created manually
- Placed in: `process_cv/cv-data/template/Lebenslauf_template.docx`
- Tested with DocxTpl before implementation

---

## 8. Performance Considerations

### 8.1 Performance Impact

**Added Latency:**
- OpenAI API call: ~2-5 seconds
- Template rendering: <1 second
- File I/O: <1 second
- **Total added time:** ~3-7 seconds

**Mitigation:**
- Non-blocking execution (doesn't delay letter generation)
- Parallel processing possible in future iteration
- Caching potential (not in MVP)

### 8.2 API Usage

**Cost Impact:**
- Additional OpenAI API call per application
- Estimated tokens: ~1500 (input) + ~500 (output) = ~2000 tokens
- Cost: ~$0.04 per generation (GPT-4 pricing)

**Optimization Opportunities:**
- Batch processing (future)
- Template caching (future)
- Model selection (GPT-3.5 sufficient?)

---

## 9. Security Considerations

### 9.1 Data Privacy

**Sensitive Data:**
- CV content (personal information)
- Job details (company information)

**Protection Measures:**
- No data sent to external services except OpenAI
- Generated files stored locally only
- Follow existing security patterns

### 9.2 Input Validation

**Validation Points:**
1. CV summary file path (prevent directory traversal)
2. Template path (ensure within allowed directory)
3. Output path (ensure within application folder)
4. Generated content (sanitize before rendering)

**Implementation:**
```python
def safe_path_join(base: Path, *parts) -> Path:
    """Safely join paths preventing traversal attacks."""
    result = base.joinpath(*parts).resolve()
    if not result.is_relative_to(base):
        raise ValueError(f"Path traversal detected: {result}")
    return result
```

---

## 10. Migration & Rollout

### 10.1 Deployment Strategy

**Phase 1: Implementation**
- Create `cv_template_generator.py`
- Add integration to `letter_generation_utils.py`
- Add unit tests

**Phase 2: Testing**
- Manual testing with sample jobs
- Verify non-blocking behavior
- Test error scenarios

**Phase 3: Deployment**
- Deploy to production
- Monitor logs for errors
- Gather user feedback

### 10.2 Rollback Plan

**If Issues Occur:**
1. Remove CV generation call from `letter_generation_utils.py`
2. Workflow reverts to previous behavior
3. No data loss or corruption
4. Users can still generate letters

**Rollback Trigger:**
- High error rate (>10%)
- Performance degradation
- User complaints

---

## 11. Future Enhancements

### 11.1 Potential Improvements

**Short-term:**
- Add UI toggle to enable/disable CV generation
- Allow manual CV content editing before generation
- Add preview mode for CV template

**Medium-term:**
- Support multiple CV templates (different designs)
- Cache CV content for similar jobs
- Add CV version history

**Long-term:**
- AI-powered template selection
- Multi-language CV support
- Integration with LinkedIn profile
- Automated A/B testing of CV variants

### 11.2 Technical Debt Considerations

**Areas to Monitor:**
- Code duplication with `word_template_generator.py`
- Template management (single template vs. multiple)
- Configuration management (hardcoded paths)

**Refactoring Opportunities:**
- Extract common template rendering logic
- Create unified configuration system
- Implement template registry pattern

---

## 12. Success Metrics

### 12.1 Key Performance Indicators

**Technical Metrics:**
- CV generation success rate: >95%
- Average generation time: <7 seconds
- Error rate: <5%
- Non-blocking success rate: 100%

**User Metrics:**
- CV templates generated: Track count
- User feedback: Collect qualitative data
- Time saved: Compare manual vs. automated

### 12.2 Monitoring

**Log Monitoring:**
```python
# Track these metrics
cv_generation_success_count
cv_generation_failure_count
cv_generation_skip_count
cv_generation_duration_seconds
```

**Alerting:**
- Alert if error rate >10%
- Alert if generation time >15 seconds
- Alert if template file missing

---

## 13. Implementation Checklist

### 13.1 Development Tasks

```
[ ] Create cv_template_generator.py module
    [ ] generate_cv_docx() function
    [ ] generate_cv_content() function
    [ ] validate_cv_content() function
    [ ] Error handling and logging
    
[ ] Integrate into letter_generation_utils.py
    [ ] Add import statement
    [ ] Add CV generation call after DOCX generation
    [ ] Add CV summary path helper
    [ ] Add error handling (non-blocking)
    
[ ] Create CV template file
    [ ] Design template layout
    [ ] Add placeholders
    [ ] Test with DocxTpl
    [ ] Save to process_cv/cv-data/template/
    
[ ] Add configuration
    [ ] Path constants
    [ ] OpenAI settings reuse
    [ ] Validation rules
    
[ ] Write tests
    [ ] Unit tests for cv_template_generator
    [ ] Integration tests
    [ ] Manual test scenarios
    
[ ] Documentation
    [ ] Code comments
    [ ] Update README if needed
    [ ] API documentation
```

### 13.2 Quality Assurance

```
[ ] Code review
[ ] Unit test coverage >80%
[ ] Integration tests pass
[ ] Manual testing completed
[ ] Performance benchmarking
[ ] Security review
[ ] Error handling verification
```

### 13.3 Deployment

```
[ ] Merge to main branch
[ ] Deploy to production
[ ] Monitor logs for 24 hours
[ ] Verify metrics
[ ] Collect user feedback
```

---

## 14. Dependencies

### 14.1 External Libraries

**Required:**
- `docxtpl`: Template rendering (already installed)
- `openai`: API client (already installed)
- `python-docx`: DOCX manipulation (indirect, via docxtpl)

**No new dependencies required.**

### 14.2 Internal Dependencies

**Modules:**
- `motivation_letter_generator.py`: OpenAI client configuration
- `letter_generation_utils.py`: Integration point
- `utils/file_utils.py`: File operations
- `config.py`: Configuration settings

**Data Files:**
- CV summary files: `process_cv/cv-data/processed/*_summary.txt`
- CV template: `process_cv/cv-data/template/Lebenslauf_template.docx`

---

## 15. Appendix

### 15.1 Code Examples

**Complete cv_template_generator.py Structure:**

```python
"""
CV Template Generator Module

Generates customized CV templates using AI-powered content generation
and DocxTpl template rendering.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from docxtpl import DocxTemplate
from motivation_letter_generator import get_openai_client, get_model_config

logger = logging.getLogger(__name__)

# Constants
DEFAULT_TEMPLATE_PATH = 'process_cv/cv-data/template/Lebenslauf_template.docx'
DEFAULT_CV_SUMMARY_DIR = 'process_cv/cv-data/processed'
WORD_COUNT_MIN = 45
WORD_COUNT_MAX = 55
COMPETENCIES_COUNT = 9

def generate_cv_docx(
    cv_summary: str,
    job_details: Dict,
    template_path: str,
    output_path: str
) -> bool:
    """
    Generate CV DOCX from template with AI-generated content.
    
    Args:
        cv_summary: Processed CV summary text
        job_details: Job information dict
        template_path: Path to template file
        output_path: Destination path
    
    Returns:
        bool: Success status
    """
    try:
        # 1. Generate content
        content = generate_cv_content(cv_summary, job_details)
        if not content:
            return False
        
        # 2. Validate content
        is_valid, error = validate_cv_content(content)
        if not is_valid:
            logger.error(f"Content validation failed: {error}")
            return False
        
        # 3. Render template
        return render_cv_template(content, template_path, output_path)
        
    except Exception as e:
        logger.error(f"CV generation failed: {e}")
        return False

def generate_cv_content(cv_summary: str, job_details: Dict) -> Optional[Dict]:
    """Generate CV content using OpenAI API."""
    # Implementation here
    pass

def validate_cv_content(content: Dict) -> Tuple[bool, str]:
    """Validate generated CV content."""
    # Implementation here
    pass

def render_cv_template(
    content: Dict,
    template_path: str,
    output_path: str
) -> bool:
    """Render CV template with content."""
    # Implementation here
    pass

def get_cv_summary_path() -> Optional[Path]:
    """Get path to most recent CV summary file."""
    # Implementation here
    pass
```

### 15.2 References

**Related Documentation:**
- Bewerbungsschreiben workflow: `word_template_generator.py`
- Letter generation: `letter_generation_utils.py`
- CV processing: `process_cv/cv_processor.py`

**External Resources:**
- DocxTpl documentation: https://docxtpl.readthedocs.io/
- OpenAI API: https://platform.openai.com/docs/

---

## Document Control

**Version History:**
- v1.0 (2025-11-02): Initial architecture document

**Reviewers:**
- [ ] Product Owner (validation against requirements)
- [ ] Development Team (technical feasibility)
- [ ] QA Team (testability assessment)

**Approval:**
- [ ] Approved for implementation

---

**End of Architecture Document**

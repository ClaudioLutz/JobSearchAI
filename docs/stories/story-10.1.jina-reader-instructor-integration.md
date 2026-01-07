# Story 10.1: Jina Reader + Instructor Integration

## Story Info
**Epic:** [Epic 10: Automatic Job Extraction Enhancement](epic-10-automatic-job-extraction.md)
**Status:** Completed
**Effort:** 5 Story Points
**Created:** 2026-01-07
**Completed:** 2026-01-07

## Goal
Implement a fully automatic job extraction pipeline that reliably fetches content from any job URL (including JavaScript-rendered pages, PDFs, and dynamic content) and extracts structured job details using LLM with Pydantic validation.

## Context
The existing job extraction methods (ScrapeGraphAI, simple HTTP requests) frequently fail on modern job sites that:
- Load content dynamically via JavaScript
- Display job details in embedded PDFs
- Use anti-bot measures
- Require cookie consent interactions

Users had to manually copy-paste job posting text as a workaround, which was time-consuming and error-prone.

**Research Findings:**
- Jina Reader API (`r.jina.ai/URL`) handles all these cases for free
- Instructor library provides structured LLM output with Pydantic validation
- Combining both achieves near 100% extraction success rate

## User Story
As a job seeker,
I want the system to automatically extract complete job details from any job URL,
So that I can generate personalized applications without manual data entry.

## Acceptance Criteria

1. **Content Fetching (web_content_fetcher.py)**:
   - [x] Jina Reader fetches content from URLs (handles JS, PDF, dynamic)
   - [x] Playwright fallback for sites that block Jina
   - [x] Simple requests fallback as last resort
   - [x] Returns clean text/markdown content

2. **Structured Extraction (job_text_extractor.py)**:
   - [x] Pydantic `JobPosting` model with all fields
   - [x] Required fields validated: job_title, company_name, job_description
   - [x] Optional fields: skills, responsibilities, location, salary, dates
   - [x] Contact person and email extracted when available
   - [x] Automatic salutation generation (Herr/Frau based on contact)

3. **API Endpoints**:
   - [x] `POST /job_data/extract-from-url` - automatic URL extraction
   - [x] `POST /job_data/extract-from-text` - pasted text extraction
   - [x] Both return standardized job details JSON
   - [x] Proper error handling with meaningful messages

4. **Integration**:
   - [x] `get_job_details_automatic()` function in job_details_utils.py
   - [x] Compatible with existing letter generation pipeline
   - [x] Works with full pipeline: URL → Extraction → Bewerbungsschreiben → Email

5. **Quality**:
   - [x] 100% success rate on tested ostjob.ch URLs
   - [x] 8-10 fields extracted per job
   - [x] Extraction completes in <30 seconds
   - [x] Contact person found when listed in posting

## Technical Implementation

### Files Created

#### `utils/web_content_fetcher.py`
Multi-strategy content fetching with automatic fallback:

```python
def fetch_page_content(url, prefer_jina=True) -> Tuple[Optional[str], str]:
    """
    Strategy order:
    1. Jina Reader (handles JS/PDF/dynamic)
    2. Playwright (for sites that block Jina)
    3. Simple requests (last resort)
    """
```

Key functions:
- `fetch_with_jina_reader(url)` - Free API at r.jina.ai
- `fetch_with_playwright(url)` - Browser-based fallback
- `fetch_with_requests(url)` - Simple HTTP fallback
- `get_job_page_content(url)` - Main entry point

#### `utils/job_text_extractor.py`
Instructor-based extraction with Pydantic validation:

```python
class JobPosting(BaseModel):
    job_title: str = Field(..., min_length=2)
    company_name: str = Field(..., min_length=2)
    job_description: str = Field(..., min_length=20)
    required_skills: str = Field(default="")
    responsibilities: str = Field(default="")
    company_info: Optional[str] = None
    location: Optional[str] = None
    salary_range: Optional[str] = None
    posting_date: Optional[str] = None
    contact_person: Optional[str] = None
    contact_email: Optional[str] = None
    salutation: str = Field(default="Sehr geehrte Damen und Herren")
    application_url: Optional[str] = None

    @model_validator(mode='after')
    def generate_salutation_from_contact(self):
        # Auto-generates "Sehr geehrte Frau X" or "Sehr geehrter Herr X"
```

Key functions:
- `extract_job_from_text(raw_text, source_url)` - Returns JobPosting model
- `job_posting_to_dict(job)` - Converts to standard dict format
- `get_job_details_from_text(pasted_text, source_url)` - Main entry point

### Files Modified

#### `job_details_utils.py`
Added automatic extraction function:

```python
def get_job_details_automatic(job_url):
    """
    Fully automatic: fetch content + extract details.
    1. Jina Reader for content fetching
    2. Instructor-based LLM extraction with Pydantic validation
    """
```

#### `blueprints/job_data_routes.py`
Added two new endpoints:

```python
@job_data_bp.route('/extract-from-url', methods=['POST'])
def extract_job_from_url():
    # Accepts: {"url": "https://..."}
    # Returns: extracted job details JSON

@job_data_bp.route('/extract-from-text', methods=['POST'])
def extract_job_from_text():
    # Accepts: {"text": "...", "url": "..."}
    # Returns: extracted job details JSON
```

## Testing Results

### Automatic Extraction Test (3 URLs)
```
URL 1: IT-System-Engineer/in (m/w/d)
  - Company: ZbW - Zentrum für berufliche Weiterbildung
  - Location: 9015 St. Gallen, Home Office möglich
  - Contact: D. Weiss (dweiss@zbw.ch)
  - Fields: 10/13 ✓

URL 2: IT Verantwortliche:r
  - Company: Consult & Pepper AG
  - Location: 8603 Schwerzenbach
  - Fields: 8/13 ✓

URL 3: Business Analyst IT (w/m/d)
  - Company: Raiffeisen Schweiz
  - Location: 8058 Zürich, Home Office möglich
  - Fields: 8/13 ✓

Success Rate: 100% (3/3)
```

### Full Pipeline Test
```
Job URL → Content (68,555 chars via Jina Reader)
       → Job Details (10 fields extracted)
       → CV Summary (4,567 chars loaded)
       → Bewerbungsschreiben (generated)
       → Email Text (generated)
       → READY TO SEND ✓
```

## Dependencies

**New Dependencies:**
- `instructor` - Structured LLM extraction with Pydantic
  ```bash
  pip install instructor
  ```

**Existing Dependencies Used:**
- `pydantic` - Data validation
- `openai` - LLM API
- `requests` - HTTP client
- `playwright` - Browser automation (optional fallback)
- `beautifulsoup4` - HTML parsing

## Configuration

Uses existing configuration from `config.py`:
- `OPENAI_API_KEY` - For LLM extraction
- `openai.model` - Default: gpt-4.1

No additional configuration required. Jina Reader API is free and keyless.

## API Documentation

### POST /job_data/extract-from-url

Automatically fetch and extract job details from a URL.

**Request:**
```json
{
  "url": "https://www.ostjob.ch/job/example/123456"
}
```

**Response (200):**
```json
{
  "Job Title": "Software Engineer (m/w/d)",
  "Company Name": "Example GmbH",
  "Job Description": "...",
  "Required Skills": "Python, JavaScript, ...",
  "Responsibilities": "...",
  "Company Information": "...",
  "Location": "Zürich, Switzerland",
  "Salary Range": "",
  "Posting Date": "2026-01-07",
  "Contact Person": "Frau Müller",
  "Application Email": "jobs@example.com",
  "Salutation": "Sehr geehrte Frau Müller",
  "Application URL": "https://www.ostjob.ch/job/example/123456"
}
```

**Error Response (400/500):**
```json
{
  "error": "Failed to extract job details",
  "detail": "Could not fetch or extract structured data from the provided URL"
}
```

### POST /job_data/extract-from-text

Extract job details from pasted text (fallback when URL extraction fails).

**Request:**
```json
{
  "text": "Software Engineer (m/w/d)\n\nFirma: Example GmbH\n...",
  "url": "https://original-source.com/job/123"
}
```

**Response:** Same format as extract-from-url.

## Definition of Done

- [x] web_content_fetcher.py implemented with multi-strategy fallback
- [x] job_text_extractor.py implemented with Pydantic validation
- [x] API endpoints added and functional
- [x] Integration with job_details_utils.py
- [x] 100% success rate on test URLs
- [x] Contact person and email extraction working
- [x] Salutation auto-generation working
- [x] Full pipeline tested end-to-end
- [x] Code committed and pushed to git
- [x] Story documentation created

## Future Enhancements

- Frontend UI for manual URL entry
- Bulk URL processing
- Caching of extracted job details
- Integration with job matching pipeline
- Support for additional job sites (LinkedIn, Indeed, etc.)

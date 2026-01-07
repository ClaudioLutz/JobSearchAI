# Epic 10: Automatic Job Extraction Enhancement

**Status:** Completed
**Epic Owner:** Development Team
**Target Version:** 2.1
**Business Value:** High
**Technical Risk:** Low

---

## Epic Overview

Enhance the job detail extraction pipeline to reliably handle any job posting URL, including JavaScript-rendered pages, embedded PDFs, and dynamically generated content. The previous approach using simple HTTP requests or ScrapeGraphAI often failed on modern job sites that load content dynamically.

This epic implements a robust multi-strategy content fetching system using Jina Reader API combined with Instructor/Pydantic for structured LLM extraction with validation.

---

## Business Goals

1. **Reliability:** Achieve near 100% success rate on job URL extraction (vs ~60% previously)
2. **Automation:** Eliminate manual copy-paste of job posting text
3. **Data Quality:** Extract all available fields including contact person and email
4. **Speed:** Complete extraction in under 30 seconds per job
5. **Cost Efficiency:** Use free Jina Reader API for content fetching

---

## Technical Goals

1. Implement multi-strategy content fetching (Jina Reader → Playwright → requests)
2. Use Instructor library with Pydantic models for structured, validated extraction
3. Add automatic salutation generation based on contact person
4. Create API endpoints for both URL-based and text-based extraction
5. Integrate with existing job details pipeline

---

## Scope

### In Scope

- New `web_content_fetcher.py` module for reliable content fetching
- New `job_text_extractor.py` module using Instructor + Pydantic
- API endpoint for automatic URL extraction (`/job_data/extract-from-url`)
- API endpoint for pasted text extraction (`/job_data/extract-from-text`)
- Integration with `job_details_utils.py`
- Unit tests for extraction modules

### Out of Scope

- Changes to existing ScrapeGraphAI workflow (kept as alternative)
- Frontend UI changes (API only in this epic)
- Bulk URL processing (future enhancement)
- Rate limiting/queueing for Jina Reader (not needed at current volume)

---

## Stories

1. **Story 10.1:** Jina Reader + Instructor Integration *(Completed)*
   - Implement web content fetcher with Jina Reader
   - Implement Instructor-based extraction with Pydantic validation
   - Add API endpoints for extraction
   - Integration with job_details_utils.py

2. **Story 10.2:** Frontend Integration *(Future)*
   - Add "Extract from URL" button to UI
   - Add manual text paste modal
   - Progress indicator during extraction

3. **Story 10.3:** Bulk Processing *(Future)*
   - Process multiple URLs in parallel
   - Queue management for large batches
   - Progress tracking and error handling

---

## Success Criteria

- [x] 100% success rate on ostjob.ch job URLs
- [x] Contact person and email extracted when available
- [x] Correct salutation generated (Herr/Frau based on contact)
- [x] Extraction completes in <30 seconds
- [x] Pydantic validation ensures data quality
- [x] API endpoints functional and documented
- [x] Full pipeline test from URL to Bewerbungsschreiben

---

## Technical Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Job Extraction Pipeline                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [Job URL] ──► [web_content_fetcher.py]                         │
│                     │                                            │
│                     ├─► Jina Reader (r.jina.ai) ──► Markdown    │
│                     │   (handles JS, PDF, dynamic)               │
│                     │                                            │
│                     ├─► Playwright (fallback)                    │
│                     │                                            │
│                     └─► requests (last resort)                   │
│                                                                  │
│               ▼                                                  │
│  [Markdown/Text Content]                                         │
│               │                                                  │
│               ▼                                                  │
│  [job_text_extractor.py]                                        │
│               │                                                  │
│               ├─► Instructor + OpenAI (gpt-4.1)                 │
│               │                                                  │
│               └─► Pydantic JobPosting Model                     │
│                     • job_title (required)                       │
│                     • company_name (required)                    │
│                     • job_description (required)                 │
│                     • required_skills                            │
│                     • responsibilities                           │
│                     • company_info                               │
│                     • location                                   │
│                     • salary_range                               │
│                     • posting_date                               │
│                     • contact_person                             │
│                     • contact_email                              │
│                     • salutation (auto-generated)                │
│                     • application_url                            │
│                                                                  │
│               ▼                                                  │
│  [Validated Job Details Dict]                                    │
│               │                                                  │
│               ▼                                                  │
│  [letter_generation_utils.py] ──► Bewerbungsschreiben           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Jina Reader rate limits | Medium | Low | Fallback to Playwright, free tier allows 20 req/min |
| LLM extraction errors | Medium | Low | Pydantic validation, max_retries=2 in Instructor |
| Content not extractable | Low | Low | Multi-strategy fallback chain |
| API costs | Low | Low | Using existing OpenAI budget, gpt-4.1 is cost-effective |

---

## Dependencies

- `instructor` library (pip install instructor)
- `pydantic` library (already installed)
- `requests` library (already installed)
- `playwright` library (already installed, optional)
- OpenAI API key (already configured)
- Jina Reader API (free, no key required)

---

## Files Created/Modified

**New Files:**
- `utils/web_content_fetcher.py` - Multi-strategy content fetching
- `utils/job_text_extractor.py` - Instructor-based extraction

**Modified Files:**
- `job_details_utils.py` - Added `get_job_details_automatic()`
- `blueprints/job_data_routes.py` - Added extraction endpoints

---

## Notes

- Jina Reader is free and handles most modern job sites
- Instructor provides structured output with automatic retries
- Pydantic validation ensures data quality before processing
- Salutation auto-generation improves letter personalization
- Full pipeline tested end-to-end with real job URLs

---
title: 'Job Detail Extraction from Pasted Text'
slug: 'job-text-extraction'
created: '2026-01-07'
status: 'completed'
stepsCompleted: [1, 2, 3]
tech_stack: ['Python', 'Flask', 'Pydantic', 'Instructor', 'OpenAI gpt-4.1']
files_to_modify: ['utils/job_text_extractor.py (new)', 'blueprints/job_data_routes.py', 'job_details_utils.py']
code_patterns: ['Singleton OpenAI client', 'Blueprint routes with @login_required', 'Pydantic models for validation']
test_patterns: []
---

# Tech-Spec: Job Detail Extraction from Pasted Text

**Created:** 2026-01-07

## Overview

### Problem Statement

When web scraping fails due to dynamic content or bot detection, users have no way to manually provide job posting text for extraction. The current `get_job_details()` function in `job_details_utils.py` relies on ScrapeGraphAI and pre-scraped data, both of which can fail for certain job postings.

### Solution

Add an Instructor + Pydantic-based extraction utility that processes pasted job posting text using `gpt-4.1` model. This provides a reliable fallback when automated scraping fails, allowing users to copy/paste job posting content directly.

### Scope

**In Scope:**
- Pydantic model for JobPosting with field validation
- Instructor-based extraction utility using existing OpenAI client pattern
- Flask API endpoint (`/api/jobs/extract-from-text`) for pasted text input
- Integration helper in `job_details_utils.py`

**Out of Scope:**
- Changes to existing ScrapeGraphAI workflow
- Automatic fallback integration (this is a standalone endpoint)
- CLI utility
- Frontend UI changes (API only)

## Context for Development

### Codebase Patterns

1. **OpenAI Client Pattern:** Use `openai_client` singleton from `utils/api_utils.py` - provides centralized config, error handling, and GPT-5.1 compatibility
2. **Blueprint Routes:** Routes use `@login_required` decorator and follow REST conventions
3. **Logging:** Use module-level loggers with `logging.getLogger(__name__)`
4. **Config Access:** Use `config` singleton from `config.py` for API keys and defaults
5. **German Prompts:** Existing extraction prompts are in German to match job posting language

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `utils/api_utils.py` | OpenAI client wrapper, use `openai_client.generate_chat_completion()` |
| `job_details_utils.py` | Existing job extraction logic, dict format to match |
| `blueprints/job_data_routes.py` | Blueprint pattern for job-related routes |
| `graph_scraper_utils.py` | German extraction prompt to reference |
| `config.py` | Configuration access pattern |

### Technical Decisions

1. **Model:** Use `gpt-4.1` (default from config) for consistency with existing code
2. **Library:** Instructor for structured extraction with Pydantic validation
3. **Location:** New file `utils/job_text_extractor.py` for clean separation
4. **Output Format:** Return dict matching existing `job_details_utils.py` format for compatibility
5. **Validation:** Pydantic model with `min_length` constraints for required fields

## Implementation Plan

### Tasks

#### Task 1: Install Instructor Library
- Add `instructor` to project dependencies
- Verify installation with import test

#### Task 2: Create Pydantic JobPosting Model
- Create `utils/job_text_extractor.py`
- Define `JobPosting` Pydantic model with all fields from existing extraction
- Add field validators for required content (job_title, company_name, job_description)
- Include German salutation logic

#### Task 3: Create Instructor Extraction Function
- Implement `extract_job_from_text(raw_text, source_url)` function
- Use Instructor with existing OpenAI client pattern
- German system prompt matching existing style
- Return validated JobPosting model

#### Task 4: Add Conversion Helper
- Implement `job_posting_to_dict(job: JobPosting)` function
- Convert Pydantic model to dict format matching `job_details_utils.py` output
- Ensure field name compatibility

#### Task 5: Add Flask API Endpoint
- Add route to `blueprints/job_data_routes.py`
- Endpoint: `POST /job_data/extract-from-text`
- Accept JSON body: `{"text": "...", "url": "..."}`
- Return extracted job details as JSON

#### Task 6: Add Integration Helper
- Add `get_job_details_from_pasted_text()` in `job_details_utils.py`
- Wrapper that calls extractor and converts to standard dict format
- Maintains compatibility with existing code

### Acceptance Criteria

**AC1: Pydantic Model Validation**
- Given a JobPosting model instance
- When job_title is empty or missing
- Then validation error is raised

**AC2: Text Extraction Success**
- Given raw job posting text with title, company, description
- When `extract_job_from_text()` is called
- Then returns JobPosting with all fields populated

**AC3: API Endpoint Response**
- Given POST to `/job_data/extract-from-text` with valid text
- When request is authenticated
- Then returns 200 with extracted job details JSON

**AC4: API Endpoint Validation**
- Given POST with text shorter than 100 characters
- When request is processed
- Then returns 400 with error message

**AC5: Dict Compatibility**
- Given extracted JobPosting model
- When converted to dict
- Then field names match existing `job_details_utils.py` output format

## Additional Context

### Dependencies

- `instructor` - Structured LLM extraction with Pydantic
- `pydantic` - Already installed (used elsewhere in project)
- `openai` - Already installed

### Testing Strategy

Manual testing via API endpoint:
1. Copy job posting text from real job site
2. POST to endpoint with text
3. Verify extracted fields match source

### Notes

- Research document: `_bmad-output/planning-artifacts/research/technical-job-detail-extraction-research-2026-01-06.md`
- Instructor docs: https://python.useinstructor.com/
- Keep prompts in German to match existing extraction style

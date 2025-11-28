# Epic 7: LinkedIn Outreach Integration

## Epic Status
**Status:** Implemented
**Created:** 2025-11-28
**Owner:** Product Manager
**Architecture Reference:** [brainstorming_linkedin_integration.md](../brainstorming_linkedin_integration.md)

---

## Epic Goal

Empower the user to effectively network by generating personalized, high-impact LinkedIn connection requests and messages for hiring managers and peers, directly leveraging existing job data and CV profiles.

---

## Epic Description

### Existing System Context

**Current State:**
- The system excels at generating formal application documents (CVs, Cover Letters).
- It captures rich data about jobs (Company, Title, Skills) and the candidate (CV Summary).
- However, it lacks support for the "hidden job market" and networking aspect of job hunting.
- Users currently have to manually craft LinkedIn messages, often struggling to fit them within the 300-character connection limit while remaining personalized.

**Technology Stack:**
- Python 3.x with Flask
- OpenAI API (GPT-4) for content generation
- Existing `job_details_utils.py` and `letter_generation_utils.py` patterns
- Frontend: Jinja2 templates + Bootstrap

### Enhancement Details

**What's Being Added:**

1.  **LinkedIn Generator Module** (`services/linkedin_generator.py`)
    - A specialized AI module to generate three types of messages:
        - **Connection Request**: Strict <300 char limit, high impact.
        - **Peer Networking**: Casual tone, focused on culture/insight.
        - **InMail/Direct**: Longer form, value-proposition focused.

2.  **UI Integration**
    - A new "LinkedIn" tab in the Job Details view.
    - "Copy to Clipboard" functionality for quick usage.
    - Option to regenerate messages with different tones (e.g., "Casual", "Formal").

3.  **Data Integration**
    - Utilizes `Contact Person` from job details if available (critical for personalization).
    - Falls back to generic but professional placeholders if no contact is found.

**Success Criteria:**
- Generated connection requests are ALWAYS under 300 characters.
- Messages correctly reference the specific company and job title.
- Users can generate messages in <3 seconds.
- UI provides a seamless "Copy" experience.

---

## Stories

### 7.1: LinkedIn Generator Service
**Status:** Complete  
**Effort:** 5 Story Points (1 day)  
**Documentation:** [story-7.1.linkedin-generator-service.md](story-7.1.linkedin-generator-service.md)

**Goal:** Create the backend AI service for generating personalized LinkedIn messages.

**Key Deliverables:**
- `services/linkedin_generator.py` module with `generate_linkedin_messages()` function
- OpenAI prompt engineering with strict character limit enforcement (< 300 chars for connection requests)
- Language detection and matching (generates in same language as job description)
- Contact person handling (uses provided name or falls back to placeholders)
- Post-processing validation and truncation safety net
- Manual test suite in `tests/manual_test_linkedin.py`

**Acceptance Highlights:**
- Connection request ALWAYS under 300 characters
- Messages generated in job description language (German/English)
- Never hallucinates contact person names
- Comprehensive error handling and logging

---

### 7.2: API & Route Integration
**Status:** Complete  
**Effort:** 3 Story Points (0.5 days)  
**Documentation:** [story-7.2.api-route-integration.md](story-7.2.api-route-integration.md)

**Goal:** Expose the LinkedIn message generator to the frontend via REST API.

**Key Deliverables:**
- `blueprints/linkedin_routes.py` with Flask Blueprint
- `POST /linkedin/generate` endpoint with authentication
- Request validation (job_url, cv_filename required)
- Integration with `get_job_details()` and CV summary file reading
- JSON response format with success/error handling
- Blueprint registration in `app.py`

**Acceptance Highlights:**
- Proper HTTP status codes (200, 400, 404, 500)
- Authentication required (`@login_required`, `@admin_required`)
- Comprehensive error handling for missing files and API failures
- Clear JSON response format for frontend consumption

---

### 7.3: Frontend Implementation
**Status:** Complete  
**Effort:** 5 Story Points (1 day)  
**Documentation:** [story-7.3.frontend-implementation.md](story-7.3.frontend-implementation.md)

**Goal:** Provide user-friendly UI for generating and copying LinkedIn messages.

**Key Deliverables:**
- "LinkedIn Outreach" button in job actions dropdown
- Bootstrap modal with three tabs (Connection Request, Peer Networking, InMail)
- AJAX integration with `/linkedin/generate` API endpoint
- Copy to clipboard functionality with visual feedback
- Character counter for connection requests (shows X/300, turns red if over)
- Loading states, error handling, and regenerate functionality
- Responsive design matching existing UI

**Acceptance Highlights:**
- Smooth user experience with loading states
- One-click copy to clipboard with "Copied!" feedback
- Character counter warns if connection request exceeds 300 chars
- Regenerate button allows getting new message variations
- Works seamlessly with existing job data view

---

## Compatibility Requirements

- [ ] Must work with existing Job Data structure.
- [ ] No database schema changes required (messages are generated on-demand, not necessarily stored).
- [ ] Must handle both English and German jobs (matching the job language).

---

## Risk Mitigation

**Primary Risks:**
1.  **Character Limit Violation**: LinkedIn is strict about 300 chars.
    *   *Mitigation*: Post-processing step in Python to truncate or regenerate if AI fails the constraint.
2.  **Hallucination**: AI inventing a contact person.
    *   *Mitigation*: Strict prompting to ONLY use provided contact names or fallback to "Hiring Manager".

---

## Definition of Done

- [x] `linkedin_generator.py` implemented and tested.
- [x] Frontend UI allows generation and copying of messages.
- [x] Character limits are strictly enforced via tests.
- [x] Documentation updated.

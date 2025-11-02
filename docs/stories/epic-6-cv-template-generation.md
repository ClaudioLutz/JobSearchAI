# Epic 6: CV Template Generation - Brownfield Enhancement

**Status:** Draft  
**Created:** 2025-11-02  
**Epic Type:** Brownfield Enhancement

---

## Epic Goal

Add automatic generation of customized CV templates (Lebenslauf.docx) during the motivation letter generation workflow, providing users with job-specific CV content that highlights relevant skills and experience.

---

## Epic Description

### Existing System Context

**Current Functionality:**
- Application generates motivation letters (bewerbungsschreiben.docx/html)
- Copies original CV (lebenslauf.pdf) to application folders
- Generates email text for applications
- Uses OpenAI API for letter content generation
- Follows established checkpoint/application folder structure

**Technology Stack:**
- Python 3.x with Flask
- OpenAI API (GPT-4) for content generation
- DocxTpl for Word document template rendering
- Existing motivation letter workflow in `letter_generation_utils.py`

**Integration Points:**
- Hooks into `letter_generation_utils.py::generate_motivation_letter()`
- Uses existing CV summary files from `process_cv/cv-data/processed/`
- Follows same pattern as `word_template_generator.py`
- Outputs to application checkpoint folders

### Enhancement Details

**What's Being Added:**
- New module `cv_template_generator.py` for CV content generation
- AI-powered generation of job-specific CV content (motivation, profile, competencies)
- Word template rendering using DocxTpl
- Integration into existing letter generation workflow
- Non-blocking implementation (CV generation failures don't prevent letter generation)

**How It Integrates:**
- Executes automatically after motivation letter DOCX generation
- Reads CV summary from processed CV files
- Uses same OpenAI configuration as motivation letter generator
- Outputs `Lebenslauf.docx` to application checkpoint folder
- Maintains existing workflow integrity

**Success Criteria:**
- CV templates generated successfully in >95% of letter generations
- CV generation completes in <7 seconds average
- No impact on existing letter generation success rate
- Generated CV content meets quality requirements (word counts, language, relevance)
- Non-blocking design proven (letter generation succeeds even when CV generation fails)

---

## Stories

### Story 6.1: Create CV Template Generator Module

Create the core `cv_template_generator.py` module with AI-powered content generation and template rendering capabilities.

**Key Deliverables:**
- `cv_template_generator.py` module with all core functions
- OpenAI API integration for CV content generation
- Content validation logic (word counts, bullet point counts)
- Error handling and logging
- Unit tests

### Story 6.2: Integrate CV Generation into Letter Workflow

Integrate CV template generation into the existing motivation letter workflow with non-blocking execution.

**Key Deliverables:**
- Integration code in `letter_generation_utils.py`
- CV summary path resolution helper
- Non-blocking error handling
- Integration tests
- Verification of existing letter generation unchanged

### Story 6.3: Template Creation and Testing

Create the Word template file and conduct comprehensive end-to-end testing.

**Key Deliverables:**
- `Lebenslauf_template.docx` with proper placeholders
- Manual testing of full workflow
- Performance validation
- Documentation updates
- Deployment readiness verification

---

## Compatibility Requirements

- [x] Existing motivation letter generation remains unchanged
- [x] No changes to existing APIs or database schema
- [x] Application folder structure follows existing pattern
- [x] CV generation failures don't block letter generation
- [x] Performance impact <7 seconds per application
- [x] No new external dependencies required

---

## Risk Mitigation

**Primary Risk:** CV generation failures could disrupt motivation letter workflow

**Mitigation:**
- Non-blocking implementation with try/catch wrappers
- Extensive logging for debugging
- Single retry logic for content validation failures
- CV generation skipped if CV summary or template missing
- Integration tests verify existing functionality unchanged

**Rollback Plan:**
- Remove CV generation call from `letter_generation_utils.py`
- Existing workflow reverts to previous behavior immediately
- No data corruption or loss possible
- No database migration needed for rollback

---

## Definition of Done

- [x] All three stories completed with acceptance criteria met
- [x] CV template successfully generated in application folders
- [x] Existing motivation letter generation verified unchanged
- [x] Integration points working correctly with <7 second overhead
- [x] No regression in existing features confirmed via testing
- [x] Error handling tested (missing files, API failures, validation failures)
- [x] Documentation updated with new feature details
- [x] Code reviewed and deployed

---

## Architecture Reference

Full architecture details available in:
`docs/03_Individual CV Template/architecture.md`

---

## Notes

- This enhancement mirrors the existing motivation letter generation pattern
- No UI changes required - automatic generation during existing workflow
- Feature can be disabled by removing integration code with no side effects
- Future enhancements could include multiple template support and manual editing

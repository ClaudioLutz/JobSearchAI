# Story 1.1: Backend Infrastructure (Email Sending + Data Validation)

Status: Approved

## Story

As a **job applicant using JobSearchAI**,
I want **reliable email sending with automated validation checks**,
so that **I can confidently send professional job applications while preventing incomplete or invalid submissions**.

## Acceptance Criteria

1. **AC-1: Email Sending Module**
   - Create `utils/email_sender.py` with `EmailSender` class
   - Implement Gmail SMTP authentication using app password from environment variables
   - Support HTML email format with plain text fallback
   - Return success/failure status with detailed error messages
   - Log all email attempts (success and failures) for debugging
   - Handle authentication errors, connection timeouts, and SMTP exceptions gracefully

2. **AC-2: Data Validation Module**
   - Create `utils/validation.py` with `ApplicationValidator` class
   - Validate all required fields: recipient_email, recipient_name, company_name, job_title, job_description, motivation_letter
   - Check minimum character lengths: job_description (50 chars), motivation_letter (200 chars)
   - Validate email format using email-validator library
   - Calculate completeness score (0-100%) based on validation results
   - Return structured validation result with missing_fields, invalid_fields, and warnings

3. **AC-3: Email Sender Unit Tests**
   - Create `tests/test_email_sender.py` with comprehensive test coverage
   - Test successful email sending scenario (mocked SMTP)
   - Test authentication failure handling
   - Test invalid recipient email handling
   - Test HTML email formatting correctness
   - Achieve >80% code coverage for email_sender module

4. **AC-4: Validation Unit Tests**
   - Create `tests/test_validation.py` with comprehensive test coverage
   - Test complete valid application returns is_valid=True, score=100
   - Test missing required fields detected correctly
   - Test invalid email format detected
   - Test minimum length violations detected
   - Test completeness score calculation accuracy
   - Achieve >80% code coverage for validation module

5. **AC-5: Environment Configuration**
   - Update `.env.example` with Gmail credentials documentation
   - Document Gmail App Password setup process in comments
   - Validate credentials loaded correctly on application startup

6. **AC-6: Dependencies Installation**
   - Add `email-validator==2.1.0` to `requirements.txt`
   - Verify installation with `pip install email-validator==2.1.0`
   - Document new dependency in README.md

## Tasks / Subtasks

- [ ] **Task 1: Create Email Sender Module** (AC: #1)
  - [ ] Create `utils/email_sender.py` file
  - [ ] Implement `EmailSender.__init__()` with credential loading from environment
  - [ ] Implement `send_application()` method with SMTP connection logic
  - [ ] Add HTML email composition with MIME multipart
  - [ ] Implement TLS encryption on port 587
  - [ ] Add comprehensive error handling (auth, connection, SMTP exceptions)
  - [ ] Add logging for all email operations
  - [ ] Test manual email send with test script

- [ ] **Task 2: Create Data Validation Module** (AC: #2)
  - [ ] Create `utils/validation.py` file
  - [ ] Implement `ApplicationValidator` class with field definitions
  - [ ] Implement `validate_application()` method
  - [ ] Add required field presence checks
  - [ ] Add minimum length validation logic
  - [ ] Add email format validation using email-validator
  - [ ] Implement completeness score calculation
  - [ ] Return structured validation result dictionary
  - [ ] Test with sample application data

- [ ] **Task 3: Create Email Sender Tests** (AC: #3)
  - [ ] Create `tests/test_email_sender.py` file
  - [ ] Write test for successful email sending (mock SMTP)
  - [ ] Write test for authentication failure scenario
  - [ ] Write test for invalid recipient handling
  - [ ] Write test for HTML formatting correctness
  - [ ] Write test for missing credentials error
  - [ ] Run tests and verify >80% coverage
  - [ ] Fix any failing tests

- [ ] **Task 4: Create Validation Tests** (AC: #4)
  - [ ] Create `tests/test_validation.py` file
  - [ ] Write test for complete valid application
  - [ ] Write test for missing required fields
  - [ ] Write test for invalid email format
  - [ ] Write test for minimum length violations
  - [ ] Write test for completeness score calculation
  - [ ] Run tests and verify >80% coverage
  - [ ] Fix any failing tests

- [ ] **Task 5: Update Environment Configuration** (AC: #5)
  - [ ] Add GMAIL_ADDRESS variable to `.env.example`
  - [ ] Add GMAIL_APP_PASSWORD variable to `.env.example`
  - [ ] Document Gmail App Password setup steps in comments
  - [ ] Update `.env` with actual credentials (local only, not committed)
  - [ ] Verify credentials load correctly on app startup

- [ ] **Task 6: Update Dependencies** (AC: #6)
  - [ ] Add `email-validator==2.1.0` to `requirements.txt`
  - [ ] Run `pip install email-validator==2.1.0` in virtual environment
  - [ ] Verify successful installation
  - [ ] Update README.md with new dependency information
  - [ ] Test import `from email_validator import validate_email`

## Dev Notes

### Architecture Patterns and Constraints

**Email Sending Approach:**
- Using Python's built-in `smtplib` library (zero external dependencies beyond stdlib)
- Gmail SMTP server: `smtp.gmail.com:587` with TLS encryption
- App Password authentication (simpler than OAuth2 for MVP)
- Synchronous sending (async deferred to post-MVP)
- Detailed error logging for production debugging

**Validation Strategy:**
- Fail-safe design: Invalid applications cannot be sent
- Clear, specific feedback for each validation failure
- Quantifiable progress via completeness score
- Extensible validation rule system

**Error Handling Philosophy:**
- Fail fast with clear error messages
- Log all failures for debugging
- Return actionable error messages to user
- No silent failures

### Project Structure Notes

**Alignment with Unified Project Structure:**
```
utils/
  ├── email_sender.py         # NEW - Email sending module
  ├── validation.py           # NEW - Data validation module
  ├── api_utils.py            # EXISTING - No changes
  ├── decorators.py           # EXISTING - No changes
  └── file_utils.py           # EXISTING - No changes

tests/
  ├── test_email_sender.py    # NEW - Email sender tests
  ├── test_validation.py      # NEW - Validation tests
  └── (other existing tests)  # EXISTING - No changes

requirements.txt              # MODIFIED - Add email-validator
.env.example                  # MODIFIED - Add Gmail variables
README.md                     # MODIFIED - Document new features
```

**No Conflicts Detected:**
- New modules follow existing `utils/` pattern
- Tests follow existing test structure
- No name collisions with existing modules

### Testing Standards Summary

**Unit Test Requirements:**
- Use `pytest` framework (already in use)
- Mock external dependencies (SMTP, file I/O)
- Achieve >80% code coverage
- Test both success and failure scenarios
- Use descriptive test names: `test_<module>_<scenario>_<expected_result>()`

**Test Execution:**
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_email_sender.py

# Run with coverage report
pytest --cov=utils --cov-report=html tests/
```

### References

**Technical Implementation Details:**
- [Source: docs/tech-spec.md#Module 1: Email Sender] - Complete Python implementation of EmailSender class
- [Source: docs/tech-spec.md#Module 2: Data Validation] - Complete Python implementation of ApplicationValidator class
- [Source: docs/tech-spec.md#Testing Approach] - Unit test specifications and manual testing checklist
- [Source: docs/tech-spec.md#Email Configuration] - SMTP settings and Gmail app password setup

**Epic and Story Context:**
- [Source: docs/epic-stories.md#Story 1: Backend Infrastructure] - Story overview, deliverables, and estimates
- [Source: docs/epic-stories.md#Implementation Sequence] - Story execution order and timeline

**Product Requirements:**
- [Source: docs/product-brief-JobSearchAI-2025-10-15.md#MVP Priorities] - Strategic context for email automation feature

## Dev Agent Record

### Context Reference

- `Documentation/Stories/story-context-1.1.xml` - Comprehensive Story Context with artifacts, constraints, interfaces, and testing guidance

### Agent Model Used

_To be filled by development agent_

### Debug Log References

_To be filled by development agent during implementation_

### Completion Notes List

_To be filled by development agent upon story completion_

### File List

**Created Files:**
- `utils/email_sender.py`
- `utils/validation.py`
- `tests/test_email_sender.py`
- `tests/test_validation.py`

**Modified Files:**
- `requirements.txt` (added email-validator)
- `.env.example` (added Gmail variables)
- `README.md` (documented new features)

### Change Log

**2025-10-15 22:59 UTC - Story Created**
- Generated from Epic 1 (email-automation), Story 1
- Based on tech-spec.md definitive implementation guidance
- Epic Story ID: email-automation-1
- Story Points: 5
- Estimated Hours: 5-7 hours
- Dependencies: None (can start immediately)
- Created by: @sm (Bob - Scrum Master)

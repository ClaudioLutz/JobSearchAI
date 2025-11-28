# Story 7.1: LinkedIn Generator Service

**Epic:** Epic 7 - LinkedIn Outreach Integration  
**Status:** Complete  
**Story Type:** Implementation  
**Estimate:** 5 Story Points  
**Actual Effort:** 5 Story Points  
**Completed:** 2025-11-28

---

## User Story

As a **job seeker using the application**,  
I want **the system to generate personalized LinkedIn messages using AI**,  
So that **I can effectively network with hiring managers and peers at target companies with professionally crafted, character-limited messages**.

---

## Story Context

### Existing System Integration

**Integrates with:**
- `motivation_letter_generator.py` - Reuses OpenAI client configuration pattern
- `utils/api_utils.py` - Uses `generate_json_from_prompt()` for AI generation
- `config.py` - Uses OpenAI configuration via `get_openai_defaults()`
- `job_details_utils.py` - Receives job details data structure

**Technology:**
- Python 3.x
- OpenAI API (GPT-4 or configured model)
- Python logging framework
- JSON for structured output

**Follows pattern:**
- Similar to `motivation_letter_generator.py` structure
- Reuses OpenAI configuration from existing generators
- Follows established error handling patterns
- Uses JSON-based AI responses

**Touch points:**
- Receives CV summary text from processed CV files
- Receives job details dict with company, title, contact person, description
- Calls OpenAI API for content generation
- Returns structured JSON with three message types

---

## Acceptance Criteria

### Functional Requirements

1. **Module Structure Created**
   - Create `services/linkedin_generator.py` module
   - Module contains `generate_linkedin_messages()` function
   - Proper docstrings and type hints on all public functions
   - Import statements organized and minimal

2. **AI Message Generation Function**
   - `generate_linkedin_messages(cv_summary, job_details)` function signature
   - Constructs appropriate prompt for OpenAI API with strict character limits
   - Returns dict with three keys: `connection_request_hiring_manager`, `peer_networking`, `inmail_message`
   - Handles both German and English language generation (matches job description language)
   - Applies ß → ss replacement for German text
   - Uses contact person from job_details if available

3. **Character Limit Enforcement**
   - Connection request STRICTLY under 300 characters
   - Peer networking message under 500 characters (300 preferred)
   - InMail message max 150 words
   - Post-processing validation to ensure limits are respected
   - Truncation with "..." if AI exceeds limit (fallback safety)

4. **Language Detection**
   - Automatically detects language from job description
   - Generates messages in the EXACT same language as job posting
   - Explicit instruction in prompt to match job language
   - Works for both English and German job postings

5. **Contact Person Handling**
   - Uses contact person name if provided in job_details
   - Falls back to generic placeholders like "[Name]" or "Hiring Manager" if not provided
   - Never hallucinates or invents contact names
   - Clear prompt instructions to prevent AI from making up names

### Integration Requirements

6. **OpenAI Configuration Reuse**
   - Uses `generate_json_from_prompt()` from `utils/api_utils.py`
   - Passes system prompt and user prompt separately
   - Uses default OpenAI configuration from config
   - Handles API errors gracefully

7. **Existing Pattern Adherence**
   - Module structure mirrors other service modules
   - Function naming follows project conventions
   - Error handling matches existing patterns
   - Logging format consistent with project standards

8. **Non-Breaking Implementation**
   - Module is standalone and doesn't modify existing code
   - No changes to existing imports or dependencies
   - No changes to configuration files
   - Module can be imported without side effects

### Quality Requirements

9. **Error Handling and Logging**
   - All exceptions caught and logged with appropriate levels
   - INFO level for successful operations
   - WARNING level for character limit violations (before truncation)
   - ERROR level for API failures
   - Log messages include relevant context (company, job title, error details)

10. **Testing Coverage**
    - Create `tests/manual_test_linkedin.py` for manual testing
    - Test successful message generation with mock API
    - Test character limit validation
    - Test both German and English content generation
    - Test with and without contact person
    - Test API error handling

11. **Code Quality**
    - Code follows PEP 8 style guidelines
    - Type hints on function signatures
    - Docstrings follow project style
    - No hardcoded values (use constants where appropriate)
    - Clear variable names
    - Function is single-purpose and testable

---

## Technical Notes

### Implementation Approach

**OpenAI Prompt Structure:**
```python
# System prompt
system_prompt = """You are an expert networking coach helping a candidate craft 
high-impact LinkedIn messages. You strictly enforce character limits and match 
the language of the job description."""

# User prompt includes:
# - Explicit language matching instruction (CRITICAL)
# - Job details (company, title, contact person, description snippet)
# - Candidate CV summary
# - Output requirements (character limits, format)
# - JSON output format specification
```

**Character Limit Enforcement:**
```python
# Primary: AI prompt instruction with STRICT emphasis
# Secondary: Post-processing validation
if len(messages_json.get('connection_request_hiring_manager', '')) > 300:
    logger.warning("Generated connection request exceeded 300 chars. Truncating.")
    messages_json['connection_request_hiring_manager'] = 
        messages_json['connection_request_hiring_manager'][:297] + "..."
```

**Language Detection:**
- Relies on AI to detect language from job description
- Explicit instruction in prompt: "Write in THE EXACT SAME LANGUAGE as the job description"
- No separate language detection logic needed

### Module Constants

```python
CONNECTION_REQUEST_MAX_CHARS = 300
PEER_NETWORKING_MAX_CHARS = 500
INMAIL_MAX_WORDS = 150
JOB_DESCRIPTION_SNIPPET_LENGTH = 500  # Only send first 500 chars to AI
```

### Error Scenarios to Handle

| Scenario | Handling |
|----------|----------|
| OpenAI API failure | Log error, return None |
| Invalid JSON response | Log error, return None |
| Character limit exceeded | Log warning, truncate with "..." |
| Missing job details | Use fallback values ("the company", "the position") |
| Missing CV summary | Log error, return None (required input) |

### Expected Output Format

```json
{
    "connection_request_hiring_manager": "Hi [Name], I saw the Senior Engineer role at Tech Corp. My background in Python and AI seems like a great fit. I'd love to connect!",
    "peer_networking": "Hi [Name], I'm a Python Developer interested in Tech Corp. I see you're working as an Engineer there. I'd love to hear your thoughts on the engineering culture if you're open to connecting.",
    "inmail_message": "Dear [Name],\n\nI am writing to express my interest in the Senior Engineer position at Tech Corp. With 5 years of experience in Python development and AI integration, I believe I would be a strong fit for your team.\n\nMy background includes...\n\nI would welcome the opportunity to discuss how my skills align with your needs.\n\nBest regards"
}
```

---

## Definition of Done

- [x] `services/linkedin_generator.py` created
- [x] `generate_linkedin_messages()` function implemented with proper signature
- [x] OpenAI API integration working with `generate_json_from_prompt()`
- [x] Character limit enforcement implemented (prompt + post-processing)
- [x] Language matching instruction in prompt
- [x] Contact person handling (use if available, fallback if not)
- [x] Error handling comprehensive and logged appropriately
- [x] Manual test created in `tests/manual_test_linkedin.py`
- [x] Manual test passes with mocked API
- [x] Code follows project style guidelines
- [x] Docstrings complete
- [x] No changes to existing code or configuration
- [x] Module can be imported without errors
- [x] Manual smoke test with real API passes (verified character limits)

---

## Testing Checklist

### Manual Tests to Create

```
[x] test_linkedin_generation - Basic generation with mock API
[x] Test character limit validation (connection request < 300 chars)
[x] Test with contact person provided
[x] Test without contact person (generic placeholder)
[x] Test German job description (messages in German)
[x] Test English job description (messages in English)
[x] Test error handling (mock API failure)
```

### Manual Testing Steps

```
[x] Import module successfully
[x] Call generate_linkedin_messages() with test data - verify output structure
[x] Verify connection_request_hiring_manager < 300 characters
[x] Verify peer_networking message present
[x] Verify inmail_message present
[x] Verify logging output at each step
[x] Verify error handling with missing CV summary
[x] Test with real OpenAI API (optional, costs tokens)
```

---

## Dependencies

**External Libraries:**
- `openai` - Already installed
- `logging` - Python standard library
- `json` - Python standard library

**Internal Modules:**
- `utils/api_utils.py` - For `generate_json_from_prompt()`
- `config.py` - For OpenAI configuration

**Data Inputs:**
- CV summary text (string)
- Job details dict with keys: Company Name, Job Title, Contact Person (optional), Job Description

---

## Risk Assessment

**Risk:** AI fails to respect 300 character limit for connection requests

**Mitigation:**
- Explicit STRICT emphasis in prompt
- Post-processing truncation as safety net
- Logging warning if truncation occurs
- Manual testing to verify limits respected

**Risk:** AI hallucinates contact person names

**Mitigation:**
- Explicit instruction to ONLY use provided contact names
- Instruction to use generic placeholders if not provided
- Clear prompt structure separating provided vs. generated content

**Risk:** Language mismatch (generates English for German job or vice versa)

**Mitigation:**
- EXPLICIT instruction in prompt to match job description language
- All-caps emphasis in prompt
- Manual testing with both languages

---

## Notes for Developer

- **DO NOT** modify existing code in this story
- Focus on creating standalone, testable module
- Follow patterns from `motivation_letter_generator.py` closely
- Use comprehensive logging for debugging
- Character limits are CRITICAL - test thoroughly
- Language matching is CRITICAL - test with both German and English
- Contact person handling must never hallucinate names
- Integration with routes happens in Story 7.2
- Frontend integration happens in Story 7.3

---

## Implementation Details

### Actual Implementation

The module was implemented in `services/linkedin_generator.py` with the following key features:

1. **Function Signature:**
   ```python
   def generate_linkedin_messages(cv_summary, job_details):
   ```

2. **Prompt Engineering:**
   - System prompt emphasizes networking coach expertise and strict limits
   - User prompt includes EXPLICIT language matching instruction
   - Job description limited to first 500 characters for efficiency
   - Clear JSON output format specification

3. **Character Limit Enforcement:**
   - Primary: AI instruction with "STRICTLY UNDER 300 CHARACTERS"
   - Secondary: Post-processing check with truncation fallback
   - Warning logged if truncation needed

4. **Error Handling:**
   - Try-except block around API call
   - Returns None on failure
   - Comprehensive logging at all stages

5. **Special Handling:**
   - ß → ss replacement instruction in prompt
   - Contact person fallback to "Not specified (Use generic placeholder if needed)"
   - Language detection via AI analysis of job description

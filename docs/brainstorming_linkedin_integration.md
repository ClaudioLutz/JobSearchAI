# Brainstorming Session: LinkedIn Outreach Generator

## Goal
Enable the user to effectively network by generating personalized LinkedIn connection messages for hiring managers or peers at the target company.

## Concept
Leverage the existing job data (Company Name, Job Title, Description) and the candidate's profile (CV Summary) to create short, high-impact messages suitable for LinkedIn connection requests (limited character count) or InMail.

## Proposed Features

1.  **Hiring Manager Connection Request (300 chars max)**
    *   *Context*: Sending a connection request to a potential boss/recruiter.
    *   *Content*: "Hi [Name], I saw the [Job Title] role at [Company]. My background in [Skill 1] and [Skill 2] seems like a great fit. I'd love to connect!"

2.  **Peer Networking Message**
    *   *Context*: Connecting with someone in a similar role to ask about company culture.
    *   *Content*: "Hi [Name], I'm a [Current Role] interested in [Company]. I see you're working as a [Role] there. I'd love to hear your thoughts on the engineering culture if you're open to connecting."

3.  **InMail / Direct Message (Longer form)**
    *   *Context*: You have Premium or are already connected.
    *   *Content*: A slightly more detailed pitch, similar to a mini-cover letter but more conversational.

## Implementation Plan (Draft)

### 1. New Module: `linkedin_generator.py`
*   Similar structure to `letter_generation_utils.py`.
*   Function: `generate_linkedin_messages(cv_summary, job_details)`
*   Output: JSON object with 2-3 variations of messages.

### 2. Integration
*   **Backend**: Add a new route `/generate_linkedin` in a new or existing blueprint.
*   **Frontend**:
    *   Add a "LinkedIn" tab or section in the "Job Details" or "Application" view.
    *   Display the generated messages with a "Copy to Clipboard" button.

### 3. Data Requirements
*   **Input**:
    *   `Company Name` (from job details)
    *   `Job Title` (from job details)
    *   `Contact Person` (if available in job details - highly valuable here!)
    *   `CV Summary` (for personalization)

## Open Questions
*   Should we try to find the hiring manager's name automatically? (Likely out of scope for now, assume user provides it or we use a generic placeholder).
*   Should this be part of the standard "Combined Process" or an "On Demand" feature? (On Demand seems better, as you don't reach out for *every* job).

## Next Steps
1.  Create a new Story/Epic for this feature.
2.  Define the exact prompts for the AI.
3.  Design the UI integration.

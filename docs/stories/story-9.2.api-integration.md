# Story 9.2: API & Route Integration

## Story Info
**Epic:** [Epic 9: Job Stage Classification](epic-9-job-stage-classification.md)
**Status:** Planned
**Effort:** 3 Story Points

## Goal
Expose the application status management capabilities to the frontend via a RESTful API.

## Context
The frontend needs a way to fetch the current status of a job and update it when the user interacts with the UI (e.g., clicks "Mark as Applied" or drags a card).

## Acceptance Criteria
1.  **API Endpoints**:
    *   `POST /api/applications/status`: Updates the status of a job match.
        *   Input: `{ job_match_id: int, status: string }`
        *   Output: `{ success: bool, new_status: string }`
    *   `GET /api/applications`: Retrieves all application records (or a specific one).
2.  **Integration with Job Fetching**:
    *   When fetching job matches (e.g., for the dashboard), the response should now include the `status` field for each job.
    *   This might require joining `job_matches` and `applications` in the SQL query.
3.  **Error Handling**:
    *   Invalid status strings should be rejected.
    *   Invalid IDs should return 404.

## Technical Implementation Plan
1.  **Create Blueprint**:
    *   Create `blueprints/application_routes.py`.
2.  **Implement Routes**:
    *   `update_status` route: Calls `application_service.update_application_status`.
3.  **Update Existing Queries**:
    *   Modify the main job fetch query in `dashboard.py` (or relevant service) to `LEFT JOIN applications ON job_matches.id = applications.job_match_id`.
    *   If `applications.status` is NULL, default to `MATCHED` in the response.

## Dependencies
- Story 9.1 (Database Schema) must be complete.

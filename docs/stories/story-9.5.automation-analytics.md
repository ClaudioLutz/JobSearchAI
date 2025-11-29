# Story 9.5: Automation & Analytics

## Story Info
**Epic:** [Epic 9: Job Stage Classification](epic-9-job-stage-classification.md)
**Status:** Planned
**Effort:** 3 Story Points

## Goal
Implement smart automations to reduce manual effort and provide basic analytics on the job search progress.

## Context
To make the system feel "smart", it should infer status changes where possible (e.g., generating a letter implies "Preparing"). Users also need feedback on their funnel (e.g., how many jobs are in each stage).

## Acceptance Criteria
1.  **Auto-Transition**:
    *   When a user clicks "Generate Letter" (or successfully generates one), the job status automatically moves from `MATCHED` or `INTERESTED` to `PREPARING` (if not already further along).
2.  **Stale Detection**:
    *   Jobs in `PREPARING` for > 7 days are visually flagged (e.g., with a warning icon or different color).
3.  **Basic Analytics**:
    *   A summary widget on the dashboard showing counts for each active stage (e.g., "Applied: 12", "Interview: 2").

## Technical Implementation Plan
1.  **Hook into Generation**:
    *   In `letter_generation_utils.py` or the route handler for generation, call `application_service.update_status(..., 'PREPARING')`.
2.  **Dashboard Widget**:
    *   Create a new template partial `stats_widget.html`.
    *   Backend: `SELECT status, COUNT(*) FROM applications GROUP BY status`.
3.  **Stale Logic**:
    *   In the job fetch query, calculate `days_since_update`.
    *   Frontend: `if status == 'PREPARING' and days > 7: show_warning`.

## Dependencies
- Story 9.1 (DB) and 9.2 (API) must be complete.

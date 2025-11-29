# Story 9.1: Database Schema & Backend Logic

## Story Info
**Epic:** [Epic 9: Job Stage Classification](epic-9-job-stage-classification.md)
**Status:** Planned
**Effort:** 5 Story Points

## Goal
Implement the foundational data model and backend logic to support job stage classification, moving from a stateless "match" system to a stateful "application" tracking system.

## Context
Currently, `job_matches` stores the match data, but there is no concept of an "application" lifecycle. We need a new table `applications` to track the status (`MATCHED`, `APPLIED`, etc.) and timestamps for each stage.

## Acceptance Criteria
1.  **Database Schema**:
    *   A new SQLite table `applications` is created.
    *   Columns: `id`, `job_match_id` (FK), `status` (Text/Enum), `created_at`, `updated_at`, `notes`.
    *   `status` defaults to 'MATCHED'.
2.  **Data Migration**:
    *   A script or logic exists to ensure the table is created on startup if it doesn't exist.
    *   (Optional) Existing `job_matches` can be backfilled into `applications` with `MATCHED` status, or we can treat a missing record as `MATCHED`.
3.  **Backend Model**:
    *   A Python class or set of functions in `db_utils.py` (or new `application_service.py`) to:
        *   `get_application_status(job_match_id)`
        *   `update_application_status(job_match_id, new_status)`
        *   `add_application_note(job_match_id, note)`
4.  **Enums**:
    *   Define a standard Enum for statuses: `MATCHED`, `INTERESTED`, `PREPARING`, `APPLIED`, `INTERVIEW`, `OFFER`, `REJECTED`, `ARCHIVED`.

## Technical Implementation Plan
1.  **Define SQL Schema**:
    ```sql
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_match_id INTEGER NOT NULL UNIQUE,
        status TEXT NOT NULL DEFAULT 'MATCHED',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        notes TEXT,
        FOREIGN KEY(job_match_id) REFERENCES job_matches(id)
    );
    ```
2.  **Update `db_utils.py`**:
    *   Add `init_applications_table()` function.
    *   Add CRUD functions for applications.
3.  **Service Layer**:
    *   Create `services/application_service.py` to handle business logic (e.g., validating state transitions if necessary).

## Dependencies
- None. This is the foundation for the rest of the epic.

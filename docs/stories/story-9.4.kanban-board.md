# Story 9.4: Kanban Board View

## Story Info
**Epic:** [Epic 9: Job Stage Classification](epic-9-job-stage-classification.md)
**Status:** Planned
**Effort:** 8 Story Points

## Goal
Implement a Kanban board visualization to manage the job application pipeline effectively.

## Context
A list view is good for discovery, but a board view is better for process management. Users want to drag and drop jobs from "Interested" to "Applied" to "Interview".

## Acceptance Criteria
1.  **New Route**:
    *   `/kanban` displays the board.
2.  **Board Layout**:
    *   Columns for active stages: `INTERESTED`, `PREPARING`, `APPLIED`, `INTERVIEW`, `OFFER`.
    *   `MATCHED` (Inbox) might be a separate column or a sidebar.
    *   `REJECTED`/`ARCHIVED` are hidden or in a separate "Done" column.
3.  **Drag and Drop**:
    *   Users can drag a job card from one column to another.
    *   Dropping the card triggers an API call to update the status.
4.  **Card Content**:
    *   Simplified job card: Company, Title, Match Score.

## Technical Implementation Plan
1.  **Frontend Library**:
    *   Evaluate if a library (like SortableJS) is needed or if native HTML5 DnD is sufficient. (Native is likely fine for simple columns).
2.  **Template Structure**:
    *   Create `templates/kanban.html`.
    *   Loop through jobs and group them by status into columns.
3.  **JavaScript**:
    *   Handle dragstart, dragover, drop events.
    *   On drop:
        *   Identify new status based on column ID.
        *   Call API `update_status`.
        *   Move DOM element.

## Dependencies
- Story 9.3 (Frontend Controls) should be done first to ensure basic status logic works, though they can be parallel.

# Story 9.3: Frontend UI - Status Controls

## Story Info
**Epic:** [Epic 9: Job Stage Classification](epic-9-job-stage-classification.md)
**Status:** Planned
**Effort:** 5 Story Points

## Goal
Update the existing Job List and Job Detail views to display the current application status and allow users to change it.

## Context
Users currently see a list of matches. They need to see which ones they've already applied to or are preparing for. They also need a quick way to update this status without leaving the page.

## Acceptance Criteria
1.  **Status Display**:
    *   Each Job Card in the main list displays a status badge (e.g., "Applied" in Green, "Preparing" in Yellow).
    *   The Job Detail modal also displays the current status prominently.
2.  **Status Update Control**:
    *   A dropdown menu or a set of buttons allows changing the status.
    *   Common transitions (e.g., "Mark as Applied") should be easily accessible.
3.  **Visual Feedback**:
    *   Changing status updates the badge immediately (optimistic UI or after API success).
    *   Toasts/Notifications confirm the update.

## Technical Implementation Plan
1.  **Update Templates**:
    *   Modify `templates/dashboard.html` (or relevant component) to render the status badge.
    *   Add a "Status" dropdown to the job actions area.
2.  **JavaScript Logic**:
    *   Add event listeners for the status change.
    *   Call `POST /api/applications/status` via `fetch`.
    *   Update the DOM element class/text upon success.
3.  **CSS Styling**:
    *   Define classes for each status (e.g., `.badge-applied`, `.badge-rejected`).

## Dependencies
- Story 9.2 (API) must be complete.

# Epic 9: Job Stage Classification

## Epic Status
**Status:** Planned
**Created:** 2025-11-29
**Owner:** Product Manager
**Architecture Reference:** [9_brainstorming_job_stage_classification.md](../9_brainstorming_job_stage_classification.md)

---

## Epic Goal

Transform JobSearchAI from a simple job discovery tool into a complete Applicant Tracking System (ATS) by introducing a formal state machine for job applications, allowing users to track their progress from "Matched" to "Offer" or "Rejected".

---

## Epic Description

### Existing System Context

**Current State:**
- The system currently treats jobs primarily as "matches" based on CV comparison.
- There is no way to track whether a user has applied, is interviewing, or has been rejected.
- Users rely on external tools (spreadsheets, Trello) or memory to track application status.
- "Letter Generated" is the only implicit signal of user interest, but it's not a formal state.

**Technology Stack:**
- Python 3.x with Flask and SQLite
- Frontend: Jinja2 templates + Bootstrap + Vanilla JS
- Existing `job_matches` table

### Enhancement Details

**What's Being Added:**

1.  **Formal Job Stages (State Machine)**
    - Introduction of explicit states: `MATCHED`, `INTERESTED`, `PREPARING`, `APPLIED`, `INTERVIEW`, `OFFER`, `REJECTED`, `ARCHIVED`.
    - A new database structure (likely a separate `applications` table) to track these states and their history.

2.  **UI Controls for Status Management**
    - Visual indicators (badges) on job cards showing the current stage.
    - Controls (dropdowns/buttons) to manually update the stage (e.g., "Mark as Applied").

3.  **Kanban Board View**
    - A new dashboard view visualizing jobs as cards in columns corresponding to their stage.
    - Drag-and-drop functionality to move jobs between stages.

**Success Criteria:**
- Users can see the current status of any job match at a glance.
- Users can update the status of a job with < 2 clicks.
- The system preserves the history of when a job moved to "Applied".
- A Kanban view provides a high-level overview of the job search pipeline.

---

## Stories

### 9.1: Database Schema & Backend Logic
**Status:** Planned
**Effort:** 5 Story Points (1 day)
**Documentation:** [story-9.1.database-schema.md](story-9.1.database-schema.md)

**Goal:** Implement the data model for tracking job application stages.

**Key Deliverables:**
- New `applications` table in SQLite (linked to `job_matches`).
- `ApplicationStatus` Enum definition.
- Database migration script/logic.
- Backend service functions to create/update application records.

---

### 9.2: API & Route Integration
**Status:** Planned
**Effort:** 3 Story Points (0.5 days)
**Documentation:** [story-9.2.api-integration.md](story-9.2.api-integration.md)

**Goal:** Expose status management to the frontend via REST API.

**Key Deliverables:**
- `POST /api/applications/status` endpoint.
- `GET /api/applications` endpoint (or augmentation of existing job fetch).
- Integration with `dashboard.py` routes.

---

### 9.3: Frontend UI - Status Controls
**Status:** Planned
**Effort:** 5 Story Points (1 day)
**Documentation:** [story-9.3.frontend-controls.md](story-9.3.frontend-controls.md)

**Goal:** Allow users to view and change job status from the existing Job List/Detail views.

**Key Deliverables:**
- Status badges on Job Cards (color-coded).
- "Move to..." dropdown or action buttons.
- Visual feedback upon status change.

---

### 9.4: Kanban Board View
**Status:** Planned
**Effort:** 8 Story Points (1.5 days)
**Documentation:** [story-9.4.kanban-board.md](story-9.4.kanban-board.md)

**Goal:** Create a visual Kanban board for managing the application pipeline.

**Key Deliverables:**
- New `/kanban` route and page.
- Columnar layout for each active stage (`INTERESTED` to `OFFER`).
- Drag-and-drop implementation (using HTML5 DnD or a lightweight library).
- "Archived" view for `REJECTED`/`ARCHIVED` jobs.

---

### 9.5: Automation & Analytics
**Status:** Planned
**Effort:** 3 Story Points (0.5 days)
**Documentation:** [story-9.5.automation-analytics.md](story-9.5.automation-analytics.md)

**Goal:** Implement smart automations and basic funnel analytics.

**Key Deliverables:**
- Auto-transition to `PREPARING` on letter generation.
- Stale application highlighting (> 7 days).
- Dashboard widget showing counts per stage.

---

## Compatibility Requirements

- [ ] Must be backward compatible with existing `job_matches`.
- [ ] Existing matches should default to `MATCHED` state.
- [ ] Must not break the existing "Generate Letter" workflow.

---

## Risk Mitigation

**Primary Risks:**
1.  **Data Consistency**: Ensuring the `applications` table stays in sync with `job_matches`.
    *   *Mitigation*: Use Foreign Keys and ensure application records are created lazily or via migration for existing matches.
2.  **UI Clutter**: Adding too many buttons/badges to the job card.
    *   *Mitigation*: Use a clean dropdown or a subtle status indicator that expands on hover.

---

## Definition of Done

- [ ] Database schema updated with `applications` table.
- [ ] API endpoints for status updates are functional and tested.
- [ ] UI allows changing status on individual jobs.
- [ ] Kanban board is functional (drag-and-drop works).
- [ ] Documentation updated.

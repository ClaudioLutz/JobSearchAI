# Brainstorming: Job Stage Classification

## 1. Overview of Current Implementation

The current JobSearchAI system focuses primarily on **Job Discovery** and **Matching**. The workflow is as follows:

1.  **Data Acquisition**: Jobs are scraped from external sources.
2.  **Matching**: Jobs are compared against a CV to generate match scores (Overall, Skills, Experience, etc.).
3.  **Storage**: Matches are stored in the `job_matches` SQLite table.
4.  **Reporting**: Results are presented in Markdown/JSON reports and a web dashboard.
5.  **Action**: Users can generate motivation letters for specific matches.

### Current "Implicit" Stages
There is no formal state machine or status tracking for job applications. However, some states can be inferred:
*   **New Match**: A job exists in `job_matches` but has no associated actions.
*   **Letter Generated**: The system detects the existence of motivation letter files (`.html`, `.docx`, `.json`) corresponding to a job match (via URL or Title matching).

### Limitations
*   **No Application Tracking**: Users cannot mark a job as "Applied".
*   **No Pipeline Management**: There is no way to track progress (Interview, Offer, Rejected).
*   **Stateless**: The system treats a job primarily as a "match" rather than an "application process".

## 2. Proposed Job Stage Classification

To evolve JobSearchAI into a complete Applicant Tracking System (ATS) for the candidate, we should introduce a formal **Job Stage Classification** system.

### 2.1. Proposed Stages (Status Enum)

We suggest adding a `status` field to the `job_matches` table (or creating a linked `applications` table) with the following states:

| Stage | Description | Trigger/Transition |
| :--- | :--- | :--- |
| **MATCHED** | (Default) Job found and matched with CV. | Automatic upon scraping/matching. |
| **INTERESTED** | User has flagged this job for review. | Manual "Star" or "Save". |
| **PREPARING** | User is working on the application (e.g., generating CV/Letter). | Automatic when "Generate Letter" is clicked. |
| **APPLIED** | Application has been sent. | Manual confirmation or Email integration detection. |
| **INTERVIEW** | User has been invited to an interview. | Manual update. |
| **OFFER** | User received an offer. | Manual update. |
| **REJECTED** | Application was rejected. | Manual update or Email analysis. |
| **ARCHIVED** | User is not interested or job is old. | Manual or Auto-archive after X days. |

### 2.2. Database Schema Changes

**Option A: Modify `job_matches`**
Add columns to the existing table:
```sql
ALTER TABLE job_matches ADD COLUMN status TEXT DEFAULT 'MATCHED';
ALTER TABLE job_matches ADD COLUMN status_updated_at TEXT;
ALTER TABLE job_matches ADD COLUMN notes TEXT;
```

**Option B: New `applications` Table (Recommended)**
Decouple the "Match" (data) from the "Application" (process).
```sql
CREATE TABLE applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_match_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'MATCHED',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    applied_date TEXT,
    notes TEXT,
    FOREIGN KEY(job_match_id) REFERENCES job_matches(id)
);
```

## 3. Feature Suggestions

### 3.1. Kanban Board UI
Implement a Trello-like Kanban board in the dashboard where users can drag and drop jobs between columns (Stages).

### 3.2. Smart Automation
*   **Auto-Advance**: If a user generates a motivation letter, automatically move status from `MATCHED` to `PREPARING`.
*   **Stale Detection**: Highlight jobs that have been in `PREPARING` for > 7 days without being marked `APPLIED`.

### 3.3. Analytics
*   **Funnel Analysis**: Visualize the conversion rate: Matches -> Applied -> Interview -> Offer.
*   **Velocity**: Track how many applications are sent per week.

### 3.4. Integration with Email (Future)
*   Scan sent emails to auto-detect "Applied" status.
*   Scan inbox for keywords like "Interview Invitation" or "Unfortunately" to suggest status updates.

## 4. Implementation Plan (Draft)

1.  **Database Migration**: Add `status` column to `job_matches` (simplest start).
2.  **Backend API**: Create endpoints to update job status (`POST /api/jobs/<id>/status`).
3.  **Frontend**:
    *   Add status badge to Job Cards.
    *   Add "Mark as Applied" button.
    *   Create a "My Applications" view filtering by status.

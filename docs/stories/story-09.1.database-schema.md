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
    *   A new SQLite table `applications` is created with proper constraints.
    *   Columns: `id`, `job_match_id` (FK with ON DELETE CASCADE), `status` (Text validated against Enum), `created_at`, `updated_at`, `notes`.
    *   `status` defaults to 'MATCHED'.
    *   UNIQUE constraint on `job_match_id` ensures one-to-one relationship.
    *   Index on `status` column for query performance.
2.  **Data Migration**:
    *   Table creation uses `CREATE TABLE IF NOT EXISTS` (non-breaking, additive change).
    *   **No backfill required**: Application records are created lazily on first status update.
    *   **Backward Compatibility**: Jobs without an application record are treated as 'MATCHED' status in queries (using COALESCE).
3.  **Backend Model**:
    *   A Python class or set of functions in `db_utils.py` (or new `services/application_service.py`) to:
        *   `get_application_status(job_match_id)` - Returns status or 'MATCHED' if no record exists
        *   `update_application_status(job_match_id, new_status)` - Creates record if needed, updates `updated_at` timestamp
        *   `add_application_note(job_match_id, note)`
        *   `get_application_by_job_match_id(job_match_id)` - Returns full application record
4.  **Enums**:
    *   Define a standard Enum for statuses: `MATCHED`, `INTERESTED`, `PREPARING`, `APPLIED`, `INTERVIEW`, `OFFER`, `REJECTED`, `ARCHIVED`.
    *   Enum is used for validation in all status update operations.
5.  **Timestamp Management**:
    *   `updated_at` field is automatically updated on every status change (via SQL or application logic).
    *   Ensures accurate tracking for stale detection (Story 9.5).

## Technical Implementation Plan

### 1. Define SQL Schema
```sql
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_match_id INTEGER NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'MATCHED',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    FOREIGN KEY(job_match_id) REFERENCES job_matches(id) ON DELETE CASCADE
);

-- Index for performance on status queries (Kanban board, analytics)
CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
```

**Key Schema Decisions:**
- **ON DELETE CASCADE**: If a job_match is deleted, its application record is also deleted.
- **UNIQUE constraint on job_match_id**: Prevents duplicate application records for the same job.
- **Index on status**: Optimizes queries like "SELECT * FROM applications WHERE status = 'APPLIED'".
- **TEXT timestamps**: SQLite uses TEXT for dates; defaults to CURRENT_TIMESTAMP (UTC).

### 2. Create Application Status Enum
Define in a new file `models/application_status.py` or within `db_utils.py`:

```python
from enum import Enum

class ApplicationStatus(Enum):
    MATCHED = "MATCHED"
    INTERESTED = "INTERESTED"
    PREPARING = "PREPARING"
    APPLIED = "APPLIED"
    INTERVIEW = "INTERVIEW"
    OFFER = "OFFER"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"
    
    @classmethod
    def is_valid(cls, status_str):
        """Validate if a status string is valid."""
        return status_str in [s.value for s in cls]
    
    @classmethod
    def get_all_values(cls):
        """Return list of all valid status values."""
        return [s.value for s in cls]
```

### 3. Update Database Initialization
In `db_utils.py`, add to `init_database()` method or create a separate function:

```python
def init_applications_table():
    """Initialize the applications table if it doesn't exist."""
    db = JobMatchDatabase()
    db.create_connection()
    
    # Create table
    cursor = db.conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_match_id INTEGER NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'MATCHED',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            FOREIGN KEY(job_match_id) REFERENCES job_matches(id) ON DELETE CASCADE
        )
    ''')
    
    # Create index
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_applications_status 
        ON applications(status)
    ''')
    
    db.conn.commit()
    db.close_connection()
```

### 4. Implement Service Functions
Create `services/application_service.py` (or add to `db_utils.py`):

```python
from models.application_status import ApplicationStatus
from utils.db_utils import JobMatchDatabase
import logging

logger = logging.getLogger(__name__)

def get_application_status(job_match_id):
    """
    Get the status of an application by job_match_id.
    Returns 'MATCHED' if no application record exists.
    """
    db = JobMatchDatabase()
    db.create_connection()
    
    cursor = db.conn.cursor()
    cursor.execute(
        'SELECT status FROM applications WHERE job_match_id = ?',
        (job_match_id,)
    )
    result = cursor.fetchone()
    db.close_connection()
    
    return result[0] if result else ApplicationStatus.MATCHED.value

def update_application_status(job_match_id, new_status, notes=None):
    """
    Update or create an application status.
    Returns True on success, False on failure.
    Automatically updates updated_at timestamp.
    """
    # Validate status
    if not ApplicationStatus.is_valid(new_status):
        logger.error(f"Invalid status: {new_status}")
        return False
    
    db = JobMatchDatabase()
    db.create_connection()
    cursor = db.conn.cursor()
    
    # Check if record exists
    cursor.execute(
        'SELECT id FROM applications WHERE job_match_id = ?',
        (job_match_id,)
    )
    exists = cursor.fetchone()
    
    if exists:
        # Update existing record
        cursor.execute('''
            UPDATE applications 
            SET status = ?, 
                updated_at = CURRENT_TIMESTAMP,
                notes = COALESCE(?, notes)
            WHERE job_match_id = ?
        ''', (new_status, notes, job_match_id))
        logger.info(f"Updated status for job_match_id {job_match_id} to {new_status}")
    else:
        # Insert new record
        cursor.execute('''
            INSERT INTO applications (job_match_id, status, notes)
            VALUES (?, ?, ?)
        ''', (job_match_id, new_status, notes))
        logger.info(f"Created application for job_match_id {job_match_id} with status {new_status}")
    
    db.conn.commit()
    db.close_connection()
    
    return True

def add_application_note(job_match_id, note):
    """Add or append a note to an application."""
    db = JobMatchDatabase()
    db.create_connection()
    
    cursor = db.conn.cursor()
    cursor.execute('''
        UPDATE applications 
        SET notes = CASE 
            WHEN notes IS NULL THEN ?
            ELSE notes || '\n' || ?
        END,
        updated_at = CURRENT_TIMESTAMP
        WHERE job_match_id = ?
    ''', (note, note, job_match_id))
    
    db.conn.commit()
    db.close_connection()
    
    return cursor.rowcount > 0

def get_application_by_job_match_id(job_match_id):
    """Get full application record."""
    db = JobMatchDatabase()
    db.create_connection()
    
    cursor = db.conn.cursor()
    cursor.execute('''
        SELECT id, job_match_id, status, created_at, updated_at, notes
        FROM applications 
        WHERE job_match_id = ?
    ''', (job_match_id,))
    
    result = cursor.fetchone()
    db.close_connection()
    
    if result:
        return {
            'id': result[0],
            'job_match_id': result[1],
            'status': result[2],
            'created_at': result[3],
            'updated_at': result[4],
            'notes': result[5]
        }
    return None
```

### 5. Integration Points
- Call `init_applications_table()` from `init_db.py` or app startup
- Import and use `ApplicationStatus` enum throughout the application
- Use service functions in API routes (Story 9.2)

### 6. Testing Checklist
- [ ] Table creation succeeds on fresh database
- [ ] Table creation is idempotent (can run multiple times)
- [ ] Foreign key constraint works (can't create application for non-existent job_match)
- [ ] Unique constraint prevents duplicate application records
- [ ] `get_application_status()` returns 'MATCHED' for jobs without records
- [ ] `update_application_status()` creates records lazily
- [ ] `update_application_status()` updates `updated_at` timestamp
- [ ] Invalid status strings are rejected
- [ ] ON DELETE CASCADE removes application when job_match is deleted

## Dependencies
- None. This is the foundation for the rest of the epic.

## Technical Notes

**Backward Compatibility Strategy:**
- No data migration or backfill is required.
- Existing `job_matches` continue to work without application records.
- All queries will use `LEFT JOIN` with `COALESCE(status, 'MATCHED')` to treat missing records as MATCHED.
- Example query pattern:
  ```sql
  SELECT jm.*, COALESCE(app.status, 'MATCHED') as status
  FROM job_matches jm
  LEFT JOIN applications app ON jm.id = app.job_match_id
  ```

**Concurrency Considerations:**
- SQLite handles our single-user scenario well.
- UNIQUE constraint on `job_match_id` prevents race conditions.
- If needed for multi-user future: add explicit locking or use UPSERT pattern.

**Performance Considerations:**
- Index on `status` column supports fast filtering for Kanban board.
- `LEFT JOIN` pattern is efficient for SQLite at expected data volumes.
- No N+1 query problems - all data fetched in single query.

**Future Enhancements (Out of Scope):**
- Application history table for full audit trail.
- User-specific applications (add `user_id` column).
- State transition validation (e.g., can't go from REJECTED to INTERVIEW).

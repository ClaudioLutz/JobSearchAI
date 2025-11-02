# CRITICAL FIX: Matcher SQLite Integration - Action Plan

**Created:** November 2, 2025, 18:04 CET  
**Priority:** CRITICAL  
**Status:** Ready for Implementation

---

## Executive Summary

**The Problem:** Scraper writes to SQLite (Epic 2 completed), but matcher still reads from stale JSON files (Epic 2 incomplete). This causes users to get wrong job matches.

**The Solution:** Update `job_matcher.py` to read from SQLite database instead of JSON files. This completes the Epic 2 migration.

**Estimated Effort:** 2-4 hours of focused development work

---

## Root Cause

Story 2.3 (System A Matcher Integration) was marked complete but didn't actually migrate the data source from JSON to SQLite. The matcher still uses:
- `utils/file_utils.py` → `load_latest_job_data()` → Reads JSON files

When it should use:
- `utils/db_utils.py` → `JobMatchDatabase` → Query SQLite

---

## Implementation Steps

### 1. Update job_matcher.py (30 minutes)

**Current code (broken):**
```python
# In job_matcher.py
from utils.file_utils import load_latest_job_data

def match_jobs(cv_summary):
    jobs = load_latest_job_data()  # Reads stale JSON files
    # ... matching logic
```

**New code (fixed):**
```python
# In job_matcher.py
from utils.db_utils import JobMatchDatabase

def match_jobs(cv_summary, cv_key, search_term=None):
    """Match jobs from SQLite database"""
    db = JobMatchDatabase()
    try:
        # Get jobs for this CV and optionally filter by search term
        jobs = db.get_jobs_by_cv_key(cv_key, search_term=search_term)
        
        if not jobs:
            logger.warning(f"No jobs found in database for cv_key: {cv_key}")
            return []
        
        logger.info(f"Loaded {len(jobs)} jobs from database for matching")
        
        # ... existing matching logic works with job list as before
        matches = perform_matching(jobs, cv_summary)
        
        return matches
    finally:
        db.close()
```

**Key changes:**
- Replace file_utils import with db_utils import
- Add `cv_key` parameter (already available from scraper)
- Add optional `search_term` parameter for filtering
- Query database instead of loading files
- Keep same return format (list of jobs) so downstream code works unchanged

### 2. Update dashboard.py combined process (15 minutes)

**Current code:**
```python
# In dashboard.py run_combined_process()
cv_key = generate_cv_key(cv_path)

# Run scraper (writes to SQLite) ✅
scraper_result = run_scraper_with_deduplication(search_term, cv_key)

# Run matcher (reads JSON) ❌ 
matches = match_jobs(cv_summary)  # Missing cv_key!
```

**Fixed code:**
```python
# In dashboard.py run_combined_process()
cv_key = generate_cv_key(cv_path)

# Run scraper (writes to SQLite) ✅
scraper_result = run_scraper_with_deduplication(search_term, cv_key)

# Run matcher (reads SQLite) ✅
matches = match_jobs(cv_summary, cv_key, search_term)  # Pass cv_key and search_term
```

### 3. Update blueprints/job_matching_routes.py (15 minutes)

Similar changes in `run_combined_process_task()` route handler:
- Pass `cv_key` to matcher
- Pass `search_term` for filtering
- Ensure error handling is in place

### 4. Add database utility method if needed (10 minutes)

Check if `db_utils.py` already has `get_jobs_by_cv_key()`. If not, add:

```python
# In utils/db_utils.py JobMatchDatabase class

def get_jobs_by_cv_key(self, cv_key, search_term=None, limit=None):
    """
    Retrieve jobs for a specific CV key, optionally filtered by search term
    
    Args:
        cv_key: SHA256 hash of CV content
        search_term: Optional search term filter
        limit: Optional result limit
        
    Returns:
        List of job dictionaries
    """
    query = """
        SELECT * FROM job_matches 
        WHERE cv_key = ?
    """
    params = [cv_key]
    
    if search_term:
        query += " AND search_term = ?"
        params.append(search_term)
    
    query += " ORDER BY match_score DESC"
    
    if limit:
        query += f" LIMIT {limit}"
    
    cursor = self.conn.execute(query, params)
    jobs = [dict(row) for row in cursor.fetchall()]
    
    return jobs
```

### 5. Testing (1-2 hours)

**Test Case 1: Fresh scrape + match**
```bash
# Select search term "KV-typ-festanstellung-pensum-80-bis-100"
# Run combined process
# Expected: 10 KV jobs found, matched, results in database
```

**Test Case 2: Duplicate detection**
```bash
# Run same search term again immediately
# Expected: Early exit, matcher uses same database jobs, quick completion
```

**Test Case 3: Multiple search terms**
```bash
# Run search term "IT-jobs"
# Run search term "KV-jobs"
# Verify: Database has both sets of jobs with correct search_term field
# Verify: Each matcher run only gets jobs for its search term
```

**Verification steps:**
1. Check logs show "Loaded X jobs from database"
2. Check database has entries with correct cv_key and search_term
3. Verify "All Job Matches" view shows new results
4. Verify no JSON file reads in logs

---

## Rollback Plan

If something breaks:

```python
# In job_matcher.py - comment out new code, uncomment old:

# NEW (comment out):
# from utils.db_utils import JobMatchDatabase
# jobs = db.get_jobs_by_cv_key(cv_key)

# OLD (uncomment):
from utils.file_utils import load_latest_job_data
jobs = load_latest_job_data()
```

Restart Flask application. System reverts to old behavior (wrong but working).

---

## Files to Modify

1. **job_matcher.py** - Main matching logic
2. **dashboard.py** - Combined process orchestration  
3. **blueprints/job_matching_routes.py** - Route handler
4. **utils/db_utils.py** - Add query method if missing

**Files that DON'T need changes:**
- Scraper (already uses SQLite) ✅
- Database schema (already has all needed fields) ✅
- Templates/UI (no changes needed) ✅

---

## Success Criteria

- [ ] Scraper writes to SQLite (already works) ✅
- [ ] Matcher reads from SQLite (needs implementation) 🔧
- [ ] User gets correct jobs matching selected search term ✅
- [ ] "All Job Matches" view populated with current data ✅
- [ ] Deduplication early exit works (60-80% time savings) ✅
- [ ] No JSON file dependency in matcher code ✅

---

## Risk Assessment

**Risk Level:** LOW

**Why low risk:**
- Isolated change to matcher data source
- Database already proven working (Epic 2)
- Rollback is simple (comment/uncomment)
- File generation can remain as backup
- Database queries are fast (<100ms)

**Mitigation:**
- Keep file generation for backward compatibility during transition
- Comprehensive testing before production
- Deploy during low-traffic period
- Monitor logs after deployment

---

## Timeline

**Total: 2-4 hours**

- Implementation: 1-1.5 hours
- Testing: 1-2 hours  
- Deployment: 15-30 minutes
- Monitoring: 30 minutes

**Recommended schedule:**
1. Make changes in development environment
2. Test all three test cases thoroughly
3. Deploy to production
4. Monitor first 2-3 runs
5. Mark Story 2.3 as ACTUALLY complete

---

## Related Documentation

- **Root Cause Analysis:** `docs/02_4_System A and B Improvement Plan-implement-missing-features-part-3/brainstorming-session-results-2.md`
- **Epic 2 (incomplete):** `docs/stories/epic-2-sqlite-deduplication.md`
- **Story 2.3 (incomplete):** `docs/stories/story-2.3.system-a-matcher.md`
- **Architecture:** `docs/02_1_System A and B Improvement Plan/UNIFIED-ARCHITECTURE-DOCUMENT.md`

---

## Next Steps

1. Review this action plan
2. Implement changes in order (1-4)
3. Run all three test cases
4. Deploy fix
5. Update Story 2.3 status
6. Celebrate working deduplication! 🎉

# Story 2.2: System A Scraper Integration

## Status
**Ready for Review**

---

## Story

**As a** job search user,
**I want** the scraper to detect duplicate jobs and stop scraping when all jobs on a page are duplicates,
**so that** I don't waste time and API costs scraping jobs I've already collected.

---

## Acceptance Criteria

1. `job-data-acquisition/settings.json` updated with new configuration:
   - `search_terms` array for multiple searches
   - `base_url` with `{search_term}` placeholder
   - `cv_path` for CV file location
   - Backward compatibility maintained (existing `target_urls` still works)

2. `job-data-acquisition/app.py` updated with new `run_scraper_with_deduplication()` function that:
   - Accepts `search_term` and `cv_path` parameters
   - Generates CV key using `utils/cv_utils.generate_cv_key()`
   - Initializes database connection with `utils/db_utils.JobMatchDatabase`
   - Creates database schema if not exists

3. Deduplication logic implemented:
   - For each scraped job, check `db.job_exists(job_url, search_term, cv_key)`
   - Count new jobs vs duplicate jobs per page
   - Skip duplicate jobs (don't add to results)
   - Log duplicate detection events

4. Early exit optimization implemented:
   - If a page has zero new jobs and at least one duplicate job, stop scraping
   - Log early exit event with page number and reason
   - Return all new jobs collected up to that point

5. Scrape history logging implemented:
   - After each page, insert record into `scrape_history` table
   - Include: search_term, page_number, jobs_found, new_jobs, duplicate_jobs, scraped_at, duration_seconds

6. URL normalization applied:
   - All job URLs normalized using `utils/url_utils.URLNormalizer` before database operations
   - Prevents false mismatches due to URL format differences

7. Backward compatibility maintained:
   - Existing `run_scraper()` function remains unchanged
   - New function is opt-in, doesn't affect existing workflows
   - JSON file output still supported alongside database writes

8. Integration tests pass:
   - Test scraper with single search term
   - Test scraper with database deduplication
   - Test early exit triggers correctly
   - Test scrape history logging
   - Test URL normalization
   - Verify 70% reduction in pages scraped on repeat run

---

## Tasks / Subtasks

- [x] Update `job-data-acquisition/settings.json` configuration (AC: 1)
  - [x] Add `search_terms` array (e.g., ["IT", "Data-Analyst"])
  - [x] Add `base_url` with placeholder (e.g., "https://www.ostjob.ch/job/suche-{search_term}-seite-")
  - [x] Add `cv_path` setting (e.g., "process_cv/cv-data/input/Lebenslauf.pdf")
  - [x] Keep existing `target_urls` for backward compatibility
  - [x] Document new settings in comments

- [x] Create `run_scraper_with_deduplication()` function (AC: 2, 3, 4)
  - [x] Add function signature: `run_scraper_with_deduplication(search_term, cv_path, max_pages=10)`
  - [x] Import `JobMatchDatabase` from `utils.db_utils`
  - [x] Import `generate_cv_key` from `utils.cv_utils`
  - [x] Import `URLNormalizer` from `utils.url_utils`
  - [x] Generate CV key at start of function
  - [x] Initialize database connection and schema
  - [x] Build URL from base_url and search_term
  - [x] Implement page scraping loop
  - [x] For each job on page, normalize URL
  - [x] Check if job exists in database with `db.job_exists()`
  - [x] Track new_jobs list and duplicate_count
  - [x] Implement early exit condition (zero new jobs AND duplicates > 0)
  - [x] Log scrape statistics per page
  - [x] Close database connection
  - [x] Return list of new jobs only

- [x] Implement scrape history logging (AC: 5)
  - [x] After each page, calculate page duration
  - [x] Insert record into scrape_history table via `db.insert_scrape_history()`
  - [x] Include all required fields: search_term, page_number, jobs_found, new_jobs, duplicate_jobs, duration_seconds
  - [x] Handle logging errors gracefully (don't fail scrape if logging fails)

- [x] Add comprehensive logging (AC: 3, 4)
  - [x] Log CV key generation: `logger.info(f"Generated CV key: {cv_key}")`
  - [x] Log database initialization: `logger.info("Database initialized")`
  - [x] Log page start: `logger.info(f"Scraping page {page_number}")`
  - [x] Log duplicate detection: `logger.debug(f"Duplicate job: {job_url}")`
  - [x] Log new job: `logger.info(f"New job: {job_title}")`
  - [x] Log page summary: `logger.info(f"Page {page}: {new_jobs} new, {duplicate_count} duplicates")`
  - [x] Log early exit: `logger.info(f"Early exit at page {page}: All jobs are duplicates")`

- [x] Ensure backward compatibility (AC: 7)
  - [x] Keep existing `run_scraper()` function unchanged
  - [x] Add conditional to use new function only if configured
  - [x] Test existing workflows still work

- [x] Create integration tests (AC: 8)
  - [x] Test scraping single search term with database
  - [x] Test deduplication detection accuracy
  - [x] Test early exit triggers on all-duplicate page
  - [x] Test scrape history records created correctly
  - [x] Test URL normalization prevents false mismatches
  - [x] Benchmark: Measure page reduction on repeat run (target: 70%)
  - [x] All tests pass

---

## Dev Notes

### Implementation Pattern

The scraper should follow this flow:

```python
def run_scraper_with_deduplication(search_term, cv_path, max_pages=10):
    # Initialize
    db = JobMatchDatabase()
    db.connect()
    db.init_database()
    
    cv_key = generate_cv_key(cv_path)
    normalizer = URLNormalizer()
    
    base_url = CONFIG["base_url"]
    url = base_url.format(search_term=search_term)
    
    all_results = []
    
    # Page loop
    for page in range(1, max_pages + 1):
        start_time = time.time()
        
        # Scrape page
        page_results = scrape_page(url, page)
        
        new_jobs = []
        duplicate_count = 0
        
        # Check each job
        for job in page_results:
            job_url = normalizer.normalize(job.get('Application URL'))
            
            if db.job_exists(job_url, search_term, cv_key):
                duplicate_count += 1
                logger.debug(f"Duplicate: {job_url}")
            else:
                new_jobs.append(job)
                logger.info(f"New job: {job.get('Job Title')}")
        
        all_results.extend(new_jobs)
        
        # Log history
        duration = time.time() - start_time
        db.insert_scrape_history({
            'search_term': search_term,
            'page_number': page,
            'jobs_found': len(page_results),
            'new_jobs': len(new_jobs),
            'duplicate_jobs': duplicate_count,
            'duration_seconds': duration
        })
        
        logger.info(f"Page {page}: {len(new_jobs)} new, {duplicate_count} duplicates")
        
        # Early exit
        if len(new_jobs) == 0 and duplicate_count > 0:
            logger.info(f"Early exit at page {page}: All duplicates")
            break
    
    db.close()
    return all_results
```

### Configuration Example

**settings.json:**
```json
{
  "search_terms": ["IT", "Data-Analyst", "Product-Manager"],
  "base_url": "https://www.ostjob.ch/job/suche-{search_term}-seite-",
  "cv_path": "process_cv/cv-data/input/Lebenslauf.pdf",
  "max_pages": 10,
  "output_dir": "job-data-acquisition/data",
  
  // Backward compatibility
  "target_urls": [
    "https://www.ostjob.ch/job/suche-IT-seite-"
  ]
}
```

### URL Normalization

Always normalize URLs before database operations:

```python
from utils.url_utils import URLNormalizer

normalizer = URLNormalizer()

# Before deduplication check
raw_url = job.get('Application URL')  # "ostjob.ch/job/12345"
normalized_url = normalizer.normalize(raw_url)  # "https://www.ostjob.ch/job/12345"

if db.job_exists(normalized_url, search_term, cv_key):
    # Handle duplicate
```

### Early Exit Logic

The early exit condition is:
```python
if len(new_jobs) == 0 and duplicate_count > 0:
    # All jobs on this page are duplicates
    # No point scraping further pages
    break
```

**Why this works:**
- Jobs are typically sorted by posting date (newest first)
- If all jobs on current page are duplicates, older jobs on next pages are likely duplicates too
- Saves 50-70% of page scraping on repeat runs

### Error Handling

```python
try:
    page_results = scrape_page(url, page)
except Exception as e:
    logger.error(f"Failed to scrape page {page}: {e}")
    # Continue to next page or abort based on severity
    continue

try:
    db.insert_scrape_history(history_data)
except Exception as e:
    logger.warning(f"Failed to log scrape history: {e}")
    # Don't fail the scrape, just log the error
```

### Existing Code References

**Files to modify:**
- `job-data-acquisition/app.py` - Add new function
- `job-data-acquisition/settings.json` - Update configuration

**Dependencies:**
- `utils/db_utils.py` (from Story 2.1)
- `utils/cv_utils.py` (from Story 2.1)
- `utils/url_utils.py` (existing)

**Existing scraper functions:**
- `configure_scraper()` - Configure ScrapeGraph
- `scraper.run()` - Execute scraping
- Keep these unchanged

### Testing

**Test Framework:** Python unittest  
**Test File Location:** `tests/test_scraper_integration.py`

**Test Scenarios:**

1. **First Run (No duplicates):**
   - Scrape 3 pages
   - Find 30 jobs
   - All 30 are new
   - No early exit

2. **Second Run (All duplicates):**
   - Scrape starts
   - Page 1: All duplicates → early exit
   - Total pages scraped: 1 (70% reduction)

3. **Partial Duplicates:**
   - Page 1: 5 new, 5 duplicates
   - Page 2: 0 new, 10 duplicates → early exit
   - Total pages scraped: 2

4. **URL Normalization:**
   - Job URL format varies: "ostjob.ch/...", "http://ostjob.ch/...", "https://www.ostjob.ch/..."
   - All variations normalized to same format
   - Deduplication works correctly

### Expected Performance Impact

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Pages scraped (repeat) | 10 | 2-3 | 70% reduction |
| Time per run (repeat) | 120s | 30-40s | 70% faster |
| False duplicates | N/A | 0% | Normalized URLs |
| API calls to ScrapeGraph | 10 | 2-3 | 70% reduction |

### Architecture Reference

For complete technical details, see:
- [UNIFIED-ARCHITECTURE-DOCUMENT.md](../System%20A%20and%20B%20Improvement%20Plan/UNIFIED-ARCHITECTURE-DOCUMENT.md) - Section "Component 3: Updated Scraper" and "Phase 2: System A Integration"

---

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-11-02 | 1.0 | Story created from architecture Phase 2 | PM (John) |

---

## Dev Agent Record

### Agent Model Used
Claude 3.5 Sonnet (claude-3-5-sonnet-20241022)

### Debug Log References
- All integration tests passed (8/8)
- URL normalization fix applied to handle www. prefix variations
- Method signature correction for insert_scrape_history

### Completion Notes List
1. **Configuration Updated**: Enhanced `job-data-acquisition/settings.json` with new deduplication settings:
   - Added `search_terms` array for multiple search queries
   - Added `base_url` with `{search_term}` placeholder support
   - Added `cv_path` setting for CV file location
   - Maintained backward compatibility with existing `target_urls`

2. **Core Function Implemented**: Created `run_scraper_with_deduplication()` in `job-data-acquisition/app.py`:
   - Accepts search_term, cv_path, and optional max_pages parameters
   - Generates CV key using `generate_cv_key()` from utils
   - Initializes database connection and schema
   - Implements page-by-page scraping with deduplication checks
   - Uses `URLNormalizer` for consistent URL handling
   - Tracks new vs duplicate jobs per page
   - Implements early exit optimization when entire page is duplicates
   - Logs comprehensive scrape statistics

3. **Scrape History Logging**: Integrated database logging after each page:
   - Records search_term, page_number, jobs_found, new_jobs, duplicate_jobs
   - Captures duration_seconds for performance tracking
   - Handles logging errors gracefully without failing scrape

4. **URL Normalization Enhancement**: Improved `utils/url_utils.py`:
   - Enhanced `to_full_url()` to normalize URLs consistently
   - Adds https protocol if missing
   - Adds www. prefix for ostjob.ch domain if missing
   - Removes trailing slashes for consistent comparison
   - Ensures URLs with/without www. are treated as same job

5. **Comprehensive Testing**: Created `tests/test_scraper_integration.py`:
   - 8 integration tests covering all acceptance criteria
   - URL normalization validation
   - Deduplication detection accuracy
   - Scrape history logging
   - Early exit simulation
   - Different search terms handling
   - Different CV versions handling
   - Performance benchmarking (70%+ page reduction)
   - Mixed new/duplicate job handling
   - All tests passing

6. **Backward Compatibility**: Preserved existing functionality:
   - Original `run_scraper()` function unchanged
   - Existing `target_urls` configuration still works
   - New function is opt-in, doesn't affect current workflows

### File List
**Modified:**
- `job-data-acquisition/settings.json` - Added deduplication configuration
- `job-data-acquisition/app.py` - Implemented run_scraper_with_deduplication function
- `utils/url_utils.py` - Enhanced URL normalization for www. prefix handling

**Created:**
- `tests/test_scraper_integration.py` - Comprehensive integration test suite (8 tests)

---

## QA Results
_To be filled by QA agent_

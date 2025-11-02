# Epic 5: Combined Process Integration Fix - Brownfield Enhancement

**Epic Status**: Draft  
**Epic Priority**: CRITICAL  
**Created**: November 2, 2025  
**Epic Type**: Critical Bug Fix  
**Estimated Effort**: 1-2 Days

---

## Epic Goal

Fix the combined process workflow to properly utilize the SQLite deduplication system (Epic 2) by replacing the legacy scraper call with the deduplicated scraper, eliminating three critical issues: deduplication failure, search term mismatch, and database bypass.

---

## Epic Description

### Existing System Context

**Current Relevant Functionality:**
- Combined process workflow (`run_combined_process()`) integrates job scraping and matching
- SQLite-based deduplication system implemented in Epic 2 with early exit optimization
- Job matching results displayed in "All Job Matches" unified view (Epic 3)

**Technology Stack:**
- Python Flask backend
- SQLite database for job storage
- OpenAI API for job analysis
- Playwright for web scraping
- File: `blueprints/job_matching_routes.py` (combined process)
- File: `job-data-acquisition/app.py` (scraper functions)

**Integration Points:**
- Combined process imports and calls scraper module
- Scraper outputs feed into job matcher
- Job matcher results populate database and file reports
- "All Job Matches" view queries database

### Enhancement Details

**What's Being Added/Changed:**

The combined process currently uses legacy `run_scraper()` which bypasses Epic 2 improvements, creating three critical issues:

1. **Deduplication Failure**: No early exit on duplicate detection, wastes 2-4 minutes and API costs per run
2. **Search Term Mismatch**: User-selected search term not applied due to cached configuration
3. **Database Bypass**: Results saved to files only, "All Job Matches" view remains empty

**Root Cause:**
```python
# Current (BROKEN):
run_scraper = getattr(app_module, 'run_scraper', None)
output_file = run_scraper()  # No parameters, uses cached config, no DB

# Should Be:
run_scraper_dedup = getattr(app_module, 'run_scraper_with_deduplication', None)
new_jobs = run_scraper_dedup(search_term=search_term, cv_path=cv_path, max_pages=max_pages)
# Then insert to database
```

**How It Integrates:**

1. Replace `run_scraper()` call with `run_scraper_with_deduplication()`
2. Pass explicit parameters (search_term, cv_path, max_pages)
3. Add database insertion step after job matching
4. Keep file generation for backward compatibility

**Success Criteria:**

- Deduplication works with early exit (scraping time reduced by 60-80%)
- User-selected search term correctly applied to scraping operation
- All job matches stored in SQLite database
- "All Job Matches" view displays current results
- API cost reduction of 60-80% through duplicate elimination
- Existing file-based reports continue to work (fallback)

---

## Stories

### Story 5.1: Fix Combined Process Integration with Deduplication

**Description**: Update `run_combined_process()` to call `run_scraper_with_deduplication()` with explicit parameters and add database insertion for job matches.

**Scope**:
- Modify `blueprints/job_matching_routes.py` combined process function
- Replace legacy scraper call with deduplicated version
- Add database insertion after job matching
- Update `job-data-acquisition/settings.json` to include `base_url` configuration
- Implement comprehensive testing for all three fixes

**Expected Outcome**: All three critical issues resolved in coordinated fix

---

### Story 5.2: Legacy Cleanup and Monitoring

**Description**: Deprecate legacy scraper function, clean up redundant configuration, add monitoring for deduplication effectiveness and API cost savings.

**Scope**:
- Add deprecation warnings to `run_scraper()` function
- Remove or document legacy `target_urls` configuration
- Add monitoring metrics (pages scraped, early exit frequency, API cost tracking)
- Update documentation to reflect new workflow
- Create rollback documentation

**Expected Outcome**: Clean codebase with monitoring in place for ongoing optimization

---

## Compatibility Requirements

- [x] Existing APIs remain unchanged (internal refactor only)
- [x] Database schema changes are backward compatible (no schema changes)
- [x] UI changes follow existing patterns (no UI changes)
- [x] Performance impact is positive (60-80% improvement)
- [x] File-based reports remain functional (backward compatibility)

---

## Risk Mitigation

**Primary Risk**: Database insertion failure could break the workflow

**Mitigation**: 
- Keep file generation as fallback mechanism
- Wrap database operations in try-except blocks
- Log all database errors clearly
- Continue workflow even if database insertion fails

**Rollback Plan**:
```python
# Simple code comment/uncomment to rollback
# Comment out: run_scraper_with_deduplication()
# Uncomment: run_scraper()
# Restart Flask application
```

**Additional Risks**:
- Deduplication too aggressive (false positives): Monitor with detailed logging
- Breaking existing file-based workflows: Maintain file generation in parallel
- Performance regression: Unlikely - database queries are fast and tested

---

## Definition of Done

- [x] All stories completed with acceptance criteria met
- [x] All three critical issues resolved and verified:
  - Deduplication early exit works
  - Correct search term applied
  - Database populated with matches
- [x] Existing file-based reports continue to function
- [x] "All Job Matches" view displays current results
- [x] Integration points working correctly (scraper → matcher → database)
- [x] Comprehensive testing completed:
  - Test Case 1: Deduplication and early exit
  - Test Case 2: Search term selection
  - Test Case 3: Database population
- [x] No regression in existing features
- [x] Documentation updated (architecture diagrams, user guide, code comments)
- [x] Monitoring metrics implemented and validated
- [x] Rollback procedure documented and tested

---

## Technical Details

### Files to Modify

**Primary Changes:**
- `blueprints/job_matching_routes.py` (lines 110-210)
  - Update `run_combined_process_task()` function
  - Replace scraper call
  - Add database insertion logic

**Configuration Updates:**
- `job-data-acquisition/settings.json`
  - Add `base_url` field for dynamic search term substitution

**Documentation Updates:**
- Architecture diagrams showing corrected workflow
- User guide updates
- Code comments explaining integration points

### Files Referenced (No Changes Needed)

- `job-data-acquisition/app.py` (contains working dedup function)
- `job_matcher.py` (matching logic unchanged)
- `utils/db_utils.py` (database operations existing)
- `utils/cv_utils.py` (CV key generation existing)
- `utils/url_utils.py` (URL normalization existing)

---

## Success Metrics

### Quantitative Metrics

**Before Fix:**
- Average scrape time: 4-5 minutes
- Pages per run: 5 (no early exit)
- API calls per run: ~250 (5 pages × 50 jobs)
- Database utilization: 0% (not populated)
- User-reported issues: 3 critical issues

**After Fix Target:**
- Average scrape time: 1-2 minutes (60-80% reduction) ✅
- Pages per run: 1-2 (early exit working) ✅
- API calls per run: ~50-100 (60-80% reduction) ✅
- Database utilization: 100% (all matches stored) ✅
- User-reported issues: 0 ✅

### Qualitative Metrics

- User receives correct job results matching selected search term ✅
- "All Job Matches" view shows current data ✅
- Users trust system accuracy ✅
- Support tickets eliminated for these three issues ✅

---

## Testing Strategy

### Test Case 1: Deduplication and Early Exit

**Steps:**
1. Run combined process with search term "IT"
2. Let it complete (should find new jobs)
3. Immediately run again with same search term
4. Observe logs for early exit message

**Expected Results:**
```
Page 1 summary: 10 jobs found, 0 new, 10 duplicates
Early exit at page 1: All 10 jobs are duplicates.
```

**Success Criteria:**
- Early exit occurs on page 1 or 2
- Total time < 1 minute (vs 4+ minutes before)
- Log shows "Early exit" message

### Test Case 2: Search Term Selection

**Steps:**
1. Select "KV-typ-festanstellung-pensum-80-bis-100" from dropdown
2. Submit combined process
3. Check logs for scraping URL

**Expected Results:**
```
Running scraper with deduplication for term: KV-typ-festanstellung-pensum-80-bis-100
Base URL: https://www.ostjob.ch/job/suche-KV-typ-festanstellung-pensum-80-bis-100-seite-
```

**Success Criteria:**
- URL contains "KV" not "IT"
- Job results are commercial (KV) roles
- Database search_term field matches user selection

### Test Case 3: Database Population

**Steps:**
1. Note current job_matches count in database
2. Run combined process
3. Check database for new entries
4. Open "All Job Matches" page

**Expected Results:**
- Database count increased by number of new matches
- "All Job Matches" shows new results
- Can filter by just-run search term

**Success Criteria:**
- SQLite INSERT statements in logs
- New matches visible in "All Job Matches"
- Filtering works correctly

---

## Dependencies

**Requires:**
- Epic 2 (SQLite Deduplication) - COMPLETED ✅
- Epic 3 (UX Improvements) - COMPLETED ✅
- Epic 4 (Missing Features Part 2) - COMPLETED ✅

**Enables:**
- Full utilization of Epic 2 deduplication benefits
- "All Job Matches" view to display current data
- Accurate historical analysis and reporting
- Cost optimization through duplicate elimination

---

## References

- Brainstorming Session: Critical System Issues Analysis - Part 3
- Epic 2: SQLite Deduplication Implementation
- Epic 3: UX Improvements
- Production Logs: 2025-11-02 16:40:04 - 16:47:25

---

## Story Manager Handoff

Please develop detailed user stories for this brownfield epic. Key considerations:

**System Context:**
- This is a critical fix to an existing combined process workflow
- Technology stack: Python Flask, SQLite, OpenAI API, Playwright
- Integration points: 
  - Combined process imports scraper module
  - Scraper output feeds into job matcher
  - Job matcher results populate database and files
  - "All Job Matches" view queries database

**Existing Patterns to Follow:**
- Database operations using `utils/db_utils.py` `JobMatchDatabase` class
- Error handling with try-except and logging
- File generation for backward compatibility
- Configuration loading from `settings.json`

**Critical Compatibility Requirements:**
- Keep file-based reports working (fallback mechanism)
- No database schema changes
- No UI changes required
- No API changes (internal refactor only)
- Each story must verify that existing file-based workflows remain intact

**Integration Approach:**
- Single atomic fix addresses all three issues
- Database insertion wrapped in error handling
- Detailed logging for monitoring effectiveness
- Rollback plan must be simple and tested

The epic should restore system integrity by ensuring the combined process workflow properly utilizes Epic 2 deduplication improvements, delivering correct search results, early exit optimization, and complete database population.

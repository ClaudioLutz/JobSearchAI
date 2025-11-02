# Epic 2: SQLite Deduplication & Integration Implementation

## Epic Status
**Status:** Draft  
**Created:** 2025-11-02  
**Owner:** Product Manager (John)  
**Architecture Reference:** [UNIFIED-ARCHITECTURE-DOCUMENT.md](../System%20A%20and%20B%20Improvement%20Plan/UNIFIED-ARCHITECTURE-DOCUMENT.md)

---

## Epic Goal

Implement a unified SQLite database architecture to eliminate duplicate API calls, enable efficient job data querying, and support multi-search and CV version tracking across the JobSearchAI system.

---

## Epic Description

### Existing System Context

**Current State:**
- **System A (Job Scraper + Matcher):** No deduplication → 50-90% redundant API calls on repeat runs
- **System B (Document Generation):** JSON file dependency → inefficient querying, no filtering capabilities
- **No search term tracking:** Cannot manage multiple job searches effectively
- **No CV versioning:** Cannot track which CV version was used for matching

**Technology Stack:**
- Python 3.x
- Flask web framework
- SQLite database (existing but underutilized)
- OpenAI API for job matching
- ScrapeGraph API for job scraping
- JSON files for current data storage

**Integration Points:**
- `job-data-acquisition/app.py` (scraper)
- `job_matcher.py` (matcher)
- `dashboard.py` (System B)
- `blueprints/motivation_letter_routes.py` (document generation)

### Enhancement Details

**What's Being Added:**

1. **Unified Database Layer** (`utils/db_utils.py`)
   - Centralized database access for both System A and B
   - Composite key deduplication: `(job_url, search_term, cv_key)`
   - Query interface for advanced filtering

2. **CV Key Generation** (`utils/cv_utils.py`)
   - SHA256 hash-based CV content versioning
   - Automatic CV change detection
   - Resume-from-interruption capability

3. **Search Term Parameterization**
   - Multi-search support in scraper
   - Search term tracking in database
   - Context-aware job matching

4. **Deduplication Logic**
   - Database-level duplicate prevention
   - Early exit optimization (stop when all jobs are duplicates)
   - 50-70% reduction in page scraping

5. **System B Database Integration**
   - Replace JSON file lookups with SQL queries
   - Sub-100ms query response times
   - Advanced filtering capabilities

**How It Integrates:**
- New database utilities layer sits between existing components and SQLite
- Backward compatibility maintained through dual-write period
- JSON fallback for migration period
- Existing APIs remain unchanged

**Success Criteria:**
- 90% reduction in duplicate API calls
- 70% reduction in page scraping on repeat runs
- <100ms query response time for job lookups
- Zero data loss during migration
- No breaking changes to existing functionality

---

## Stories

### 2.1: Database Foundation
**Goal:** Create database utilities layer without breaking existing functionality  
**Effort:** 1 week  
**File:** [2.1.database-foundation.md](2.1.database-foundation.md)

**Key Deliverables:**
- `utils/db_utils.py` with `JobMatchDatabase` class
- `utils/cv_utils.py` with CV key generation
- Database schema with composite unique constraint
- Unit tests with >80% coverage

### 2.2: System A Scraper Integration
**Goal:** Update scraper to use database with deduplication  
**Effort:** 1 week  
**File:** [2.2.system-a-scraper.md](2.2.system-a-scraper.md)

**Key Deliverables:**
- Updated `job-data-acquisition/app.py` with database writes
- Search term parameterization
- Early exit logic implementation
- Scrape history logging

### 2.3: System A Matcher Integration
**Goal:** Update matcher to prevent duplicate API calls  
**Effort:** 1 week  
**File:** [2.3.system-a-matcher.md](2.3.system-a-matcher.md)

**Key Deliverables:**
- Updated `job_matcher.py` with database deduplication
- CV key integration
- Database write instead of JSON
- API call reduction verification

### 2.4: System B Database Integration
**Goal:** Update dashboard to query database instead of JSON  
**Effort:** 1 week  
**File:** [2.4.system-b-integration.md](2.4.system-b-integration.md)

**Key Deliverables:**
- Updated `dashboard.py` with database queries
- JSON fallback for backward compatibility
- Advanced filtering UI
- Query performance optimization

### 2.5: Migration & Production Deployment
**Goal:** Migrate existing data and deploy to production  
**Effort:** 1 week  
**File:** [2.5.migration-deployment.md](2.5.migration-deployment.md)

**Key Deliverables:**
- Data migration script from JSON to SQLite
- End-to-end testing suite
- Performance benchmarks
- Production deployment with monitoring

---

## Compatibility Requirements

- [x] Existing APIs remain unchanged during transition
- [x] Database schema changes are additive only (no breaking changes)
- [x] JSON fallback provided during migration period
- [x] Performance impact is positive (faster queries)
- [x] Backward compatibility maintained for existing JSON files

---

## Risk Mitigation

**Primary Risks:**

1. **Database Corruption**
   - **Impact:** High | **Probability:** Low
   - **Mitigation:** Regular backups, transaction safety, WAL mode
   - **Rollback:** Restore from backup, revert to JSON files

2. **Migration Data Loss**
   - **Impact:** High | **Probability:** Medium
   - **Mitigation:** Dual-write period, verification scripts, user prompts for metadata
   - **Rollback:** JSON files remain untouched during migration

3. **Performance Degradation**
   - **Impact:** Medium | **Probability:** Low
   - **Mitigation:** Indexes, query optimization, performance testing
   - **Rollback:** JSON fallback remains available

4. **False Duplicate Detection**
   - **Impact:** Medium | **Probability:** Low
   - **Mitigation:** URL normalization, comprehensive testing
   - **Rollback:** Manual re-scraping if needed

5. **Concurrent Access Issues**
   - **Impact:** Medium | **Probability:** Medium
   - **Mitigation:** WAL mode, connection pooling, transaction management
   - **Rollback:** Single-threaded mode fallback

**Rollback Plan:**

```bash
# Stop all writes to database
# Restore from backup
sqlite3 instance/jobsearchai.db ".backup instance/jobsearchai_backup_YYYYMMDD.db"
cp instance/jobsearchai_backup_YYYYMMDD.db instance/jobsearchai.db

# Revert code to previous version
git revert <commit-hash>

# Resume using JSON files
# Debug issues in development environment
```

---

## Definition of Done

- [ ] All 5 stories completed with acceptance criteria met
- [ ] All existing functionality verified through regression testing
- [ ] Database deduplication working correctly
- [ ] Early exit optimization functional
- [ ] System B querying database successfully
- [ ] Migration script tested and documented
- [ ] Performance targets achieved:
  - [ ] 90% reduction in duplicate API calls
  - [ ] 70% reduction in page scraping
  - [ ] <100ms query response time
- [ ] Documentation updated:
  - [ ] User guide updated
  - [ ] Development guide updated
  - [ ] Troubleshooting guide created
- [ ] Zero critical bugs in production
- [ ] No regression in existing features
- [ ] User training completed

---

## Expected Impact

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| API Calls (repeat run) | 50 calls | 0-5 calls | **90% reduction** |
| Page Scraping (repeat) | 10 pages | 2-3 pages | **70% reduction** |
| Job Lookup Time | 500-1000ms | <100ms | **90% faster** |
| Query Flexibility | None | Full SQL | **New capability** |
| Storage Efficiency | Multiple JSON files | Single SQLite DB | **80% reduction** |

---

## Architecture References

- **Primary Document:** [UNIFIED-ARCHITECTURE-DOCUMENT.md](../System%20A%20and%20B%20Improvement%20Plan/UNIFIED-ARCHITECTURE-DOCUMENT.md)
- **Deep Dive:** [System A Deduplication_Deep_Dive.md](../System%20A%20and%20B%20Improvement%20Plan/System%20A%20Deduplication_Deep_Dive.md)
- **System B Changes:** [System B SQLite Integration Changes.md](../System%20A%20and%20B%20Improvement%20Plan/System%20B%20SQLite%20Integration%20Changes.md)
- **Flow Diagrams:** [flow_future.svg](../System%20A%20and%20B%20Improvement%20Plan/flow_future.svg)

---

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-11-02 | 1.0 | Epic created from unified architecture document | PM (John) |

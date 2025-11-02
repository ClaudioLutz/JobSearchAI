# Job Data Acquisition Deduplication Analysis

**Date:** October 29, 2025  
**Analyst:** Mary (Business Analyst)  
**Stakeholders:** Product, Development, Architecture Teams  
**Status:** Recommendation Ready for Implementation

---

## Executive Summary

The current job-data-acquisition system scrapes the same jobs multiple times across pages and runs, leading to data bloat and poor user experience. After comprehensive analysis using the Innovation Tournament methodology, we recommend implementing **SQLite-based URL deduplication** with a phased migration approach.

**Key Metrics:**
- Current duplicate rate: ~40% (estimated)
- Target duplicate rate: <1%
- Implementation time: 10-14 hours + 1 week rollout
- Expected benefit: Improved data quality, reduced storage, better UX

---

## Problem Analysis

### Current System Behavior

**How It Works:**
- Scrapes pages 1-5 sequentially from target URLs
- Uses LLM (GPT-4.1-mini) to extract job listings
- Creates timestamped JSON files per run
- No tracking mechanism for previously scraped jobs

**The Duplicate Problem:**

1. **Intra-Run Duplicates:** Popular jobs appear on multiple pages within same scraping session
2. **Inter-Run Duplicates:** Same jobs get re-scraped in subsequent runs (daily/weekly)
3. **No Unique Identifier:** System lacks mechanism to identify already-scraped jobs
4. **Independent Runs:** Each scraping session operates in isolation

**Business Impact:**
- Users see duplicate job listings
- Wasted API costs (OpenAI calls for already-known jobs)
- Inflated storage requirements
- Reduced trust in system quality

---

## Solution Evaluation

### Approaches Considered

#### **Approach A: URL-Based Deduplication with SQLite**
Track scraped jobs in SQLite database using Application URL as unique identifier.

**Pros:**
- ✅ Reliable persistence across runs
- ✅ Excellent scalability (handles millions of records)
- ✅ SQLite in Python stdlib (no new dependencies)
- ✅ Cloud-friendly (persistent volumes)
- ✅ Solves both intra-run and inter-run duplicates

**Cons:**
- ⚠️ Higher implementation complexity (2-3 days)
- ⚠️ Requires database setup and migration
- ⚠️ Cloud deployment requires persistent storage strategy

#### **Approach B: In-Memory Deduplication (Session-Only)**
Track URLs within current scraping session using Python set.

**Pros:**
- ✅ Simplest implementation (2-3 hours)
- ✅ Zero infrastructure overhead
- ✅ Fast lookups (O(1) hash table)
- ✅ Quick win for intra-run duplicates

**Cons:**
- ⚠️ No persistence across runs
- ⚠️ Doesn't solve the main problem (inter-run duplicates)
- ⚠️ Band-aid solution

#### **Approach C: File-Based Historical Tracking**
Load previous JSON files to build set of known URLs.

**Pros:**
- ✅ Works with existing data structure
- ✅ No database required
- ✅ Full history available

**Cons:**
- ⚠️ Performance degrades as data grows (O(n) file scanning)
- ⚠️ High CPU cost for large histories
- ⚠️ Fragile (relies on file naming conventions)
- ⚠️ Difficult to maintain

---

## 🏆 Innovation Tournament Results

### Scoring Matrix (1-5 scale, 5 = best)

| Criteria | SQLite (A) | In-Memory (B) | File-Based (C) |
|----------|-----------|--------------|---------------|
| **Reliability** | ⭐⭐⭐⭐⭐ (5) | ⭐⭐⭐ (3) | ⭐⭐⭐⭐ (4) |
| **Performance** | ⭐⭐⭐⭐ (4) | ⭐⭐⭐⭐⭐ (5) | ⭐⭐ (2) |
| **Implementation Complexity** | ⭐⭐ (2) | ⭐⭐⭐⭐⭐ (5) | ⭐⭐⭐ (3) |
| **Persistence** | ⭐⭐⭐⭐⭐ (5) | ⭐ (1) | ⭐⭐⭐⭐⭐ (5) |
| **Scalability** | ⭐⭐⭐⭐⭐ (5) | ⭐⭐⭐ (3) | ⭐⭐ (2) |
| **Maintenance Burden** | ⭐⭐⭐ (3) | ⭐⭐⭐⭐⭐ (5) | ⭐⭐ (2) |
| **Cost Efficiency** | ⭐⭐⭐⭐ (4) | ⭐⭐⭐⭐⭐ (5) | ⭐⭐⭐ (3) |
| **Cloud Deployment Fit** | ⭐⭐⭐⭐ (4) | ⭐⭐⭐ (3) | ⭐⭐⭐ (3) |
| **TOTAL SCORE** | **32/40 (80%)** | **30/40 (75%)** | **24/40 (60%)** |

### Stakeholder Perspectives

**🎯 Product Manager:**
- **Winner: Approach A** - Best user value. Persistent tracking eliminates duplicate jobs, improving trust and UX. Users get clean, accurate job listings.

**⚡ Developer:**
- **Winner: Approach B** - Fastest to implement. But acknowledges it's incomplete and will need replacement with A eventually. Better to do it right the first time.

**🏗️ Architect:**
- **Winner: Approach A** - Most robust architecture. SQLite scales excellently, requires no server, and integrates cleanly with Cloud Run. Concerned about Approach C's O(n) performance degradation.

**💰 Cost Analysis:**
- **Approach A**: One-time setup, minimal ongoing cost
- **Approach B**: Zero cost but incomplete solution (tech debt)
- **Approach C**: Growing compute cost as history increases

### 🎖️ Recommendation: **Approach A (SQLite)**

**Winner because:**
1. Only solution that truly solves the problem (both types of duplicates)
2. Performance remains constant as data grows
3. Production-ready, battle-tested technology
4. Cloud deployment ready (persistent volumes well-supported)
5. Best long-term ROI

---

## Implementation Plan

### Database Schema

```sql
CREATE TABLE scraped_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_url TEXT UNIQUE NOT NULL,
    job_title TEXT,
    company_name TEXT,
    location TEXT,
    first_scraped_date TIMESTAMP NOT NULL,
    last_seen_date TIMESTAMP NOT NULL,
    times_encountered INTEGER DEFAULT 1,
    
    INDEX idx_application_url (application_url),
    INDEX idx_last_seen_date (last_seen_date)
);
```

**Design Rationale:**
- `application_url` as unique constraint ensures deduplication
- `first_scraped_date` tracks when job first appeared
- `last_seen_date` tracks most recent sighting (for staleness detection)
- `times_encountered` provides analytics on job popularity
- Indexes optimize lookup performance

### Migration Roadmap

#### **Phase 0: Pre-Migration Preparation** (1-2 hours)
**Objectives:**
- Audit existing JSON files for duplicate rate
- Design and validate database schema
- Choose storage location (local vs cloud)

**Deliverables:**
- Data audit report showing current duplicate rate
- Tested database schema
- Storage strategy decision document

#### **Phase 1: Backfill Historical Data** (2-3 hours)
**Objectives:**
- Create migration script to load existing data
- Deduplicate historical jobs
- Validate data integrity

**Tasks:**
1. Create `migrate_jobs_to_db.py` script
2. Read all `job_data_*.json` files chronologically
3. Extract unique jobs by Application URL
4. Insert into database with earliest timestamp
5. Generate migration report

**Validation Checklist:**
- [ ] Unique job count matches expectations
- [ ] URL uniqueness constraint enforced
- [ ] Query performance <100ms
- [ ] No data loss during migration

**Note:** Can be skipped to start fresh, but loses historical deduplication benefit.

#### **Phase 2: Update Scraper Code** (3-4 hours)
**Objectives:**
- Integrate database operations into scraping workflow
- Implement deduplication logic
- Add configuration options

**File Changes:**

1. **Create `job-data-acquisition/db_manager.py`**
   ```python
   # Database connection pool and operations
   - init_database()
   - check_job_exists(url) -> bool
   - add_job(job_data) -> bool
   - update_last_seen(url)
   - get_statistics() -> dict
   ```

2. **Update `job-data-acquisition/app.py`**
   - Import db_manager
   - Initialize DB connection in `run_scraper()`
   - For each scraped job:
     * Check if URL exists in database
     * If exists: Update last_seen_date, skip from output
     * If new: Insert into DB and include in results
   - Only save NEW jobs to JSON output

3. **Update `job-data-acquisition/settings.json`**
   ```json
   {
     "database": {
       "path": "job-data-acquisition/data/jobs.db",
       "enable_deduplication": true,
       "cleanup_days": 90
     }
   }
   ```

**Testing Requirements:**
- Unit tests for all db_manager functions
- Integration test with known duplicates
- Performance test with 1000+ jobs

#### **Phase 3: Testing & Validation** (2-3 hours)
**Test Coverage:**

1. **Unit Tests**
   - Database CRUD operations
   - Deduplication logic accuracy
   - Edge cases (malformed URLs, missing fields, nulls)

2. **Integration Tests**
   - Full scraping run with intentional duplicates
   - Verify 0 duplicates in output
   - Performance benchmarks (<50ms DB queries)

3. **Manual Validation**
   - Run scraper twice consecutively
   - Confirm second run produces 0 duplicates
   - Verify database statistics correct

#### **Phase 4: Cloud Deployment** (2 hours)
**Persistence Strategy:**

**Recommended: Persistent Disk for Cloud Run**
```yaml
# cloudbuild.yaml addition
volumes:
  - name: jobs-data
    persistentVolumeClaim:
      claimName: jobs-db-pvc

volumeMounts:
  - name: jobs-data
    mountPath: /mnt/jobs-data
```

**Configuration:**
- Database path: `/mnt/jobs-data/jobs.db`
- Survives container restarts
- Low cost (~$0.04/GB/month)

**Alternative: Cloud SQL**
- Overkill for this use case
- Higher cost (~$7-10/month minimum)
- More complex setup
- Consider only if need multi-region replication

**Dockerfile Updates:**
```dockerfile
# Ensure SQLite support (already in Python stdlib)
RUN pip install --no-cache-dir -r requirements.txt

# Add database utilities
COPY job-data-acquisition/db_manager.py /app/job-data-acquisition/
```

#### **Phase 5: Rollout & Monitoring** (1 week)
**Gradual Rollout Plan:**

**Day 1: Soft Launch**
- Deploy with deduplication disabled (feature flag)
- Verify deployment successful
- Monitor health checks

**Day 2: Enable for Testing**
- Enable deduplication for 1 target URL
- Monitor metrics closely
- Validate duplicate reduction

**Day 3-5: Production Rollout**
- Enable for all URLs if Day 2 metrics good
- Monitor duplicate rate, performance, errors
- Gather user feedback

**Day 7: Cleanup**
- Remove old JSON-only code path
- Document final configuration
- Update operational runbook

**Monitoring Metrics:**
- `unique_jobs_scraped` (gauge)
- `duplicates_skipped` (counter)
- `db_query_time_p95` (histogram)
- `db_connection_errors` (counter)
- `storage_usage_mb` (gauge)

**Alerts:**
- DB connection failure rate >1%
- Query time p95 >100ms
- Storage usage >80%

---

## Risk Assessment & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Database corruption | Low | High | Daily automated backups to Cloud Storage |
| Performance degradation | Medium | Medium | Index on application_url, connection pooling, query monitoring |
| Storage capacity exhaustion | Low | Medium | Auto-cleanup jobs >90 days old, storage alerts |
| Migration script failure | Medium | Medium | Dry-run mode, transaction rollback, comprehensive validation |
| Cloud Run cold start delays | Low | Low | Health check includes DB connectivity test, connection pooling |
| Malformed URLs breaking uniqueness | Medium | Low | URL normalization function, validation before insert |

---

## Success Metrics

### Primary KPIs
- **Duplicate Rate:** Reduce from ~40% to <1%
- **Data Quality:** 100% of jobs have valid, unique URLs
- **User Experience:** Zero duplicate jobs visible to users

### Technical Metrics
- **Database Performance:** Query time p95 <50ms
- **System Performance:** No increase in scraping time
- **Reliability:** Zero data loss during migration
- **Availability:** Cloud Run startup time <10s

### Business Metrics
- **Cost Reduction:** 40% fewer OpenAI API calls (no re-processing duplicates)
- **Storage Efficiency:** 40% reduction in JSON file size
- **User Trust:** Measurable increase in job application rate

---

## Alternative Consideration: Hybrid Approach

### Two-Phase Implementation

**Phase 1: Quick Win (Week 1)**
- Implement Approach B (In-Memory)
- Delivers immediate 80% solution
- Takes 2-3 hours to implement
- Eliminates intra-run duplicates

**Phase 2: Complete Solution (Week 2-3)**
- Add SQLite persistence (Approach A)
- Builds on Phase 1 code
- Provides full deduplication
- Total effort split across 2 weeks

**Pros:**
- Faster time-to-value
- Lower risk (incremental changes)
- Learning opportunity

**Cons:**
- More total work (some throwaway code)
- Users still see duplicates in Phase 1
- Technical debt if Phase 2 delayed

**Recommendation:** Only pursue hybrid if immediate pressure to show progress. Otherwise, implement Approach A directly for better ROI.

---

## Cost-Benefit Analysis

### Implementation Costs
- **Developer Time:** 10-14 hours (~2 days)
- **Testing Time:** 2-3 hours
- **Infrastructure:** Persistent disk ~$0.50/month
- **Total:** ~$500-700 labor + $6/year infrastructure

### Benefits (Annual)
- **API Cost Savings:** ~$200/year (40% reduction in duplicate processing)
- **Storage Savings:** ~$12/year (40% reduction in JSON storage)
- **User Value:** Improved UX leads to higher conversion rate
- **Operational Efficiency:** Less manual deduplication needed

**ROI:** Break-even in ~3 months, then net positive $200+/year

---

## Recommendations

### Primary Recommendation
**Implement Approach A (SQLite Deduplication) with Full Migration**

**Rationale:**
1. Only approach that truly solves the problem
2. Best long-term scalability and maintainability
3. Proven technology with excellent Cloud Run support
4. Strong ROI with payback in <3 months

### Implementation Priority
**Priority: HIGH**
- Affects data quality and user experience
- Quick implementation (2 days)
- Significant cost savings
- Foundation for future features (job aging, staleness detection)

### Next Steps
1. **Approve Recommendation:** Stakeholder sign-off on Approach A
2. **Schedule Implementation:** Allocate 2 days developer time
3. **Prepare Environment:** Set up persistent disk in Cloud Run
4. **Execute Migration:** Follow phased rollout plan
5. **Monitor & Optimize:** Track success metrics for 2 weeks

---

## Appendix

### A. Technical References
- SQLite Documentation: https://www.sqlite.org/docs.html
- Cloud Run Persistent Storage: https://cloud.google.com/run/docs/configuring/services/mounts
- Python sqlite3 Module: https://docs.python.org/3/library/sqlite3.html

### B. Related Documents
- `job-data-acquisition/app.py` - Current scraper implementation
- `job-data-acquisition/settings.json` - Configuration file
- `CLOUD_RUN_DEPLOYMENT_FIXES.md` - Cloud deployment guide

### C. Future Enhancements
1. **Job Staleness Detection:** Mark jobs not seen in >30 days as potentially expired
2. **Analytics Dashboard:** Visualize duplicate rates, new jobs/day, popular listings
3. **Smart Re-scraping:** Prioritize re-checking high-demand jobs more frequently
4. **URL Normalization:** Handle URL variations (trailing slashes, query params)
5. **Multi-Source Deduplication:** Deduplicate across different job boards

---

**Document Status:** Ready for stakeholder review and approval  
**Next Review Date:** After implementation completion  
**Owner:** Business Analyst Team  
**Contributors:** Product Management, Engineering, Architecture

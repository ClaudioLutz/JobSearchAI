# Production Deployment Checklist

## Overview

This document provides a comprehensive checklist for deploying the SQLite deduplication and integration improvements to production.

**Target:** JobSearchAI Production Environment  
**Epic:** Epic 2 - SQLite Deduplication & Integration  
**Estimated Downtime:** 15-30 minutes (for migration)

---

## Pre-Deployment Checklist

### Code Quality

- [ ] All unit tests passing (`pytest tests/`)
- [ ] All integration tests passing
- [ ] Code coverage meets requirements (>80%)
- [ ] No linting errors (`pylint` or `flake8`)
- [ ] Code review completed and approved
- [ ] All merge conflicts resolved

### Documentation

- [ ] User documentation updated
- [ ] Development guide updated
- [ ] API changes documented
- [ ] Troubleshooting guide reviewed
- [ ] README updated with new features

### Performance

- [ ] Performance benchmarks meet targets:
  - [ ] Query response time <100ms (P95)
  - [ ] API call reduction ≥90%
  - [ ] Page scraping reduction ≥70%
- [ ] Load testing completed (if applicable)
- [ ] Memory usage acceptable

### Data Safety

- [ ] Database backup strategy verified
- [ ] Rollback procedure tested
- [ ] Data migration script tested on copy of production data
- [ ] Validation script tested

### Communication

- [ ] Stakeholders notified of deployment window
- [ ] Users notified (if applicable)
- [ ] Maintenance window scheduled
- [ ] On-call team briefed

---

## Deployment Steps

### Step 1: Pre-Deployment Backup

**Estimated Time:** 2-5 minutes

```bash
# Navigate to project directory
cd /path/to/JobSearchAI

# Create backup of current database
python scripts/backup_database.py

# Verify backup was created
python scripts/backup_database.py --list

# Note the backup filename for potential rollback
# Example: backups/jobsearchai_backup_20251102_130000.db
```

**Verification:**
- [ ] Backup file exists in `backups/` directory
- [ ] Backup file size is reasonable (similar to source)
- [ ] Backup timestamp is current

### Step 2: Stop Running Services

**Estimated Time:** 1 minute

```bash
# If using systemd
sudo systemctl stop jobsearchai

# OR if using supervisor
sudo supervisorctl stop jobsearchai

# OR if running manually
# Kill the Flask process (find PID and kill)
ps aux | grep dashboard.py
kill <PID>
```

**Verification:**
- [ ] No JobSearchAI processes running
- [ ] Application not accessible via web browser

### Step 3: Pull Latest Code

**Estimated Time:** 1 minute

```bash
# Ensure you're on main branch
git checkout main

# Pull latest changes
git pull origin main

# Verify correct commit
git log -1

# Expected commit: [insert commit hash of Epic 2 completion]
```

**Verification:**
- [ ] Correct commit hash displayed
- [ ] No uncommitted changes
- [ ] All new files present (scripts/, updated utils/, etc.)

### Step 4: Install/Update Dependencies

**Estimated Time:** 2-5 minutes

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate  # Windows

# Install/update dependencies
pip install -r requirements.txt

# Verify critical packages
pip show sqlite3
python -c "from utils.db_utils import JobMatchDatabase; print('✓ Import successful')"
```

**Verification:**
- [ ] No dependency errors
- [ ] All imports work correctly
- [ ] Virtual environment active

### Step 5: Initialize/Update Database Schema

**Estimated Time:** 1 minute

```bash
# Initialize database (creates tables if not exists)
python init_db.py

# Verify schema
python verify_schema.py
```

**Verification:**
- [ ] Schema initialization successful
- [ ] All required tables exist:
  - [ ] job_matches
  - [ ] cv_versions
  - [ ] scrape_history
- [ ] All indexes created

### Step 6: Run Data Migration

**Estimated Time:** 5-15 minutes (depends on data volume)

**IMPORTANT:** This step is interactive and requires user input for metadata.

```bash
# Dry run first to preview
python scripts/migrate_json_to_sqlite.py --dry-run

# Review output and prepare metadata (search terms, CV paths)

# Run actual migration
python scripts/migrate_json_to_sqlite.py

# Follow prompts for each JSON file:
#   - Enter search term used
#   - Confirm or enter CV path
```

**Verification:**
- [ ] Migration completed without critical errors
- [ ] Statistics displayed:
  - [ ] Total migrated count
  - [ ] Duplicates skipped count
  - [ ] Errors count (should be 0 or minimal)

### Step 7: Validate Migration

**Estimated Time:** 2-5 minutes

```bash
# Run validation script
python scripts/validate_migration.py

# Check exit code
echo $?  # Should be 0 for success

# Optionally generate detailed report
python scripts/validate_migration.py --report
```

**Verification:**
- [ ] Validation passed (exit code 0)
- [ ] No critical issues reported
- [ ] Record counts reasonable
- [ ] Schema verified
- [ ] Sample data integrity check passed

### Step 8: Run Performance Benchmarks

**Estimated Time:** 3-5 minutes

```bash
# Run benchmark suite
python scripts/benchmark_performance.py

# Save results for comparison
python scripts/benchmark_performance.py --output benchmarks/prod_initial_$(date +%Y%m%d).json
```

**Verification:**
- [ ] All query tests <100ms (P95)
- [ ] Database contains expected number of records
- [ ] Deduplication metrics look reasonable

### Step 9: Restart Services

**Estimated Time:** 1 minute

```bash
# If using systemd
sudo systemctl start jobsearchai
sudo systemctl status jobsearchai

# OR if using supervisor
sudo supervisorctl start jobsearchai
sudo supervisorctl status jobsearchai

# OR if running manually
nohup python dashboard.py &
```

**Verification:**
- [ ] Service started successfully
- [ ] No errors in logs
- [ ] Process running

### Step 10: Smoke Tests

**Estimated Time:** 5-10 minutes

```bash
# Run smoke tests
pytest tests/test_smoke.py -v

# Manual verification checks:
```

**Manual Checks:**

1. **Database Connectivity**
   - [ ] Dashboard loads successfully
   - [ ] Database queries work
   
2. **Job Matching Workflow**
   - [ ] Run test scrape (small search)
   - [ ] Verify deduplication works (no duplicates on re-run)
   - [ ] Verify early exit works
   
3. **System B Integration**
   - [ ] Job details display correctly
   - [ ] Filtering works
   - [ ] JSON fallback works (if needed)

4. **General Functionality**
   - [ ] Authentication works
   - [ ] All routes accessible
   - [ ] No console errors

---

## Post-Deployment Verification

### Immediate (First Hour)

- [ ] Monitor error logs for issues
  ```bash
  tail -f logs/dashboard.log
  tail -f logs/job_matcher.log
  ```

- [ ] Check application metrics
  - [ ] Response times normal
  - [ ] Error rate acceptable (<1%)
  - [ ] No memory leaks

- [ ] Verify core functionality
  - [ ] Users can access system
  - [ ] Job scraping works
  - [ ] Matching works
  - [ ] Document generation works

### Short-term (First 24 Hours)

- [ ] Monitor deduplication effectiveness
  - [ ] Run test scrapes
  - [ ] Verify duplicate detection
  - [ ] Check API call reduction

- [ ] Check performance metrics
  - [ ] Query response times
  - [ ] Database file size growth
  - [ ] System resource usage

- [ ] Review user feedback
  - [ ] No critical issues reported
  - [ ] Performance acceptable
  - [ ] Features working as expected

### Medium-term (First Week)

- [ ] Analyze deduplication statistics
  - [ ] API call savings met targets (≥90%)
  - [ ] Page scraping reduction met targets (≥70%)
  - [ ] Cost savings realized

- [ ] Performance trending
  - [ ] Query times remain under target
  - [ ] Database performance stable
  - [ ] No degradation over time

- [ ] Data integrity
  - [ ] No data loss reported
  - [ ] All queries returning correct results
  - [ ] Backward compatibility maintained

---

## Rollback Procedure

**Use this if critical issues arise during deployment**

### When to Rollback

Initiate rollback immediately if:
- [ ] Data loss detected
- [ ] Critical functionality broken
- [ ] Performance degradation >50%
- [ ] Error rate >5%
- [ ] Database corruption
- [ ] User-reported blocking issues

### Rollback Steps

**Estimated Time:** 5-10 minutes

#### 1. Stop Services

```bash
# Stop the application
sudo systemctl stop jobsearchai
# OR
sudo supervisorctl stop jobsearchai
```

#### 2. Restore Database

```bash
# Find latest backup
python scripts/backup_database.py --list

# Restore from backup
python scripts/backup_database.py --restore backups/jobsearchai_backup_YYYYMMDD_HHMMSS.db

# OR manual restore
cp backups/jobsearchai_backup_YYYYMMDD_HHMMSS.db instance/jobsearchai.db
```

#### 3. Revert Code

```bash
# Find last stable commit before Epic 2
git log --oneline

# Revert to previous version
git checkout <previous-stable-commit>

# OR create revert commit
git revert <epic-2-merge-commit> --no-commit
git commit -m "Revert Epic 2 changes - rollback to stable"
```

#### 4. Reinstall Dependencies (if needed)

```bash
pip install -r requirements.txt
```

#### 5. Restart Services

```bash
sudo systemctl start jobsearchai
sudo systemctl status jobsearchai
```

#### 6. Verify Rollback

- [ ] System accessible
- [ ] Existing functionality works
- [ ] Database queries work
- [ ] No errors in logs

#### 7. Post-Rollback

- [ ] Notify stakeholders
- [ ] Document issues encountered
- [ ] Create hotfix plan
- [ ] Schedule redeployment

---

## Monitoring and Alerting

### Metrics to Monitor

**Database Performance**
- Query response time (target: <100ms P95)
- Database file size (alert: >1GB)
- Connection pool usage
- Lock wait times

**Application Performance**
- API response times
- Error rate (target: <1%)
- Request throughput
- Memory usage

**Deduplication Effectiveness**
- Duplicate skip rate
- API calls per scrape
- New vs duplicate jobs ratio
- Cost savings realized

### Log Locations

```
logs/dashboard.log          # Main application logs
logs/job_matcher.log        # Job matching logs
logs/cv_processor.log       # CV processing logs
job-data-acquisition/logs/  # Scraper logs
```

### Alert Conditions

Set up alerts for:
- [ ] Database file size > 1GB
- [ ] Query time P95 > 100ms
- [ ] Error rate > 5%
- [ ] API call count anomalies
- [ ] Database locked errors
- [ ] Disk space < 10%

---

## Troubleshooting

### Common Issues

**Issue:** Migration fails with "database locked"
- **Solution:** Ensure all database connections closed, retry migration
- **Command:** `python scripts/migrate_json_to_sqlite.py`

**Issue:** Validation shows missing records
- **Solution:** This may be expected (duplicates), verify error count is low
- **Command:** `python scripts/validate_migration.py --report`

**Issue:** Query performance slow
- **Solution:** Verify indexes created, run VACUUM, check database size
- **Commands:**
  ```bash
  python verify_schema.py
  sqlite3 instance/jobsearchai.db "VACUUM;"
  ```

**Issue:** Deduplication not working
- **Solution:** Check URL normalization, verify composite key constraint
- **Command:** Run test scrape and check logs

**Issue:** JSON fallback not working
- **Solution:** Verify JSON files still present, check fallback logic
- **Location:** `dashboard.py` and `blueprints/job_matching_routes.py`

---

## Success Criteria

Deployment is considered successful when:

- [x] All deployment steps completed without errors
- [x] All smoke tests passing
- [x] Performance targets met:
  - [x] Query response time <100ms (P95)
  - [x] API call reduction ≥90% on repeat runs
  - [x] Page scraping reduction ≥70% on repeat runs
- [x] No critical bugs in first 48 hours
- [x] No data loss
- [x] No regression in existing functionality
- [x] User acceptance positive
- [x] Monitoring and alerts configured
- [x] Documentation complete and accessible

---

## Post-Deployment Tasks

### Documentation

- [ ] Update production wiki with deployment details
- [ ] Document any issues encountered and resolutions
- [ ] Update runbooks with new procedures
- [ ] Archive deployment logs

### Cleanup

- [ ] Archive old JSON files (after validation period)
- [ ] Clean up old backups (automated, but verify)
- [ ] Remove debug/test code (if any)
- [ ] Clean up temporary files

### Knowledge Transfer

- [ ] Brief team on new features
- [ ] Document lessons learned
- [ ] Update training materials
- [ ] Conduct retrospective

### Follow-up

- [ ] Schedule 1-week review meeting
- [ ] Plan next iteration improvements
- [ ] Address any technical debt created
- [ ] Update roadmap

---

## Support Contacts

**Technical Issues:**
- Development Team: [contact info]
- Database Admin: [contact info]
- DevOps: [contact info]

**Escalation:**
- Tech Lead: [contact info]
- Product Manager: [contact info]

---

## Revision History

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2025-11-02 | 1.0 | Initial deployment checklist | Dev Agent |

---

## Appendix: Command Reference

### Quick Command Reference

```bash
# Backup
python scripts/backup_database.py
python scripts/backup_database.py --list

# Migration
python scripts/migrate_json_to_sqlite.py --dry-run
python scripts/migrate_json_to_sqlite.py

# Validation
python scripts/validate_migration.py
python scripts/validate_migration.py --report

# Benchmarks
python scripts/benchmark_performance.py
python scripts/benchmark_performance.py --output benchmarks/results.json

# Database
python init_db.py
python verify_schema.py
sqlite3 instance/jobsearchai.db "VACUUM;"

# Testing
pytest tests/ -v
pytest tests/test_smoke.py -v

# Logs
tail -f logs/dashboard.log
tail -f logs/job_matcher.log

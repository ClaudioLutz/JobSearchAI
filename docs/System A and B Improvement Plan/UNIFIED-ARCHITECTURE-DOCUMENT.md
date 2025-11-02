# System A & B Unified Architecture Document
## SQLite Deduplication & Integration Implementation

**Document Type:** Comprehensive Architecture Specification  
**Project:** JobSearchAI System A & B Improvement  
**Version:** 1.0  
**Date:** 2025-11-02  
**Architect:** Winston (System Arc"hitect)  
**Status:** Ready for Implementation

---

## 📋 Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State Analysis](#current-state-analysis)
3. [Target Architecture](#target-architecture)
4. [Database Schema Design](#database-schema-design)
5. [Component Architecture](#component-architecture)
6. [Implementation Roadmap](#implementation-roadmap)
7. [Migration Strategy](#migration-strategy)
8. [Technical Specifications](#technical-specifications)
9. [Testing Strategy](#testing-strategy)
10. [Success Metrics](#success-metrics)

---

## 📊 Executive Summary

### Problem Statement

The current JobSearchAI system suffers from critical inefficiencies:

**System A (Job Scraper + Matcher) Issues:**
- **No deduplication** → 50-90% redundant API calls on repeat runs
- **No search term tracking** → Cannot manage multiple job searches effectively
- **No CV versioning** → Cannot track which CV version was used for matching
- **No early exit** → Scrapes all pages even when all jobs are duplicates
- **JSON-only storage** → Inefficient querying, no filtering capabilities

**System B (Document Generation) Issues:**
- **JSON file dependency** → Cannot query or filter job data efficiently
- **No database integration** → Must parse entire JSON files for each lookup
- **Manual file selection** → No smart filtering by score, date, location, etc.

### Solution Overview

**Implement a unified SQLite database architecture with:**

1. **Composite Key Deduplication:** `(job_url, search_term, cv_key)` ensures:
   - Same job can be matched for different search terms
   - Same job can be re-evaluated with different CV versions
   - True duplicates are automatically prevented

2. **Content-Based CV Versioning:** SHA256 hash of CV content enables:
   - Automatic detection of CV changes
   - Re-matching when CV is updated
   - Resume-from-interruption capability

3. **Early Exit Optimization:** Stop scraping when page has zero new jobs:
   - 50-70% reduction in page loads
   - Faster execution times
   - Reduced resource consumption

4. **System B Database Integration:** Query job data from SQLite instead of JSON:
   - Sub-100ms query response times
   - Advanced filtering by score, date, location, search term
   - Efficient multi-job selection

### Expected Impact

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| API Calls (repeat run) | 50 calls | 0-5 calls | **90% reduction** |
| Page Scraping (repeat) | 10 pages | 2-3 pages | **70% reduction** |
| Job Lookup Time | 500-1000ms | <100ms | **90% faster** |
| Query Flexibility | None | Full SQL | **New capability** |
| Storage Efficiency | Multiple JSON files | Single SQLite DB | **80% reduction** |

---

## 🔍 Current State Analysis

### System A: Job Data Acquisition & Matching

#### Component 1: Job Scraper (`job-data-acquisition/app.py`)

**Current Implementation:**
```python
def run_scraper():
    for url in target_urls:
        for page in range(1, max_pages + 1):
            scraper = configure_scraper(url, page)
            results = scraper.run()
            all_results.append(results)
    
    # Save to JSON file
    output_file = f"{output_dir}/{file_prefix}{timestamp}.json"
    with open(output_file, "w") as f:
        json.dump(all_results, f)
```

**Problems:**
- ❌ URL hardcoded in `settings.json` - no search term parameter
- ❌ No database check - creates new file every run
- ❌ No deduplication - same jobs scraped repeatedly
- ❌ No early exit - always scrapes all `max_pages`
- ❌ No CV association - doesn't know which CV will use this data

**Current Data Flow:**
```
settings.json (hardcoded URL) 
  ↓
ScrapeGraph API (OpenAI + Playwright)
  ↓
JSON file: job-data-acquisition/data/job_data_YYYYMMDD_HHMMSS.json
  ↓
Structure: [ [page1_jobs], [page2_jobs], ... ]
```

#### Component 2: Job Matcher (`job_matcher.py`)

**Current Implementation:**
```python
def match_jobs_with_cv(cv_path, min_score=6, max_jobs=50):
    cv_text = extract_cv_text(cv_path)
    cv_summary = summarize_cv(cv_text)
    job_listings = load_latest_job_data(max_jobs=max_jobs)
    
    matches = []
    for job in job_listings:
        evaluation = evaluate_job_match(cv_summary, job)  # OpenAI API call
        matches.append(evaluation)
    
    filtered = [m for m in matches if m["overall_match"] >= min_score]
    return sorted(filtered)[:max_results]
```

**Problems:**
- ❌ No database check - re-evaluates already matched jobs
- ❌ No search term tracking - can't associate job with search context
- ❌ Uses file path instead of CV content hash
- ❌ Filters AFTER matching - wastes API calls
- ❌ JSON file output only

**Current Data Flow:**
```
Latest job_data_*.json file
  ↓
Load & flatten nested array structure
  ↓
Loop through jobs → OpenAI API call for each
  ↓
Filter by min_score
  ↓
Save to: job_matches/job_matches_YYYYMMDD_HHMMSS.json
```

### System B: Document Generation & Dashboard

#### Component 3: Dashboard (`dashboard.py`)

**Current Implementation:**
```python
def get_job_details_for_url(job_url):
    job_id = job_url.split('/')[-1]
    job_data_dir = Path('job-data-acquisition/data')
    latest_file = max(job_data_dir.glob('job_data_*.json'), key=os.path.getctime)
    
    with open(latest_file, 'r') as f:
        job_data = json.load(f)
    
    # Flatten nested arrays and search for job_id
    for job in flatten_job_data(job_data):
        if job_id in job.get('Application URL', ''):
            return job
    return {}
```

**Problems:**
- ❌ Reads entire JSON file for each lookup
- ❌ O(n) search complexity
- ❌ No filtering, sorting, or advanced queries
- ❌ No search term or CV version awareness
- ❌ Manual file selection UI

### Inefficiency Analysis

**Scenario: User runs scraper twice for "IT" jobs**

```
Run #1:
  - Scrape 10 pages → Find 50 jobs
  - Match 50 jobs → 50 OpenAI API calls
  - Save to job_matches_20251102_100000.json

Run #2 (same day, same search):
  - Scrape 10 pages → Find same 50 jobs (duplicates!)
  - Match 50 jobs → 50 MORE OpenAI API calls (waste!)
  - Save to job_matches_20251102_140000.json (different file)

Total: 100 API calls
Necessary: 50 API calls
Waste: 50 API calls (50% redundancy)
Cost: 2x OpenAI API fees
```

**Scenario: User updates CV and wants to re-match**

```
Current System:
  - No CV tracking → System doesn't know CV changed
  - Must manually delete old match files
  - Re-run matcher → Matches ALL jobs again (even if some were matched with old CV)

Desired System:
  - CV content hash detects change automatically
  - Only new CV key = re-match
  - Old matches remain in database for comparison
```

---

## 🎯 Target Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         SYSTEM A                                │
│                   Job Data Acquisition                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐         ┌──────────────┐                    │
│  │   Scraper    │────────>│   Matcher    │                    │
│  │   (app.py)   │         │(job_matcher) │                    │
│  └──────┬───────┘         └──────┬───────┘                    │
│         │                        │                             │
│         │ search_term           │ match_data                  │
│         │ + cv_key              │ + scores                    │
│         │                        │                             │
│         v                        v                             │
│  ┌──────────────────────────────────────┐                     │
│  │      SQLite Database                 │                     │
│  │   (instance/jobsearchai.db)         │                     │
│  │                                      │                     │
│  │  Table: job_matches                  │                     │
│  │  UNIQUE(job_url, search_term,        │                     │
│  │         cv_key)                      │                     │
│  │                                      │                     │
│  │  - Deduplication                     │                     │
│  │  - Early exit detection              │                     │
│  │  - Multi-search support              │                     │
│  │  - CV version tracking               │                     │
│  └──────────────┬───────────────────────┘                     │
│                 │                                              │
└─────────────────┼──────────────────────────────────────────────┘
                  │
                  │ Query job data
                  │ by job_url, cv_key,
                  │ search_term, score, etc.
                  │
┌─────────────────▼──────────────────────────────────────────────┐
│                         SYSTEM B                                │
│                Document Generation + Dashboard                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐         ┌──────────────┐                    │
│  │  Dashboard   │────────>│Letter Gen    │                    │
│  │ (dashboard)  │         │  (utils)     │                    │
│  └──────┬───────┘         └──────────────┘                    │
│         │                                                       │
│         │ Filter by:                                           │
│         │ - search_term                                        │
│         │ - min_score                                          │
│         │ - date_range                                         │
│         │ - location                                           │
│         │                                                       │
│         v                                                       │
│  ┌──────────────────────────────────┐                         │
│  │   Query Interface                │                         │
│  │   (utils/db_utils.py)            │                         │
│  │                                  │                         │
│  │   - Fast SQL queries (<100ms)    │                         │
│  │   - Advanced filtering           │                         │
│  │   - Multi-job selection          │                         │
│  └──────────────────────────────────┘                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Key Architectural Changes

#### 1. Unified Database Layer

**New Component:** `utils/db_utils.py`

```python
class JobMatchDatabase:
    """
    Centralized database access layer for both System A and System B
    
    Responsibilities:
    - Database connection management
    - Schema initialization
    - Deduplication checks
    - Job match insertion
    - Query interface for System B
    """
```

#### 2. CV Key Generation

**New Component:** `utils/cv_utils.py`

```python
def generate_cv_key(cv_path):
    """
    Generate unique key based on CV content (SHA256 hash)
    
    Benefits:
    - Same content = same key (idempotent)
    - Detects CV changes automatically
    - Enables resume-from-interruption
    """
```

#### 3. Search Term Parameterization

**Updated:** `job-data-acquisition/settings.json`

```json
{
  "search_terms": ["IT", "Data-Analyst", "Product-Manager"],
  "base_url": "https://www.ostjob.ch/job/suche-{search_term}-seite-",
  "cv_path": "process_cv/cv-data/input/Lebenslauf.pdf"
}
```

#### 4. Deduplication Logic

**Core Concept:** Composite key prevents duplicate matches

```sql
-- Database enforces uniqueness at schema level
UNIQUE(job_url, search_term, cv_key)

-- This allows:
-- ✅ Same job + different search → ALLOWED (new context)
-- ✅ Same job + different CV → ALLOWED (new candidate profile)
-- ❌ Same job + same search + same CV → REJECTED (true duplicate)
```

---

## 💾 Database Schema Design

### Primary Table: job_matches

```sql
CREATE TABLE job_matches (
    -- Primary key
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Composite deduplication key
    job_url TEXT NOT NULL,
    search_term TEXT NOT NULL,
    cv_key TEXT NOT NULL,
    
    -- Job metadata (extracted from scraped data)
    job_title TEXT,
    company_name TEXT,
    location TEXT,
    posting_date TEXT,
    salary_range TEXT,
    
    -- Match scores (from OpenAI evaluation)
    overall_match INTEGER NOT NULL,
    skills_match INTEGER,
    experience_match INTEGER,
    education_fit INTEGER,
    career_trajectory_alignment INTEGER,
    preference_match INTEGER,
    potential_satisfaction INTEGER,
    location_compatibility TEXT,
    reasoning TEXT,
    
    -- Complete job data (preserved as JSON for flexibility)
    scraped_data JSON NOT NULL,
    
    -- Timestamps
    scraped_at TIMESTAMP NOT NULL,
    matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Enforce deduplication at database level
    UNIQUE(job_url, search_term, cv_key)
);

-- Indexes for query performance
CREATE INDEX idx_search_term ON job_matches(search_term);
CREATE INDEX idx_cv_key ON job_matches(cv_key);
CREATE INDEX idx_overall_match ON job_matches(overall_match);
CREATE INDEX idx_matched_at ON job_matches(matched_at);
CREATE INDEX idx_location ON job_matches(location);
CREATE INDEX idx_compound ON job_matches(search_term, cv_key, overall_match);
```

### Supporting Table: cv_versions

```sql
CREATE TABLE cv_versions (
    cv_key TEXT PRIMARY KEY,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_hash TEXT NOT NULL,  -- Same as cv_key for redundancy
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    summary TEXT,  -- Cached CV summary
    metadata JSON  -- Additional CV metadata
);
```

### Supporting Table: scrape_history

```sql
CREATE TABLE scrape_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    search_term TEXT NOT NULL,
    page_number INTEGER NOT NULL,
    jobs_found INTEGER NOT NULL,
    new_jobs INTEGER NOT NULL,
    duplicate_jobs INTEGER NOT NULL,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    duration_seconds REAL
);
```

### Schema Rationale

**Why JSON for scraped_data?**

1. **Flexibility:** Scraper output may evolve with new fields
2. **Completeness:** Preserves all job information for letter generation
3. **No Migration:** Adding new fields doesn't require schema changes
4. **Hybrid Approach:** Key fields extracted for fast queries, complete data in JSON

**Why Composite Unique Constraint?**

1. **Semantic Correctness:** Same job has different value in different contexts
2. **Multi-Search Support:** User can search multiple terms simultaneously
3. **CV Versioning:** Re-evaluate jobs when CV changes
4. **Database-Level Enforcement:** Prevent duplicates at write time (fail-fast)

---

## 🏗️ Component Architecture

### Component 1: Database Utilities (`utils/db_utils.py`)

**Purpose:** Centralized database access layer

**Key Methods:**

```python
class JobMatchDatabase:
    def __init__(self, db_path="instance/jobsearchai.db")
    def connect() -> sqlite3.Connection
    def close()
    def init_database()  # Create tables and indexes
    
    # Deduplication
    def job_exists(job_url, search_term, cv_key) -> bool
    
    # Write operations
    def insert_job_match(match_data: Dict) -> Optional[int]
    def insert_scrape_history(history_data: Dict)
    
    # Query operations (for System B)
    def query_matches(filters: Dict) -> List[Dict]
    def get_job_by_url(job_url, cv_key=None) -> Optional[Dict]
```

**Usage Examples:**

```python
# System A: Check for duplicates before matching
db = JobMatchDatabase()
db.connect()

if not db.job_exists(job_url, "IT", cv_key):
    evaluation = evaluate_job_match(cv_summary, job)
    db.insert_job_match(evaluation)
else:
    logger.info(f"Skipping duplicate: {job_url}")

db.close()
```

```python
# System B: Query matches with filters
db = JobMatchDatabase()
db.connect()

matches = db.query_matches({
    'search_term': 'IT',
    'cv_key': current_cv_key,
    'min_score': 7,
    'date_from': '2025-11-01',
    'location': 'Zürich'
})

db.close()
```

### Component 2: CV Utilities (`utils/cv_utils.py`)

**Purpose:** CV key generation and version management

**Key Functions:**

```python
def generate_cv_key(cv_path: str) -> str:
    """
    Generate unique key based on CV content (SHA256 hash)
    
    Returns:
        str: 16-character hex string (first 16 chars of SHA256)
    """
    with open(cv_path, 'rb') as f:
        cv_bytes = f.read()
    return hashlib.sha256(cv_bytes).hexdigest()[:16]

def get_or_create_cv_metadata(cv_path, db_conn):
    """
    Get CV key and create metadata entry if new version
    
    Returns:
        str: CV key
    """
    cv_key = generate_cv_key(cv_path)
    
    cursor = db_conn.cursor()
    cursor.execute("SELECT * FROM cv_versions WHERE cv_key = ?", (cv_key,))
    
    if not cursor.fetchone():
        # New CV version - create entry
        cv_text = extract_cv_text(cv_path)
        cv_summary = summarize_cv(cv_text)
        
        cursor.execute("""
            INSERT INTO cv_versions (cv_key, file_name, file_path, file_hash, summary)
            VALUES (?, ?, ?, ?, ?)
        """, (cv_key, Path(cv_path).name, str(cv_path), cv_key, cv_summary))
        
        db_conn.commit()
    
    return cv_key
```

### Component 3: Updated Scraper (`job-data-acquisition/app.py`)

**Changes Required:**

1. **Add search_term parameter support**
2. **Add CV key generation**
3. **Add database deduplication check**
4. **Add early exit logic**
5. **Add scrape history logging**

**Updated Flow:**

```python
def run_scraper_with_deduplication(search_term, cv_path):
    """Run scraper with database deduplication"""
    
    # Initialize database
    db = JobMatchDatabase()
    db.connect()
    db.init_database()
    
    # Generate CV key
    cv_key = generate_cv_key(cv_path)
    
    # Build URL
    base_url = CONFIG["base_url"]
    url = base_url.format(search_term=search_term)
    
    all_results = []
    for page in range(1, max_pages + 1):
        page_results = scrape_page(url, page)
        
        new_jobs = []
        duplicate_count = 0
        
        for job in page_results:
            job_url = job.get('Application URL')
            
            # Check if exists in database
            if db.job_exists(job_url, search_term, cv_key):
                duplicate_count += 1
                logger.debug(f"Duplicate: {job_url}")
            else:
                new_jobs.append(job)
                logger.info(f"New job: {job.get('Job Title')}")
        
        all_results.extend(new_jobs)
        
        # Log scrape history
        db.insert_scrape_history({
            'search_term': search_term,
            'page_number': page,
            'jobs_found': len(page_results),
            'new_jobs': len(new_jobs),
            'duplicate_jobs': duplicate_count
        })
        
        # Early exit if all duplicates
        if len(new_jobs) == 0 and duplicate_count > 0:
            logger.info(f"Page {page}: All duplicates. Stopping.")
            break
    
    db.close()
    return all_results
```

### Component 4: Updated Matcher (`job_matcher.py`)

**Changes Required:**

1. **Add database deduplication check**
2. **Add search_term parameter**
3. **Use CV key instead of file path**
4. **Save to database instead of JSON**

**Updated Flow:**

```python
def match_jobs_with_cv_dedup(cv_path, search_term, min_score=6, max_jobs=50):
    """Match jobs with database deduplication"""
    
    # Initialize database
    db = JobMatchDatabase()
    db.connect()
    db.init_database()
    
    # Generate CV key
    cv_key = generate_cv_key(cv_path)
    
    # Extract and summarize CV
    cv_text = extract_cv_text(cv_path)
    cv_summary = summarize_cv(cv_text)
    
    # Load job data
    job_listings = load_latest_job_data(max_jobs=max_jobs)
    
    matches = []
    skipped_count = 0
    
    for job in job_listings:
        job_url = job.get('Application URL')
        
        # Check if already matched
        if db.job_exists(job_url, search_term, cv_key):
            skipped_count += 1
            logger.debug(f"Already matched: {job_url}")
            continue
        
        # Evaluate (OpenAI API call)
        evaluation = evaluate_job_match(cv_summary, job)
        
        # Prepare match data
        match_data = {
            'job_url': job_url,
            'search_term': search_term,
            'cv_key': cv_key,
            'job_title': job.get('Job Title'),
            'company_name': job.get('Company Name'),
            'location': job.get('Location'),
            'posting_date': job.get('Posting Date'),
            'salary_range': job.get('Salary Range'),
            'overall_match': evaluation['overall_match'],
            'skills_match': evaluation.get('skills_match'),
            'experience_match': evaluation.get('experience_match'),
            'education_fit': evaluation.get('education_fit'),
            'career_trajectory_alignment': evaluation.get('career_trajectory_alignment'),
            'preference_match': evaluation.get('preference_match'),
            'potential_satisfaction': evaluation.get('potential_satisfaction'),
            'location_compatibility': evaluation.get('location_compatibility'),
            'reasoning': evaluation.get('reasoning'),
            'scraped_data': job,
            'scraped_at': datetime.now().isoformat()
        }
        
        # Save to database
        db.insert_job_match(match_data)
        
        if evaluation['overall_match'] >= min_score:
            matches.append(match_data)
    
    db.close()
    
    logger.info(f"Matched {len(matches)} new jobs, skipped {skipped_count}")
    return matches
```

### Component 5: Updated Dashboard (`dashboard.py`)

**Changes Required:**

1. **Update `get_job_details_for_url()` to query database**
2. **Add database fallback to JSON (for migration period)**
3. **Add CV key parameter support**

**Updated Function:**

```python
def get_job_details_for_url(job_url, cv_key=None):
    """Get job details from database with JSON fallback"""
    
    # Try database first
    db = JobMatchDatabase()
    try:
        db.connect()
        cursor = db.conn.cursor()
        
        if cv_key:
            # Get specific match for this CV
            query = """
                SELECT scraped_data FROM job_matches 
                WHERE job_url = ? AND cv_key = ?
                ORDER BY matched_at DESC LIMIT 1
            """
            cursor.execute(query, (job_url, cv_key))
        else:
            # Get any match (most recent)
            query = """
                SELECT scraped_data FROM job_matches 
                WHERE job_url = ?
                ORDER BY matched_at DESC LIMIT 1
            """
            cursor.execute(query, (job_url,))
        
        row = cursor.fetchone()
        if row:
            job_details = json.loads(row['scraped_data'])
            logger.info(f"Retrieved from database: {job_details.get('Job Title')}")
            return job_details
            
    except Exception as e:
        logger.error(f"Database error: {e}")
    finally:
        db.close()
    
    # Fallback to JSON files (backward compatibility)
    logger.warning("Database lookup failed, using JSON fallback")
    return get_job_details_from_json_legacy(job_url)
```

---

## 📅 Implementation Roadmap

### Phase 1: Database Foundation (Week 1)

**Goal:** Create database layer without breaking existing functionality

**Tasks:**

1. **Create `utils/db_utils.py`**
   - [ ] Implement `JobMatchDatabase` class
   - [ ] Add connection management
   - [ ] Add schema initialization
   - [ ] Add deduplication check methods
   - [ ] Add insert methods
   - [ ] Add query methods

2. **Create `utils/cv_utils.py`**
   - [ ] Implement `generate_cv_key()`
   - [ ] Implement `get_or_create_cv_metadata()`
   - [ ] Add CV version comparison utilities

3. **Database Initialization**
   - [ ] Create `init_db.py` script
   - [ ] Test schema creation
   - [ ] Test index creation
   - [ ] Verify constraints work

4. **Unit Tests**
   - [ ] Test database connection
   - [ ] Test deduplication logic
   - [ ] Test CV key generation
   - [ ] Test query methods

**Deliverables:**
- `utils/db_utils.py` (fully tested)
- `utils/cv_utils.py` (fully tested)
- `init_db.py` (database setup script)
- Unit tests with >80% coverage

**Success Criteria:**
- Database creates successfully
- Composite unique constraint prevents duplicates
- CV key generation is deterministic
- All unit tests pass

---

### Phase 2: System A Integration (Week 2)

**Goal:** Update scraper and matcher to use database

**Tasks:**

1. **Update `job-data-acquisition/settings.json`**
   - [ ] Add `search_terms` array
   - [ ] Add `base_url` with placeholder
   - [ ] Add `cv_path` configuration

2. **Update `job-data-acquisition/app.py`**
   - [ ] Add `run_scraper_with_deduplication()` function
   - [ ] Implement search term loop
   - [ ] Add database deduplication check
   - [ ] Implement early exit logic
   - [ ] Add scrape history logging
   - [ ] Keep existing `run_scraper()` for backward compatibility

3. **Update `job_matcher.py`**
   - [ ] Add `match_jobs_with_cv_dedup()` function
   - [ ] Add database deduplication check before matching
   - [ ] Implement database save instead of JSON
   - [ ] Add search_term parameter
   - [ ] Keep existing `match_jobs_with_cv()` for backward compatibility

4. **Integration Tests**
   - [ ] Test scraper with single search term
   - [ ] Test scraper with multiple search terms
   - [ ] Test early exit behavior
   - [ ] Test matcher deduplication
   - [ ] Test CV key detection

**Deliverables:**
- Updated scraper with database support
- Updated matcher with deduplication
- Integration test suite
- Migration guide

**Success Criteria:**
- Scraper writes to database
- Matcher reads from database
- No duplicate matches created
- Early exit works correctly
- All integration tests pass

---

### Phase 3: System B Integration (Week 3)

**Goal:** Update dashboard to query database instead of JSON

**Tasks:**

1. **Update `dashboard.py`**
   - [ ] Update `get_job_details_for_url()` to query database
   - [ ] Add JSON fallback for backward compatibility
   - [ ] Add CV key parameter support

2. **Update Blueprint Routes**
   - [ ] Update `motivation_letter_routes.py` to pass cv_key
   - [ ] Update `job_matching_routes.py` to use database queries
   - [ ] Add filtering endpoints

3. **Add Database Query UI**
   - [ ] Create filter form (search_term, score, date, location)
   - [ ] Add sort options
   - [ ] Add multi-select for job list
   - [ ] Create database statistics page

4. **Testing**
   - [ ] Test database queries from dashboard
   - [ ] Test JSON fallback
   - [ ] Test filtering functionality
   - [ ] Test performance with large datasets

**Deliverables:**
- Updated dashboard with database integration
- New filtering UI
- Database statistics page
- Performance test results

**Success Criteria:**
- Dashboard queries database successfully
- JSON fallback works when needed
- Query response time <100ms
- Filtering works correctly
- UI shows database-sourced data

---

### Phase 4: Migration & Testing (Week 4)

**Goal:** Migrate existing data and validate system

**Tasks:**

1. **Data Migration**
   - [ ] Create migration script for existing JSON files
   - [ ] Prompt user for search_term and cv_key for old data
   - [ ] Verify data integrity after migration
   - [ ] Archive old JSON files

2. **End-to-End Testing**
   - [ ] Test complete scrape → match → display workflow
   - [ ] Test duplicate detection accuracy
   - [ ] Measure API call reduction
   - [ ] Test multi-search scenario
   - [ ] Test CV version change scenario

3. **Performance Testing**
   - [ ] Load test with 1000+ jobs
   - [ ] Measure query response times
   - [ ] Test concurrent access
   - [ ] Memory usage profiling

4. **Documentation**
   - [ ] Update user guide
   - [ ] Update development guide
   - [ ] Create troubleshooting guide
   - [ ] Document API changes

**Deliverables:**
- Data migration script
- Complete test suite
- Performance benchmarks
- Updated documentation

**Success Criteria:**
- All existing data migrated successfully
- 70%+ reduction in API calls verified
- <100ms query performance confirmed
- All tests passing
- Documentation complete

---

### Phase 5: Production Deployment (Week 5)

**Goal:** Deploy to production and monitor

**Tasks:**

1. **Deployment Preparation**
   - [ ] Backup production data
   - [ ] Create rollback plan
   - [ ] Prepare deployment checklist
   - [ ] Schedule maintenance window

2. **Deployment**
   - [ ] Deploy database updates
   - [ ] Deploy System A changes
   - [ ] Deploy System B changes
   - [ ] Run smoke tests

3. **Monitoring**
   - [ ] Monitor database performance
   - [ ] Track API usage reduction
   - [ ] Watch for errors
   - [ ] Collect user feedback

4. **Optimization**
   - [ ] Tune database queries if needed
   - [ ] Adjust indexes based on usage
   - [ ] Optimize slow operations
   - [ ] Clean up legacy code

**Deliverables:**
- Production deployment
- Monitoring dashboard
- Performance reports
- User feedback summary

**Success Criteria:**
- Zero downtime deployment
- No critical bugs in first week
- Performance targets met
- Positive user feedback

---

## 🔄 Migration Strategy

### Backward Compatibility Approach

**Philosophy:** Gradual migration with fallback support

```
Phase 1: Database writes + JSON writes (both)
  ↓
Phase 2: Database reads + JSON fallback
  ↓
Phase 3: Database only + optional JSON export
  ↓
Phase 4: Remove JSON code (cleanup)
```

### Migration Script

**File:** `scripts/migrate_json_to_sqlite.py`

```python
import json
import sqlite3
import glob
from datetime import datetime
from pathlib import Path
from utils.db_utils import JobMatchDatabase
from utils.cv_utils import generate_cv_key

def migrate_legacy_json_files(
    json_dir="job_matches",
    db_path="instance/jobsearchai.db"
):
    """
    Migrate existing JSON match files to SQLite database
    
    Interactive migration with user prompts for missing data
    """
    db = JobMatchDatabase(db_path)
    db.connect()
    db.init_database()
    
    json_files = glob.glob(f"{json_dir}/job_matches_*.json")
    
    total_migrated = 0
    total_duplicates = 0
    total_errors = 0
    
    for json_file in json_files:
        print(f"\n{'='*60}")
        print(f"Processing: {json_file}")
        print(f"{'='*60}")
        
        with open(json_file, 'r', encoding='utf-8') as f:
            matches = json.load(f)
        
        # Prompt for metadata
        print(f"\nFile contains {len(matches)} matches")
        search_term = input("Enter search term for this file (e.g., 'IT'): ").strip()
        cv_path = input("Enter CV path used (relative to project root): ").strip()
        
        if not search_term or not cv_path:
            print("⚠️  Skipping file - missing search term or CV path")
            continue
        
        # Generate CV key
        try:
            cv_key = generate_cv_key(cv_path)
            print(f"✓ Generated CV key: {cv_key}")
        except FileNotFoundError:
            print(f"⚠️  CV file not found: {cv_path}")
            cv_key = input("Enter CV key manually (or press Enter to skip): ").strip()
            if not cv_key:
                continue
        
        # Migrate each match
        for i, match in enumerate(matches, 1):
            try:
                match_data = {
                    'job_url': match.get('application_url') or match.get('Application URL', ''),
                    'search_term': search_term,
                    'cv_key': cv_key,
                    'job_title': match.get('job_title') or match.get('Job Title', ''),
                    'company_name': match.get('company_name') or match.get('Company Name', ''),
                    'location': match.get('location') or match.get('Location', ''),
                    'posting_date': match.get('posting_date'),
                    'salary_range': match.get('salary_range'),
                    'overall_match': match.get('overall_match', 0),
                    'skills_match': match.get('skills_match'),
                    'experience_match': match.get('experience_match'),
                    'education_fit': match.get('education_fit'),
                    'career_trajectory_alignment': match.get('career_trajectory_alignment'),
                    'preference_match': match.get('preference_match'),
                    'potential_satisfaction': match.get('potential_satisfaction'),
                    'location_compatibility': match.get('location_compatibility'),
                    'reasoning': match.get('reasoning', ''),
                    'scraped_data': {
                        'Job Title': match.get('job_title', ''),
                        'Company Name': match.get('company_name', ''),
                        'Job Description': match.get('job_description', ''),
                        'Location': match.get('location', ''),
                        'Required Skills': match.get('required_skills', ''),
                    },
                    'scraped_at': datetime.now().isoformat()
                }
                
                row_id = db.insert_job_match(match_data)
                
                if row_id:
                    total_migrated += 1
                    print(f"  [{i}/{len(matches)}] ✓ Migrated: {match_data['job_title']}")
                else:
                    total_duplicates += 1
                    print(f"  [{i}/{len(matches)}] ⊘ Duplicate: {match_data['job_title']}")
                    
            except Exception as e:
                total_errors += 1
                print(f"  [{i}/{len(matches)}] ✗ Error: {str(e)}")
    
    db.close()
    
    print(f"\n{'='*60}")
    print(f"Migration Complete")
    print(f"{'='*60}")
    print(f"Total migrated: {total_migrated}")
    print(f"Total duplicates: {total_duplicates}")
    print(f"Total errors: {total_errors}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    migrate_legacy_json_files()
```

### Rollback Plan

**If issues arise during migration:**

1. **Stop all writes to database**
2. **Restore from backup**
3. **Revert code to previous version**
4. **Resume using JSON files**
5. **Debug issues in development environment**
6. **Retry migration after fixes**

**Backup Strategy:**

```bash
# Before deployment
sqlite3 instance/jobsearchai.db ".backup instance/jobsearchai_backup_$(date +%Y%m%d).db"

# Restore if needed
cp instance/jobsearchai_backup_YYYYMMDD.db instance/jobsearchai.db
```

---

## 🔧 Technical Specifications

### Database Configuration

**Connection Parameters:**

```python
# Database path
DB_PATH = "instance/jobsearchai.db"

# Connection settings
TIMEOUT = 30  # seconds
CHECK_SAME_THREAD = False  # Allow multi-threaded access

# SQLite settings
PRAGMA_SETTINGS = {
    'journal_mode': 'WAL',  # Write-Ahead Logging for better concurrency
    'synchronous': 'NORMAL',  # Balance between safety and performance
    'foreign_keys': 'ON',  # Enforce foreign key constraints
    'temp_store': 'MEMORY',  # Use memory for temp tables
}
```

### URL Normalization

**Important:** URLs must be normalized before database operations

```python
from utils.url_utils import URLNormalizer

normalizer = URLNormalizer()

# Normalize before database check
normalized_url = normalizer.normalize(raw_url)
db.job_exists(normalized_url, search_term, cv_key)

# Examples:
# "ostjob.ch/job/12345" → "https://www.ostjob.ch/job/12345"
# "http://ostjob.ch/job/12345" → "https://www.ostjob.ch/job/12345"
# "www.ostjob.ch/job/12345" → "https://www.ostjob.ch/job/12345"
```

### Error Handling

**Database Operations:**

```python
try:
    db.connect()
    db.insert_job_match(match_data)
except sqlite3.IntegrityError:
    # Duplicate entry (expected during deduplication)
    logger.debug(f"Duplicate entry: {match_data['job_url']}")
except sqlite3.OperationalError as e:
    # Database locked or other operational issue
    logger.error(f"Database operational error: {e}")
    # Retry or fallback to JSON
except Exception as e:
    # Unexpected error
    logger.error(f"Unexpected database error: {e}", exc_info=True)
finally:
    db.close()
```

### Performance Tuning

**Query Optimization:**

```sql
-- Use EXPLAIN QUERY PLAN to analyze queries
EXPLAIN QUERY PLAN
SELECT * FROM job_matches 
WHERE search_term = 'IT' 
  AND overall_match >= 7
ORDER BY overall_match DESC;

-- Ensure indexes are being used
-- Expected output should show "USING INDEX idx_compound" or similar
```

**Batch Operations:**

```python
# Instead of individual inserts
for match in matches:
    db.insert_job_match(match)  # Slow

# Use transactions for batch
db.conn.execute("BEGIN TRANSACTION")
try:
    for match in matches:
        db.insert_job_match(match)
    db.conn.commit()
except:
    db.conn.rollback()
```

---

## 🧪 Testing Strategy

### Unit Tests

**Test Coverage Targets:**

- Database utilities: >90%
- CV utilities: >90%
- Updated scraper: >80%
- Updated matcher: >80%
- Dashboard integration: >75%

**Example Unit Test:**

```python
import unittest
from utils.db_utils import JobMatchDatabase
from utils.cv_utils import generate_cv_key

class TestDeduplication(unittest.TestCase):
    def setUp(self):
        """Set up in-memory test database"""
        self.db = JobMatchDatabase(":memory:")
        self.db.connect()
        self.db.init_database()
    
    def test_duplicate_detection(self):
        """Test that duplicates are correctly detected"""
        match_data = {
            'job_url': 'https://ostjob.ch/job/12345',
            'search_term': 'IT',
            'cv_key': 'abc123',
            'job_title': 'Test Job',
            'overall_match': 7,
            'scraped_data': {'Job Title': 'Test'},
            'scraped_at': '2025-11-02'
        }
        
        # First insert should succeed
        row_id = self.db.insert_job_match(match_data)
        self.assertIsNotNone(row_id)
        
        # Duplicate insert should return None
        row_id_dup = self.db.insert_job_match(match_data)
        self.assertIsNone(row_id_dup)
    
    def test_same_job_different_search(self):
        """Same job with different search_term should be allowed"""
        base_match = {
            'job_url': 'https://ostjob.ch/job/12345',
            'search_term': 'IT',
            'cv_key': 'abc123',
            'job_title': 'Test Job',
            'overall_match': 7,
            'scraped_data': {'Job Title': 'Test'},
            'scraped_at': '2025-11-02'
        }
        
        # Insert for "IT" search
        row_id_1 = self.db.insert_job_match(base_match)
        self.assertIsNotNone(row_id_1)
        
        # Insert for "Data-Analyst" search (different search_term)
        match_2 = {**base_match, 'search_term': 'Data-Analyst'}
        row_id_2 = self.db.insert_job_match(match_2)
        self.assertIsNotNone(row_id_2)
        
        # Should have two separate records
        self.assertNotEqual(row_id_1, row_id_2)
```

### Integration Tests

**Test Scenarios:**

1. **Complete Workflow Test**
   ```python
   def test_end_to_end_workflow():
       # Scrape jobs
       jobs = run_scraper_with_deduplication("IT", "test_cv.pdf")
       assert len(jobs) > 0
       
       # Match jobs
       matches = match_jobs_with_cv_dedup("test_cv.pdf", "IT")
       assert len(matches) > 0
       
       # Query from dashboard
       db_matches = query_matches({'search_term': 'IT'})
       assert len(db_matches) > 0
   ```

2. **Deduplication Test**
   ```python
   def test_duplicate_prevention():
       # Run scraper twice
       run1 = run_scraper_with_deduplication("IT", "test_cv.pdf")
       run2 = run_scraper_with_deduplication("IT", "test_cv.pdf")
       
       # Second run should find zero new jobs
       assert len(run2) == 0
   ```

3. **CV Version Change Test**
   ```python
   def test_cv_version_change():
       # Match with CV v1
       cv_key_v1 = generate_cv_key("cv_v1.pdf")
       matches_v1 = match_jobs_with_cv_dedup("cv_v1.pdf", "IT")
       
       # Match with CV v2 (updated content)
       cv_key_v2 = generate_cv_key("cv_v2.pdf")
       matches_v2 = match_jobs_with_cv_dedup("cv_v2.pdf", "IT")
       
       # Should have different CV keys
       assert cv_key_v1 != cv_key_v2
       
       # Should have matches for both versions in database
       db_v1 = query_matches({'cv_key': cv_key_v1})
       db_v2 = query_matches({'cv_key': cv_key_v2})
       assert len(db_v1) > 0
       assert len(db_v2) > 0
   ```

### Performance Tests

**Benchmarks:**

```python
import time

def benchmark_query_performance():
    """Measure query response time"""
    db = JobMatchDatabase()
    db.connect()
    
    # Populate with test data
    for i in range(1000):
        db.insert_job_match(create_test_match(i))
    
    # Measure query time
    start = time.time()
    results = db.query_matches({
        'search_term': 'IT',
        'min_score': 7
    })
    elapsed = time.time() - start
    
    print(f"Query returned {len(results)} results in {elapsed*1000:.2f}ms")
    assert elapsed < 0.1, "Query took longer than 100ms"
```

---

## 📈 Success Metrics

### Primary Metrics

| Metric | Baseline | Target | Measurement Method |
|--------|----------|--------|-------------------|
| **API Call Reduction** | 100% redundancy | <10% redundancy | Count OpenAI calls |
| **Page Scraping Reduction** | 100% of max_pages | <30% on reruns | Log page scraping |
| **Duplicate Detection Accuracy** | 0% (no dedup) | 100% | Unit tests |
| **Query Response Time** | 500-1000ms (JSON) | <100ms (SQLite) | Performance tests |
| **Storage Efficiency** | Multiple JSON files | Single DB | File size comparison |

### Secondary Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Database Size Growth** | Linear with jobs | Monitor DB file size |
| **Concurrent Access** | 10+ simultaneous | Load testing |
| **Index Effectiveness** | >95% index usage | EXPLAIN QUERY PLAN |
| **Error Rate** | <1% | Error logs |
| **User Satisfaction** | >4/5 rating | User surveys |

### Monitoring Dashboard

**Key Performance Indicators:**

```python
def get_system_metrics():
    """Get real-time system performance metrics"""
    db = JobMatchDatabase()
    db.connect()
    
    cursor = db.conn.cursor()
    
    # Total jobs in database
    cursor.execute("SELECT COUNT(*) FROM job_matches")
    total_jobs = cursor.fetchone()[0]
    
    # Unique jobs (deduplicated)
    cursor.execute("SELECT COUNT(DISTINCT job_url) FROM job_matches")
    unique_jobs = cursor.fetchone()[0]
    
    # Average match score
    cursor.execute("SELECT AVG(overall_match) FROM job_matches")
    avg_score = cursor.fetchone()[0]
    
    # Scraping efficiency (from last run)
    cursor.execute("""
        SELECT 
            SUM(new_jobs) as total_new,
            SUM(duplicate_jobs) as total_duplicates
        FROM scrape_history
        WHERE scraped_at > datetime('now', '-1 day')
    """)
    scrape_stats = cursor.fetchone()
    
    # Deduplication rate
    if scrape_stats and scrape_stats[0] + scrape_stats[1] > 0:
        dedup_rate = scrape_stats[1] / (scrape_stats[0] + scrape_stats[1]) * 100
    else:
        dedup_rate = 0
    
    db.close()
    
    return {
        'total_matches': total_jobs,
        'unique_jobs': unique_jobs,
        'avg_match_score': round(avg_score, 1),
        'deduplication_rate': round(dedup_rate, 1),
        'new_jobs_24h': scrape_stats[0] if scrape_stats else 0,
        'duplicates_24h': scrape_stats[1] if scrape_stats else 0
    }
```

---

## ✅ Acceptance Criteria

### Phase 1: Database Foundation

- [ ] Database schema creates without errors
- [ ] Composite unique constraint prevents duplicates
- [ ] CV key generation produces consistent hashes
- [ ] Unit tests achieve >80% coverage
- [ ] All unit tests pass

### Phase 2: System A Integration

- [ ] Scraper accepts search_term parameter
- [ ] Scraper writes to database successfully
- [ ] Early exit logic works correctly
- [ ] Matcher checks database before matching
- [ ] No duplicate API calls on second run
- [ ] Integration tests pass

### Phase 3: System B Integration

- [ ] Dashboard queries database successfully
- [ ] JSON fallback works when needed
- [ ] Query response time <100ms
- [ ] Filtering UI functional
- [ ] All dashboard features work

### Phase 4: Production Ready

- [ ] All data migrated successfully
- [ ] Performance targets met
- [ ] Documentation complete
- [ ] No critical bugs
- [ ] User training completed

---

## 🚨 Risk Management

### Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Database corruption** | High | Low | Regular backups, transaction safety |
| **Migration data loss** | High | Medium | Dual-write period, verification |
| **Performance degradation** | Medium | Low | Indexes, query optimization |
| **False duplicates** | Medium | Low | URL normalization, testing |
| **Concurrent access issues** | Medium | Medium | WAL mode, connection pooling |

### Operational Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **User resistance** | Medium | Medium | Training, gradual rollout |
| **Downtime during deployment** | Medium | Low | Blue-green deployment |
| **Rollback complexity** | High | Low | Comprehensive rollback plan |
| **Documentation gaps** | Low | Medium | Thorough documentation review |

---

## 📚 References

### Related Documents

- [System A Deduplication Deep Dive](System%20A%20Deduplication_Deep_Dive.md)
- [System B SQLite Integration Changes](System%20B%20SQLite%20Integration%20Changes.md)
- [Elicitation Iteration 2](Elicitation_Iteration_2.md)
- [Flow Diagrams](flow_future.svg)

### Code References

- Current Scraper: `job-data-acquisition/app.py`
- Current Matcher: `job_matcher.py`
- Current Dashboard: `dashboard.py`
- URL Utilities: `utils/url_utils.py`
- Config Management: `config.py`

---

## 📞 Implementation Support

### Getting Started

1. **Review this document thoroughly**
2. **Set up development environment**
3. **Create feature branch**: `git checkout -b feature/sqlite-deduplication`
4. **Start with Phase 1**: Database foundation
5. **Follow the implementation roadmap**
6. **Run tests after each phase**
7. **Document any deviations**

### Questions & Clarifications

**For technical questions:**
- Review the detailed component specifications
- Check the code examples in this document
- Refer to the deep dive documents

**For architectural decisions:**
- Review the "Architectural Changes" section
- Check the database schema rationale
- Consult the testing strategy

---

## 📝 Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-02 | Winston | Initial comprehensive architecture document |

---

## ✅ Document Status

- **Status:** Ready for Implementation
- **Next Review:** After Phase 1 completion
- **Owner:** Winston (System Architect)
- **Approvers:** PM, Product Owner, Dev Team

---

**END OF DOCUMENT**

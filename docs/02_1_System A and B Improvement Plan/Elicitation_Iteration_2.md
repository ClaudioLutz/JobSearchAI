# System A Improvement Plan - Code Analysis & ReWOO Optimization

## Business Analyst Deep Dive - Iteration 2

**Analysis Date:** 2025-11-02  
**Method Applied:** ReWOO (Reasoning Without Observation) for efficiency optimization  
**Analyst:** Mary (Business Analyst)

---

## 📊 **Current Implementation Analysis**

### **1. Job Scraper (System A - Part 1)**
**File:** `job-data-acquisition/app.py`

#### Current Behavior:
```python
# Loops through pages 1 to max_pages
for page in range(1, max_pages + 1):
    scraper = configure_scraper(url, page)
    results = scraper.run()
    all_results.append(results)
```

#### Key Findings:
- ✅ **Functional:** Scrapes job listings from ostjob.ch
- ❌ **No Deduplication:** Jobs scraped multiple times if script runs multiple times
- ❌ **No Search Term Parameter:** URL is hardcoded in `settings.json`
- ❌ **No CV Key Tracking:** No concept of which CV is being used
- ❌ **No Early Exit:** Continues scraping even if all jobs on page are duplicates
- ❌ **JSON Storage Only:** Saves to `job-data-acquisition/data/job_data_{timestamp}.json`
- ❌ **No Database:** All data in flat files

**Data Structure (Output):**
```json
[
  [  // Page 1
    {"Job Title": "...", "Application URL": "https://...", ...},
    {"Job Title": "...", "Application URL": "https://...", ...}
  ],
  [  // Page 2
    {...},
    {...}
  ]
]
```

---

### **2. Job Matcher (System A - Part 2)**
**File:** `job_matcher.py`

#### Current Behavior:
```python
def match_jobs_with_cv(cv_path, min_score=6, max_jobs=50, max_results=10):
    # Load latest job data JSON file
    job_listings = load_latest_job_data(max_jobs=max_jobs)
    
    # Evaluate each job (calls OpenAI API)
    for job in job_listings:
        evaluation = evaluate_job_match(cv_summary, job)
        matches.append(evaluation)
    
    # Filter by min_score and return top matches
    filtered_matches = [m for m in matches if m["overall_match"] >= min_score]
    return sorted_matches[:max_results]
```

#### Key Findings:
- ✅ **Functional:** Matches jobs to CV using OpenAI
- ❌ **No Deduplication Check:** Re-evaluates same job+CV combination if run multiple times
- ❌ **No Search Term Tracking:** No concept of which search produced this job
- ❌ **No CV Key Tracking:** Uses CV file path, not a unique identifier
- ❌ **Filtering Happens After Matching:** All jobs matched first, then filtered by min_score
- ❌ **JSON Storage Only:** Saves to `job_matches/job_matches_{timestamp}.json`
- ❌ **No Database:** Results stored as flat files
- ⚠️ **Limited Processing:** `max_jobs=50` limits total jobs processed (not per search term)

**Inefficiency Example:**
```
Run 1: Match 50 jobs → Get 10 results (score >= 6)
Run 2: Match same 50 jobs again → Get same 10 results
Cost: 100 OpenAI API calls instead of 0 (all duplicates)
```

---

### **3. Dashboard (System B)**
**File:** `dashboard.py`

#### Current Behavior:
```python
@app.route('/')
def index():
    # List available files
    cv_files = [list of CV files]
    job_data_files = [list of job data JSON files]
    report_files = [list of match report files]
    # Render simple file browser
```

#### Key Findings:
- ✅ **Functional:** Displays available files
- ❌ **No Database Querying:** No ability to filter, sort, search
- ❌ **No Job Selection UI:** Can't select specific jobs for application
- ❌ **File-Based:** Just lists JSON/Markdown files
- ❌ **No Search Term Filter:** Can't filter by which search produced results
- ❌ **No Score Filter:** Can't set min_score threshold in UI
- ❌ **No Date Range Filter:** Can't filter by scrape date
- ❌ **Manual Selection:** User must open file to see matches, then manually proceed

---

## 🧠 **ReWOO Analysis: Pure Reasoning vs Data Dependencies**

### **What Can Be Optimized Through Pure Reasoning (No Code Changes Needed)**

#### 1. **Deduplication Key Structure**
**Reasoning:**
- A job posting URL is the same physical opportunity
- BUT same URL can match different search terms ("IT" and "Data-Analyst")
- AND same URL should be matched against different CVs
- THEREFORE: Composite key = `(URL, search_term, cv_key)`

**Implication:**
```sql
-- Optimal schema
CREATE TABLE job_matches (
    id INTEGER PRIMARY KEY,
    job_url TEXT NOT NULL,
    search_term TEXT NOT NULL,
    cv_key TEXT NOT NULL,
    match_scores JSON,
    scraped_data JSON,
    created_at TIMESTAMP,
    UNIQUE(job_url, search_term, cv_key)  -- Composite unique constraint
);
```

**Why This Works:**
- Same job URL + same search + same CV = SKIP (already matched)
- Same job URL + different search + same CV = MATCH (new context)
- Same job URL + same search + different CV = MATCH (different candidate)

---

#### 2. **Early Exit Strategy**
**Reasoning:**
- If page N has zero new jobs → page N+1 likely all duplicates
- Ostjob.ch search results are chronological (newest first)
- Once all results are duplicates, subsequent pages will be duplicates too

**Optimization:**
```python
for page in range(1, max_pages + 1):
    jobs = scrape_page(page)
    new_jobs_count = 0
    
    for job in jobs:
        if not exists_in_db(job_url, search_term, cv_key):
            new_jobs_count += 1
            # Process job
    
    if new_jobs_count == 0:
        logger.info(f"Page {page}: All jobs are duplicates. Stopping.")
        break  # Don't waste time on remaining pages
```

**Benefit:**
- Saves API calls to scraper
- Reduces processing time
- Avoids unnecessary page loads

---

#### 3. **CV Key Generation Strategy**
**Reasoning:**
- Content hash > timestamp for CV identification
- Same CV content = same match results (idempotent)
- Enables resume-from-interruption scenarios

**Implementation:**
```python
import hashlib

def generate_cv_key(cv_path):
    """Generate unique key based on CV content"""
    with open(cv_path, 'rb') as f:
        cv_bytes = f.read()
    return hashlib.sha256(cv_bytes).hexdigest()[:16]
```

**Benefits:**
- Re-uploading same CV = same key = skip re-matching
- Update CV = new key = re-match needed
- Explicit versioning

---

#### 4. **SQLite vs JSON Storage**
**Reasoning:**
- Need: Filter by date, search_term, score, location
- Need: Sort by match_score
- Need: Complex queries (e.g., "jobs in Zürich with score >= 7 from last week")
- JSON requires: Full file read, manual parsing, O(n) filtering
- SQLite provides: Indexes, WHERE clauses, ORDER BY, efficient queries

**Query Performance:**
```sql
-- Fast with SQLite indexes
SELECT * FROM job_matches 
WHERE search_term = 'IT' 
  AND overall_match >= 7 
  AND created_at > date('now', '-7 days')
ORDER BY overall_match DESC
LIMIT 20;

-- Slow with JSON (must read entire file)
jobs = json.load(file)
filtered = [j for j in jobs 
            if j['search_term'] == 'IT' 
            and j['overall_match'] >= 7 
            and j['date'] > week_ago]
```

---

#### 5. **Match Score Filtering Location**
**Reasoning:**
- Filtering BEFORE matching = Wasted processing (can't know score without matching)
- Filtering AFTER matching = Correct (but current approach still wastes API calls)
- Optimal: Check database first, only match NEW jobs

**Current Waste:**
```python
# Current: Match all 50 jobs, then filter
matches = [evaluate(job) for job in jobs]  # 50 API calls
filtered = [m for m in matches if m['score'] >= 6]  # Maybe 10 results
```

**Optimized:**
```python
# Optimal: Skip already matched jobs
for job in jobs:
    if exists_in_db(job_url, search_term, cv_key):
        continue  # Skip - already matched
    match = evaluate(job)  # API call only for new jobs
    save_to_db(match)
```

---

### **What Requires External Data/Implementation**

1. **Current Database Schema:** Need to inspect existing DB structure (if any)
2. **API Rate Limits:** OpenAI API limits affect batch size decisions
3. **Scraper Settings:** Current `settings.json` configuration
4. **File System Paths:** Where files are currently stored
5. **UI Framework:** What's available for System B interface

---

## 🎯 **Gap Analysis: Current vs Desired State**

### **Critical Gaps**

| Feature | Current State | Desired State | Gap Size |
|---------|---------------|---------------|----------|
| **Storage** | JSON files only | SQLite database | 🔴 LARGE |
| **Deduplication** | None | (URL, search_term, CV) composite key | 🔴 LARGE |
| **Search Term** | Hardcoded URL | Configurable parameter | 🟡 MEDIUM |
| **CV Key** | File path | Content hash | 🟡 MEDIUM |
| **Early Exit** | Always scrapes max_pages | Exit on zero new jobs | 🟢 SMALL |
| **System B UI** | File browser | Query/filter/select interface | 🔴 LARGE |
| **Match Efficiency** | Re-matches duplicates | Skip existing matches | 🔴 LARGE |

---

## ⚡ **Efficiency Optimizations Identified**

### **1. Avoid Redundant Matching**
**Current Problem:** Same job+CV matched multiple times

**Impact:**
```
Scenario: Run scraper twice for same search
- First run: 50 jobs → 50 OpenAI API calls
- Second run: Same 50 jobs → 50 MORE API calls (duplicates)
- Total: 100 API calls
- Necessary: 50 API calls (first run only)
- Waste: 50 API calls (50% waste)
```

**Solution:**
```python
# Before matching, check database
cursor.execute("""
    SELECT 1 FROM job_matches 
    WHERE job_url = ? AND search_term = ? AND cv_key = ?
""", (job_url, search_term, cv_key))

if cursor.fetchone():
    logger.info(f"Skipping already matched job: {job_url}")
    continue  # Don't call OpenAI again
```

**Savings:** 50-90% reduction in API calls on subsequent runs

---

### **2. Early Page Exit**
**Current Problem:** Scrapes all pages even if no new jobs

**Impact:**
```
Scenario: 10 max_pages, but page 3 has all duplicates
- Current: Scrapes pages 3-10 (7 unnecessary page loads)
- Optimized: Stops at page 3
- Savings: 70% fewer page requests
```

**Solution:**
```python
for page in range(1, max_pages + 1):
    jobs = scrape_page(page)
    new_count = process_jobs(jobs)  # Returns count of NEW jobs
    
    if new_count == 0:
        logger.info(f"Page {page}: No new jobs. Exiting.")
        break
```

---

### **3. Batch Processing Optimization**
**Current:** Processes jobs sequentially

**Optimization:**
```python
# Group jobs by novelty
new_jobs = []
duplicate_jobs = []

for job in scraped_jobs:
    if exists_in_db(job_url, search_term, cv_key):
        duplicate_jobs.append(job)
    else:
        new_jobs.append(job)

logger.info(f"New: {len(new_jobs)}, Duplicates: {len(duplicate_jobs)}")

# Only match new jobs
for job in new_jobs:
    match = evaluate_job_match(cv_summary, job)
    save_to_db(match)
```

---

### **4. Search Term Parameterization**
**Current Problem:** URL hardcoded, can't run multiple search terms

**Impact:**
```
User wants to search:
- "IT" jobs
- "Data-Analyst" jobs  
- "Product-Manager" jobs

Current: Must manually edit settings.json, run 3 times
Optimized: Pass search_term as parameter
```

**Solution:**
```python
# In settings.json
{
    "search_terms": ["IT", "Data-Analyst", "Product-Manager"],
    "base_url": "https://www.ostjob.ch/job/suche-{search_term}-seite-"
}

# In app.py
for search_term in config["search_terms"]:
    url = config["base_url"].format(search_term=search_term)
    for page in range(1, max_pages + 1):
        scrape_page(url, page, search_term)
```

---

## 📋 **Implementation Roadmap**

### **Phase 1: Database Foundation (Week 1)**
**Goal:** Replace JSON storage with SQLite

**Tasks:**
1. Create SQLite schema
   ```sql
   CREATE TABLE job_matches (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       job_url TEXT NOT NULL,
       search_term TEXT NOT NULL,
       cv_key TEXT NOT NULL,
       job_title TEXT,
       company_name TEXT,
       location TEXT,
       overall_match INTEGER,
       skills_match INTEGER,
       experience_match INTEGER,
       education_fit INTEGER,
       career_trajectory_alignment INTEGER,
       preference_match INTEGER,
       potential_satisfaction INTEGER,
       location_compatibility TEXT,
       reasoning TEXT,
       scraped_data JSON,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       UNIQUE(job_url, search_term, cv_key)
   );
   
   CREATE INDEX idx_search_term ON job_matches(search_term);
   CREATE INDEX idx_match_score ON job_matches(overall_match);
   CREATE INDEX idx_created_at ON job_matches(created_at);
   ```

2. Create database utility module (`utils/db_utils.py`)
   - `get_db_connection()`
   - `init_database()`
   - `job_exists(job_url, search_term, cv_key)`
   - `insert_job_match(match_data)`
   - `query_matches(filters)`

3. Update job_matcher.py to use database
   - Replace `save_json_file()` with `insert_job_match()`
   - Add deduplication check before matching
   - Keep JSON export for compatibility

**Acceptance Criteria:**
- ✅ Database created with correct schema
- ✅ All new matches saved to database
- ✅ No duplicate (URL, search_term, cv_key) entries
- ✅ Existing JSON export still works

---

### **Phase 2: Scraper Enhancements (Week 2)**
**Goal:** Add search_term parameter and deduplication

**Tasks:**
1. Add CV key generation
   ```python
   # In utils/cv_utils.py
   def generate_cv_key(cv_path):
       with open(cv_path, 'rb') as f:
           return hashlib.sha256(f.read()).hexdigest()[:16]
   ```

2. Update settings.json
   ```json
   {
       "search_terms": ["IT", "Data-Analyst"],
       "base_url": "https://www.ostjob.ch/job/suche-{search_term}-seite-",
       "cv_path": "process_cv/cv-data/input/Lebenslauf.pdf",
       "max_pages": 10
   }
   ```

3. Update scraper to accept search_term
   ```python
   def run_scraper(search_term, cv_key):
       for page in range(1, max_pages + 1):
           jobs = scrape_page(search_term, page)
           new_count = 0
           
           for job in jobs:
               if not job_exists(job['url'], search_term, cv_key):
                   new_count += 1
                   # Process job
           
           if new_count == 0:
               break  # Early exit
   ```

4. Update job_matcher.py to check database
   ```python
   for job in job_listings:
       if job_exists(job['Application URL'], search_term, cv_key):
           continue  # Skip already matched
       
       evaluation = evaluate_job_match(cv_summary, job)
       insert_job_match(evaluation)
   ```

**Acceptance Criteria:**
- ✅ Can run multiple search terms in one execution
- ✅ Duplicate jobs skipped automatically
- ✅ Early exit when page has zero new jobs
- ✅ CV identified by content hash

---

### **Phase 3: System B UI Overhaul (Week 3)**
**Goal:** Create query/filter/select interface

**Tasks:**
1. Create new dashboard route `/jobs/browse`
   ```python
   @app.route('/jobs/browse')
   def browse_jobs():
       filters = {
           'search_term': request.args.get('search_term'),
           'min_score': request.args.get('min_score', 6),
           'date_from': request.args.get('date_from'),
           'date_to': request.args.get('date_to'),
           'location': request.args.get('location')
       }
       
       matches = query_matches(filters)
       return render_template('jobs_browse.html', matches=matches)
   ```

2. Create filter UI template
   - Search term dropdown
   - Score slider (1-10)
   - Date range picker
   - Location filter
   - Sort options (score, date, location)

3. Add job selection checkboxes
   - Multi-select interface
   - "Generate Applications" button
   - Batch processing for selected jobs

4. Create job detail modal
   - Show full job description
   - Display match reasoning
   - Link to original job posting
   - "Generate Letter" button

**Acceptance Criteria:**
- ✅ Can filter jobs by search_term, score, date, location
- ✅ Results sortable by multiple criteria
- ✅ Can select multiple jobs for batch processing
- ✅ Click job to see full details

---

### **Phase 4: Testing & Validation (Week 4)**
**Goal:** Ensure system works end-to-end

**Tasks:**
1. Test deduplication
   - Run scraper twice with same search_term
   - Verify zero duplicate matches in database
   - Verify zero duplicate API calls

2. Test multi-search
   - Run scraper with ["IT", "Data-Analyst"]
   - Verify same URL appears for both searches
   - Verify separate match records per search

3. Test CV versioning
   - Match jobs with CV version 1
   - Update CV (new content)
   - Verify CV key changes
   - Verify re-matching triggered

4. Test System B filtering
   - Create test data with various scores/dates/locations
   - Verify filters work correctly
   - Verify sort options work

5. Performance testing
   - Measure API call reduction (target: 70%+)
   - Measure query response time (target: <100ms)
   - Measure scraper efficiency (target: 50%+ fewer pages)

**Acceptance Criteria:**
- ✅ Zero duplicate matches in database
- ✅ 70%+ reduction in API calls on repeat runs
- ✅ Queries return in <100ms
- ✅ All filters functional

---

## 🔍 **Key Metrics for Success**

### **Efficiency Metrics**
| Metric | Baseline (Current) | Target (Optimized) | Measurement |
|--------|--------------------|--------------------|-------------|
| API Calls (Repeat Run) | 50 | 0-5 | Count OpenAI calls |
| Pages Scraped | 10 (always) | 3-5 (avg) | Log page loads |
| Database Queries | N/A (JSON) | <100ms | Query timing |
| Duplicate Job Matches | Unlimited | 0 | UNIQUE constraint violations |

### **Functional Metrics**
| Feature | Current | Target | Status |
|---------|---------|--------|--------|
| Multi-Search Support | ❌ | ✅ | 🔨 Build |
| CV Versioning | ❌ | ✅ | 🔨 Build |
| Deduplication | ❌ | ✅ | 🔨 Build |
| Query/Filter UI | ❌ | ✅ | 🔨 Build |
| Early Page Exit | ❌ | ✅ | 🔨 Build |

---

## 💡 **Recommendations Summary**

### **High Priority (Do First)**
1. **Implement SQLite Database** - Foundation for all other improvements
2. **Add Deduplication Logic** - Biggest efficiency gain (70%+ API savings)
3. **Add search_term Parameter** - Enables multi-search capability

### **Medium Priority (Do Second)**
4. **Implement CV Key Generation** - Enables version tracking
5. **Add Early Page Exit** - Reduces unnecessary scraping

### **Lower Priority (Do Third)**
6. **Build System B Query UI** - Nice to have, but can work with database queries manually first
7. **Add Advanced Filtering** - Polish after core functionality works

---

## 🎯 **Next Steps**

1. **Review this analysis** with stakeholders
2. **Prioritize phases** based on business value
3. **Create detailed user stories** for Phase 1 tasks
4. **Set up development environment** with SQLite
5. **Begin Phase 1 implementation**

---

## 📚 **References**

- Current Implementation: `job-data-acquisition/app.py`, `job_matcher.py`, `dashboard.py`
- Flow Diagrams: `docs/System A Improvement Plan/flow_current.svg`, `flow_future.svg`
- Previous Analysis: `docs/System A Improvement Plan/Elicitation_Iteration_1.md`

---

**Document Status:** ✅ Complete  
**Last Updated:** 2025-11-02  
**Next Review:** After Phase 1 completion

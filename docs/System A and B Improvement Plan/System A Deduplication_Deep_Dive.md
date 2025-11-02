# System A Deduplication - Comprehensive Deep Dive

## Business Analyst Advanced Elicitation - Deduplication Strategy
**Analysis Date:** 2025-11-02  
**Analyst:** Mary (Business Analyst)  
**Method:** Advanced Elicitation with Technical Implementation Focus  
**Purpose:** Deep dive into deduplication architecture, implementation, and migration strategy

---

## 📋 Executive Summary

This document provides a comprehensive analysis of the deduplication strategy for System A (Job Scraper + Job Matcher). The current implementation has **no deduplication**, resulting in:
- **Wasted API calls** (50-90% redundant on repeat runs)
- **Duplicate database entries** (same job matched multiple times)
- **Inefficient scraping** (continues even when all jobs are duplicates)
- **No CV versioning** (can't track which CV version was used)

**Solution:** Implement a composite key deduplication strategy based on `(job_url, search_term, cv_key)` stored in SQLite database with early-exit optimization.

---

## 🎯 Core Deduplication Concept

### The Three-Dimensional Problem

Deduplication in this system is **not just about job URLs**. We have three independent dimensions:

```
Dimension 1: Job URL (the physical job posting)
Dimension 2: Search Term (the query that found the job)
Dimension 3: CV Key (the candidate's resume version)
```

### Why All Three Dimensions Matter

#### **Scenario 1: Same Job URL, Different Search Terms**
```
Job URL: https://ostjob.ch/job/12345 (Senior Data Engineer)

Search Term #1: "IT" → Found this job
Search Term #2: "Data-Analyst" → Found same job
Search Term #3: "Software-Engineer" → Found same job

Question: Should we match this job three times?
Answer: YES! Different search contexts may produce different match scores.
```

**Reasoning:**
- When found via "IT" → Generic match, maybe score 6/10
- When found via "Data-Analyst" → Specific match, maybe score 8/10
- When found via "Software-Engineer" → Tangential match, maybe score 5/10

The **search_term provides context** that affects the matching algorithm's evaluation.

#### **Scenario 2: Same Job URL, Different CV Versions**
```
Job URL: https://ostjob.ch/job/12345 (Senior Data Engineer)
CV Version 1 (before): Python, SQL (2 years experience)
CV Version 2 (after): Python, SQL, Spark, Kubernetes (5 years experience)

Question: Should we match this job twice?
Answer: YES! The match score will be completely different.
```

**Reasoning:**
- CV v1 → Overall match might be 6/10
- CV v2 → Overall match might be 9/10

**User update their CV to be more competitive** → System must re-evaluate all jobs.

#### **Scenario 3: True Duplicates**
```
Job URL: https://ostjob.ch/job/12345
Search Term: "IT"
CV Key: abc123

Run #1: Match this job → Score 7/10
Run #2 (same day): Should we re-match?
Answer: NO! This is a true duplicate.
```

**Reasoning:**
- Same URL + Same search context + Same CV = Identical result
- No value in calling OpenAI API again
- **Skip this job entirely**

### The Composite Key Solution

```sql
UNIQUE(job_url, search_term, cv_key)
```

This constraint ensures:
✅ Same job can appear for different searches
✅ Same job can be re-evaluated for different CV versions
❌ Same job + same search + same CV = rejected as duplicate

---

## 🔍 Current Implementation Analysis

### Current Scraper Flow (job-data-acquisition/app.py)

```python
def run_scraper():
    all_results = []
    max_pages = CONFIG["scraper"].get("max_pages", 50)
    
    for url in target_urls:
        for page in range(1, max_pages + 1):
            scraper = configure_scraper(url, page)
            results = scraper.run()
            all_results.append(results)
    
    # Save to JSON with timestamp
    output_file = f"{output_dir}/{file_prefix}{timestamp}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
```

**Problems Identified:**
1. ❌ No database check - every run creates new file
2. ❌ No search_term tracking - URL is hardcoded in settings.json
3. ❌ No early exit - always scrapes all max_pages
4. ❌ No CV association - scraper doesn't know which CV will use this data
5. ❌ No deduplication - same jobs scraped repeatedly

### Current Matcher Flow (job_matcher.py)

```python
def match_jobs_with_cv(cv_path, min_score=6, max_jobs=50, max_results=10):
    cv_text = extract_cv_text(cv_path)
    cv_summary = summarize_cv(cv_text)
    
    job_listings = load_latest_job_data(max_jobs=max_jobs)
    
    matches = []
    for job in job_listings:
        evaluation = evaluate_job_match(cv_summary, job)  # OpenAI API call
        matches.append(evaluation)
    
    filtered_matches = [m for m in matches if m["overall_match"] >= min_score]
    return sorted(filtered_matches, key=lambda x: x["overall_match"], reverse=True)[:max_results]
```

**Problems Identified:**
1. ❌ No database check - re-evaluates already matched jobs
2. ❌ No search_term tracking - can't filter by which search found the job
3. ❌ No CV key - uses file path instead of content hash
4. ❌ No deduplication - same job+CV matched multiple times
5. ❌ Filters AFTER matching - wastes API calls on low-scoring jobs (though unavoidable)

---

## 🗄️ Database Schema Design

### Recommended SQLite Schema

```sql
-- Main table for job matches
CREATE TABLE job_matches (
    -- Primary key
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Composite unique constraint (deduplication key)
    job_url TEXT NOT NULL,
    search_term TEXT NOT NULL,
    cv_key TEXT NOT NULL,
    
    -- Job metadata
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
    
    -- Raw data (stored as JSON for flexibility)
    scraped_data JSON NOT NULL,
    
    -- Timestamps
    scraped_at TIMESTAMP NOT NULL,
    matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure no duplicates for same job+search+CV combination
    UNIQUE(job_url, search_term, cv_key)
);

-- Indexes for fast querying
CREATE INDEX idx_search_term ON job_matches(search_term);
CREATE INDEX idx_cv_key ON job_matches(cv_key);
CREATE INDEX idx_overall_match ON job_matches(overall_match);
CREATE INDEX idx_matched_at ON job_matches(matched_at);
CREATE INDEX idx_location ON job_matches(location);
CREATE INDEX idx_compound ON job_matches(search_term, cv_key, overall_match);

-- Table for CV metadata (optional but recommended)
CREATE TABLE cv_versions (
    cv_key TEXT PRIMARY KEY,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    summary TEXT,
    metadata JSON
);

-- Table for scraping history (optional but useful for monitoring)
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

### Why JSON for scraped_data?

```python
# The scraped_data field stores the complete job posting:
{
    "Job Title": "Senior Data Engineer",
    "Company Name": "Tech Corp",
    "Job Description": "Full description here...",
    "Required Skills": "Python, SQL, Spark",
    "Location": "Zürich",
    "Salary Range": "120-150k CHF",
    "Posting Date": "01.11.2025",
    "Application URL": "https://ostjob.ch/job/12345",
    
    # Additional fields that might be added later
    "Benefits": ["Remote work", "Health insurance"],
    "Company Size": "50-200 employees",
    "Employment Type": "Full-time"
}
```

**Benefits:**
1. **Flexibility** - Can add new fields without schema migration
2. **Complete Data** - Preserves all scraped information
3. **Easy Display** - Can show full job details in UI
4. **Versioning** - Track how scraper output evolves

---

## 🔑 CV Key Generation Strategy

### Content-Based Hashing

```python
import hashlib
from pathlib import Path

def generate_cv_key(cv_path):
    """
    Generate a unique key based on CV content (not filename or timestamp)
    
    Args:
        cv_path (str): Path to CV file
        
    Returns:
        str: 16-character hex string uniquely identifying CV content
    """
    cv_path = Path(cv_path)
    
    if not cv_path.exists():
        raise FileNotFoundError(f"CV file not found: {cv_path}")
    
    # Read file content in binary mode
    with open(cv_path, 'rb') as f:
        cv_bytes = f.read()
    
    # Generate SHA256 hash
    hash_object = hashlib.sha256(cv_bytes)
    hash_hex = hash_object.hexdigest()
    
    # Return first 16 characters (sufficient for uniqueness)
    return hash_hex[:16]

# Example usage:
# CV v1 content: [original resume]
cv_key_v1 = generate_cv_key("Lebenslauf.pdf")
# Result: "a3f4b2c1e8d9f7a6"

# Update CV (add skills, experience)
# CV v2 content: [updated resume]
cv_key_v2 = generate_cv_key("Lebenslauf.pdf")
# Result: "e9d8c7b6a5f4e3d2"  <- Different key!
```

### Why Content Hashing?

**Scenario 1: User updates CV without changing filename**
```
Before: Lebenslauf.pdf (Python, SQL, 2 years)
After:  Lebenslauf.pdf (Python, SQL, Spark, Kubernetes, 5 years)

Timestamp-based: Same key (file hasn't been re-uploaded)
Content-based: Different key ✓ (content changed)
```

**Scenario 2: User re-uploads same CV**
```
Upload #1: Lebenslauf.pdf → key: abc123
Upload #2: Lebenslauf_v2.pdf (but exact same content)

Timestamp-based: Different key (new upload timestamp)
Content-based: Same key ✓ (identical content)
```

**Scenario 3: Resuming after interruption**
```
Run #1: Match 25 jobs, crash
Run #2: Resume matching

Timestamp-based: Different key (system restart)
Content-based: Same key ✓ (can resume from job 26)
```

### CV Version Tracking

```python
def get_or_create_cv_metadata(cv_path, db_conn):
    """
    Get CV key and metadata, creating DB entry if new CV version
    """
    cv_key = generate_cv_key(cv_path)
    
    cursor = db_conn.cursor()
    cursor.execute("SELECT * FROM cv_versions WHERE cv_key = ?", (cv_key,))
    existing = cursor.fetchone()
    
    if existing:
        logger.info(f"Using existing CV version: {cv_key}")
        return cv_key
    
    # New CV version - create metadata entry
    cv_text = extract_cv_text(cv_path)
    cv_summary = summarize_cv(cv_text)
    
    cursor.execute("""
        INSERT INTO cv_versions (cv_key, file_name, file_path, file_hash, summary)
        VALUES (?, ?, ?, ?, ?)
    """, (cv_key, Path(cv_path).name, str(cv_path), cv_key, cv_summary))
    
    db_conn.commit()
    logger.info(f"Created new CV version: {cv_key}")
    
    return cv_key
```

---

## 🚀 Implementation Strategy

### Phase 1: Database Setup

**File: `utils/db_utils.py`**

```python
import sqlite3
import json
from pathlib import Path
from typing import Optional, Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class JobMatchDatabase:
    """Manages database operations for job matching with deduplication"""
    
    def __init__(self, db_path: str = "instance/jobsearchai.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        
    def connect(self):
        """Establish database connection"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Enable column access by name
        return self.conn
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def init_database(self):
        """Initialize database schema"""
        cursor = self.conn.cursor()
        
        # Create job_matches table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS job_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_url TEXT NOT NULL,
                search_term TEXT NOT NULL,
                cv_key TEXT NOT NULL,
                job_title TEXT,
                company_name TEXT,
                location TEXT,
                posting_date TEXT,
                salary_range TEXT,
                overall_match INTEGER NOT NULL,
                skills_match INTEGER,
                experience_match INTEGER,
                education_fit INTEGER,
                career_trajectory_alignment INTEGER,
                preference_match INTEGER,
                potential_satisfaction INTEGER,
                location_compatibility TEXT,
                reasoning TEXT,
                scraped_data JSON NOT NULL,
                scraped_at TIMESTAMP NOT NULL,
                matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(job_url, search_term, cv_key)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_search_term ON job_matches(search_term)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_cv_key ON job_matches(cv_key)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_overall_match ON job_matches(overall_match)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_matched_at ON job_matches(matched_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_location ON job_matches(location)")
        
        # Create cv_versions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cv_versions (
                cv_key TEXT PRIMARY KEY,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                summary TEXT,
                metadata JSON
            )
        """)
        
        # Create scrape_history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scrape_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                search_term TEXT NOT NULL,
                page_number INTEGER NOT NULL,
                jobs_found INTEGER NOT NULL,
                new_jobs INTEGER NOT NULL,
                duplicate_jobs INTEGER NOT NULL,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                duration_seconds REAL
            )
        """)
        
        self.conn.commit()
        logger.info("Database schema initialized")
    
    def job_exists(self, job_url: str, search_term: str, cv_key: str) -> bool:
        """
        Check if job+search+CV combination already exists (deduplication check)
        
        Returns:
            bool: True if combination exists, False otherwise
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 1 FROM job_matches 
            WHERE job_url = ? AND search_term = ? AND cv_key = ?
            LIMIT 1
        """, (job_url, search_term, cv_key))
        
        result = cursor.fetchone()
        return result is not None
    
    def insert_job_match(self, match_data: Dict[str, Any]) -> Optional[int]:
        """
        Insert a new job match into database
        
        Args:
            match_data: Dictionary containing match information
            
        Returns:
            int: ID of inserted row, or None if duplicate
        """
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO job_matches (
                    job_url, search_term, cv_key,
                    job_title, company_name, location, posting_date, salary_range,
                    overall_match, skills_match, experience_match, education_fit,
                    career_trajectory_alignment, preference_match, potential_satisfaction,
                    location_compatibility, reasoning,
                    scraped_data, scraped_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                match_data['job_url'],
                match_data['search_term'],
                match_data['cv_key'],
                match_data.get('job_title'),
                match_data.get('company_name'),
                match_data.get('location'),
                match_data.get('posting_date'),
                match_data.get('salary_range'),
                match_data['overall_match'],
                match_data.get('skills_match'),
                match_data.get('experience_match'),
                match_data.get('education_fit'),
                match_data.get('career_trajectory_alignment'),
                match_data.get('preference_match'),
                match_data.get('potential_satisfaction'),
                match_data.get('location_compatibility'),
                match_data.get('reasoning'),
                json.dumps(match_data.get('scraped_data', {})),
                match_data.get('scraped_at')
            ))
            
            self.conn.commit()
            return cursor.lastrowid
            
        except sqlite3.IntegrityError:
            # Duplicate entry (composite unique constraint violation)
            logger.debug(f"Duplicate job match skipped: {match_data['job_url']}")
            return None
    
    def query_matches(self, filters: Dict[str, Any] = None) -> List[Dict]:
        """
        Query job matches with optional filters
        
        Args:
            filters: Dictionary of filter conditions
            
        Returns:
            List of matching job dictionaries
        """
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM job_matches WHERE 1=1"
        params = []
        
        if filters:
            if 'search_term' in filters:
                query += " AND search_term = ?"
                params.append(filters['search_term'])
            
            if 'cv_key' in filters:
                query += " AND cv_key = ?"
                params.append(filters['cv_key'])
            
            if 'min_score' in filters:
                query += " AND overall_match >= ?"
                params.append(filters['min_score'])
            
            if 'location' in filters:
                query += " AND location LIKE ?"
                params.append(f"%{filters['location']}%")
            
            if 'date_from' in filters:
                query += " AND matched_at >= ?"
                params.append(filters['date_from'])
            
            if 'date_to' in filters:
                query += " AND matched_at <= ?"
                params.append(filters['date_to'])
        
        query += " ORDER BY overall_match DESC, matched_at DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Convert to dictionaries
        results = []
        for row in rows:
            result = dict(row)
            # Parse JSON fields
            if result.get('scraped_data'):
                result['scraped_data'] = json.loads(result['scraped_data'])
            results.append(result)
        
        return results
```

### Phase 2: Updated Scraper with Deduplication

**File: `job-data-acquisition/app.py` (key changes)**

```python
from utils.db_utils import JobMatchDatabase
from utils.cv_utils import generate_cv_key

def run_scraper_with_deduplication(search_term: str, cv_path: str):
    """
    Run scraper with deduplication support
    
    Args:
        search_term: Search keyword (e.g., "IT", "Data-Analyst")
        cv_path: Path to CV file (used to generate cv_key)
    """
    logger = setup_logging()
    
    # Initialize database
    db = JobMatchDatabase()
    db.connect()
    db.init_database()
    
    # Generate CV key
    cv_key = generate_cv_key(cv_path)
    logger.info(f"Using CV key: {cv_key}")
    
    # Build URL with search term
    base_url = "https://www.ostjob.ch/job/suche-{search_term}-seite-"
    url = base_url.format(search_term=search_term)
    
    max_pages = CONFIG["scraper"].get("max_pages", 10)
    all_results = []
    
    for page in range(1, max_pages + 1):
        logger.info(f"Scraping page {page} for search term: {search_term}")
        
        # Scrape page
        scraper = configure_scraper(url, page)
        page_results = scraper.run()
        
        if not isinstance(page_results, list):
            logger.warning(f"Unexpected result format on page {page}")
            continue
        
        # Check for duplicates
        new_jobs = []
        duplicate_count = 0
        
        for job in page_results:
            job_url = job.get('Application URL')
            
            if not job_url:
                logger.warning(f"Job missing URL: {job.get('Job Title', 'Unknown')}")
                continue
            
            # Check if this job+search+CV combination exists
            if db.job_exists(job_url, search_term, cv_key):
                duplicate_count += 1
                logger.debug(f"Duplicate job skipped: {job_url}")
            else:
                new_jobs.append(job)
                logger.info(f"New job found: {job.get('Job Title', 'Unknown')}")
        
        logger.info(f"Page {page}: {len(new_jobs)} new jobs, {duplicate_count} duplicates")
        all_results.extend(new_jobs)
        
        # Early exit if all jobs were duplicates
        if duplicate_count > 0 and len(new_jobs) == 0:
            logger.info(f"Page {page} had zero new jobs. Stopping scrape.")
            break
    
    db.close()
    
    logger.info(f"Scraping complete: {len(all_results)} new jobs found")
    return all_results
```

### Phase 3: Updated Matcher with Deduplication

**File: `job_matcher.py` (key changes)**

```python
from utils.db_utils import JobMatchDatabase
from utils.cv_utils import generate_cv_key

def match_jobs_with_cv_dedup(cv_path, search_term, min_score=6, max_jobs=50):
    """
    Match jobs with deduplication support
    
    Args:
        cv_path: Path to CV file
        search_term: Search term used to find jobs
        min_score: Minimum match score threshold
        max_jobs: Maximum jobs to process
    """
    # Initialize database
    db = JobMatchDatabase()
    db.connect()
    db.init_database()
    
    # Generate CV key
    cv_key = generate_cv_key(cv_path)
    logger.info(f"Using CV key: {cv_key}")
    
    # Extract CV
    cv_text = extract_cv_text(cv_path)
    cv_summary = summarize_cv(cv_text)
    
    # Load job data
    job_listings = load_latest_job_data(max_jobs=max_jobs)
    
    matches = []
    skipped_count = 0
    matched_count = 0
    
    for job in job_listings:
        job_url = job.get('Application URL')
        
        if not job_url:
            logger.warning(f"Job missing URL: {job.get('Job Title', 'Unknown')}")
            continue
        
        # Check if already matched
        if db.job_exists(job_url, search_term, cv_key):
            skipped_count += 1
            logger.debug(f"Already matched, skipping: {job_url}")
            continue
        
        # Evaluate match (OpenAI API call)
        logger.info(f"Evaluating new job: {job.get('Job Title', 'Unknown')}")
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
        row_id = db.insert_job_match(match_data)
        if row_id:
            matched_count += 1
            if evaluation['overall_match'] >= min_score:
                matches.append(match_data)
    
    db.close()
    
    logger.info(f"Matching complete: {matched_count} new matches, {skipped_count} skipped")
    
    # Sort by match score
    matches.sort(key=lambda x: x['overall_match'], reverse=True)
    
    return matches
```

---

## ⚠️ Edge Cases & Gotchas

### Edge Case 1: URL Variations

```python
# Same job, different URL formats:
"https://www.ostjob.ch/job/12345"
"https://ostjob.ch/job/12345"
"http://www.ostjob.ch/job/12345"
"www.ostjob.ch/job/12345"
"ostjob.ch/job/12345"

# Solution: URL normalization
from utils.url_utils import URLNormalizer

normalizer = URLNormalizer()
normalized_url = normalizer.normalize(raw_url)
# All variations → "https://www.ostjob.ch/job/12345"
```

### Edge Case 2: Job Reposted

```python
# Company closes job and reposts with new URL
Old URL: https://ostjob.ch/job/12345
New URL: https://ostjob.ch/job/67890
Content: Identical job posting

# Current behavior: Treated as different job ✓
# Rationale: URL is the unique identifier
# Alternative: Could implement content-based deduplication (complex)
```

### Edge Case 3: Search Term Variations

```python
# User searches multiple related terms:
"IT"
"IT-Jobs"
"it"
"I.T."

# Current behavior: Treated as different searches
# Consideration: Should we normalize search terms?

# Recommendation: Keep as-is for now
# Rationale: Different terms may yield different result sets
```

### Edge Case 4: CV Hash Collision

```python
# Probability of SHA256 collision:
# P(collision) ≈ 1 / (2^256) = practically zero

# Even with 16-char truncation:
# P(collision) ≈ 1 / (2^64) = 1 in 18 quintillion

# Verdict: Hash collision not a concern
```

### Edge Case 5: Database Corruption

```python
# SQLite UNIQUE constraint prevents duplicates at DB level
# But what if constraint is accidentally removed?

# Solution: Add application-level check
def insert_job_match(self, match_data):
    # Double-check before insert
    if self.job_exists(match_data['job_url'], 
                       match_data['search_term'], 
                       match_data['cv_key']):
        logger.warning("Duplicate detected despite DB constraint")
        return None
    
    # Proceed with insert...
```

---

## 📊 Performance Analysis

### Current System (No Deduplication)

```
Run #1: Scrape 50 jobs × Match 50 jobs = 50 API calls
Run #2: Scrape 50 jobs × Match 50 jobs = 50 API calls (ALL DUPLICATES)
Run #3: Scrape 50 jobs × Match 50 jobs = 50 API calls (ALL DUPLICATES)

Total: 150 API calls
Necessary: 50 API calls
Waste: 100 API calls (67% waste)
```

### With Deduplication

```
Run #1: Scrape 50 jobs × Match 50 new jobs = 50 API calls
Run #2: Scrape stops at page 2 (all duplicates) × Match 0 new jobs = 0 API calls
Run #3: Scrape stops at page 1 (all duplicates) × Match 0 new jobs = 0 API calls

Total: 50 API calls
Necessary: 50 API calls
Waste: 0 API calls (0% waste)

Efficiency gain: 67% reduction in API calls
```

### Multi-Search Scenario

```
Search #1 "IT": 50 jobs → 50 API calls
Search #2 "Data-Analyst": 30 unique jobs + 20 overlapping with "IT"
  - 20 already matched (skipped) = 0 API calls
  - 30 new jobs = 30 API calls

Total: 80 API calls
Without dedup: 80 API calls (but would also re-match the 20 overlapping)
With dedup: 80 API calls (but correctly identifies overlaps)

Value: Prevents re-matching same job for different searches
```

---

## 🚦 Migration Strategy: JSON to SQLite

### Step 1: Backward Compatibility

```python
# Keep JSON export for backward compatibility during transition
def save_results_dual_format(matches, db, output_dir):
    """
    Save to both database AND JSON file during migration period
    """
    # Save to database
    for match in matches:
        db.insert_job_match(match)
    
    # Also save to JSON (legacy format)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = f"{output_dir}/job_matches_{timestamp}.json"
    
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(matches, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved to database and JSON: {json_file}")
```

### Step 2: Migrate Existing JSON Files

```python
import glob
import json
from datetime import datetime

def migrate_legacy_json_files(json_dir="job_matches", db_path="instance/jobsearchai.db"):
    """
    Migrate existing JSON match files to database
    
    Args:
        json_dir: Directory containing JSON files
        db_path: Path to SQLite database
    """
    db = JobMatchDatabase(db_path)
    db.connect()
    db.init_database()
    
    json_files = glob.glob(f"{json_dir}/job_matches_*.json")
    
    total_migrated = 0
    total_duplicates = 0
    
    for json_file in json_files:
        logger.info(f"Migrating file: {json_file}")
        
        with open(json_file, 'r', encoding='utf-8') as f:
            matches = json.load(f)
        
        # Extract search_term and cv_key from filename or ask user
        # Format: job_matches_YYYYMMDD_HHMMSS.json
        # We'll need to prompt for search_term and cv_key
        
        print(f"\nProcessing: {json_file}")
        search_term = input("Enter search term for this file (e.g., 'IT'): ")
        cv_path = input("Enter CV path used for this matching: ")
        
        cv_key = generate_cv_key(cv_path)
        
        for match in matches:
            match_data = {
                'job_url': match.get('application_url'),
                'search_term': search_term,
                'cv_key': cv_key,
                'job_title': match.get('job_title'),
                'company_name': match.get('company_name'),
                'location': match.get('location'),
                'posting_date': match.get('posting_date'),
                'salary_range': match.get('salary_range'),
                'overall_match': match.get('overall_match'),
                'skills_match': match.get('skills_match'),
                'experience_match': match.get('experience_match'),
                'education_fit': match.get('education_fit'),
                'career_trajectory_alignment': match.get('career_trajectory_alignment'),
                'preference_match': match.get('preference_match'),
                'potential_satisfaction': match.get('potential_satisfaction'),
                'location_compatibility': match.get('location_compatibility'),
                'reasoning': match.get('reasoning'),
                'scraped_data': {
                    'Job Title': match.get('job_title'),
                    'Company Name': match.get('company_name'),
                    'Job Description': match.get('job_description'),
                    'Location': match.get('location')
                },
                'scraped_at': datetime.now().isoformat()
            }
            
            row_id = db.insert_job_match(match_data)
            
            if row_id:
                total_migrated += 1
            else:
                total_duplicates += 1
    
    db.close()
    
    logger.info(f"Migration complete: {total_migrated} records migrated, {total_duplicates} duplicates skipped")
```

### Step 3: Gradual Rollout

```python
# Phase 1: Enable database writes, keep JSON reads
USE_DATABASE_WRITE = True
USE_DATABASE_READ = False  # Still read from JSON

# Phase 2: Enable database writes and reads, keep JSON writes
USE_DATABASE_WRITE = True
USE_DATABASE_READ = True
KEEP_JSON_BACKUP = True

# Phase 3: Full database mode, optional JSON export
USE_DATABASE_WRITE = True
USE_DATABASE_READ = True
KEEP_JSON_BACKUP = False  # JSON only on demand
```

---

## 🎯 Implementation Checklist

### Phase 1: Foundation (Week 1)
- [ ] Create `utils/db_utils.py` with `JobMatchDatabase` class
- [ ] Create `utils/cv_utils.py` with `generate_cv_key()` function
- [ ] Write database migration script
- [ ] Test database schema creation
- [ ] Test composite unique constraint
- [ ] Verify indexes are created
- [ ] Write unit tests for deduplication logic

### Phase 2: Scraper Integration (Week 2)
- [ ] Update `job-data-acquisition/app.py` to accept `search_term` parameter
- [ ] Update scraper to generate CV key
- [ ] Implement deduplication check in scraper
- [ ] Implement early exit logic (stop when all duplicates)
- [ ] Add scrape_history logging
- [ ] Test scraper with multiple search terms
- [ ] Test early exit behavior
- [ ] Verify no duplicate API calls on re-run

### Phase 3: Matcher Integration (Week 3)
- [ ] Update `job_matcher.py` to accept `search_term` parameter
- [ ] Implement deduplication check before matching
- [ ] Save matches to database instead of JSON
- [ ] Test matcher with existing CV
- [ ] Test matcher with updated CV (different key)
- [ ] Verify API call reduction
- [ ] Test multi-search scenario

### Phase 4: UI Updates (Week 4)
- [ ] Update dashboard to query database instead of JSON files
- [ ] Add search_term filter dropdown
- [ ] Add CV version selector
- [ ] Add date range filter
- [ ] Add score slider filter
- [ ] Add location filter
- [ ] Test filtering performance
- [ ] Verify UI shows correct deduplicated results

### Phase 5: Testing & Validation (Week 5)
- [ ] End-to-end test: Scrape → Match → Display
- [ ] Test duplicate detection accuracy
- [ ] Measure API call reduction (target: 70%+)
- [ ] Test CV update scenario
- [ ] Test multi-search scenario
- [ ] Performance test with 1000+ jobs
- [ ] Verify database integrity
- [ ] Document migration process

---

## 📝 Key Decisions & Rationale

### Decision 1: Composite Key vs Single Job URL Key

**Option A: Simple key (job_url only)**
```sql
UNIQUE(job_url)
```
- ❌ Can't match same job for different searches
- ❌ Can't re-evaluate when CV changes
- ✅ Simpler implementation

**Option B: Composite key (job_url, search_term, cv_key)** ✓ CHOSEN
```sql
UNIQUE(job_url, search_term, cv_key)
```
- ✅ Supports multiple search contexts
- ✅ Supports CV versioning
- ✅ More accurate deduplication
- ⚠️ Slightly more complex

**Rationale:** Option B provides the correct semantics for the use case. Same job has different value in different search contexts.

### Decision 2: Content Hash vs Timestamp for CV Key

**Option A: Timestamp-based**
```python
cv_key = f"cv_{timestamp}"
```
- ❌ Changes on every upload even if content identical
- ❌ Can't resume after interruption
- ✅ Simple to implement

**Option B: Content hash** ✓ CHOSEN
```python
cv_key = hashlib.sha256(cv_content).hexdigest()[:16]
```
- ✅ Idempotent (same content = same key)
- ✅ Detects actual CV changes
- ✅ Enables resume from interruption
- ⚠️ Requires reading file content

**Rationale:** Content hash provides better deduplication accuracy and supports edge cases like resume-from-crash.

### Decision 3: Early Exit Strategy

**Option A: Always scrape max_pages**
```python
for page in range(1, max_pages + 1):
    scrape_page(page)
```
- ❌ Wastes time on duplicate pages
- ❌ Unnecessary API/network calls
- ✅ Predictable behavior

**Option B: Exit when all jobs are duplicates** ✓ CHOSEN
```python
if duplicate_count > 0 and new_jobs_count == 0:
    break
```
- ✅ 50-70% reduction in page loads
- ✅ Faster execution
- ✅ Same end result
- ⚠️ Assumes chronological ordering

**Rationale:** Ostjob.ch results are chronological (newest first). Once all jobs on a page are duplicates, subsequent pages will likely be duplicates too.

### Decision 4: JSON Storage Format

**Option A: Normalized columns only**
```sql
job_title TEXT, company_name TEXT, location TEXT, ...
```
- ❌ Schema migration needed for new fields
- ❌ Loses flexibility
- ✅ Faster queries on specific fields

**Option B: Key fields + JSON blob** ✓ CHOSEN
```sql
job_title TEXT, location TEXT, ..., scraped_data JSON
```
- ✅ Extract key fields for fast queries
- ✅ Preserve complete data in JSON
- ✅ No schema migration for new scraper fields
- ⚠️ Slightly more storage

**Rationale:** Hybrid approach balances query performance with flexibility. Scraper output may evolve over time.

---

## 🔬 Testing Strategy

### Unit Tests

```python
import unittest
from utils.db_utils import JobMatchDatabase
from utils.cv_utils import generate_cv_key

class TestDeduplication(unittest.TestCase):
    
    def setUp(self):
        """Set up test database"""
        self.db = JobMatchDatabase(":memory:")  # In-memory for tests
        self.db.connect()
        self.db.init_database()
    
    def tearDown(self):
        """Clean up"""
        self.db.close()
    
    def test_duplicate_detection(self):
        """Test that duplicates are correctly detected"""
        match_data = {
            'job_url': 'https://ostjob.ch/job/12345',
            'search_term': 'IT',
            'cv_key': 'abc123',
            'job_title': 'Test Job',
            'overall_match': 7,
            'scraped_data': {},
            'scraped_at': '2025-11-02'
        }
        
        # First insert should succeed
        row_id = self.db.insert_job_match(match_data)
        self.assertIsNotNone(row_id)
        
        # Duplicate insert should return None
        row_id_dup = self.db.insert_job_match(match_data)
        self.assertIsNone(row_id_dup)
    
    def test_same_job_different_search(self):
        """Test that same job with different search_term is allowed"""
        match_data_1 = {
            'job_url': 'https://ostjob.ch/job/12345',
            'search_term': 'IT',
            'cv_key': 'abc123',
            'job_title': 'Test Job',
            'overall_match': 7,
            'scraped_data': {},
            'scraped_at': '2025-11-02'
        }
        
        match_data_2 = {
            **match_data_1,
            'search_term': 'Data-Analyst'  # Different search
        }
        
        row_id_1 = self.db.insert_job_match(match_data_1)
        row_id_2 = self.db.insert_job_match(match_data_2)
        
        self.assertIsNotNone(row_id_1)
        self.assertIsNotNone(row_id_2)
        self.assertNotEqual(row_id_1, row_id_2)
    
    def test_cv_key_generation(self):
        """Test CV key generation is consistent"""
        cv_path = "test_cv.pdf"
        
        # Generate key twice
        key1 = generate_cv_key(cv_path)
        key2 = generate_cv_key(cv_path)
        
        # Should be identical
        self.assertEqual(key1, key2)
        
        # Should be 16 characters
        self.assertEqual(len(key1), 16)
```

### Integration Tests

```python
def test_end_to_end_deduplication():
    """Test complete scrape → match → display flow"""
    
    # Run 1: Scrape and match
    search_term = "IT"
    cv_path = "test_cv.pdf"
    
    # Scrape jobs
    scraped_jobs = run_scraper_with_deduplication(search_term, cv_path)
    assert len(scraped_jobs) > 0
    
    # Match jobs
    matches = match_jobs_with_cv_dedup(cv_path, search_term)
    assert len(matches) > 0
    
    # Run 2: Repeat (should find zero new jobs)
    scraped_jobs_2 = run_scraper_with_deduplication(search_term, cv_path)
    assert len(scraped_jobs_2) == 0  # All duplicates
    
    matches_2 = match_jobs_with_cv_dedup(cv_path, search_term)
    assert len(matches_2) == 0  # Already matched
    
    # Verify API call count
    assert api_call_count_run_2 == 0  # No wasted calls
```

---

## 📈 Success Metrics

### Primary Metrics

| Metric | Baseline | Target | Measurement Method |
|--------|----------|--------|-------------------|
| API Call Reduction (repeat runs) | 100% (all duplicates) | <10% | Count OpenAI API calls |
| Pages Scraped (repeat runs) | 100% of max_pages | <30% | Log page scraping events |
| Duplicate Detection Accuracy | N/A (no dedup) | 100% | Unit tests |
| Database Query Speed | N/A | <100ms | Query timing |

### Secondary Metrics

| Metric | Baseline | Target | Measurement Method |
|--------|----------|--------|-------------------|
| Storage Efficiency | JSON files | SQLite DB | Compare file sizes |
| Query Flexibility | None (manual JSON parsing) | Full SQL | Feature testing |
| Multi-Search Support | Manual | Automated | Integration test |
| CV Version Tracking | None | Automated | Feature test |

---

## 🚨 Risks & Mitigation

### Risk 1: Database Corruption
**Impact:** High  
**Probability:** Low  
**Mitigation:**
- Regular database backups
- Transaction-based writes
- Application-level duplicate checking
- Database integrity checks on startup

### Risk 2: Migration Data Loss
**Impact:** High  
**Probability:** Medium  
**Mitigation:**
- Keep JSON files during migration
- Dual-format writes (JSON + DB)
- Verify migrated data before deletion
- Rollback plan

### Risk 3: Performance Degradation
**Impact:** Medium  
**Probability:** Low  
**Mitigation:**
- Database indexes on key columns
- Query optimization
- Connection pooling
- Performance testing with large datasets

### Risk 4: False Duplicates
**Impact:** Medium  
**Probability:** Low  
**Mitigation:**
- URL normalization
- Thorough testing
- Logging of skipped jobs
- Manual review capability

---

## 💡 Future Enhancements

### Enhancement 1: Content-Based Deduplication
```python
# Detect when job is reposted with new URL but same content
def calculate_content_similarity(job1, job2):
    """Use fuzzy matching to detect reposts"""
    from difflib import SequenceMatcher
    
    desc1 = job1['Job Description']
    desc2 = job2['Job Description']
    
    similarity = SequenceMatcher(None, desc1, desc2).ratio()
    
    return similarity > 0.95  # 95% similar = likely duplicate
```

### Enhancement 2: Automatic CV Key Detection
```python
# Automatically detect CV changes and prompt re-matching
def check_cv_changes():
    """Check if CV has changed since last run"""
    current_cv_key = generate_cv_key("Lebenslauf.pdf")
    last_cv_key = get_last_used_cv_key()
    
    if current_cv_key != last_cv_key:
        print("⚠️ CV has changed! Consider re-matching existing jobs.")
        response = input("Re-match all jobs with new CV? (y/n): ")
        
        if response.lower() == 'y':
            re_match_all_jobs(current_cv_key)
```

### Enhancement 3: Smart Early Exit
```python
# More sophisticated early exit based on historical patterns
def should_continue_scraping(page, new_jobs, duplicate_jobs, history):
    """Decide whether to continue scraping based on patterns"""
    
    # Exit if 3 consecutive pages with zero new jobs
    if history.last_3_pages_zero_new_jobs():
        return False
    
    # Exit if duplicate ratio exceeds 90%
    if duplicate_jobs / (new_jobs + duplicate_jobs) > 0.9:
        return False
    
    # Continue otherwise
    return True
```

---

## 📚 References

- **Original Analysis:** `docs/System A Improvement Plan/Elicitation_Iteration_2.md`
- **Architecture Diagrams:** `docs/System A Improvement Plan/flow_future.svg`
- **Current Scraper:** `job-data-acquisition/app.py`
- **Current Matcher:** `job_matcher.py`
- **URL Utilities:** `utils/url_utils.py`

---

## ✅ Conclusion

This comprehensive deduplication strategy addresses all identified inefficiencies in System A:

1. **Composite Key Approach** - Correctly identifies duplicates across three dimensions
2. **Content-Based CV Versioning** - Accurately tracks CV changes
3. **Early Exit Optimization** - Reduces unnecessary scraping by 50-70%
4. **Database-Backed Storage** - Enables efficient querying and filtering
5. **Backward Compatible Migration** - Safe transition from JSON to SQLite

**Expected Benefits:**
- 67% reduction in API calls on repeat runs
- 50-70% reduction in page scraping
- 100% duplicate detection accuracy
- Sub-100ms query response times
- Support for multiple search terms
- Automatic CV version tracking

**Next Steps:**
1. Review this analysis with stakeholders
2. Prioritize implementation phases
3. Begin Phase 1: Database Setup
4. Iterative testing and validation
5. Gradual rollout with monitoring

---

**Document Status:** ✅ Complete  
**Last Updated:** 2025-11-02  
**Next Review:** After implementation begins

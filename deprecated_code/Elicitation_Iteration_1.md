# System A Improvement Plan - Documented Requirements

## Business Analyst Analysis Complete

Based on elicitation session with user and code analysis, here is the refined System A improvement plan:

---

## 📋 **Key Clarifications from User**

### 1. **No Min Score Filtering in System A**
- **Original Plan**: Filter by min_match_score before System B
- **New Plan**: ALL jobs are scored, none filtered
- **Rationale**: User wants flexibility to review all scored jobs

### 2. **SQLite Database Instead of JSON Files**
- **Current**: Job match reports saved as JSON files
- **Future**: Single SQLite table for all job match data
- **Benefits**: 
  - Query by date, keywords, score
  - Sort and filter in System B UI
  - Better data management

### 3. **Search-Term-Specific URL Deduplication**
- **Critical Insight**: Same URL can appear for different search terms
- **Example**: A job ad for "Senior Developer" might match both "IT" AND "Data-Analyst" searches
- **Solution**: Track (URL + search_term) combinations
- **Exit Logic**: Skip ONLY if (URL, search_term) pair already processed

---

## 🎯 **Refined System A Flow**

### **System A Process:**
```
1. User enters search_term (e.g., "IT", "Data-Analyst", "Marketing")
2. User enters max_pages
3. For each page:
   a. Scrape job listings (Title, Company, Location, URL, etc.)
   b. For each job:
      - Check if (URL + search_term) already processed
      - If YES: Skip (already scored for this search)
      - If NO: Continue
   c. Run Job Matcher on ALL scraped jobs
   d. Save ALL scores to SQLite table:
      - job_url
      - search_term
      - match_scores (all metrics)
      - scraped_data
      - timestamp
4. System A Complete
```

### **System B Process** (User-Driven):
```
1. User opens System B UI
2. UI queries SQLite table
3. User applies filters:
   - Search term
   - Date range  
   - Min score threshold
   - Location
   - Keywords
4. User selects jobs to process
5. System B generates applications for selected jobs
```

---

## 🔧 **Implementation Requirements**

### **Phase 1: Database Schema**
```sql
CREATE TABLE job_matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_url TEXT NOT NULL,
    search_term TEXT NOT NULL,
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
    UNIQUE(job_url, search_term)
);
```

### **Phase 2: Scraper Updates**
1. Add `search_term` parameter to settings.json
2. Expose `search_term` in UI form
3. Pass `search_term` to scraper
4. Before matching, check: `SELECT 1 FROM job_matches WHERE job_url = ? AND search_term = ?`
5. Skip if exists, otherwise proceed

### **Phase 3: Job Matcher Updates**
1. Accept `search_term` parameter
2. Save ALL match results to SQLite (no filtering)
3. Include `search_term` in each record

### **Phase 4: System B UI**
1. Query interface for job_matches table
2. Filter controls (date, score, keywords, location, search_term)
3. Sorting options
4. Selection checkboxes
5. "Generate Applications" button for selected jobs

---

## 📊 **Data Flow Diagram**

```
System A (Automated):
┌─────────────┐
│  User Input │ search_term="IT", max_pages=5
└──────┬──────┘
       │
       v
┌─────────────────┐
│  Scrape Jobs    │ Get URLs, Titles, Companies
└───────┬─────────┘
        │
        v
┌────────────────────────┐
│ Check Deduplication    │ (URL, search_term) exists?
│ SELECT FROM job_matches│
└───────┬────────────────┘
        │
     ┌──┴──┐
     │ YES │ → Skip (Already scored for "IT")
     └─────┘
        │ NO
        v
┌───────────────┐
│  Job Matcher  │ Score ALL jobs
└───────┬───────┘
        │
        v
┌─────────────────────┐
│ Save to SQLite      │ INSERT job_matches
│ (URL, search_term,  │
│  all_scores)        │
└─────────────────────┘

System B (Manual):
┌─────────────────┐
│  System B UI    │ User filters/sorts
└───────┬─────────┘
        │
        v
┌─────────────────────┐
│ Query job_matches   │ WHERE score >= 6
│                     │ AND search_term = 'IT'
└───────┬─────────────┘
        │
        v
┌─────────────────────┐
│ User Selects Jobs   │ Checkboxes
└───────┬─────────────┘
        │
        v
┌──────────────────────┐
│ Generate Applications│ System B process
└──────────────────────┘
```

---

## ✅ **Benefits of This Approach**

1. **No Data Loss**: Every job is scored and saved
2. **Flexible Filtering**: User decides which jobs to pursue
3. **Multi-Search Support**: Same job can be scored for different searches
4. **Efficient Deduplication**: Per-search-term tracking prevents redundant work
5. **Queryable History**: SQLite enables powerful queries and analytics
6. **Clear Separation**: System A = Data Collection, System B = Application Generation

---

## 🚀 **Next Steps**

1. **Iterate on this plan** - User will review and refine
2. **Create implementation stories** - Break down into development tasks
3. **Design database schema** - Finalize table structure
4. **Design System B UI** - Mockup filtering interface
5. **Implement incrementally** - Phase by phase rollout

---

## 📝 **Key Decisions Made**

| Decision | Rationale |
|----------|-----------|
| No min_score filtering in System A | User wants all data for flexible filtering later |
| SQLite over JSON | Better querying, sorting, filtering capabilities |
| (URL + search_term) deduplication | Same job can match different search categories |
| System B as manual selection UI | User control over which applications to generate |

---

**Analysis Complete** - Plan documented and ready for next iteration.

This document serves as the foundation for your System A improvements. You can now iterate on this plan with additional refinements as needed.
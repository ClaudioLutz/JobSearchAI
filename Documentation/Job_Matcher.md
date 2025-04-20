# 3. Job Matcher

**Purpose**: Match job listings with candidate profiles using semantic understanding.

**Key Files**:
- `job_matcher.py`: Main script for matching jobs with CVs

**Technologies**:
- OpenAI GPT models for semantic matching
- JSON for data storage
- Markdown for human-readable reports

**Process**:
1. Loads the processed CV summary
2. Loads the latest job data from the job-data-acquisition component
3. For each job listing, uses OpenAI's GPT-4o model to evaluate:
   - Skills match (1-10 scale)
   - Experience match (1-10 scale)
   - Location compatibility (Yes/No)
   - Education fit (1-10 scale)
   - Overall match score (1-10 scale)
   - Reasoning for the match
4. Filters jobs based on a minimum score threshold
5. Sorts jobs by overall match score
6. Generates a report with the top matches

**Functions**:
- `load_latest_job_data(max_jobs=10)`: Loads the most recent job data file
- `evaluate_job_match(cv_summary, job_listing)`: Uses ChatGPT to evaluate how well a job matches the candidate's profile
- `match_jobs_with_cv(cv_path, min_score=6, max_results=10)`: Match jobs with a CV and return the top matches
- `generate_report(matches, output_file=None)`: Generate a report with the top job matches

**Output Format**:
- JSON file with detailed match information
- Markdown report with the top job matches, including:
  - Job title and company
  - Overall match score
  - Skills match score
  - Experience match score
  - Education fit score
  - Location compatibility
  - Reasoning for the match
  - Application URL

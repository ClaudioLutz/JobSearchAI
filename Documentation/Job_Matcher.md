# 3. Job Matcher

**Purpose**: Match job listings with candidate profiles using semantic understanding.

**Key Files**:
- `job_matcher.py`: Main script for matching jobs with CVs. Imports functions from `process_cv.cv_processor`.

**Technologies**:
- OpenAI GPT models (`gpt-4.1`) for semantic matching and evaluation.
- JSON for data storage (both input job data and output match details).
- Markdown for human-readable reports.
- `python-dotenv` for loading API keys.

**Process**:
1. Loads environment variables (including OpenAI API key) from `process_cv/.env`.
2. Processes a given CV file using `extract_cv_text` and `summarize_cv` from `process_cv.cv_processor`.
3. Loads the most recent `job_data_*.json` file from the `job-data-acquisition/job-data-acquisition/data/` directory, handling various potential nested structures within the JSON. Limits the number of jobs processed based on `max_jobs` parameter (default 50). Includes fallback to sample data if loading fails.
4. For each loaded job listing (up to `max_jobs`), uses OpenAI's `gpt-4.1` model (forcing JSON output) to evaluate the match based on the CV summary and job details. The evaluation includes:
   - Skills Match (1-10)
   - Experience Match (1-10)
   - Location Compatibility (Yes/No)
   - Education Fit (1-10)
   - **Career Trajectory Alignment (1-10)**
   - **Preference Match (1-10)**
   - **Potential Satisfaction (1-10)**
   - Overall Match Score (1-10)
   - Reasoning for the match
5. Filters the evaluated jobs based on a minimum `overall_match` score (`min_score`, default 6 in function signature, 3 in `if __name__ == "__main__"`).
6. Sorts the filtered jobs by `overall_match` score in descending order.
7. Generates two output files in the `job_matches` directory (by default):
   - A JSON file (`job_matches_YYYYMMDD_HHMMSS.json`) containing the detailed evaluation results for the top matches (up to `max_results`, default 10).
   - A Markdown report (`job_matches_YYYYMMDD_HHMMSS.md`) summarizing the top matches, including the evaluation scores and reasoning. Attempts to reconstruct `ostjob.ch` URLs.

**Functions**:
- `load_latest_job_data(max_jobs=50)`: Loads the most recent job data file from `job-data-acquisition/job-data-acquisition/data/`, handling potential structures and limiting jobs processed. Includes fallback sample data.
- `evaluate_job_match(cv_summary, job_listing)`: Uses OpenAI (`gpt-4.1`, forced JSON output) to evaluate how well a job matches the candidate's profile based on multiple criteria (including career trajectory, preferences, satisfaction).
- `match_jobs_with_cv(cv_path, min_score=6, max_jobs=50, max_results=10)`: Orchestrates the process: processes CV, loads job data, evaluates matches, filters, sorts, and returns the top results.
- `generate_report(matches, output_file=None, output_dir="job_matches")`: Generates JSON and Markdown reports in the specified output directory. Attempts to reconstruct `ostjob.ch` URLs in the Markdown report.
- `ensure_output_directory(output_dir="job_matches")`: Helper to create the output directory.

**Output Format**:
- **JSON File**: Saved to `job_matches/job_matches_YYYYMMDD_HHMMSS.json` (by default). Contains a list of dictionaries, each representing a matched job with its full evaluation details (all scores, reasoning, job info).
- **Markdown Report**: Saved to `job_matches/job_matches_YYYYMMDD_HHMMSS.md` (by default). Provides a human-readable summary of the top matches, including:
  - Job title and company
  - Overall match score
  - Location
  - Skills match score
  - Experience match score
  - Education fit score
  - Location compatibility
  - **Career Trajectory Alignment score**
  - **Preference Match score**
  - **Potential Satisfaction score**
  - Reasoning for the match
  - Application URL (potentially reconstructed to point to `ostjob.ch`)

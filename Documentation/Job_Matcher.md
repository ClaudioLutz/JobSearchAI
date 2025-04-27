# 3. Job Matcher

**Purpose**: Match job listings with candidate profiles using semantic understanding.

**Key Files**:
- `job_matcher.py`: Main script for matching jobs with CVs. Imports functions from `process_cv.cv_processor`.
- `job_matcher.log`: Log file containing detailed operation logs.

**Technologies**:
- OpenAI GPT models (`gpt-4.1`) for semantic matching and evaluation.
- JSON for data storage (both input job data and output match details).
- Markdown for human-readable reports.
- `python-dotenv` for loading API keys.
- Python's logging module for comprehensive logging.

**Process**:
1. Loads environment variables (including OpenAI API key) from `process_cv/.env`.
2. Processes a given CV file using `extract_cv_text` and `summarize_cv` from `process_cv.cv_processor`.
3. Loads the most recent `job_data_*.json` file from the `job-data-acquisition/data/` directory, handling various potential nested structures:
   - Array of arrays (flattened)
   - Dictionary with "content" key
   - List of dictionaries with "content" keys
   - Flat array of job listings
4. For each loaded job listing (up to `max_jobs`), uses OpenAI's `gpt-4.1` model with a detailed German prompt to evaluate the match based on:
   ```
   1. Fähigkeiten-Übereinstimmung (1-10): Wie gut passen die Fähigkeiten des Kandidaten zu den Anforderungen der Stelle?
   2. Erfahrungspassung (1-10): Ist das Erfahrungsniveau des Kandidaten angemessen?
   3. Standortkompatibilität (Yes/No): Entspricht der Arbeitsort den Präferenzen des Kandidaten?
   4. Ausbildungsübereinstimmung (1-10): Wie gut passt die Ausbildung des Kandidaten zu den Anforderungen?
   5. Karriereverlauf-Übereinstimmung (1-10): Wie gut passt die Stelle zur bisherigen Karriereentwicklung des Kandidaten?
   6. Präferenzen-Übereinstimmung (1-10): Wie gut entspricht die Stelle den beruflichen Präferenzen des Kandidaten?
   7. Potenzielle Zufriedenheit (1-10): Wie wahrscheinlich ist es, dass der Kandidat in dieser Position zufrieden wäre?
   8. Gesamtübereinstimmung (1-10): Wie geeignet ist der Kandidat insgesamt, unter Berücksichtigung aller Faktoren?
   9. Begründung: Erklären Sie kurz Ihre Bewertung.
   ```
5. Filters the evaluated jobs based on a minimum `overall_match` score (default 6 in function signature, but 3 when run directly via `__main__`).
6. Sorts the filtered jobs by `overall_match` score in descending order.
7. Generates two output files in the `job_matches` directory:
   - A JSON file (`job_matches_YYYYMMDD_HHMMSS.json`) containing the detailed evaluation results.
   - A Markdown report (`job_matches_YYYYMMDD_HHMMSS.md`) summarizing the matches.

**Functions**:
- `load_latest_job_data(max_jobs=50)`: 
  - Loads the most recent job data file
  - Handles various nested JSON structures
  - Includes fallback to sample data if loading fails
  - Logs detailed information about the loading process
- `evaluate_job_match(cv_summary, job_listing)`:
  - Uses OpenAI (`gpt-4.1`) with forced JSON output
  - Uses a detailed German prompt for evaluation
  - Returns structured evaluation with scores and reasoning
  - Includes error handling with default scores
- `match_jobs_with_cv(cv_path, min_score=6, max_jobs=50, max_results=10)`:
  - Processes CV and loads job data
  - Evaluates matches and filters by minimum score
  - Returns top matches sorted by overall score
  - Includes comprehensive error handling
- `ensure_output_directory(output_dir="job_matches")`:
  - Creates output directory if it doesn't exist
  - Returns Path object for the directory
- `generate_report(matches, output_file=None, output_dir="job_matches")`:
  - Generates both JSON and Markdown reports
  - Reconstructs ostjob.ch URLs from local paths
  - Formats matches in a readable structure

**Error Handling & Logging**:
- Comprehensive logging to both file and console:
  - File: `job_matcher.log`
  - Format: timestamp, logger name, level, message
  - Level: INFO for normal operations, ERROR for issues
- Fallback mechanisms:
  - Sample job data if loading fails
  - Default scores (0) if evaluation fails
  - Empty list return if CV processing fails
- Detailed error messages and stack traces
- Progress logging for each major operation

**Output Format**:
- **JSON File** (`job_matches_YYYYMMDD_HHMMSS.json`):
  ```json
  [
    {
      "skills_match": 8,
      "experience_match": 7,
      "location_compatibility": "Yes",
      "education_fit": 9,
      "career_trajectory_alignment": 7,
      "preference_match": 8,
      "potential_satisfaction": 8,
      "overall_match": 8,
      "reasoning": "Detailed reasoning here",
      "job_title": "Position Title",
      "company_name": "Company Name",
      "job_description": "Full description",
      "location": "Location",
      "application_url": "URL"
    }
  ]
  ```
- **Markdown Report** (`job_matches_YYYYMMDD_HHMMSS.md`):
  - Formatted sections for each match
  - All evaluation scores and reasoning
  - Reconstructed ostjob.ch URLs:
    - Converts `http://127.0.0.1:5000/path` to `https://www.ostjob.ch/path`
    - Converts `127.0.0.1:5000/path` to `https://www.ostjob.ch/path`
  - Ordered by match score (descending)

**URL Reconstruction**:
The system automatically converts local development URLs to production ostjob.ch URLs in the Markdown report:
- Input: `http://127.0.0.1:5000/jobs/12345` or `127.0.0.1:5000/jobs/12345`
- Output: `https://www.ostjob.ch/jobs/12345`
This ensures the report contains valid, clickable links to the actual job postings.

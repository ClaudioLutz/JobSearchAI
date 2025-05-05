# 3. Job Matcher

**Purpose**: Match job listings with candidate profiles using semantic understanding.

**Key Files**:
- `job_matcher.py`: Main script for matching jobs with CVs. Imports functions from `process_cv.cv_processor`. Fully optimized with centralized configuration, file utility integration, and error handling.
- `job_matcher.log`: Log file containing detailed operation logs.
- `config.py`: Centralized configuration for paths, environment variables, and default parameters.
- `utils/file_utils.py`: Utility functions for file operations with improved error handling.
- `utils/api_utils.py`: Wrappers for OpenAI API operations with retries and caching.
- `utils/decorators.py`: Decorators for error handling, retries, caching, and execution timing.

**Technologies**:
- OpenAI GPT models (`gpt-4.1`) for semantic matching and evaluation.
- JSON for data storage (both input job data and output match details).
- Markdown for human-readable reports.
- Centralized configuration (`config.py`) for consistent settings across the application.
- Utility modules for common operations with improved error handling.
- Decorator patterns for error handling, retries, caching, and performance tracking.
- Type hints for better IDE support and code quality.

**Process**:
1. **Initiation**: User selects a CV and initiates matching via the dashboard (`job_matching_routes.py`). The process runs as a background task with cancellation support.
2. **Configuration Loading**: Loads settings through the centralized `config.py` module.
3. **CV Summary Loading**: Loads the required CV summary using the dashboard's `get_cv_summary` helper function (which utilizes the in-memory cache).
4. **Job Data Loading**: Uses `file_utils.get_latest_file` and `file_utils.load_json_file` to load the most recent job data with improved error handling, handling various potential nested structures:
   - Array of arrays (flattened)
   - Dictionary with "content" key
   - List of dictionaries with "content" keys
   - Flat array of job listings
5. **Evaluation**: For each loaded job listing (up to `max_jobs`), uses the OpenAI client from `api_utils` with improved error handling, retries, and caching to evaluate the match based on:
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
6. **Filtering & Sorting**: Filters the evaluated jobs based on a minimum `overall_match` score (passed from dashboard, default 3). Sorts the filtered jobs by `overall_match` score in descending order.
7. **Report Generation**: Uses `file_utils.ensure_output_directory` and `file_utils.save_json_file` to generate two output files in the configured `job_matches` directory:
   - A JSON file (`job_matches_YYYYMMDD_HHMMSS.json`) containing the detailed evaluation results (including the `cv_path` used).
   - A Markdown report (`job_matches_YYYYMMDD_HHMMSS.md`) summarizing the matches.
8. **Database Update**: Records metadata about the generated report (timestamp, paths, parameters, counts, related CV/batch IDs) in the `JOB_MATCH_REPORTS` table.

**Functions**:
- `load_latest_job_data(max_jobs=50)`: 
  - Uses `file_utils.get_latest_file` to find the most recent job data file
  - Uses `file_utils.load_json_file` with error handling to load the file
  - Uses `file_utils.flatten_nested_job_data` to handle various nested JSON structures
  - Includes fallback to sample data if loading fails
  - Uses the `@handle_exceptions` decorator for consistent error handling
  - Uses the `@log_execution_time` decorator to track performance
- `evaluate_job_match(cv_summary, job_listing)`:
  - Uses `api_utils.openai_client` with built-in retries and caching
  - Uses a detailed German prompt for evaluation with proper JSON formatting (using double curly braces)
  - Returns structured evaluation with scores and reasoning
  - Uses the `@handle_exceptions` decorator with appropriate default return values
  - Uses the `@retry` decorator for API call stability
- `match_jobs_with_cv(cv_path, min_score=3, max_jobs=50, max_results=10)`:
  - **Note**: This function is now primarily called by the dashboard's background task, which handles CV summary loading. If called directly, it would need modification to use the cache helper.
  - Uses `config.get_path()` for consistent file path handling.
  - Loads job data with proper error handling.
  - Evaluates matches and filters by minimum score.
  - Returns top matches sorted by overall score.
  - Uses the `@handle_exceptions` decorator for comprehensive error handling.
  - Uses the `@log_execution_time` decorator to track performance.
- `generate_report(matches, output_file=None, output_dir="job_matches")`:
  - Uses `file_utils.save_json_file` to save JSON with error handling.
  - Generates both JSON and Markdown reports.
  - Reconstructs ostjob.ch URLs from local paths.
  - Formats matches in a readable structure
  - Uses `config.ensure_dir()` for directory management

**Error Handling & Logging**:
- Comprehensive logging to both file and console using the Python logging module:
  - File: `job_matcher.log`
  - Format: timestamp, logger name, level, message
  - Level: INFO for normal operations, ERROR for issues
- Consistent error handling through decorators:
  - `@handle_exceptions`: Provides default return values and logs errors
  - `@retry`: Automatically retries failed operations with exponential backoff
  - `@log_execution_time`: Tracks and logs performance metrics
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

**Optimization Benefits**:
- **Centralized Configuration**: All paths and settings are now managed through `config.py`, providing a single source of truth.
- **Improved Error Handling**: Consistent error handling across all functions using the `@handle_exceptions` decorator.
- **Better API Usage**: OpenAI API calls are now cached, retried, and have better error handling using `api_utils.openai_client`.
- **File Operations**: Common file operations are now handled by `file_utils` with improved error handling and consistency.
- **Performance Tracking**: Critical operations are now tracked with the `@log_execution_time` decorator.
- **Type Hints**: All functions include type hints for better IDE support and code quality.
- **F-string Fixes**: Proper handling of JSON templates in f-strings using double curly braces `{{` and `}}`.

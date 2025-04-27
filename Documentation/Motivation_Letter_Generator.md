# 4. Motivation Letter Generator

**Purpose**: Create personalized motivation letters based on the candidate's CV and job details.

**Key Files**:
- `motivation_letter_generator.py`: Main orchestrator script.
- `job_details_utils.py`: Contains functions for fetching and processing job details. Fully optimized with centralized configuration, file utility integration, and error handling.
- `letter_generation_utils.py`: Contains functions for generating letter content and format. Fully optimized with centralized configuration, file utility integration, and error handling.
- `graph_scraper_utils.py`: Handles job detail extraction using ScrapeGraphAI.
- `config.py`: Centralized configuration for paths, environment variables, and default parameters.
- `utils/file_utils.py`: Utility functions for file operations with improved error handling.
- `utils/api_utils.py`: Wrappers for OpenAI API operations with retries and caching.
- `utils/decorators.py`: Decorators for error handling, retries, caching, and execution timing.
- `job-data-acquisition/settings.json`: Configuration for ScrapeGraphAI (API key, model, etc.).
- `process_cv/.env`: Used for loading the OpenAI API key (as a fallback if not in settings.json).
- `process_cv/cv-data/processed/`: Directory where input CV summaries are expected (e.g., `Lebenslauf_summary.txt`).
- `job-data-acquisition/data/`: Directory where pre-scraped job data is loaded from as a fallback.
- `motivation_letters/`: Output directory for generated letters and scraped data.
  - `motivation_letter_{job_title}.json`: Structured JSON output of the generated letter.
  - `motivation_letter_{job_title}.html`: HTML version of the generated letter.
  - `motivation_letter_{job_title}_scraped_data.json`: Raw job details dictionary used as input for generation.
- `motivation_letter_generator.log`: Log file containing detailed operation logs.

**Technologies**:
- OpenAI GPT models (`gpt-4.1`) for:
    - Structuring text extracted by ScrapeGraphAI (`job_details_utils.py`).
    - Generating personalized motivation letters (`letter_generation_utils.py`).
- Web Scraping:
    - `scrapegraphai`: Primary method for fetching job page content and extracting details (used in `graph_scraper_utils.py`). Relies on Playwright internally.
- JSON for structured data storage (pre-scraped job data, output letter structure).
- HTML for generating a formatted letter view from the JSON structure.
- Centralized configuration (`config.py`) for consistent settings across the application.
- Utility modules for common operations with improved error handling.
- Decorator patterns for error handling, retries, caching, and performance tracking.
- Type hints for better IDE support and code quality.
- Python's logging module for comprehensive logging.
- Standard Python libraries (`os`, `pathlib`, `sys`).

**Process**:
1.  **Initialization and Setup:**
    - Uses centralized configuration through `config.py` for consistent settings
    - Configures logging with both file and console handlers
    - Log format includes timestamp, logger name, level, and message
    - Attempts to import utility functions with graceful fallback
    - Sets up dummy functions if imports fail to prevent NameError

2.  **Load CV Summary:**
    - Uses `file_utils.load_text_file` with improved error handling
    - Uses `config.get_path()` for consistent file path handling
    - Includes comprehensive error handling through decorators
    - Returns None if file not found or read fails

3.  **Get Job Details:**
    - Uses optimized `job_details_utils.get_job_details` with error handling decorators
    - Primary method: Live ScrapeGraphAI extraction
    - Fallback: Pre-scraped data using `file_utils.get_latest_file` and `file_utils.load_json_file`
    - Final fallback: Default dictionary with placeholders
    - Performance tracking with `@log_execution_time` decorator

4.  **Generate Letter Content:**
    - Uses optimized `letter_generation_utils.generate_motivation_letter` with OpenAI API wrapper
    - Uses `api_utils.openai_client` with retries and caching
    - Combines CV summary and job details in prompt with proper JSON formatting (using double curly braces)
    - Includes error handling for JSON parsing through decorators
    - Uses the `@retry` decorator for API call stability

5.  **Save and Return Results:**
    - Uses `file_utils.save_json_file` with improved error handling
    - Generates and saves HTML version
    - Saves raw job details for reference
    - Returns dictionary with file paths using `config.get_path()`
    - Handles both JSON and HTML-only results with consistent error handling

**Functions**:

*   **`motivation_letter_generator.py`**:
    *   `load_cv_summary(cv_filename)`:
        - Uses `file_utils.load_text_file` with error handling
        - Uses `config.get_path()` for consistent file path handling
        - Returns text content or None on failure
        - Uses the `@handle_exceptions` decorator for consistent error handling
    *   `main(cv_filename, job_url)`:
        - Orchestrates the complete process
        - Uses centralized configuration through `config.py`
        - Includes step-by-step logging
        - Handles different result structures with consistent error handling
        - Returns dictionary with file paths or None
        - Uses the `@log_execution_time` decorator to track performance

*   **`job_details_utils.py`** (Fully optimized):
    *   `has_sufficient_content(details_dict)`: 
        - Validates content completeness
        - Uses type hints for better IDE support
    *   `structure_text_with_openai(text_content, source_url, source_type)`: 
        - Structures raw text using `api_utils.openai_client` with retries and caching
        - Uses proper JSON formatting with double curly braces
        - Uses the `@retry` decorator for API call stability
        - Uses the `@handle_exceptions` decorator with appropriate default return values
    *   `get_job_details_from_scraped_data(job_url)`: 
        - Fallback data loader using `file_utils.get_latest_file` and `file_utils.load_json_file`
        - Uses `config.get_path()` for consistent file path handling
        - Uses the `@handle_exceptions` decorator for consistent error handling
    *   `get_job_details(job_url)`: 
        - Main job detail retrieval function with comprehensive error handling
        - Uses the `@log_execution_time` decorator to track performance
        - Uses the `@handle_exceptions` decorator with appropriate default return values

*   **`letter_generation_utils.py`** (Fully optimized):
    *   `json_to_html(motivation_letter_json)`: 
        - JSON to HTML converter with improved error handling
        - Uses the `@handle_exceptions` decorator for consistent error handling
    *   `generate_motivation_letter(cv_summary, job_details)`: 
        - Main letter generator using `api_utils.openai_client` with retries and caching
        - Uses proper JSON formatting with double curly braces
        - Uses the `@retry` decorator for API call stability
        - Uses the `@handle_exceptions` decorator with appropriate default return values
        - Uses the `@log_execution_time` decorator to track performance
    *   `generate_email_text_only(cv_summary, job_details)`: 
        - Email text generator with the same optimizations as `generate_motivation_letter`
        - Uses the `@handle_exceptions` decorator with appropriate default return values

*   **`graph_scraper_utils.py`**:
    *   `load_config()`: Configuration loader
    *   `get_job_details_with_graphscrapeai(job_url)`: Primary scraper function

**Error Handling**:

1. **Import Handling**:
   - Catches ImportError for utility functions
   - Creates dummy functions as fallback
   - Logs critical errors with stack traces
   - Allows script to load but fail gracefully

2. **File Operations**:
   - Uses `file_utils` functions with built-in error handling
   - Uses proper encoding (utf-8)
   - Uses the `@handle_exceptions` decorator for consistent error handling
   - Returns None instead of raising errors

3. **Process Flow**:
   - Step-by-step validation and logging
   - Early returns on critical failures
   - Fallback mechanisms for each stage
   - Detailed error messages in logs
   - Uses the `@log_execution_time` decorator to track performance

4. **Result Handling**:
   - Validates result structure with consistent error handling
   - Handles both JSON and HTML results
   - Logs unexpected result formats
   - Returns consistent output format
   - Uses the `@handle_exceptions` decorator with appropriate default return values

**Logging System**:
- **Configuration**:
  ```python
  logging.basicConfig(
      level=logging.INFO,
      format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
      handlers=[
          logging.FileHandler("motivation_letter_generator.log"),
          logging.StreamHandler()
      ]
  )
  ```
- **Log Levels**:
  - INFO: Normal operations and progress
  - ERROR: Operation failures
  - CRITICAL: Import or setup failures
  - WARNING: Unexpected but non-fatal issues
- **Performance Logging**: 
  - The `@log_execution_time` decorator automatically logs the execution time of decorated functions
  - Helps identify performance bottlenecks

**Output Format**:
- **Letter JSON File**: Complete letter structure including:
  - Candidate and company information
  - Letter components
  - Optional email text
- **Scraped Data JSON File**: Raw job details used for generation
- **HTML File**: Formatted letter representation

**Testing**:
The script includes a test mode when run directly:
```python
if __name__ == "__main__":
    cv_file = "Lebenslauf"
    test_job_url = "https://www.ostjob.ch/job/..."
    generation_result = main(cv_file, test_job_url)
```
This allows for quick testing of the complete generation process.

**Optimization Benefits**:
- **Centralized Configuration**: All paths and settings are now managed through `config.py`, providing a single source of truth.
- **Improved Error Handling**: Consistent error handling across all functions using the `@handle_exceptions` decorator.
- **Better API Usage**: OpenAI API calls are now cached, retried, and have better error handling using `api_utils.openai_client`.
- **File Operations**: Common file operations are now handled by `file_utils` with improved error handling and consistency.
- **Performance Tracking**: Critical operations are now tracked with the `@log_execution_time` decorator.
- **Type Hints**: All functions include type hints for better IDE support and code quality.
- **F-string Fixes**: Proper handling of JSON templates in f-strings using double curly braces `{{` and `}}`.
- **Enhanced File Path Handling**: Improved file path management with `config.get_path()`.

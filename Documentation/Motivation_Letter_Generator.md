# 4. Motivation Letter Generator

**Purpose**: Create personalized motivation letters based on the candidate's CV and job details.

**Key Files**:
- `motivation_letter_generator.py`: Main orchestrator script.
- `job_details_utils.py`: Contains functions for fetching and processing job details.
- `letter_generation_utils.py`: Contains functions for generating letter content and format.
- `graph_scraper_utils.py`: Handles job detail extraction using ScrapeGraphAI.
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
- `python-dotenv` for loading API keys (fallback mechanism).
- Python's logging module for comprehensive logging.
- Standard Python libraries (`os`, `pathlib`, `sys`).

**Process**:
1.  **Initialization and Setup:**
    - Configures logging with both file and console handlers
    - Log format includes timestamp, logger name, level, and message
    - Attempts to import utility functions with graceful fallback
    - Sets up dummy functions if imports fail to prevent NameError

2.  **Load CV Summary:**
    - Uses `load_cv_summary` to read pre-processed CV text
    - Handles paths relative to script location
    - Includes comprehensive error handling and logging
    - Returns None if file not found or read fails

3.  **Get Job Details:**
    - Uses `job_details_utils.get_job_details` for data gathering
    - Primary method: Live ScrapeGraphAI extraction
    - Fallback: Pre-scraped data from latest JSON file
    - Final fallback: Default dictionary with placeholders

4.  **Generate Letter Content:**
    - Uses `letter_generation_utils.generate_motivation_letter`
    - Combines CV summary and job details in prompt
    - Requests structured JSON output from OpenAI
    - Includes error handling for JSON parsing

5.  **Save and Return Results:**
    - Saves JSON letter structure
    - Generates and saves HTML version
    - Saves raw job details for reference
    - Returns dictionary with file paths
    - Handles both JSON and HTML-only results

**Functions**:

*   **`motivation_letter_generator.py`**:
    *   `load_cv_summary(cv_filename)`:
        - Takes base filename (e.g., "Lebenslauf")
        - Constructs path relative to script location
        - Handles file reading with error handling
        - Returns text content or None on failure
    *   `main(cv_filename, job_url)`:
        - Orchestrates the complete process
        - Includes step-by-step logging
        - Handles different result structures
        - Returns dictionary with file paths or None

*   **`job_details_utils.py`**:
    *   `has_sufficient_content(details_dict)`: Validates content completeness
    *   `structure_text_with_openai(text_content, source_url, source_type)`: Structures raw text
    *   `get_job_details_from_scraped_data(job_url)`: Fallback data loader
    *   `get_job_details(job_url)`: Main job detail retrieval function

*   **`letter_generation_utils.py`**:
    *   `json_to_html(motivation_letter_json)`: JSON to HTML converter
    *   `generate_motivation_letter(cv_summary, job_details)`: Main letter generator
    *   `generate_email_text_only(cv_summary, job_details)`: Email text generator

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
   - Validates file existence before reading
   - Uses proper encoding (utf-8)
   - Catches and logs all exceptions
   - Returns None instead of raising errors

3. **Process Flow**:
   - Step-by-step validation and logging
   - Early returns on critical failures
   - Fallback mechanisms for each stage
   - Detailed error messages in logs

4. **Result Handling**:
   - Validates result structure
   - Handles both JSON and HTML results
   - Logs unexpected result formats
   - Returns consistent output format

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

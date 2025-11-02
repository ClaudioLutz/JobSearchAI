# 1. Job Data Acquisition

**Purpose**: Scrape job listings from specified URLs (e.g., ostjob.ch) and store them in a structured format.

**Key Files**:
- `job-data-acquisition/app.py`: Main Python script for scraping job data.
- `job-data-acquisition/settings.json`: JSON configuration file for the scraper. Key settings include:
    - `target_urls`: List of base URLs to scrape (e.g., `["https://www.ostjob.ch/ostjob/Stellenpool.aspx?query=&page="]`). Pagination is handled by appending page numbers.
    - `scraper`: Contains settings:
        - `llm`: Model configuration for ScrapeGraphAI
        - `verbose`: Boolean for detailed output
        - `headless`: Boolean for browser visibility
        - `output_format`: Expected output format
        - `max_pages`: Maximum pages per URL (defaults to 50)
    - `logging`: Contains:
        - `log_directory`: Path for log files
        - `log_level`: Logging level (e.g., "INFO")
    - `data_storage`: Contains:
        - `output_directory`: Where JSON results are saved
        - `file_prefix`: Prefix for output files

**Technologies**:
- ScrapeGraph AI library for intelligent web scraping
- OpenAI GPT models (configured via `settings.json`)
- Python's logging module for comprehensive logging
- JSON for configuration and data storage

**Process**:
1. **Configuration Loading**:
   - Loads settings from `job-data-acquisition/settings.json`
   - Falls back to default values if config loading fails

2. **Logging Setup**:
   - Creates log directory if it doesn't exist
   - Sets up logging with both file and console handlers
   - Uses timestamped log files: `logs/scraper_YYYYMMDD_HHMMSS.log`
   - Falls back to default configuration if needed:
     - Directory: "job-data-acquisition/logs"
     - Level: "INFO"

3. **Scraping Process**:
   - Defines a detailed extraction prompt requesting specific job details in JSON array format
   - Iterates through each target URL
   - For each URL, processes pages 1 through max_pages
   - Configures SmartScraperGraph for each page with:
     - Custom extraction prompt
     - Paginated URL
     - LLM settings from configuration
   - Appends results from each page to a master list

4. **URL Cleaning**:
   - Processes Application URLs before saving
   - Fixes double slashes after protocol
   - Maintains protocol (if present)
   - Logs any URL modifications at debug level

5. **Data Storage**:
   - Creates output directory if it doesn't exist
   - Saves cleaned results to timestamped JSON file
   - Uses configured file prefix and directory

**Functions**:
- `load_config()`:
  - Loads settings from settings.json
  - Returns None if loading fails
  - Uses script directory for relative path resolution

- `setup_logging()`:
  - Configures logging system
  - Creates log directory
  - Sets up file and console handlers
  - Returns logger instance
  - Uses defaults if config is missing

- `configure_scraper(source_url, page)`:
  - Sets up SmartScraperGraph instance
  - Applies configuration from settings
  - Handles URL pagination
  - Raises ValueError if config is missing

- `run_scraper()`:
  - Main orchestration function
  - Handles the complete scraping process
  - Includes error handling per page
  - Cleans and saves results
  - Returns output file path

**Error Handling**:
- Configuration loading errors:
  - Falls back to default logging settings
  - Logs error and continues if possible
- Scraping errors:
  - Catches and logs exceptions per page
  - Continues to next page/URL
  - Maintains partial results
- Directory creation:
  - Creates missing directories as needed
  - Uses exist_ok=True to prevent race conditions
- URL cleaning:
  - Validates data types before processing
  - Preserves original data if format unexpected
  - Logs cleaning operations at debug level

**Output Format**:
The script saves a JSON file containing a list of page results. Each page result is a list of job objects:

```json
[
  // Page 1 Results
  [
    {
      "Job Title": "Software Engineer",
      "Company Name": "Innovate Inc.",
      "Job Description": "...",
      "Required Skills": "Python, Docker, Kubernetes",
      "Location": "Zurich",
      "Salary Range": "100,000 - 120,000 CHF",
      "Posting Date": "15.04.2025",
      "Application URL": "https://example.com/jobs/swe"  // Cleaned URL
    },
    // ... more jobs from page 1
  ],
  // Page 2 Results
  [
    // ... jobs from page 2
  ],
  // ... subsequent pages
]
```

**Extraction Prompt**:
The system uses this specific prompt for consistent data extraction:
```
Extract **all** job postings from the page. For each job listing, return a JSON object with the following fields:
1. Job Title
2. Company Name
3. Job Description
4. Required Skills
5. Location
6. Salary Range
7. Posting Date
8. Application URL

**Output** should be a **JSON array** of objects, one for each of the job listing found on the page.
```

This prompt ensures structured data extraction and consistent output format across all pages.

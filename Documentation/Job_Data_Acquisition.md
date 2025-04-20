# 1. Job Data Acquisition

**Purpose**: Scrape job listings from specified URLs (e.g., ostjob.ch) and store them in a structured format.

**Key Files**:
- `job-data-acquisition/app.py`: Main Python script for scraping job data.
- `job-data-acquisition/settings.json`: JSON configuration file for the scraper. Key settings include:
    - `target_urls`: List of base URLs to scrape (e.g., `["https://www.ostjob.ch/ostjob/Stellenpool.aspx?query=&page="]`). Pagination is handled by appending page numbers.
    - `scraper`: Contains settings like `llm` (model configuration), `verbose`, `headless`, `output_format`, and `max_pages` (maximum pages per URL, defaults to 50).
    - `logging`: Contains `log_directory` and `log_level`.
    - `data_storage`: Contains `output_directory` (where JSON results are saved) and `file_prefix` for the output file.

**Technologies**:
- ScrapeGraph AI library for intelligent web scraping.
- OpenAI GPT models (configured via `settings.json`) for extracting structured data from web pages.

**Process**:
1. Loads configuration from `job-data-acquisition/settings.json`.
2. Sets up logging based on configuration (level and directory). Logs are written to a timestamped file (e.g., `logs/scraper_YYYYMMDD_HHMMSS.log`).
3. Defines a detailed prompt (`EXTRACTION_PROMPT`) for the LLM, asking for specific job details (Job Title, Company Name, Description, Skills, Location, Salary, Date, URL) in a JSON array format for each page.
4. Iterates through each `target_url` defined in the configuration.
5. For each URL, iterates through pages from 1 up to `max_pages` (default 50). Pagination is handled by appending the page number to the base URL (e.g., `base_url/1`, `base_url/2`).
6. Configures and runs the `SmartScraperGraph` for each page URL using the defined prompt and LLM settings.
7. Appends the results (expected to be a list of job dictionaries per page) from each successfully scraped page to an overall list. Basic error handling logs issues but allows the script to continue.
8. Saves the aggregated results (a list containing the results from each page, potentially a list of lists) to a single timestamped JSON file (e.g., `data/job_data_YYYYMMDD_HHMMSS.json`) in the configured `output_directory`.

**Output Format**:
The script saves a JSON file containing a list. Each element in this list corresponds to the results scraped from a single page. If the scraper successfully extracts a list of job objects per page as requested by the prompt, the final structure will be a list of lists:

```json
[
  // Results from page 1 (expected to be a list of job objects)
  [
    {
      "Job Title": "Software Engineer",
      "Company Name": "Innovate Inc.",
      "Job Description": "...",
      "Required Skills": "Python, Docker, Kubernetes",
      "Location": "Zurich",
      "Salary Range": "100,000 - 120,000 CHF",
      "Posting Date": "15.04.2025",
      "Application URL": "https://example.com/jobs/swe"
    },
    // ... more jobs from page 1
  ],
  // Results from page 2
  [
    {
      "Job Title": "Data Scientist",
      "Company Name": "Data Corp.",
      "Job Description": "...",
      "Required Skills": "R, Python, Machine Learning",
      "Location": "Geneva",
      "Salary Range": null, // Example if not found
      "Posting Date": "16.04.2025",
      "Application URL": "https://example.com/jobs/ds"
    },
    // ... more jobs from page 2
  ],
  // ... results from subsequent pages
]

# 1. Job Data Acquisition

**Purpose**: Scrape job listings from ostjob.ch and store them in a structured format.

**Key Files**:
- `job-data-acquisition/app.py`: Main script for scraping job data
- `job-data-acquisition/settings.json`: Configuration for the scraper

**Technologies**:
- ScrapeGraph AI library for intelligent web scraping
- OpenAI GPT models for extracting structured data from web pages

**Process**:
1. Loads configuration from `settings.json`
2. Sets up logging
3. Configures the ScrapeGraph scraper with a prompt to extract job details
4. Scrapes job listings from the configured URLs (ostjob.ch) up to the configured maximum number of pages
5. Saves the extracted data to a timestamped JSON file in the `data` directory

**Output Format**:
```json
[
  {
    "content": [
      {
        "Job Title": "Data Analyst",
        "Company Name": "Tech Solutions AG",
        "Job Description": "...",
        "Required Skills": "SQL, Python, Power BI, Excel",
        "Location": "St. Gallen",
        "Salary Range": "80,000 - 95,000 CHF",
        "Posting Date": "01.04.2025",
        "Application URL": "https://example.com/jobs/data-analyst"
      },
      // More job listings...
    ]
  }
]

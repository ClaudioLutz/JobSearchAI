# Job Data Acquisition

A Python application for scraping job postings from [OstJob](https://www.ostjob.ch/job/alle-jobs) using the ScrapeGraph AI library.

## Overview

This application uses the ScrapeGraph AI library to extract structured data from job postings. It leverages a language model (gpt-4o-mini) to intelligently parse job listings and extract key information such as job title, company name, job description, required skills, location, salary range, posting date, and application URL.

## Project Structure

```
job-data-acquisition/
├── app.py            # Main application script
├── settings.json     # Configuration settings (ignored in git)
├── data/             # Directory for storing scraped data
├── logs/             # Directory for storing log files
└── dependencies.txt  # List of required dependencies
```

## Requirements

- Python 3.8+
- Virtual environment (recommended)
- Dependencies listed in `dependencies.txt`:
  - scrapegraphai
  - playwright

## Setup

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On macOS/Linux
   source venv/bin/activate
   ```

2. Install the required dependencies:
   ```bash
   pip install -r dependencies.txt
   ```

3. Install Playwright browsers:
   ```bash
   playwright install
   ```

## Configuration

The application is configured through a `settings.json` file located in the same directory as `app.py` (this file is not tracked in version control), which includes:

- Scraper settings (model, token limits, temperature, etc.)
  - `max_pages`: Maximum number of pages to scrape (default: 50)
- Target URLs to scrape
- Data storage configuration
- Logging settings
- Extraction fields

## Usage

Run the application with:

```bash
python app.py
```

The application will:
1. Load configuration from `settings.json`
2. Set up logging
3. Configure the ScrapeGraph scraper
4. Scrape job listings from the configured URLs
5. Save the extracted data to a timestamped JSON file in the `data` directory

## Output

The scraped data is saved as a JSON file in the `data` directory with a timestamp in the filename. Each job listing is represented as a JSON object with the following fields:

- Job Title
- Company Name
- Job Description
- Required Skills
- Location
- Salary Range
- Posting Date
- Application URL

## Logging

Logs are saved to the `logs` directory with timestamps in the filenames. The log level can be configured in `settings.json`.

# JobsearchAI Documentation

## Overview

JobsearchAI is a system that matches job listings with candidate CVs using AI-powered semantic matching. The system uses natural language processing and AI to understand both job listings and candidate profiles, providing intelligent job recommendations based on skills, experience, education, and location preferences.

## System Architecture

The system consists of five main components:

1. **Job Data Acquisition**: Scrapes job listings from ostjob.ch and saves them in a structured JSON format.
2. **CV Processor**: Extracts and summarizes information from candidate CVs.
3. **Job Matcher**: Matches job listings with candidate profiles using semantic understanding.
4. **Motivation Letter Generator**: Creates personalized motivation letters based on the candidate's CV and job details.
5. **Dashboard**: Provides a web interface for interacting with all components of the system.

### Component Interaction

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Job Data       │     │  CV             │     │  Job            │
│  Acquisition    │     │  Processor      │     │  Matcher        │
│                 │     │                 │     │                 │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│  Job Listings   │────▶│  Processed CV   │────▶│  Match Results  │
│  (JSON)         │     │  Summary        │     │  (JSON/MD)      │
│                 │     │                 │     │                 │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────┬───────┴───────────────┬───────┘
                         │                       │
                         ▼                       ▼
                  ┌─────────────────┐    ┌─────────────────┐
                  │                 │    │                 │
                  │   Dashboard     │───▶│  Web Browser    │
                  │                 │    │                 │
                  └─────────────────┘    └─────────────────┘
```

## Detailed Component Description

### 1. Job Data Acquisition

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
```

### 2. CV Processor

**Purpose**: Extract and summarize information from candidate CVs.

**Key Files**:
- `process_cv/cv_processor.py`: Main script for processing CVs
- `process_cv/.env`: Environment variables (OpenAI API key)

**Technologies**:
- PyMuPDF (fitz) for PDF text extraction
- python-docx for DOCX text extraction
- OpenAI GPT models for CV summarization

**Process**:
1. Extracts text from PDF or DOCX CV files
2. Uses OpenAI's GPT-4o model to summarize the CV text
3. Returns a structured summary of the candidate's skills, experience, education, and preferences

**Supported File Formats**:
- PDF (.pdf)
- Microsoft Word (.docx)

**Functions**:
- `extract_text_from_pdf(pdf_path)`: Extracts text from PDF files
- `extract_text_from_docx(docx_path)`: Extracts text from DOCX files
- `extract_cv_text(file_path)`: General function that handles both file types
- `summarize_cv(cv_text)`: Uses OpenAI to generate a structured summary of the CV

### 3. Job Matcher

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

### 4. Motivation Letter Generator

**Purpose**: Create personalized motivation letters based on the candidate's CV and job details.

**Key Files**:
- `motivation_letter_generator.py`: Main script for generating motivation letters
- `templates/motivation_letter.html`: Template for displaying the generated letter

**Technologies**:
- OpenAI GPT-4o model for generating personalized motivation letters
- ScrapeGraph AI for extracting detailed job information from websites
- Flask for web interface integration
- HTML/CSS for letter formatting and display

**Process**:
1. Extracts detailed job information directly from the job posting website using ScrapeGraph AI
2. Loads the processed CV summary
3. Combines the job details and CV information to generate a personalized motivation letter
4. Formats the letter in HTML with proper structure and styling
5. Saves the generated letter to a file with a timestamp in the filename

**Features**:
- Direct web scraping of job details for up-to-date information
- Fallback mechanism to use pre-scraped data if web scraping fails
- Detailed logging for troubleshooting
- HTML formatting for professional presentation
- Print and download options

**Functions**:
- `load_cv_summary(cv_path)`: Loads the CV summary from the processed CV file
- `get_job_details_using_scrapegraph(job_url)`: Extracts job details directly from the website
- `get_job_details_from_scraped_data(job_url)`: Gets job details from pre-scraped data as a fallback
- `get_job_details(job_url)`: Main function that tries both methods to get job details
- `generate_motivation_letter(cv_summary, job_details)`: Generates the motivation letter using GPT-4o
- `main(cv_path, job_url)`: Main function that orchestrates the entire process

**Output Format**:
- HTML file with a professionally formatted motivation letter
- The letter includes:
  - Candidate's contact information
  - Company address
  - Date
  - Subject line
  - Formal greeting
  - Introduction paragraph
  - Main body highlighting relevant skills and experience
  - Closing paragraph
  - Formal closing and signature

### 5. Dashboard

**Purpose**: Provide a web interface for interacting with all components of the system.

**Key Files**:
- `dashboard.py`: Main Flask application for the dashboard
- `templates/index.html`: Main dashboard page template
- `templates/results.html`: Job match results page template
- `static/css/styles.css`: CSS styles for the dashboard
- `static/js/main.js`: JavaScript for the dashboard

**Technologies**:
- Flask web framework
- Bootstrap for responsive UI
- JavaScript for client-side interactions
- HTML/CSS for web interface

**Features**:
1. **CV Management**:
   - Upload new CVs (PDF or DOCX)
   - View available CVs
   - View CV summaries
2. **Job Data Acquisition**:
   - Run the job scraper to get new job listings
   - View available job data files
3. **Job Matching**:
   - Run the job matcher with a selected CV
   - Configure matching parameters (min_score, max_results)
   - View job match results
   - Download job match reports
4. **Motivation Letter Generation**:
   - Generate personalized motivation letters for specific job postings
   - View generated letters in a professional format
   - Print or download motivation letters in HTML format

**Process**:
1. Provides a web interface at http://localhost:5000
2. Allows users to upload and process CVs
3. Allows users to run the job scraper to get new job listings
4. Allows users to run the job matcher with a selected CV
5. Displays job match results in a user-friendly format
6. Provides options to download job match reports
7. Allows users to generate personalized motivation letters for specific job postings
8. Displays generated motivation letters with options to print or download

**Functions**:
- `index()`: Render the main dashboard page
- `upload_cv()`: Handle CV upload and processing
- `run_job_matcher()`: Run the job matcher with the selected CV
- `run_job_scraper()`: Run the job data acquisition component
- `view_results()`: View job match results
- `download_report()`: Download a job match report
- `view_cv_summary()`: View a CV summary
- `generate_motivation_letter_route()`: Generate a motivation letter for a specific job
- `download_motivation_letter()`: Download a generated motivation letter

## System Requirements

### Dependencies

```
openai>=1.0.0
python-dotenv>=1.0.0
PyMuPDF>=1.22.0
python-docx>=0.8.11
pathlib>=1.0.1
flask>=2.0.0
werkzeug>=2.0.0
scrapegraphai (for job-data-acquisition)
playwright (for job-data-acquisition)
```

### Environment Variables

The system requires an OpenAI API key to be set in `process_cv/.env`:
```
OPENAI_API_KEY=your_api_key_here
```

## Usage Guide

### Running the Job Matcher

```bash
python job_matcher.py
```

This will:
1. Process the CV located at `process_cv/cv-data/Lebenslauf_Claudio Lutz.pdf`
2. Match it with the latest job data
3. Generate a report with the top matches

### Customizing the Matching

You can modify the following parameters in `job_matcher.py`:

- `min_score`: Minimum overall match score (default: 6)
- `max_results`: Maximum number of results to include in the report (default: 10)
- `cv_path`: Path to the CV file

### Running the Job Data Acquisition

```bash
cd job-data-acquisition
python app.py
```

This will:
1. Scrape job listings from ostjob.ch (up to the maximum number of pages configured in settings.json)
2. Save the data to a timestamped JSON file in the `job-data-acquisition/job-data-acquisition/data` directory

#### Configuring the Job Scraper

You can modify the following parameters in `job-data-acquisition/settings.json`:

- `max_pages`: Maximum number of pages to scrape (default: 50)
- Other scraper settings like model, temperature, etc.

### Processing a CV Manually

```bash
cd process_cv
python cv_processor.py
```

This will:
1. Process the CV located at `cv-data/Lebenslauf_Claudio Lutz.pdf`
2. Print the summarized CV information

### Running the Dashboard

```bash
python dashboard.py
```

This will:
1. Start the Flask web server at http://localhost:5000
2. Provide a web interface for interacting with all components of the system

Once the dashboard is running, you can:
1. **Upload and Process CVs**:
   - Click the "Upload CV" button on the dashboard
   - Select a PDF or DOCX file
   - The CV will be processed and a summary will be generated
2. **Run the Job Matcher**:
   - Select a CV from the dropdown menu
   - Set the minimum match score and maximum results
   - Click the "Run Job Matcher" button
   - View the results on the results page
3. **Run the Job Scraper**:
   - Set the maximum number of pages to scrape (default: 50)
   - Click the "Run Job Scraper" button to get new job listings
   - This may take several minutes depending on the number of pages to scrape
4. **View and Download Reports**:
   - View job match reports on the dashboard
   - Click the "View" button to see detailed results
   - Click the "Download" button to download the report
5. **Generate Motivation Letters**:
   - From the job match results page, click the "Motivationsschreiben erstellen" button next to a job listing
   - The system will extract detailed job information from the website
   - A personalized motivation letter will be generated based on your CV and the job details
   - View the generated letter in a professional format
   - Use the "Print" button to print the letter or "Download" to save it as an HTML file

## Implementation Details

### Job Matching Algorithm

The job matching algorithm uses OpenAI's GPT-4o model to perform semantic matching between the candidate's CV and job listings. The matching is based on:

1. **Skills Match**: How well the candidate's skills match the job requirements
2. **Experience Match**: Whether the candidate's experience level is appropriate
3. **Location Compatibility**: Whether the job location aligns with candidate preferences
4. **Education Fit**: How well the candidate's education matches requirements
5. **Overall Match Score**: A comprehensive score considering all factors

The system uses a prompt-based approach to instruct the AI model to evaluate these factors on a scale of 1-10 (except for location compatibility, which is Yes/No).

### CV Processing

The CV processing uses a two-step approach:
1. **Text Extraction**: Extracts raw text from PDF or DOCX files
2. **Summarization**: Uses OpenAI's GPT-4o model to generate a structured summary of the CV

The summarization prompt is in German, indicating that the system is designed to work with German-language CVs.

### Error Handling

The system includes robust error handling:
- Fallback to sample job data if loading fails
- Logging of errors and warnings
- Graceful handling of missing files or API issues

## File Structure

```
JobsearchAI/
├── .gitignore                                # Git ignore file
├── dashboard.py                              # Dashboard web application
├── dashboard.log                             # Log file for dashboard
├── job_matcher.py                            # Main job matching script
├── job_matcher.log                           # Log file for job matcher
├── motivation_letter_generator.py            # Motivation letter generation script
├── motivation_letter_generator.log           # Log file for motivation letter generator
├── README.md                                 # Project README
├── requirements.txt                          # Project dependencies
├── job_matches/                              # Directory for job match reports
├── motivation_letters/                       # Directory for generated motivation letters
│   └── .gitkeep                              # Empty file to ensure directory is tracked by git
├── static/                                   # Static files for dashboard
│   ├── css/                                  # CSS styles
│   │   └── styles.css                        # Dashboard styles
│   └── js/                                   # JavaScript files
│       └── main.js                           # Dashboard JavaScript
├── templates/                                # HTML templates for dashboard
│   ├── index.html                            # Main dashboard page
│   ├── motivation_letter.html                # Motivation letter display template
│   └── results.html                          # Job match results page
├── job-data-acquisition/                     # Job data acquisition component
│   ├── app.py                                # Main scraper script
│   ├── dependencies.txt                      # Scraper dependencies
│   ├── README.md                             # Component README
│   ├── settings.json                         # Scraper configuration
│   └── job-data-acquisition/                 # Data directory
│       └── data/                             # Job data storage
│           └── job_data_20250406_174357.json # Example job data file
└── process_cv/                               # CV processing component
    ├── .env                                  # Environment variables
    ├── cv_processor.py                       # CV processing script
    └── cv-data/                              # CV storage
        ├── Lebenslauf_Claudio Lutz.pdf       # Example CV file
        ├── input/                            # Input directory for CVs
        └── processed/                        # Output directory for processed CVs
            └── Lebenslauf_Claudio Lutz_summary.txt # Processed CV summary
```

## Logging

The system uses Python's built-in logging module to log information, warnings, and errors:

- Job matcher logs are saved to `job_matcher.log`
- Job data acquisition logs are saved to `job-data-acquisition/logs/scraper_[timestamp].log`
- Motivation letter generator logs are saved to `motivation_letter_generator.log`
- Dashboard logs are saved to `dashboard.log`

## Future Improvements

Potential future improvements include:

1. Support for additional CV formats beyond PDF and DOCX
2. More detailed skill matching using domain-specific knowledge
3. Integration with job application systems for direct applications
4. Improved handling of multilingual CVs and job listings
5. Enhanced data visualization for match results
6. Batch processing of multiple CVs simultaneously
7. Automated periodic job data updates
8. User feedback mechanism to improve matching algorithm
9. Mobile-responsive dashboard for use on smartphones and tablets
10. Email notifications for new job matches
11. Customizable motivation letter templates and styles
12. Option to edit generated motivation letters directly in the browser
13. Multiple language support for motivation letters
14. Ability to save and manage multiple versions of motivation letters for the same job
15. Integration with email clients to send applications directly from the system

## Troubleshooting

### Common Issues

1. **Missing Job Data**: If no job data files are found, the system will fall back to sample job data for testing.
2. **API Key Issues**: Ensure the OpenAI API key is correctly set in `process_cv/.env`.
3. **File Format Issues**: Only PDF and DOCX formats are supported for CVs.
4. **Scraper Configuration**: Check `job-data-acquisition/settings.json` for correct scraper configuration.
5. **Dashboard Connection Issues**: If you cannot connect to the dashboard, ensure that port 5000 is not in use by another application.
6. **CV Upload Problems**: If CV uploads fail, check that the `process_cv/cv-data/input` directory exists and has write permissions.
7. **Flask Installation**: If you get "ModuleNotFoundError: No module named 'flask'", run `pip install -r requirements.txt` to install all dependencies.

### Dashboard Troubleshooting

If you encounter issues with the dashboard:

1. **Server Not Starting**: 
   - Check if another application is using port 5000
   - Verify that Flask is installed correctly
   - Look for error messages in the terminal or `dashboard.log`

2. **CV Upload Failures**:
   - Ensure the file is in PDF or DOCX format
   - Check that the upload directory exists and has proper permissions
   - Verify that the file size is not too large (browser limitations)

3. **Job Matcher Not Running**:
   - Ensure a CV is selected in the dropdown
   - Check that the OpenAI API key is correctly set
   - Verify that job data files exist

4. **Job Scraper Issues**:
   - Ensure the `settings.json` file is correctly configured
   - Check that the ScrapeGraph AI library is installed
   - Look for error messages in the scraper logs

5. **Motivation Letter Generation Issues**:
   - Verify that the ScrapeGraph AI library is installed correctly
   - Check that the OpenAI API key is correctly set in `process_cv/.env`
   - Ensure the job URL is valid and accessible
   - Check the `motivation_letter_generator.log` file for detailed error messages
   - If web scraping fails, the system will fall back to using pre-scraped data
   - If the generated letter lacks specific job details, check if the job website structure has changed

### Debugging

- Check the log files for detailed error messages:
  - `job_matcher.log` for job matching issues
  - `dashboard.log` for dashboard issues
  - `job-data-acquisition/logs/scraper_[timestamp].log` for scraper issues
- Set the log level to DEBUG in configuration files for more verbose logging
- Use the sample job data for testing if the real job data is unavailable

## Security Considerations

### API Keys and Credentials
- The system uses API keys stored in environment variables
- API keys should never be committed to version control (they are included in .gitignore)
- For production use, consider using a more secure method for storing API keys, such as environment variables set at the system level or a secrets management service

### Data Protection
- Job data and CV information should be handled according to data protection regulations
- Personal data in CVs should be treated as confidential information
- Consider implementing data retention policies to automatically delete old CV data and job matches

### Dashboard Security
- The dashboard is designed for local use and does not implement authentication
- For production deployment, consider adding:
  - User authentication and authorization
  - HTTPS encryption
  - Rate limiting to prevent abuse
  - Input validation to prevent injection attacks
- The current implementation should not be exposed directly to the internet without these additional security measures

### Network Security
- By default, the Flask server listens on all interfaces (0.0.0.0)
- For increased security, modify the dashboard.py file to listen only on localhost (127.0.0.1) if external access is not required:
  ```python
  app.run(debug=False, host='127.0.0.1', port=5000)
  ```

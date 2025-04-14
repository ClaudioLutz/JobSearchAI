# JobsearchAI Documentation

## Overview

JobsearchAI is a system that matches job listings with candidate CVs using AI-powered semantic matching. The system uses natural language processing and AI to understand both job listings and candidate profiles, providing intelligent job recommendations based on skills, experience, education, and location preferences.

## System Architecture

The system consists of six main components:

1. **Job Data Acquisition**: Scrapes job listings from ostjob.ch and saves them in a structured JSON format.
2. **CV Processor**: Extracts and summarizes information from candidate CVs.
3. **Job Matcher**: Matches job listings with candidate profiles using semantic understanding.
4. **Motivation Letter Generator**: Creates personalized motivation letters based on the candidate's CV and job details.
5. **Word Template Generator**: Converts motivation letter data to professionally formatted Word documents.
6. **Dashboard**: Provides a web interface for interacting with all components of the system.

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
                  └────────┬────────┘    └─────────────────┘
                           │
                           │
                           ▼
                  ┌─────────────────┐
                  │                 │
                  │  Motivation     │
                  │  Letter Gen     │
                  │                 │
                  └────────┬────────┘
                           │
                           │
                           ▼
                  ┌─────────────────┐
                  │                 │
                  │  Word Template  │
                  │  Generator      │
                  │                 │
                  └─────────────────┘
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
- JSON for structured data storage
- HTML for letter formatting and display

**Process**:
1. Extracts detailed job information directly from the job posting website using ScrapeGraph AI
2. Loads the processed CV summary
3. Combines the job details and CV information to generate a personalized motivation letter
4. Formats the letter as a structured JSON object with all necessary components
5. Converts the JSON to HTML for display in the web interface
6. Saves both the JSON and HTML versions to files with timestamps in the filenames

**Features**:
- Direct web scraping of job details for up-to-date information
- Fallback mechanism to use pre-scraped data if web scraping fails
- Structured JSON output for easy conversion to different formats
- HTML formatting for professional presentation
- Print and download options for both HTML and Word formats
- Detailed logging for troubleshooting

**Functions**:
- `load_cv_summary(cv_path)`: Loads the CV summary from the processed CV file
- `get_job_details_using_scrapegraph(job_url)`: Extracts job details directly from the website
- `get_job_details_from_scraped_data(job_url)`: Gets job details from pre-scraped data as a fallback
- `get_job_details(job_url)`: Main function that tries both methods to get job details
- `json_to_html(motivation_letter_json)`: Converts the structured JSON to HTML format
- `generate_motivation_letter(cv_summary, job_details)`: Generates the motivation letter using GPT-4o
- `main(cv_path, job_url)`: Main function that orchestrates the entire process

**Output Format**:
- JSON file with a structured representation of the motivation letter, including:
  - Candidate information (name, address, contact details)
  - Company information (name, department, address)
  - Letter components (date, subject, greeting, introduction, body paragraphs, closing, signature)
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

**Error Handling**:
- Robust error handling for all steps of the process
- Fallback mechanisms for job detail extraction
- JSON parsing error handling with fallback to direct HTML output
- Detailed logging of all steps and potential errors
- Format detection to handle both JSON and legacy HTML formats

### 5. Word Template Generator

**Purpose**: Convert motivation letter JSON data to professionally formatted Word documents.

**Key Files**:
- `word_template_generator.py`: Main script for generating Word documents

**Technologies**:
- python-docx for Word document creation and formatting
- JSON for structured data input
- Datetime for timestamp generation

**Process**:
1. Takes a structured JSON representation of a motivation letter
2. Creates a new Word document with proper margins and formatting
3. Adds all letter components with appropriate styling (bold, spacing, etc.)
4. Saves the document to a file with a timestamp in the filename

**Features**:
- Professional document formatting with proper margins
- Structured layout matching standard motivation letter format
- Automatic filename generation based on job title and company
- Integration with the motivation letter generator
- Detailed logging for troubleshooting

**Functions**:
- `json_to_docx(motivation_letter_json, output_path=None)`: Converts JSON to a Word document
- `create_word_document_from_json_file(json_file_path)`: Creates a Word document from a JSON file

**Output Format**:
- Word document (.docx) with a professionally formatted motivation letter
- The document includes:
  - Proper margins (2.5 cm on all sides)
  - Candidate's contact information
  - Company address
  - Date
  - Subject line (bold)
  - Formal greeting
  - Introduction paragraph
  - Main body paragraphs
  - Closing paragraph
  - Formal closing and signature

### 6. Dashboard

**Purpose**: Provide a web interface for interacting with all components of the system.

**Key Files**:
- `dashboard.py`: Main Flask application for the dashboard
- `templates/index.html`: Main dashboard page template
- `templates/results.html`: Job match results page template
- `templates/motivation_letter.html`: Motivation letter display template
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
   - Download motivation letters in Word format
5. **User Feedback and Progress Tracking**:
   - Visual button feedback when actions are initiated (loading spinners)
   - Real-time progress tracking for long-running operations
   - Detailed status messages during processing
   - Background processing for long operations to keep UI responsive

**Process**:
1. Provides a web interface at http://localhost:5000
2. Allows users to upload and process CVs
3. Allows users to run the job scraper to get new job listings
4. Allows users to run the job matcher with a selected CV
5. Displays job match results in a user-friendly format
6. Provides options to download job match reports
7. Allows users to generate personalized motivation letters for specific job postings
8. Displays generated motivation letters with options to print or download in HTML or Word format

**Functions**:
- `index()`: Render the main dashboard page
- `upload_cv()`: Handle CV upload and processing
- `run_job_matcher()`: Run the job matcher with the selected CV
- `run_job_scraper()`: Run the job data acquisition component
- `view_results()`: View job match results
- `download_report()`: Download a job match report
- `view_cv_summary()`: View a CV summary
- `generate_motivation_letter_route()`: Generate a motivation letter for a specific job
- `download_motivation_letter()`: Download a generated motivation letter in HTML format
- `download_motivation_letter_docx()`: Download a generated motivation letter in Word format

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

### Generating a Motivation Letter Manually

```bash
python motivation_letter_generator.py
```

This will:
1. Load the CV summary from `process_cv/cv-data/processed/Lebenslauf_Claudio Lutz_summary.txt`
2. Extract job details from the example job URL
3. Generate a personalized motivation letter
4. Save the letter in both JSON and HTML formats to the `motivation_letters` directory

### Creating a Word Document from a Motivation Letter JSON

```bash
python word_template_generator.py motivation_letters/motivation_letter_example.json
```

This will:
1. Load the motivation letter data from the specified JSON file
2. Create a professionally formatted Word document
3. Save the document to the `motivation_letters` directory with the same base filename but a .docx extension

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
3. **Run the Combined Process**:
   - Select a CV from the dropdown menu
   - Set the maximum number of pages to scrape
   - Set the minimum match score and other matching parameters
   - Click the "Run Combined Process" button
   - This will first run the job scraper to get fresh job listings, then immediately run the job matcher with those listings
   - View the results on the results page when complete
4. **Run the Job Scraper**:
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
   - Use the "Print" button to print the letter
   - Use the "Download HTML" button to save it as an HTML file
   - Use the "Download Word" button to save it as a Word document

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

### Motivation Letter Generation

The motivation letter generation process uses a structured approach:

1. **Job Detail Extraction**: 
   - First attempts to extract job details directly from the job posting website using ScrapeGraph AI
   - Falls back to pre-scraped data if direct extraction fails
   - Ensures all required fields are present with default values if needed

2. **Letter Generation**:
   - Uses OpenAI's GPT-4o model with a detailed prompt
   - Instructs the model to return a structured JSON object
   - The prompt is in German, matching the target language of the motivation letter
   - Includes specific instructions for formatting and content

3. **Output Processing**:
   - Parses the JSON response from the model
   - Converts the JSON to HTML for web display
   - Saves both formats to files
   - Handles parsing errors with a fallback to direct HTML output

4. **Word Document Creation**:
   - Uses the structured JSON data to create a Word document
   - Applies professional formatting with proper margins and styling
   - Saves the document with a consistent naming convention

### Error Handling

The system includes robust error handling:
- Fallback to sample job data if loading fails
- Fallback to pre-scraped data if web scraping fails
- JSON parsing error handling with fallback mechanisms
- Format detection to handle both new and legacy output formats
- Logging of errors and warnings at all stages
- Graceful handling of missing files or API issues

### User Feedback and Progress Tracking

The system provides real-time feedback to users during long-running operations:

1. **Button State Management**:
   - Buttons show loading spinners when clicked
   - Buttons are disabled during processing to prevent multiple submissions
   - Original button text is restored when operations complete

2. **Progress Tracking System**:
   - Backend progress tracking for long-running operations
   - Operations run in background threads to keep the UI responsive
   - Real-time progress updates via a status API endpoint

3. **Visual Progress Feedback**:
   - Progress modal with a progress bar shows real-time completion percentage
   - Detailed status messages inform users about current processing steps
   - Error messages are displayed if operations fail

4. **Implementation**:
   - Client-side: JavaScript functions in `static/js/main.js` handle button states and progress updates
   - Server-side: Flask routes in `dashboard.py` track operation progress and provide status updates
   - Operations like job scraping, job matching, and motivation letter generation use this system

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
├── word_template_generator.py                # Word document template generator
├── word_template_generator.log               # Log file for Word template generator
├── README.md                                 # Project README
├── Documentation.md                          # Detailed project documentation
├── last_session.md                           # Summary of the last development session
├── requirements.txt                          # Project dependencies
├── job_matches/                              # Directory for job match reports
├── motivation_letters/                       # Directory for generated motivation letters
│   ├── .gitkeep                              # Empty file to ensure directory is tracked by git
│   ├── motivation_letter_example.html        # Example HTML motivation letter
│   ├── motivation_letter_example.json        # Example JSON motivation letter
│   └── motivation_letter_example.docx        # Example Word motivation letter
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
- Word template generator logs are saved to `word_template_generator.log`
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
16. More customization options for Word templates (fonts, margins, etc.)
17. Support for multiple Word templates for different styles or languages
18. Preview of the Word document in the web interface
19. Direct email sending functionality with attachments

## Troubleshooting

### Common Issues

1. **Missing Job Data**: If no job data files are found, the system will fall back to sample job data for testing.
2. **API Key Issues**: Ensure the OpenAI API key is correctly set in `process_cv/.env`.
3. **File Format Issues**: Only PDF and DOCX formats are supported for CVs.
4. **Scraper Configuration**: Check `job-data-acquisition/settings.json` for correct scraper configuration.
5. **Dashboard Connection Issues**: If you cannot connect to the dashboard, ensure that port 5000 is not in use by another application.
6. **CV Upload Problems**: If CV uploads fail, check that the `process_cv/cv-data/input` directory exists and has write permissions.
7. **Flask Installation**: If you get "ModuleNotFoundError: No module named 'flask'", run `pip install -r requirements.txt` to install all dependencies.
8. **python-docx Installation**: If you get "ModuleNotFoundError: No module named 'docx'", run `pip install python-docx` to install the dependency.

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

6. **Word Document Generation Issues**:
   - Verify that python-docx is installed correctly
   - Check that the JSON file exists and is properly formatted
   - Look for error messages in the `word_template_generator.log` file
   - Ensure the output directory has write permissions

### Debugging

- Check the log files for detailed error messages:
  - `job_matcher.log` for job matching issues
  - `dashboard.log` for dashboard issues
  - `job-data-acquisition/logs/scraper_[timestamp].log` for scraper issues
  - `motivation_letter_generator.log` for motivation letter generation issues
  - `word_template_generator.log` for Word document generation issues
- Set the log level to DEBUG in configuration files for more verbose logging
- Use the sample job data for testing if the real job data is unavailable

### Common Error Messages and Solutions

1. **KeyError: 'file_path'**:
   - This error occurs in the motivation letter generator when trying to access a key that doesn't exist in the result dictionary
   - The system has been updated to handle both the new JSON format and the legacy HTML format
   - If you encounter this error, ensure you're using the latest version of the code

2. **JSONDecodeError**:
   - This error occurs when the system fails to parse the JSON response from the OpenAI API
   - The system includes a fallback to treat the response as HTML directly
   - Check the `motivation_letter_generator.log` file for the raw response to diagnose the issue

3. **ModuleNotFoundError: No module named 'docx'**:
   - This error occurs when the python-docx library is not installed
   - Run `pip install python-docx` to install the dependency

4. **PermissionError: [Errno 13] Permission denied**:
   - This error occurs when the system cannot write to a file or directory
   - Check that the output directories have the correct permissions
   - Ensure no other applications have the target files open

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

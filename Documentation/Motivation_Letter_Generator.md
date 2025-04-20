# 4. Motivation Letter Generator

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

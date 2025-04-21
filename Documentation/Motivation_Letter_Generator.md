# 4. Motivation Letter Generator

**Purpose**: Create personalized motivation letters based on the candidate's CV and job details.

**Key Files**:
- `motivation_letter_generator.py`: Main script for generating motivation letters.
- `process_cv/.env`: Used for loading the OpenAI API key (as a fallback).
- `job-data-acquisition/app.py`: Dynamically loaded to use its configuration and ScrapeGraph functionality.
- `job-data-acquisition/settings.json`: Configuration used by the loaded `app.py`.
- `process_cv/cv-data/processed/`: Directory where input CV summaries are expected (e.g., `Lebenslauf_summary.txt`).
- `job-data-acquisition/job-data-acquisition/data/`: Directory where pre-scraped job data is loaded from as a fallback.
- `motivation_letters/`: Output directory for generated letters and scraped data.
  - `motivation_letter_{job_title}.json`: Structured JSON output of the generated letter.
  - `motivation_letter_{job_title}.html`: HTML version of the generated letter.
  - `motivation_letter_{job_title}_scraped_data.json`: Raw job details dictionary extracted by ScrapeGraph or retrieved from fallback data.

**Technologies**:
- OpenAI GPT models (`gpt-4.1`) for generating personalized motivation letters based on a detailed prompt.
- Web Scraping & Parsing:
  - `requests` for HTTP requests (including HEAD requests).
  - `BeautifulSoup4` for parsing HTML.
  - Potentially `scrapegraphai` (if installed and configured) as part of the iframe/HTML extraction attempt.
- PDF Processing:
  - `PyMuPDF` (`fitz`) for extracting text from PDF files.
  - `easyocr` (optional, requires installation) for Optical Character Recognition (OCR) on image-based PDFs.
  - `Pillow` and `numpy` (dependencies for `easyocr`).
- JSON for structured data storage (input job data fallback, output letter structure).
- HTML for generating a formatted letter view from the JSON structure.
- `python-dotenv` for loading API keys.
- Standard Python libraries (`os`, `logging`, `json`, `datetime`, `importlib`).

**Process**:
1. Loads the OpenAI API key (from environment or `process_cv/.env`).
2. Loads the specified CV summary from `process_cv/cv-data/processed/{cv_filename}_summary.txt`.
3. **Attempts to extract detailed job information using a multi-step approach (`get_job_details`):**
    a. **Iframe Extraction:** Tries to find a specific iframe (`vacancyDetailIFrame`) on the `job_url`, extract its text content, and structure it using OpenAI. If the iframe isn't found, it returns the parsed HTML (`BeautifulSoup` object) of the main page.
    b. **PDF Link in HTML:** If the iframe method didn't yield structured details but returned the main page's HTML, it searches this HTML for links pointing to PDF files (`/preview/pdf` or `.pdf`). If found, it attempts to process the *first* found PDF using the PDF/OCR method (`get_job_details_from_pdf`).
    c. **Direct PDF Check (HEAD Request):** If no iframe was found and no usable PDF link was found in the HTML, it performs a `HEAD` request on the original `job_url` to check its `Content-Type`. If it's `application/pdf`, it proceeds with the PDF/OCR method (`get_job_details_from_pdf`) on the original URL.
    d. **Fallback to Pre-Scraped Data:** If all direct extraction methods (iframe, HTML PDF link, direct PDF) fail to return structured job details, it falls back to searching the latest pre-scraped data file (`get_job_details_from_scraped_data`) in `job-data-acquisition/job-data-acquisition/data/`.
    e. **Default Placeholder:** If all methods fail, uses default placeholder job details.
4. Combines the CV summary and the obtained job details into a detailed German prompt for the OpenAI `gpt-4.1` model. The prompt requests a specific JSON structure for the letter.
5. Sends the prompt to OpenAI, forcing JSON output format.
6. Attempts to parse the response as JSON.
7. If JSON parsing succeeds, converts the structured JSON into a basic HTML representation using `json_to_html`.
8. Saves the structured letter as `motivation_letters/motivation_letter_{job_title}.json`.
9. Saves the generated HTML as `motivation_letters/motivation_letter_{job_title}.html`.
10. Saves the raw `job_details` dictionary (used as input for generation) as `motivation_letters/motivation_letter_{job_title}_scraped_data.json`. Filenames use a sanitized version of the job title.
11. If JSON parsing fails (fallback), saves the raw OpenAI response directly into `motivation_letters/motivation_letter_{job_title}.html` (and does not save the structured JSON or scraped data JSON).

**Features**:
- Multi-step job detail extraction:
    - Attempts iframe content extraction.
    - Scans HTML for direct PDF links.
    - Checks if the job URL itself is a PDF.
    - Processes text-based and image-based PDFs (using PyMuPDF and optional `easyocr`).
- Fallback mechanism to use pre-scraped data if direct extraction fails.
- Uses OpenAI (`gpt-4.1`) with a detailed prompt to generate highly personalized letter content.
- Generates structured JSON output representing the letter components.
- Generates a basic HTML version from the JSON structure.
- Fallback mechanism to save raw OpenAI output as HTML if JSON generation/parsing fails.
- Sanitizes job titles for use in output filenames.
- Detailed logging to `motivation_letter_generator.log` for troubleshooting.

**Functions**:
- `load_cv_summary(cv_filename)`: Loads the CV summary from `process_cv/cv-data/processed/{cv_filename}_summary.txt`.
- `get_job_details_from_iframe(job_url)`: (Replaces `get_job_details_using_scrapegraph`) Attempts to find and process a specific iframe (`vacancyDetailIFrame`). If found, extracts text and uses OpenAI to structure it. If not found, returns the parsed HTML (`BeautifulSoup` object) of the main page. May implicitly use `scrapegraphai` components if configured.
- `get_job_details_from_pdf(pdf_url_or_path)`: Downloads a PDF, extracts text using PyMuPDF. If text is minimal, attempts OCR using `easyocr` (if installed). Sends extracted text to OpenAI for structuring.
- `get_job_details_from_scraped_data(job_url)`: Gets job details from the latest pre-scraped data file in `job-data-acquisition/job-data-acquisition/data/` as a fallback. Handles potential list-of-lists structure in JSON.
- `get_job_details(job_url)`: Orchestrates job detail retrieval using the multi-step process: iframe -> HTML PDF link -> direct PDF check -> fallback to scraped data -> defaults.
- `json_to_html(motivation_letter_json)`: Converts the structured JSON letter object into a basic HTML string.
- `generate_motivation_letter(cv_summary, job_details)`: Generates the motivation letter using OpenAI (`gpt-4.1`) with a detailed prompt, forces JSON output, handles JSON parsing errors (fallback to raw HTML), saves the generated letter (JSON and HTML), and saves the input `job_details` dictionary to `motivation_letters/`. Returns a dictionary containing paths to the generated files.
- `main(cv_filename, job_url)`: Main function that orchestrates the entire process: loads summary, gets job details, generates letter, and returns results/paths.

**Output Format**:
- **Letter JSON File**: Saved to `motivation_letters/motivation_letter_{job_title}.json`. Contains a structured JSON object representing the generated letter, including:
  - Candidate information (name, address, city, email, phone)
  - Company information (name, department, street/number, PLZ/city)
  - Letter components (date, subject, greeting, introduction, body_paragraphs (list), closing, signature, full_name)
- **Scraped Data JSON File**: Saved to `motivation_letters/motivation_letter_{job_title}_scraped_data.json`. Contains the raw dictionary of job details extracted by `get_job_details` (e.g., Job Title, Company Name, Description, Skills, Responsibilities, Contact Person, Application Email, etc.). This is the data used as input for the letter generation.
- **HTML File**: Saved to `motivation_letters/motivation_letter_{job_title}.html`. Contains a basic HTML representation generated from the JSON structure (or the raw OpenAI response in case of JSON parsing failure). Includes:
  - Candidate's contact information block
  - Company address block
  - Date
  - Subject line (h2)
  - Formal greeting
  - Introduction paragraph
  - Main body paragraphs
  - Closing paragraph
  - Formal closing and signature block

**Error Handling**:
- Robust error handling for all steps of the process
- Fallback mechanisms for job detail extraction
- JSON parsing error handling with fallback to direct HTML output
- Detailed logging of all steps and potential errors
- Format detection to handle both JSON and legacy HTML formats

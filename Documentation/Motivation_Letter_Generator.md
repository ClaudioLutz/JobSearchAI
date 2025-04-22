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
- `job-data-acquisition/job-data-acquisition/data/`: Directory where pre-scraped job data is loaded from as a fallback.
- `motivation_letters/`: Output directory for generated letters and scraped data.
  - `motivation_letter_{job_title}.json`: Structured JSON output of the generated letter.
  - `motivation_letter_{job_title}.html`: HTML version of the generated letter.
  - `motivation_letter_{job_title}_scraped_data.json`: Raw job details dictionary used as input for generation.

**Technologies**:
- OpenAI GPT models (`gpt-4.1`) for:
    - Structuring text extracted by ScrapeGraphAI (`job_details_utils.py`).
    - Generating personalized motivation letters (`letter_generation_utils.py`).
- Web Scraping:
    - `scrapegraphai`: Primary method for fetching job page content and extracting details (used in `graph_scraper_utils.py`). Relies on Playwright internally.
- JSON for structured data storage (pre-scraped job data, output letter structure).
- HTML for generating a formatted letter view from the JSON structure.
- `python-dotenv` for loading API keys (fallback mechanism).
- Standard Python libraries (`os`, `logging`, `json`, `datetime`, `pathlib`, `traceback`, `urllib.parse`).

**Process**:
1.  **Load CV Summary:** The main script (`motivation_letter_generator.py`) calls `load_cv_summary` to read the pre-processed CV summary text from `process_cv/cv-data/processed/`.
2.  **Get Job Details (`job_details_utils.get_job_details`):** This is the core data gathering step:
    a.  **Attempt 1: Live ScrapeGraphAI Extraction:**
        i.  Calls `graph_scraper_utils.get_job_details_with_graphscrapeai` which uses `scrapegraphai` (forcing `headless=False`) and a structured German prompt to extract job details directly into a JSON/dictionary format.
        ii. The utility function validates the result (checks for nested 'content', presence of 'Job Title', and sufficient content in description/skills/responsibilities).
        iii. If successful and content is sufficient, the structured dictionary is returned.
    b.  **Attempt 2: Fallback to Pre-scraped Data:**
        i.  If the live ScrapeGraphAI attempt fails or returns insufficient content, it calls `get_job_details_from_scraped_data`.
        ii. This function searches the latest `job_data_*.json` file in `job-data-acquisition/job-data-acquisition/data/` for a matching job URL/ID.
        iii. If found, it returns the stored job details dictionary.
    c.  **Final Default:** If both live scraping and the pre-scraped data fallback fail, a default dictionary with placeholder values is returned.
3.  **Generate Letter Content (`letter_generation_utils.generate_motivation_letter`):**
    a.  Combines the loaded CV summary and the obtained `job_details` dictionary into a detailed German prompt for the OpenAI `gpt-4.1` model.
    b.  Sends the prompt to OpenAI, requesting a structured JSON output representing the letter components.
    c.  Parses the JSON response.
4.  **Format and Save (`letter_generation_utils.generate_motivation_letter`):**
    a.  If JSON parsing succeeds, calls `json_to_html` to create an HTML version.
    b.  Saves the structured letter as `motivation_letters/motivation_letter_{job_title}.json`.
    c.  Saves the generated HTML as `motivation_letters/motivation_letter_{job_title}.html`.
    d.  Saves the input `job_details` dictionary as `motivation_letters/motivation_letter_{job_title}_scraped_data.json`.
    e.  Returns a dictionary containing paths to the generated files.
    f.  (Handles a fallback case where JSON parsing fails by saving the raw OpenAI response as HTML - though this is less likely with forced JSON output).

**Features**:
- **Primary Job Detail Extraction via ScrapeGraphAI:**
    - Uses `scrapegraphai` with `headless=False` and a structured German prompt as the primary method to fetch and extract job details (`graph_scraper_utils.py`).
    - Handles potentially nested JSON results from `scrapegraphai`.
    - Validates extracted data for presence of 'Job Title' and sufficient content in description/skills/responsibilities (`job_details_utils.has_sufficient_content`).
- **Fallback to Pre-scraped Data:** If live scraping fails or yields insufficient content, attempts to load data from the latest `job_data_*.json` file (`job_details_utils.get_job_details_from_scraped_data`).
- **OpenAI for Letter Generation:** Uses OpenAI (`gpt-4.1`) with a detailed prompt combining CV summary and extracted job details to generate personalized letter content (`letter_generation_utils.generate_motivation_letter`).
- **Structured Output:** Generates structured JSON output representing the letter components.
- **HTML Formatting:** Generates a basic HTML version from the JSON structure (`letter_generation_utils.json_to_html`).
- **File Saving:** Saves the generated JSON letter, HTML letter, and the input job details to the `motivation_letters/` directory with sanitized filenames.
- **Configuration Driven:** Loads `scrapegraphai` configuration (LLM model, API key) from `job-data-acquisition/settings.json`.
- **Modular Design:** Functionality is split into `job_details_utils.py`, `letter_generation_utils.py`, and `graph_scraper_utils.py` for better organization.
- **Logging:** Provides logging for different stages of the process across modules.

**Functions**:

*   **`motivation_letter_generator.py`**:
    *   `load_cv_summary(cv_filename)`: Loads the CV summary text from the processed file.
    *   `main(cv_filename, job_url)`: Orchestrates the overall process: loads CV, gets job details (via `job_details_utils`), generates letter (via `letter_generation_utils`), and handles results.
*   **`job_details_utils.py`**:
    *   `has_sufficient_content(details_dict)`: Checks if extracted job details dictionary contains enough meaningful content.
    *   `structure_text_with_openai(text_content, source_url, source_type)`: Uses OpenAI to convert raw text (potentially from `graph_scraper_utils`) into a structured job details dictionary.
    *   `get_job_details_from_scraped_data(job_url)`: Loads job details from the latest pre-scraped data file as a fallback.
    *   `get_job_details(job_url)`: Main function in this module. Tries `graph_scraper_utils.get_job_details_with_graphscrapeai` first, then falls back to `get_job_details_from_scraped_data`.
*   **`letter_generation_utils.py`**:
    *   `json_to_html(motivation_letter_json)`: Converts the final letter JSON into an HTML string.
    *   `generate_motivation_letter(cv_summary, job_details)`: Takes CV summary and structured job details, prompts OpenAI to generate the letter JSON, saves all output files (JSON letter, HTML letter, input job details), and returns file paths.
*   **`graph_scraper_utils.py`**:
    *   `load_config()`: Loads configuration from `job-data-acquisition/settings.json`.
    *   `get_job_details_with_graphscrapeai(job_url)`: Uses `scrapegraphai` (with `headless=False` and structured prompt) to attempt live extraction of job details. Includes validation.

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

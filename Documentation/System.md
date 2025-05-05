# JobsearchAI System Overview

**Purpose**: The JobsearchAI system automates and enhances the job application process by intelligently scraping job listings, matching them against candidate CVs, and generating personalized application documents.

## System Workflow & Data Flow

The system operates through a series of interconnected components, primarily managed via a Flask web dashboard:

1.  **CV Processing**:
    *   User uploads a CV (PDF) via the dashboard. The file is saved to the user's configured data directory (e.g., `[data_dir]/process_cv/cv-data/input/`).
    *   The `CV Processor` (`process_cv/cv_processor.py`) extracts text using PyMuPDF.
    *   OpenAI (`gpt-4.1`) summarizes the CV text based on a detailed prompt, focusing on career trajectory, preferences, goals, etc.
    *   The summary is saved to the user's data directory (e.g., `[data_dir]/process_cv/cv-data/processed/{cv_filename}_summary.txt`).
    *   **Database Update**: Information about the uploaded CV (original filename, relative paths to original and summary files, timestamps) is recorded in the `CVS` table of the local SQLite database (`jobsearchai.db`) located in the user's configured data directory.

2.  **Job Data Acquisition**:
    *   User initiates scraping via the dashboard (background task with cancellation support).
    *   The `Job Data Acquisition` component (`job-data-acquisition/app.py`) uses ScrapeGraph AI (configured via `job-data-acquisition/settings.json`) to scrape job listings from specified URLs (e.g., ostjob.ch). **Enhanced error handling** catches specific network exceptions.
    *   It iterates through pages (up to `max_pages` defined in settings) and uses OpenAI (`gpt-4.1` or as configured) to extract structured job details (Title, Company, Description, Skills, etc.).
    *   Results (potentially a list of lists, one per page) are saved to a timestamped JSON file in the configured job data directory.
    *   **Database Update**: Information about the scraped batch (timestamp, source URLs, settings, relative filepath) is recorded in the `JOB_DATA_BATCHES` table.

3.  **Job Matching**:
    *   User selects a processed CV and initiates matching via the dashboard (background task with cancellation support).
    *   The `Job Matcher` (`job_matcher.py`) loads the selected CV summary (using the cache helper) and the latest job data JSON file.
    *   For each job listing (up to `max_jobs`), it uses OpenAI (`gpt-4.1`) to evaluate the match based on multiple criteria (Skills, Experience, Location, Education, Career Trajectory, Preferences, Satisfaction) defined in a detailed prompt, forcing JSON output.
    *   Matches are filtered by a minimum score (`min_score`) and sorted.
    *   The top matches (up to `max_results`), including the evaluation details and the path to the CV used, are saved to timestamped JSON and Markdown files in the configured job matches directory.
    *   **Database Update**: Information about the report (timestamp, relative filepaths, parameters, counts, related CV/batch IDs) is recorded in the `JOB_MATCH_REPORTS` table.

4.  **Motivation Letter Generation**:
    *   User selects one or more matched jobs from the results page on the dashboard, potentially selecting a specific CV via a dropdown.
    *   The `Motivation Letter Generator` (`motivation_letter_generator.py`) retrieves the relevant CV summary using the cache helper (`get_cv_summary`). **Fixed**: Checks if the retrieved summary is empty before proceeding.
    *   It attempts to get up-to-date job details using a **multi-step process** (`job_details_utils.py` with **enhanced network error handling**):
        *   Primary Method: Uses ScrapeGraphAI (`graph_scraper_utils.py`) with a structured German prompt to extract job details directly into JSON format.
        *   Fallback Method: If live scraping fails or yields insufficient content, searches the latest pre-scraped data file.
        *   Manual Input: Supports manual text input for job details if automatic methods are insufficient.
    *   It uses OpenAI (`gpt-4.1`) with a detailed prompt (**updated** to better integrate CV summary and job details) to:
        *   Generate a personalized motivation letter in JSON format (`letter_generation_utils.generate_motivation_letter`, now returns success/error tuple).
        *   Optionally generate short email texts for bulk operations (`letter_generation_utils.generate_email_text_only`, now returns success/error tuple).
    *   The generated content is saved in multiple formats:
        *   JSON letter structure (including optional email text)
        *   HTML formatted letter
        *   Raw scraped job details in a separate JSON file
        *   Word document (generated on demand)
    *   **Database Update**: Information about the generated letter (timestamp, job details, relative filepaths, related CV/report IDs) is recorded in the `MOTIVATION_LETTERS` table.

5.  **Word Document Generation**:
    *   User requests a Word version of a generated motivation letter via the dashboard.
    *   The `Word Template Generator` (`word_template_generator.py`) uses the `docxtpl` library.
    *   It loads the corresponding motivation letter JSON file.
    *   It populates a Word template (`motivation_letters/template/motivation_letter_template.docx`) with the data from the JSON file using Jinja2 syntax.
    *   The resulting `.docx` file is saved in the `motivation_letters/` directory, typically mirroring the JSON filename.

6.  **Dashboard Interface**:
    *   The Flask application (`dashboard.py`) provides the central user interface.
    *   It allows users to manage files (upload CVs, view/delete CVs, job data, reports, letters). **Pagination** is implemented for lists on the dashboard and results page. **CV Summary Caching** is used.
    *   It triggers the execution of the different components (scraping, matching, letter generation, bulk email text generation), using background threads (`threading`) with **cancellation support** and `ThreadPoolExecutor` for bulk tasks.
    *   It displays results (job matches, generated letters, generated email texts, bulk job data contents, specific scraped job data).
    *   It provides progress tracking for background operations via AJAX polling.

## Core Components Summary

*   **CV Processor (`process_cv/`)**: Extracts text from PDF CVs and uses AI to generate structured summaries focusing on career aspects. Requires OpenAI API key. **Fixed**: Dashboard now correctly passes extracted text to summarizer.
*   **Job Data Acquisition (`job-data-acquisition/`)**: Scrapes job listings from web pages using ScrapeGraph AI and saves structured data to JSON files. Configured via `settings.json`. Requires OpenAI API key (or other LLM config). **Enhanced** with specific network error handling.
*   **Job Matcher (`job_matcher.py`)**: Compares CV summaries against scraped job listings using AI evaluation to score and rank potential matches. Outputs JSON and Markdown reports. Requires OpenAI API key. Uses the centralized configuration and utility modules for improved error handling and code reusability.
*   **Motivation Letter Generator (`motivation_letter_generator.py`, `letter_generation_utils.py`, `job_details_utils.py`)**: Creates personalized motivation letters and/or short email texts using AI, combining CV summary and job details. Outputs/updates JSON files and generates HTML letters. Requires OpenAI API key. Uses the centralized configuration and utility modules. **Enhanced** job detail fetching error handling. **Improved** letter generation prompt and checks for empty CV summary.
*   **Word Template Generator (`word_template_generator.py`)**: Converts structured JSON motivation letters into formatted Word documents using a template and `docxtpl`.
*   **Dashboard (`dashboard.py`, `blueprints/`)**: Flask web application providing the user interface to manage files, run processes (including bulk letter and email generation), view results, and track progress. Orchestrates the interaction between components. **Enhanced** with pagination, CV summary caching, and improved background task management (cancellation, ThreadPoolExecutor). **Fixed** template rendering and variable scope bugs.
*   **Centralized Configuration (`config.py`)**: Manages application settings. **Enhanced** to handle user-specific configurations (API keys, data paths) stored in OS-appropriate locations (`appdirs`) and secure API key storage (`keyring`). Differentiates between development and packaged modes for path resolution.
*   **Utility Modules (`utils/`)**: A collection of utility modules that provide reusable functionality:
    * `utils/decorators.py`: Decorators for error handling, retries, caching, and execution timing.
    * `utils/file_utils.py`: Functions for common file operations with improved error handling.
    * `utils/api_utils.py`: Wrappers for OpenAI API operations with retries and caching.
    * `utils/database_utils.py`: Functions for initializing and connecting to the local SQLite database (`jobsearchai.db`). Provides a context manager for safe database transactions. **Enhanced** with index creation for performance.

## Key Technologies

*   **Backend**: Python, Flask
*   **AI/LLM**: OpenAI GPT models (specifically `gpt-4.1` used in several components), ScrapeGraph AI (used explicitly in scraping steps).
*   **Web Scraping/Parsing**: `requests`, `BeautifulSoup4`, ScrapeGraph AI (uses Playwright).
*   **PDF Processing**: PyMuPDF (`fitz`).
*   **Document Generation**: `docxtpl`, `python-docx`
*   **Frontend**: HTML, CSS, JavaScript, Bootstrap 5 & Bootstrap Icons (assumed)
*   **Data Format**: JSON
*   **Concurrency**: Python `threading` (for background tasks, `threading.Event` for cancellation), `concurrent.futures.ThreadPoolExecutor` (for bulk generation).
*   **Configuration**: Centralized configuration (`config.py`), `.env` files, JSON (`settings.json`)
*   **Error Handling**: Decorators for consistent error handling, retries, and caching (`utils/decorators.py`), specific exception handling in network-facing code, tuple returns for background task results.
*   **Database**: SQLite (via built-in `sqlite3` module).
*   **Type Hints**: All optimized code includes type hints for better IDE support and code quality.

## Setup & Configuration

*   **API Keys**: An OpenAI API key is **required** by the end-user. The application prompts for this key during a **first-run setup wizard** and stores it securely using the `keyring` library (OS credential manager) or in the user's configuration file as a fallback. The developer's key is **not** distributed.
*   **User Configuration**: User-specific settings (API key fallback, custom data directory path) are stored in `settings.json` within the user's configuration directory (e.g., `AppData/Local/JobsearchAI/JobsearchAI` on Windows), managed by `config.py` using `appdirs`.
*   **Job Scraper Settings**: Default scraper settings remain in `job-data-acquisition/settings.json` bundled with the application, but could potentially be overridden by user settings in the future.
*   **Data Storage**: User data (CVs, job data, reports, letters, logs) is stored by default in the user's data directory (e.g., `AppData/Local/JobsearchAI/JobsearchAI` on Windows), determined by `appdirs`. Users can configure a custom data directory during setup or via the dashboard.
*   **Word Template**: The `motivation_letters/template/motivation_letter_template.docx` file is bundled with the application.
*   **Dependencies**: Python dependencies are listed in `requirements.txt` and `setup.py`. Key libraries include `Flask`, `openai`, `python-dotenv`, `requests`, `beautifulsoup4`, `pymupdf`, `docxtpl`, `keyring`, `appdirs`, `sqlite3` (built-in), and potentially `scrapegraphai`, `easyocr`, `Pillow`, `numpy`.
*   **Centralized Configuration**: The `config.py` module provides a centralized way to access bundled settings, user settings, API keys, and dynamically determined paths across the codebase.
*   **Database**: SQLite (`jobsearchai.db` file stored in the user's configured data directory). Key tables include:
    *   `CVS`: Stores information about uploaded CVs (paths, timestamps, summary path). Columns: `id`, `original_filename`, `original_filepath`, `summary_filepath`, `processing_timestamp`, `upload_timestamp`. **Indexed**.
    *   `JOB_DATA_BATCHES`: Tracks batches of scraped job data (timestamp, source, filepath, settings). Columns: `id`, `batch_timestamp`, `source_urls`, `data_filepath`, `settings_used`. **Indexed**.
    *   `JOB_MATCH_REPORTS`: Stores results of job matching runs (timestamp, report paths, related CV/batch IDs, parameters). Columns: `id`, `report_timestamp`, `report_filepath_json`, `report_filepath_md`, `cv_id`, `job_data_batch_id`, `parameters_used`, `match_count`. **Indexed**.
    *   `MOTIVATION_LETTERS`: Records generated motivation letters (timestamp, job details, related CV/report IDs, filepaths). Columns: `id`, `generation_timestamp`, `job_title`, `company_name`, `job_url`, `cv_id`, `job_match_report_id`, `letter_filepath_json`, `letter_filepath_html`, `letter_filepath_docx`, `scraped_data_filepath`. **Indexed**.

## Running the System

The primary way to interact with the system is through the Flask dashboard:

1.  **Installation**: Install using the provided installer (Windows) or by placing the application bundle (macOS/Linux) in the desired location (See `README_for_users.md`).
2.  **First Run**: Launch the application executable (`JobsearchAI.exe` or similar). A setup wizard will appear.
3.  **Setup Wizard**: Enter your OpenAI API key when prompted. Optionally, specify a custom directory for storing application data.
4.  **Run Application**: After setup, the main dashboard will load in your default web browser (typically at `http://127.0.0.1:5000`).
5.  **Usage**: Use the dashboard interface to upload CVs, run the scraper, run the matcher, generate letters, and manage configuration via the "Configuration" tab.

## Component Dependency Graph

This diagram illustrates the primary code dependencies between the system's components and key external libraries/services. The Dashboard acts as the central orchestrator, calling functions from the other modules. The optimized components use the centralized configuration and utility modules.

```mermaid
graph TD 
  subgraph JobsearchAI System
    DASH[Dashboard - dashboard.py]
    CVPROC[CV Processor - cv_processor.py]
    JDA[Job Data Acquisition - app.py]
    JM[Job Matcher - job_matcher.py]
    MLG[Motivation Letter Generator - motivation_letter_generator.py]
    WTG[Word Template Generator - word_template_generator.py]
    CONFIG[Centralized Configuration - config.py]
    UTILS[Utility Modules - utils/]
  end

  subgraph External Services/Libraries
    OPENAI[OpenAI API]
    SCRAPEGRAPH["ScrapeGraph AI (Optional/Implicit)"]
    DOCXTPL[docxtpl]
    PYMUPDF[PyMuPDF]
    FLASK[Flask]
    REQUESTS[requests]
    BS4[BeautifulSoup4]
    EASYOCR[easyocr (Optional)]
  end

  DASH --> FLASK
  DASH --> CVPROC
  DASH --> JDA
  DASH --> JM
  DASH --> MLG
    DASH --> WTG
    DASH --> CONFIG # Dashboard uses config for paths, etc.
    DASH --> UTILS # Dashboard uses utils (implicitly via blueprints)

    JM --> CVPROC
    JM --> CONFIG
    JM --> UTILS
    JM --> DBUTILS # Job Matcher will eventually read/write reports to DB

  %% Fallback data source
  MLG --> JDA
    MLG --> CONFIG
    MLG --> UTILS
    MLG --> DBUTILS # Motivation Letter Generator will eventually read/write letters to DB

    CVPROC --> PYMUPDF
    CVPROC --> OPENAI
    CVPROC --> DBUTILS # CV Processor now writes to DB via cv_routes

    JDA --> SCRAPEGRAPH
    JDA --> OPENAI
    JDA --> DBUTILS # Job Data Acquisition will eventually write batches to DB
  
  %% OpenAI API utilities
    UTILS --> OPENAI # api_utils uses OpenAI

    %% Database Utilities
    DBUTILS[Database Utils - database_utils.py]
    DBUTILS --> CONFIG # Uses config for DB path
    DBUTILS --> SQLITE[SQLite] # Uses sqlite3 module

    %% For structuring extracted text & generation
    MLG --> OPENAI

  %% For HTTP requests (iframe, PDF checks)
  MLG --> REQUESTS

  %% For parsing HTML (iframe fallback, PDF link search)
  MLG --> BS4

  %% For PDF text extraction
  MLG --> PYMUPDF

  %% Optional for PDF OCR
  MLG --> EASYOCR

  WTG --> DOCXTPL

  classDef component fill:#f9f,stroke:#333,stroke-width:2px,color:#000;
  classDef external  fill:#9cf,stroke:#333,stroke-width:1px,color:#000;
  classDef optional  fill:#cff,stroke:#333,stroke-width:1px,color:#000;
  classDef database  fill:#ffc,stroke:#333,stroke-width:1px,color:#000;

  class DASH,CVPROC,JDA,JM,MLG,WTG,CONFIG,UTILS,DBUTILS component;
  class OPENAI,DOCXTPL,PYMUPDF,FLASK,REQUESTS,BS4,SQLITE external;
  class SCRAPEGRAPH,EASYOCR optional;

```

**Notes:**
*   Arrows indicate a dependency (e.g., `DASH --> CVPROC` means the Dashboard calls functions from the CV Processor).
*   Data file dependencies (reading/writing JSON, TXT, DOCX, MD files) are described in the "System Workflow & Data Flow" section above and are not explicitly shown in this code dependency graph for clarity.

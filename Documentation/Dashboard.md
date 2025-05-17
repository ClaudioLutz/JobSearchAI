# 6. Dashboard

**Purpose**: Provide a web interface for interacting with all components of the system, structured using Flask Blueprints.

**Key Files**:
- `dashboard.py`: Main Flask application file. Sets up the app using the factory pattern (`create_app`), registers blueprints, defines core routes (`/`, `/operation_status/<id>`, `/delete_files`), and provides shared context/functions (like operation tracking, `get_job_details_for_url`) to blueprints.
- `blueprints/`: Directory containing blueprint modules.
    - `cv_routes.py`: Blueprint (`cv_bp`) handling CV upload, deletion, and summary viewing.
    - `job_data_routes.py`: Blueprint (`job_data_bp`) handling job scraper execution, job data viewing, and deletion.
    - `job_matching_routes.py`: Blueprint (`job_matching_bp`) handling job matcher execution, combined process execution (scraping + matching), results viewing with CV selection for letter generation, report downloading, and report deletion.
    - `motivation_letter_routes.py`: Blueprint (`motivation_letter_bp`) handling:
        * Single/multiple motivation letter generation with manual text input support
        * Bulk email text generation and viewing
        * Letter viewing and downloading (HTML/DOCX)
        * Viewing scraped data associated with letters
        * Letter set deletion (JSON, HTML, DOCX, scraped data)
- `templates/index.html`: Main dashboard page template.
- `templates/results.html`: Job match results page template.
- `templates/motivation_letter.html`: Motivation letter display template.
- `templates/email_text_view.html`: Template for viewing generated email text.
- `templates/job_data_view.html`: Template for viewing bulk job data file contents.
- `templates/scraped_data_view.html`: Template for viewing specific scraped job data.
- `static/css/styles.css`: CSS styles for the dashboard.
- `static/js/main.js`: JavaScript for dashboard interactions (e.g., AJAX calls, progress polling, modal handling, bulk actions).
- **Interacts with:**
    - `process_cv/cv_processor.py`: Used by `cv_routes.py` and potentially `motivation_letter_generator.py`.
    - `job_matcher.py`: Used by `job_matching_routes.py`.
    - `motivation_letter_generator.py`: Used by `motivation_letter_routes.py`.
    - `word_template_generator.py`: Used by `motivation_letter_routes.py`.
    - `process_cv/cv-data/input/`: For CV uploads (via `cv_routes.py`).
    - `process_cv/cv-data/processed/`: For CV summaries.
    - `job-data-acquisition/job-data-acquisition/data/`: For reading/deleting job data JSON files.
    - `job-data-acquisition/settings.json`: Updates `max_pages` before running scraper (via `job_data_routes.py`).
    - `job-data-acquisition/app.py`: Dynamically imported and executed by `job_data_routes.py` and `job_matching_routes.py` (for combined process).
    - `job_matches/`: For reading/deleting report files (MD and JSON) (via `job_matching_routes.py` and `dashboard.py`).
    - `motivation_letters/`: For reading/deleting generated letters (HTML, JSON, DOCX) and scraped job data (`_scraped_data.json`) (via `motivation_letter_routes.py` and `job_matching_routes.py`).

**Technologies**:
- Flask web framework (including Blueprints).
- Python Standard Libraries: `threading` (for background tasks), `uuid` (for operation IDs), `os`, `json`, `logging`, `datetime`, `pathlib`, `urllib.parse`, `importlib.util`.
- `werkzeug` (Flask dependency): Used for `secure_filename`, routing.
- HTML/CSS/JavaScript for the frontend.
- Bootstrap 5 & Bootstrap Icons (assumed usage in templates).

**Features**:
1.  **Tabbed Interface**: Organizes functionality into logical sections:
    *   **Setup & Data**: Upload CVs, Run Job Data Acquisition.
    *   **Run Process**: Run Job Matcher, Run Combined Process.
    *   **View Files**: View available CVs, Job Data, and Reports.
2.  **CV Management**:
    *   Upload new CVs (PDF).
    *   View available CVs with timestamps (handles nested paths).
    *   View CV summaries via modal (AJAX call to `/cv/view_summary/...`, generates summary if it doesn't exist).
    *   Delete individual or multiple CVs and their associated summaries (single via link (`/cv/delete/...`), bulk via AJAX to `/delete_files`).
3.  **Job Data Acquisition**:
    *   Run the job scraper (background task via `/job_data/run_scraper`) to get new job listings, updating `max_pages` in `job-data-acquisition/settings.json` first.
    *   View available job data files (identified by timestamp) in an accordion section.
    *   View the contents of a selected job data file on a separate page (`/job_data/view/<filename>`).
    *   Delete individual or multiple job data files (single via link (`/job_data/delete/...`), bulk via AJAX to `/delete_files`).
4.  **Job Matching**:
    *   Run the job matcher (background task via `/job_matching/run_matcher`) with a selected CV and configurable parameters (`min_score`, `max_jobs`, `max_results`). Stores the `cv_path` used within the results JSON.
    *   Run a combined process (scrape + match) as a single background task (via `/job_matching/run_combined`).
    *   View available job match reports (identified by timestamp) in an accordion section.
    *   View detailed match results on a separate page (`/job_matching/view_results/<report_file>`).
    *   Download job match reports (MD format via `/job_matching/download_report/...`).
    *   Delete individual or multiple reports (MD and associated JSON) (single via link (`/job_matching/delete_report/...`), bulk via AJAX to `/delete_files`).
5.  **Motivation Letter Generation (from Results Page)**:
    *   **CV Selection**: A dropdown menu on the results page allows the user to select which CV summary to use for letter generation. It defaults to the CV used for the report (if found) or the first available CV.
    *   **Single Letter Generation**:
        - Generate personalized motivation letters for specific job postings using the selected CV (background task via `/motivation_letter/generate`)
        - Supports manual text input for job details if automatic scraping is insufficient
        - Checks for existing letters to prevent duplicates (unless using manual input)
    *   **Bulk Operations**:
        - Select multiple job matches to generate letters for all selected jobs using the currently selected CV (AJAX call to `/motivation_letter/generate_multiple`)
        - Generate email texts for multiple selected jobs (AJAX call to `/motivation_letter/generate_multiple_emails`)
    *   **File Management**:
        - View generated letters (renders `motivation_letter.html` via `/motivation_letter/view/<operation_id>` or `/motivation_letter/view/existing?...`)
        - Download letters in HTML format (via `/motivation_letter/download_html?...`)
        - Download letters in Word format (via `/motivation_letter/download_docx?...` or `/motivation_letter/download_docx_from_json?...`)
        - View raw scraped data via "View Scraped Data" option (renders `scraped_data_view.html` via `/motivation_letter/view_scraped_data/...`)
        - View generated email text via "View Email Text" option (renders `email_text_view.html` via `/motivation_letter/view_email_text/existing?...`)
        - Delete letter sets including all associated files (JSON, HTML, DOCX, scraped data)
6.  **File Linking & Display (Results Page)**:
    *   Logic reliably links job matches displayed on the results page to their corresponding generated files:
        - HTML letter (`.html`)
        - Word document (`.docx`)
        - Scraped data (`_scraped_data.json`)
        - Letter structure (`.json`, including `email_text` check)
    *   Matching uses normalized URL comparison between report and scraped data files:
        - Handles both absolute and relative URLs
        - Normalizes paths for consistent comparison
        - Falls back to partial matching if needed
    *   Filenames are constructed using sanitized job titles from matched `_scraped_data.json` files
7.  **User Feedback and Progress Tracking**:
    *   Visual feedback via Flask `flash` messages and JS-driven button states/modals.
    *   Background processing for long operations (scraping, matching, letter generation) using `threading` with proper application context handling (`app.app_context()`).
    *   Progress tracking via unique operation IDs (`uuid`) stored in application context (`current_app.extensions['operation_progress']`, `current_app.extensions['operation_status']`).
    *   Frontend polls the `/operation_status/<id>` endpoint via JavaScript (AJAX) to get progress percentage and status messages.
8.  **Dark Theme**: Consistent dark theme applied across all components (as per original documentation).

**Process**:
1.  The application is created using the `create_app` factory in `dashboard.py`.
2.  Blueprints (`cv_bp`, `job_data_bp`, `job_matching_bp`, `motivation_letter_bp`) are registered, adding their respective routes under prefixes (e.g., `/cv`, `/job_data`).
3.  The main `index` route (`/`) in `dashboard.py` renders the dashboard (`index.html`), fetching initial file lists.
4.  User interactions trigger requests to specific blueprint routes (e.g., uploading a CV goes to `/cv/upload`, running the matcher goes to `/job_matching/run_matcher`).
5.  Long-running tasks (scraping, matching, letter generation) are handled in background threads initiated by the blueprint routes, using the application context (`with app.app_context():`) to access shared resources and functions.
6.  The frontend uses JavaScript (`main.js`) to poll the `/operation_status/<id>` route (defined in `dashboard.py`) for progress updates and displays them, often using modals.
7.  Results are viewed via routes like `/job_matching/view_results/<report_file>` and `/motivation_letter/view/<operation_id>`.
8.  File management (viewing, deleting, downloading) is handled by dedicated routes within the appropriate blueprints or the core `dashboard.py` for bulk actions.

**Functions (Routes - Grouped by Blueprint)**:

*   **`dashboard.py` (Core)**
    *   `index()`: Renders `index.html`.
    *   `get_operation_status_route(operation_id)`: Provides progress updates.
    *   `delete_files_route()`: Handles bulk file deletion via POST.
*   **`cv_routes.py` (`cv_bp`, prefix `/cv`)**
    *   `upload_cv()`: Handles CV upload (POST).
    *   `delete_cv(cv_file_rel_path)`: Deletes a specific CV and summary.
    *   `view_cv_summary(cv_file_rel_path)`: Returns CV summary JSON for AJAX modal.
*   **`job_data_routes.py` (`job_data_bp`, prefix `/job_data`)**
    *   `run_job_scraper()`: Starts job scraper background task (POST).
    *   `delete_job_data(job_data_file)`: Deletes a specific job data file.
    *   `view_job_data(filename)`: Renders `job_data_view.html`.
*   **`job_matching_routes.py` (`job_matching_bp`, prefix `/job_matching`)**
    *   `run_job_matcher()`: Starts job matcher background task (POST).
    *   `run_combined_process()`: Starts combined scraper/matcher background task (POST).
    *   `view_results(report_file)`: Renders `results.html`.
    *   `download_report(report_file)`: Serves report file for download.
    *   `delete_report(report_file)`: Deletes a specific report (MD and JSON).
*   **`motivation_letter_routes.py` (`motivation_letter_bp`, prefix `/motivation_letter`)**
    *   `generate_motivation_letter_route()`: Starts single letter generation background task (POST).
    *   `generate_multiple_letters()`: Handles bulk letter generation via POST (AJAX).
    *   `view_motivation_letter(operation_id)`: Renders `motivation_letter.html` for new or existing letters.
    *   `download_motivation_letter_html()`: Serves HTML letter for download.
    *   `generate_multiple_emails()`: Handles bulk email text generation via POST (AJAX).
    *   `view_motivation_letter(operation_id)`: Renders `motivation_letter.html` for new or existing letters.
    *   `view_email_text()`: Renders `email_text_view.html` for existing email texts.
    *   `download_motivation_letter_html()`: Serves HTML letter for download.
    *   `download_motivation_letter_docx()`: Serves DOCX letter for download.
    *   `download_docx_from_json()`: Generates/serves DOCX from JSON.
    *   `view_scraped_data(scraped_data_filename)`: Renders `scraped_data_view.html`.

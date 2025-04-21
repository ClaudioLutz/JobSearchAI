# 6. Dashboard

**Purpose**: Provide a web interface for interacting with all components of the system.

**Key Files**:
- `dashboard.py`: Main Flask application. Imports functions from `process_cv.cv_processor`, `job_matcher`, `motivation_letter_generator`, `word_template_generator`.
- `templates/index.html`: Main dashboard page template.
- `templates/results.html`: Job match results page template.
- `templates/motivation_letter.html`: Motivation letter display template.
- `templates/job_data_view.html`: Template for viewing bulk job data file contents.
- `templates/scraped_data_view.html`: Template for viewing specific scraped job data.
- `static/css/styles.css`: CSS styles for the dashboard.
- `static/js/main.js`: JavaScript for dashboard interactions (e.g., AJAX calls, progress polling).
- **Interacts with:**
    - `process_cv/cv-data/input/`: For CV uploads.
    - `process_cv/cv-data/processed/`: For CV summaries.
    - `job-data-acquisition/job-data-acquisition/data/`: For reading/deleting job data JSON files.
    - `job-data-acquisition/settings.json`: Updates `max_pages` before running scraper.
    - `job_matches/`: For reading/deleting report files (MD and JSON).
    - `motivation_letters/`: For reading/deleting generated letters (HTML, JSON, DOCX) and scraped job data (`_scraped_data.json`).

**Technologies**:
- Flask web framework.
- Python Standard Libraries: `threading` (for background tasks), `uuid` (for operation IDs), `os`, `json`, `logging`, `datetime`, `pathlib`, `urllib.parse`.
- `werkzeug` (Flask dependency): Used for `secure_filename`.
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
    *   View CV summaries via modal (AJAX call to `/view_cv_summary/...`, generates summary if it doesn't exist).
    *   Delete individual or multiple CVs and their associated summaries (single via link, bulk via AJAX).
3.  **Job Data Acquisition**:
    *   Run the job scraper (background task) to get new job listings, updating `max_pages` in `job-data-acquisition/settings.json` first.
    *   View available job data files (identified by timestamp) in an accordion section.
    *   View the contents of a selected job data file on a separate page (`job_data_view.html`).
    *   Delete individual or multiple job data files (single via link, bulk via AJAX).
4.  **Job Matching**:
    *   Run the job matcher (background task) with a selected CV and configurable parameters (`min_score`, `max_jobs`, `max_results`). Stores the `cv_path` used within the results JSON.
    *   Run a combined process (scrape + match) as a single background task.
    *   View available job match reports (identified by timestamp) in an accordion section.
    *   View detailed match results on a separate page (`results.html`).
    *   Download job match reports (MD format).
    *   Delete individual or multiple reports (MD and associated JSON) (single via link, bulk via AJAX).
5.  **Motivation Letter Generation (from Results Page)**:
    *   **CV Selection**: A dropdown menu on the results page allows the user to select which CV summary to use for letter generation. It defaults to the CV used for the report (if found) or the first available CV.
    *   Generate personalized motivation letters for specific job postings using the selected CV (background task).
    *   View generated letters (renders `motivation_letter.html`).
    *   Download motivation letters in HTML format.
    *   Download motivation letters in Word format (generates DOCX from JSON on-the-fly if needed).
    *   View the raw scraped data used for a specific letter via the "View Scraped Data" option in the Actions dropdown on the results page (renders `scraped_data_view.html`).
    *   Select multiple job matches on the results page and generate letters for all selected jobs using the currently selected CV with a single click (AJAX call to `/generate_multiple_letters`).
6.  **File Linking & Display (Results Page)**:
    *   Improved logic reliably links job matches displayed on the results page to their corresponding generated files (`.html`, `.docx`, `_scraped_data.json`, `.json` letter structure).
    *   Matching is done by comparing Application URLs between the report and scraped data files.
    *   Filenames for checking existence are constructed using the Job Title found *within* the matched `_scraped_data.json` file.
7.  **User Feedback and Progress Tracking**:
    *   Visual feedback via Flask `flash` messages and likely JS-driven button states (e.g., spinners).
    *   Background processing for long operations (scraping, matching, letter generation) using `threading`.
    *   Progress tracking via unique operation IDs (`uuid`) stored in server-side dictionaries (`operation_progress`, `operation_status`).
    *   Frontend polls the `/operation_status/<id>` endpoint via JavaScript (AJAX) to get progress percentage and status messages.
7.  **Dark Theme**: Consistent dark theme applied across all components (as per original documentation).

**Process**:
1.  Provides a web interface at http://127.0.0.1:5000, organized into tabs.
2.  **Setup & Data Tab**: Allows users to upload CVs and run the job scraper (with configurable `max_pages`). Uploaded CVs are processed immediately to generate summaries.
3.  **Run Process Tab**: Allows users to run the job matcher or the combined scrape-and-match process using a selected CV and configurable parameters. These run as background tasks.
4.  **View Files Tab**: Displays available CVs, Job Data files, and Reports in collapsible accordion sections, showing timestamps and providing view/delete actions (single and bulk).
5.  Displays job match results on a separate page (`/view_results/<report_file>`). This page now includes:
    *   A dropdown to select the CV for letter generation.
    *   Improved logic to accurately check for and link to existing motivation letters (HTML, DOCX), structured letter JSON, and scraped job data JSON based on Application URL matching.
6.  Provides options to download job match reports (MD).
7.  Allows users to generate personalized motivation letters (single or multiple) for specific job postings from the results page, using the **currently selected CV** from the dropdown. Generation runs as a background task.
8.  Displays generated motivation letters with options to download in HTML or Word format. Word documents are generated from JSON on demand if not already present.

**Functions (Routes)**:
- `index()`: Render the main dashboard page (`index.html`), fetching file lists with timestamps.
- `upload_cv()`: Handle CV upload (PDF), save to `input`, process, and save summary to `processed`.
- `run_job_matcher()`: Starts the job matcher background task with selected CV and parameters. Returns operation ID.
- `run_job_scraper()`: Updates `settings.json` and starts the job scraper background task. Returns operation ID.
- `run_combined_process()`: Starts the combined scraper and matcher background task. Returns operation ID.
- `view_results(report_file)`: Loads results from JSON, fetches available CV summaries for the dropdown, uses improved logic to check for existing letters/data files by matching Application URLs and using titles from scraped data, renders `results.html`.
- `download_report(report_file)`: Download a job match report (MD).
- `view_cv_summary(cv_file_rel_path)`: Fetch and display CV summary via AJAX, generating if needed.
- `generate_motivation_letter_route()`: Starts the motivation letter generation background task for a specific job, using the **selected CV** from the request data. Returns operation ID.
- `download_motivation_letter()`: Download a generated motivation letter (HTML).
- `download_motivation_letter_docx()`: Download a generated motivation letter (DOCX).
- `download_docx_from_json()`: Generate DOCX from JSON if needed, then download.
- `view_motivation_letter(operation_id)`: Display generated motivation letter content by retrieving results associated with the operation ID. Renders `motivation_letter.html`.
- `delete_cv(cv_file_rel_path)`: Delete a CV file (from `input` or base `cv-data` dir) and its summary (from `processed`). Handles URL-encoded paths.
- `delete_job_data(job_data_file)`: Delete a job data file from `job-data-acquisition/job-data-acquisition/data/`.
- `delete_report(report_file)`: Delete a report file (MD and JSON) from `job_matches/`.
- `delete_files()`: Handle bulk file deletion (CVs, Job Data, Reports) via AJAX POST request.
- `view_job_data(filename)`: Display contents of a bulk job data JSON file using `job_data_view.html`.
- `view_scraped_data(scraped_data_filename)`: Display contents of a specific scraped job data JSON file using `scraped_data_view.html`.
- `generate_multiple_letters()`: Handle bulk motivation letter generation via AJAX POST request, using the **selected CV** from the request data.
- `get_operation_status(operation_id)`: Provide progress updates (percentage, status message) for background tasks via AJAX GET request.

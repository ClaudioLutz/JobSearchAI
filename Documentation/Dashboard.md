# 6. Dashboard

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
- Bootstrap 5 for responsive UI (including Tabs and Accordion components)
- Bootstrap Icons for iconography
- JavaScript for client-side interactions
- HTML/CSS for web interface

**Features**:
1.  **Tabbed Interface**: Organizes functionality into logical sections:
    *   **Setup & Data**: Upload CVs, Run Job Data Acquisition.
    *   **Run Process**: Run Job Matcher, Run Combined Process.
    *   **View Files**: View available CVs, Job Data, and Reports.
2.  **CV Management**:
    *   Upload new CVs (PDF).
    *   View available CVs with timestamps.
    *   View CV summaries via modal.
    *   Delete individual or multiple CVs (with icon buttons).
3.  **Job Data Acquisition**:
    *   Run the job scraper to get new job listings.
    *   View available job data files (identified by timestamp) in an accordion section.
    *   Delete individual or multiple job data files (with icon buttons).
4.  **Job Matching**:
    *   Run the job matcher with a selected CV.
    *   Configure matching parameters (min\_score, max\_results).
    *   Run a combined process (scrape + match).
    *   View available job match reports (identified by timestamp) in an accordion section.
    *   View detailed match results.
    *   Download job match reports (MD format).
    *   Delete individual or multiple reports (with icon buttons).
5.  **Motivation Letter Generation**:
    *   Generate personalized motivation letters for specific job postings from the results page.
    *   View generated letters in a professional format.
    *   Print or download motivation letters in HTML format.
    *   Download motivation letters in Word format.
    *   Select multiple job matches on the results page and generate letters for all selected jobs with a single click.
6.  **User Feedback and Progress Tracking**:
    *   Visual button feedback when actions are initiated (loading spinners).
    *   Real-time progress tracking for long-running operations.
    *   Detailed status messages during processing.
    *   Background processing for long operations to keep UI responsive.
7.  **Dark Theme**: Consistent dark theme applied across all components.

**Process**:
1.  Provides a web interface at http://localhost:5000, organized into tabs.
2.  **Setup & Data Tab**: Allows users to upload CVs and run the job scraper.
3.  **Run Process Tab**: Allows users to run the job matcher or the combined scrape-and-match process using a selected CV.
4.  **View Files Tab**: Displays available CVs, Job Data files, and Reports in collapsible accordion sections, showing timestamps and providing view/delete actions.
5.  Displays job match results on a separate page (`/view_results/...`).
6.  Provides options to download job match reports.
7.  Allows users to generate personalized motivation letters for specific job postings from the results page.
8.  Displays generated motivation letters with options to print or download in HTML or Word format.

**Functions**:
- `index()`: Render the main dashboard page, fetching file lists with timestamps.
- `upload_cv()`: Handle CV upload and processing.
- `run_job_matcher()`: Run the job matcher with the selected CV (background thread).
- `run_job_scraper()`: Run the job data acquisition component (background thread).
- `run_combined_process()`: Run job scraper then job matcher (background thread).
- `view_results()`: View job match results, checking for existing motivation letters.
- `download_report()`: Download a job match report (MD).
- `view_cv_summary()`: Fetch and display CV summary via AJAX, generating if needed.
- `generate_motivation_letter_route()`: Generate a motivation letter for a specific job (background thread).
- `download_motivation_letter()`: Download a generated motivation letter (HTML).
- `download_motivation_letter_docx()`: Download a generated motivation letter (DOCX).
- `download_docx_from_json()`: Generate DOCX from JSON if needed, then download.
- `view_motivation_letter()`: Display generated motivation letter content.
- `delete_cv()`: Delete a CV file and its summary.
- `delete_job_data()`: Delete a job data file.
- `delete_report()`: Delete a report file (MD and JSON).
- `delete_files()`: Handle bulk deletion via AJAX.
- `view_job_data()`: Display contents of a job data JSON file.
- `generate_multiple_letters()`: Handle bulk motivation letter generation via AJAX.
- `get_operation_status()`: Provide progress updates for background tasks.

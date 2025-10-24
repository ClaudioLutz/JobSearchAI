# JobsearchAI

## Quick Start (After Fresh Clone)

After cloning this repository, follow these steps to get started:

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up Environment Variables**:
   Create/update `process_cv/.env` with your OpenAI API key and Gmail credentials:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   SECRET_KEY=your_secret_key_here
   GMAIL_ADDRESS=your_gmail@gmail.com
   GMAIL_APP_PASSWORD=your_16_character_app_password
   ```
   
   **Gmail App Password Setup**:
   To send emails via Gmail, you need to create an App Password:
   1. Go to your Google Account settings: https://myaccount.google.com/
   2. Navigate to Security → 2-Step Verification (must be enabled)
   3. Scroll to "App passwords" at the bottom
   4. Select app: "Mail" and device: "Other" (Custom name: "JobSearchAI")
   5. Click "Generate" and copy the 16-character password
   6. Add it to your `.env` file as `GMAIL_APP_PASSWORD`

3. **Initialize Database**:
   ```bash
   python init_db.py
   ```

4. **Run the Application**:
   ```bash
   python dashboard.py
   ```

5. **Access the Dashboard**:
   Open your browser to `http://localhost:5000` and register a new account.

That's it! The application should now run without any critical errors.

## Overview

JobsearchAI is a secure, multi-user system that matches job listings with candidate CVs using AI-powered semantic matching. It scrapes job data, processes CVs, finds suitable matches, generates personalized motivation letters and email texts, and converts them to Word documents. A comprehensive authentication system protects all functionality, while a web dashboard provides an intuitive interface for managing the system.

The codebase has been optimized with a centralized configuration module and utility packages that improve error handling, reduce code duplication, and enhance API usage without introducing breaking changes.

## System Components

The system consists of the following main components:

1.  **Authentication System**: Secure user registration, login, and session management with Flask-Login.
2.  **Job Data Acquisition**: Scrapes job listings using ScrapeGraphAI.
3.  **CV Processor**: Extracts and summarizes CV information using OpenAI.
4.  **Job Matcher**: Matches jobs with CVs using semantic understanding via OpenAI.
5.  **Motivation Letter Generator**: Creates personalized motivation letters and email texts.
6.  **Word Template Generator**: Converts letters to Word documents.
7.  **Dashboard**: Web interface for system interaction.
8.  **Centralized Configuration**: (`config.py`) Provides a single source of truth for configuration settings.
9.  **Utility Modules**: (`utils/`) Collection of utility modules for common operations with improved error handling.

For detailed information on each component, please refer to the files in the `Documentation/` directory:

-   [Authentication System](./Documentation/Authentication_System.md) - **NEW** Complete security implementation
-   [Job Data Acquisition](./Documentation/Job_Data_Acquisition.md)
-   [CV Processor](./Documentation/CV_Processor.md)
-   [Job Matcher](./Documentation/Job_Matcher.md) - Fully optimized
-   [Motivation Letter Generator](./Documentation/Motivation_Letter_Generator.md) - Fully optimized
-   [Word Template Generator](./Documentation/Word_Template_Generator.md)
-   [Dashboard](./Documentation/Dashboard.md) - Updated with authentication integration
-   [System Overview](./Documentation/System.md) - Updated with authentication workflow

For details on the code optimization, refer to:
-   [Code Optimization](./deprecated_20250427_211727/README_OPTIMIZATION.md)

## Code Optimization

The codebase has been optimized with several new modules:

1. **Centralized Configuration** (`config.py`): Provides a single source of truth for all configuration settings including paths, environment variables, and default parameters.

2. **Utility Modules** in the `utils/` package:
   - `utils/decorators.py`: Decorators for error handling, retries, caching, and execution timing.
   - `utils/file_utils.py`: Functions for common file operations with improved error handling.
   - `utils/api_utils.py`: Wrappers for OpenAI API operations with retries and caching.

Key benefits of these optimizations:
- No breaking changes - maintains full compatibility with existing code
- Improved error handling with consistent patterns across modules
- Reduced code duplication through centralized and reusable functionality
- Better API usage with caching, retries, and error handling
- Centralized configuration management
- Type hints for better IDE support and code quality

Currently optimized components:
- `job_matcher.py`: Fully optimized
- `job_details_utils.py`: Fully optimized
- `letter_generation_utils.py`: Fully optimized

See [README_OPTIMIZATION.md](./deprecated_20250427_211727/README_OPTIMIZATION.md) for detailed examples and usage.

## Basic Usage

### Authentication Setup

Before using the system, you need to set up the database and create user accounts:

```bash
# Initialize the database
python init_db.py

# Create an admin user (follow prompts)
python init_db.py --create-admin

# Test database connection
python init_db.py --test-connection
```

### Running the Dashboard

The primary way to interact with the system is through the web dashboard:

```bash
python dashboard.py
```

Navigate to `http://localhost:5000` in your web browser. You will be redirected to the login page where you can:

- **Login** with your username/email and password
- **Register** a new account if you don't have one
- Access all system functionality after authentication

Once logged in, the dashboard allows you to:

-   Upload and manage CVs
-   Run the job scraper with configurable parameters
-   Run the job matcher with CV selection and matching parameters
-   Run a combined process (scraping + matching)
-   View and manage job match results
-   Generate motivation letters with features like:
    - Automatic job detail extraction
    - Manual text input support
    - Bulk letter generation
    - Email text generation
    - Multiple output formats (HTML, DOCX)
-   View and manage generated files
-   Track progress of background operations

**Security Features:**
- All routes protected by authentication
- Secure password hashing
- Session management with "remember me" option
- CSRF protection on all forms
- Professional login/registration interface

### Running Components Manually

You can also run individual components via the command line. See the respective files in the `Documentation/` folder for specific instructions.

## System Requirements

Ensure you have Python installed and the required dependencies:

```bash
pip install -r requirements.txt
```

API keys are required:
- OpenAI API key for AI features (CV processing, job matching, letter generation)
- ScrapeGraphAI configuration for job scraping

Set the OpenAI key in `process_cv/.env`:
```
OPENAI_API_KEY=your_api_key_here
```

Configure ScrapeGraphAI in `job-data-acquisition/settings.json`.

## File Structure

Key directories and their purposes:

-   `Documentation/`: Detailed component documentation
-   `models/`: Authentication system database models
    - `user.py`: User model with password hashing and validation
    - `__init__.py`: Database and Flask-Login initialization
-   `forms/`: Authentication forms with validation
    - `auth_forms.py`: Login and registration forms
    - `__init__.py`: Forms package initialization
-   `templates/auth/`: Authentication UI templates
    - `base_auth.html`: Base template for authentication pages
    - `login.html`: Professional login page
    - `register.html`: Interactive registration page
-   `blueprints/`: Flask blueprint modules (all protected by authentication)
    - `auth_routes.py`: Authentication routes (login, register, logout)
    - `cv_routes.py`, `job_data_routes.py`, etc.: Feature blueprints
-   `instance/`: Database files (SQLite)
    - `jobsearchai.db`: User database (created automatically)
-   `job-data-acquisition/`: Job scraping component
    - `data/`: Scraped job data (JSON)
    - `settings.json`: Scraper configuration
-   `process_cv/`: CV processing component
    - `cv-data/input/`: Uploaded CVs
    - `cv-data/processed/`: CV summaries
    - `.env`: Environment variables (OpenAI API key, database config)
-   `motivation_letters/`: Generated letters and templates
    - `template/`: Word document templates
    - Generated files: HTML, DOCX, JSON structure, scraped data
-   `job_matches/`: Job match reports (MD and JSON)
-   `static/`: Dashboard static files (CSS, JS)
-   `templates/`: Dashboard HTML templates
-   `logs/`: Component-specific log files
-   `utils/`: Utility modules for common operations
    - `__init__.py`: Package initialization
    - `decorators.py`: Error handling and performance decorators
    - `file_utils.py`: File operation utilities
    - `api_utils.py`: OpenAI API wrappers
-   `config.py`: Centralized configuration module
-   `init_db.py`: Database initialization and user management script
-   No automated tests are included in this repository at present.

## Logging

The system provides comprehensive logging:
- Main dashboard log: `dashboard.log` in root directory
- Component-specific logs in their respective directories
- Background operation progress tracking via the dashboard
- Detailed error logging and stack traces for debugging

## Features

### Authentication & Security
- **Multi-user Support**: Secure user registration and login system
- **Password Security**: Industry-standard password hashing with Werkzeug
- **Session Management**: Flask-Login integration with "remember me" functionality
- **Route Protection**: All application functionality protected by authentication
- **CSRF Protection**: Cross-site request forgery protection on all forms
- **Professional UI**: Modern, responsive login and registration pages
- **Dual Login Methods**: Support for both username and email authentication
- **Account Management**: User account status control (active/inactive)
- **Database Integration**: SQLAlchemy-based user management with proper indexing

### CV Processing
- PDF text extraction and AI-powered summarization
- Focus on career trajectory, preferences, and goals
- Structured summaries for matching and letter generation

### Job Data Acquisition
- Configurable job scraping with ScrapeGraphAI
- Structured job detail extraction
- Support for multiple pages and job sources

### Job Matching
- AI-powered semantic matching
- Configurable parameters (min_score, max_jobs, max_results)
- Detailed match evaluation across multiple criteria
- Combined process option (scraping + matching)

### Motivation Letter Generation
- Personalized letter generation using AI
- Multiple input methods:
  - Automatic job detail extraction
  - Manual text input
  - Pre-scraped data fallback
- Multiple output formats:
  - Structured JSON
  - Formatted HTML
  - Word documents
  - Email texts
- Bulk operations support
- File management and organization

### Email Automation Pipeline
- **Application Queue Dashboard**: Visual queue for reviewing and sending job applications
- **Smart Validation**: Automatic validation of application data with completeness scores
- **User-Friendly Error Messages**: Clear, actionable error messages for all failures
- **Batch Sending**: Send multiple applications at once with detailed results
- **File Management**: Automatic organization of sent/failed applications
- **Gmail Integration**: Secure email sending via Gmail with app password authentication
- **Toast Notifications**: Real-time feedback for all user actions
- **Loading States**: Visual indicators during async operations
- **Responsive Design**: Mobile-friendly interface for review on any device

**Morning Review Workflow**:
1. Navigate to the Queue Dashboard (`/queue`)
2. Review pending applications with validation status indicators
3. Click "Review" to see full application details and email preview
4. Send individual applications or batch-send all ready applications
5. Successfully sent applications are moved to "Sent" tab
6. Failed applications are logged with error details for troubleshooting

### Dashboard Interface
- **Secure Access**: All features protected behind authentication
- **User Information**: Welcome message with username and last login display
- **Session Control**: Easy logout functionality and session management
- Tabbed interface for logical organization
- File management capabilities
- Progress tracking for background tasks
- Bulk operations support
- Dark theme

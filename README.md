# JobsearchAI

## Quick Start (After Fresh Clone)

After cloning this repository, follow these steps to get started:

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up Environment Variables**:
   Create/update `process_cv/.env` with your OpenAI API key and optionally your Gmail credentials:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   SECRET_KEY=your_secret_key_here
   # Optional: Only required if you intend to send emails via the application
   GMAIL_ADDRESS=your_gmail@gmail.com
   GMAIL_APP_PASSWORD=your_16_character_app_password
   ```
   
   **Gmail App Password Setup (Optional)**:
   To send emails via Gmail, you need to create an App Password:
   1. Go to your Google Account settings: https://myaccount.google.com/
   2. Navigate to Security → 2-Step Verification (must be enabled)
   3. Scroll to "App passwords" at the bottom
   4. Select app: "Mail" and device: "Other" (Custom name: "JobSearchAI")
   5. Click "Generate" and copy the 16-character password
   6. Add it to your `.env` file as `GMAIL_APP_PASSWORD`

3. **Initialize Database**:
   ```bash
   python init_db.py full-setup
   ```

4. **Run the Application**:
   ```bash
   python dashboard.py
   ```

5. **Access the Dashboard**:
   Open your browser to `http://localhost:5000` and login with the admin credentials (default: admin / admin123 - change this immediately!).

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
6.  **LinkedIn Integration**: Generates personalized LinkedIn connection messages.
7.  **Word Template Generator**: Converts letters to Word documents.
8.  **Dashboard**: Web interface for system interaction.
9.  **Centralized Configuration**: (`config.py`) Provides a single source of truth for configuration settings.
10. **Utility Modules**: (`utils/`) Collection of utility modules for common operations.
11. **Services**: (`services/`) Business logic services for application handling and LinkedIn generation.

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

## Basic Usage

### Authentication Setup

Before using the system, you need to set up the database and create user accounts. The `init_db.py` script handles this:

```bash
# Full setup (Initialize, Migrate, Create Admin)
python init_db.py full-setup

# Create an admin user manually if needed
python init_db.py create-admin <username> <email> <password>

# Initialize just the job matching database
python init_db.py init-job-db
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

## System Requirements

Ensure you have Python installed and the required dependencies:

```bash
pip install -r requirements.txt
```

For MCP server support, install the additional requirements:
```bash
pip install -r mcp_requirements.txt
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

-   `blueprints/`: Flask blueprint modules (all protected by authentication)
    -   `auth_routes.py`: Authentication routes
    -   `cv_routes.py`: CV management routes
    -   `linkedin_routes.py`: LinkedIn generation routes
    -   `application_routes.py`: Application status API
-   `models/`: Authentication system database models
-   `forms/`: Authentication forms with validation
-   `templates/`: HTML templates
-   `static/`: Static files (CSS, JS)
-   `instance/`: Database files (SQLite)
    -   `jobsearchai.db`: User and job match database
-   `job-data-acquisition/`: Job scraping component
    -   `data/`: Scraped job data (JSON)
    -   `settings.json`: Scraper configuration
-   `process_cv/`: CV processing component
    -   `cv-data/input/`: Uploaded CVs
    -   `cv-data/processed/`: CV summaries
    - `.env`: Environment variables
-   `motivation_letters/`: Generated letters and templates
    -   `template/`: Word document templates
-   `job_matches/`: Job match reports (MD and JSON)
-   `services/`: Business logic services
    -   `linkedin_generator.py`: Generates LinkedIn messages
    -   `application_service.py`: Application pipeline service
-   `scripts/`: Utility scripts
    -   `backup_database.py`: Database backup script
-   `tests/`: Test files (currently primarily manual tests)
-   `utils/`: Utility modules for common operations
-   `config.py`: Centralized configuration module
-   `init_db.py`: Database initialization and user management script

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

### Motivation Letter & Email Generation
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

### Application Package
- **Package Generation**: Generates comprehensive application packages (CV, Cover Letter, Email Text).
- **Email Sending**: Capability to send applications directly (requires Gmail credentials). *Note: Full queue management dashboard is planned.*
- **Validation**: Smart validation utility (Smart Validation) calculates completeness scores, currently available as a backend utility.

### LinkedIn Integration
- Generates personalized connection messages for recruiters
- Uses CV summary and job details context
- Available via the dashboard for matched jobs

## Testing

Automated testing framework is set up in `tests/` (using `pytest`), but comprehensive automated test coverage is currently planned.
Manual test scripts (e.g., `manual_test_linkedin.py`) are available in the `tests/` directory.

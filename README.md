# JobsearchAI

## Overview

JobsearchAI is a system that matches job listings with candidate CVs using AI-powered semantic matching. It scrapes job data, processes CVs, finds suitable matches, generates personalized motivation letters and email texts, and converts them to Word documents.

**This project is currently being adapted for easy local deployment**, allowing users to run it as a standalone desktop application. It features a web dashboard interface for managing the system.

The codebase includes a centralized configuration module and utility packages that improve error handling, reduce code duplication, and enhance API usage.

## System Components

The system consists of the following main components:

1.  **Job Data Acquisition**: Scrapes job listings using ScrapeGraphAI.
2.  **CV Processor**: Extracts and summarizes CV information using OpenAI.
3.  **Job Matcher**: Matches jobs with CVs using semantic understanding via OpenAI.
4.  **Motivation Letter Generator**: Creates personalized motivation letters and email texts.
5.  **Word Template Generator**: Converts letters to Word documents.
6.  **Dashboard**: Web interface for system interaction.
7.  **Centralized Configuration**: (`config.py`) Provides a single source of truth for configuration settings.
8.  **Utility Modules**: (`utils/`) Collection of utility modules for common operations with improved error handling.

For detailed information on each component, please refer to the files in the `documentation/` directory:

-   [Job Data Acquisition](./documentation/Job_Data_Acquisition.md)
-   [CV Processor](./documentation/CV_Processor.md)
-   [Job Matcher](./documentation/Job_Matcher.md) - Fully optimized
-   [Motivation Letter Generator](./documentation/Motivation_Letter_Generator.md) - Fully optimized
-   [Word Template Generator](./documentation/Word_Template_Generator.md)
-   [Dashboard](./documentation/Dashboard.md)
-   [System Overview](./documentation/System.md)

For details on the code optimization, refer to:
-   [Code Optimization](./README_OPTIMIZATION.md)

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

See [README_OPTIMIZATION.md](./README_OPTIMIZATION.md) for detailed examples and usage.

## Basic Usage (Local Deployment)

For instructions on installing and running the packaged local application, please see:

**[User Guide](./README_for_users.md)**

### Development Usage

If you are running the application from source code for development:

1.  Ensure Python 3.8+ is installed.
2.  Install dependencies: `pip install -r requirements.txt`
3.  Configure your OpenAI API key (see Configuration below).
4.  Run the dashboard: `python dashboard.py`
5.  Access the dashboard at `http://localhost:5000`.

The dashboard allows you to:

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

### Running Components Manually

You can also run individual components via the command line. See the respective files in the `documentation/` folder for specific instructions.

## System Requirements

Ensure you have Python installed and the required dependencies:

```bash
pip install -r requirements.txt
```

API keys are required:
- OpenAI API key for AI features (CV processing, job matching, letter generation)
- ScrapeGraphAI configuration for job scraping

### Configuration (Development)

During development, the application uses the following configuration methods:

1.  **OpenAI API Key**:
    *   Ideally, store your key in your system's keychain/credential manager. The application will attempt to retrieve it using the `keyring` library.
    *   Alternatively, create a `.env` file in the project root (`c:/Codes/JobsearchAI`) or in the `process_cv` directory with the line: `OPENAI_API_KEY=your_api_key_here`.
    *   The application will load the key from these sources. **Do not commit `.env` files containing your key to Git.**
2.  **User Settings**: User-specific settings (like API key fallback or custom data directory) are stored in `settings.json` in the OS-specific user config directory (e.g., `AppData/Local/JobsearchAI/JobsearchAI` on Windows). This file is created automatically on first run via the setup wizard.
3.  **Scraper Settings**: Default scraper settings are in `job-data-acquisition/settings.json`.

## File Structure

Key directories and their purposes:

-   `documentation/`: Detailed component documentation
-   `job-data-acquisition/`: Job scraping component
    - `data/`: Scraped job data (JSON)
    - `settings.json`: Scraper configuration
-   `process_cv/`: CV processing component
    - `cv-data/input/`: Uploaded CVs
    - `cv-data/processed/`: CV summaries
-   `motivation_letters/`: Generated letters and templates
    - `template/`: Word document templates
    - Generated files: HTML, DOCX, JSON structure, scraped data
-   `job_matches/`: Job match reports (MD and JSON)
-   `blueprints/`: Flask blueprint modules
-   `static/`: Dashboard static files (CSS, JS)
-   `templates/`: Dashboard HTML templates
-   `logs/`: Component-specific log files
-   `utils/`: Utility modules for common operations
    - `__init__.py`: Package initialization
    - `decorators.py`: Error handling and performance decorators
    - `file_utils.py`: File operation utilities
    - `api_utils.py`: OpenAI API wrappers
-   `config.py`: Centralized configuration module
-   Testing modules:
    - `test_config.py`: Tests for configuration module
    - `test_optimized_code.py`: Integration tests for optimized modules
    - `test_letter_generation_utils.py`, `test_job_details_utils.py`: Component tests

## Logging

The system provides comprehensive logging:
- Main dashboard log: `dashboard.log` in root directory
- Component-specific logs in their respective directories
- Background operation progress tracking via the dashboard
- Detailed error logging and stack traces for debugging

## Features

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

### Dashboard Interface
- Tabbed interface for logical organization
- File management capabilities
- Progress tracking for background tasks
- Bulk operations support
- Dark theme

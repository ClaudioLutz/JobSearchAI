# JobsearchAI

## Overview

JobsearchAI is a system that matches job listings with candidate CVs using AI-powered semantic matching. It scrapes job data, processes CVs, finds suitable matches, generates personalized motivation letters, and converts them to Word documents. A web dashboard provides an interface for managing the system.

## System Components

The system consists of the following main components:

1.  **Job Data Acquisition**: Scrapes job listings.
2.  **CV Processor**: Extracts and summarizes CV information.
3.  **Job Matcher**: Matches jobs with CVs using semantic understanding.
4.  **Motivation Letter Generator**: Creates personalized motivation letters.
5.  **Word Template Generator**: Converts letters to Word documents.
6.  **Dashboard**: Web interface for system interaction.

For detailed information on each component, please refer to the files in the `Documentation/` directory:

-   [Job Data Acquisition](./Documentation/Job_Data_Acquisition.md)
-   [CV Processor](./Documentation/CV_Processor.md)
-   [Job Matcher](./Documentation/Job_Matcher.md)
-   [Motivation Letter Generator](./Documentation/Motivation_Letter_Generator.md)
-   [Word Template Generator](./Documentation/Word_Template_Generator.md)
-   [Dashboard](./Documentation/Dashboard.md)

## Basic Usage

### Running the Dashboard

The primary way to interact with the system is through the web dashboard:

```bash
python dashboard.py
```

Navigate to `http://localhost:5000` in your web browser. The dashboard allows you to:

-   Upload CVs
-   Run the job scraper
-   Run the job matcher
-   View results and reports
-   Generate motivation letters (HTML and DOCX)
-   Manage files

### Running Components Manually

You can also run individual components via the command line. See the respective files in the `Documentation/` folder for specific instructions.

## System Requirements

Ensure you have Python installed and the required dependencies:

```bash
pip install -r requirements.txt
```

An OpenAI API key is required for AI features. Set it in `process_cv/.env`:

```
OPENAI_API_KEY=your_api_key_here
```

## File Structure

Refer to the `File Structure` section in the old README (or explore the project directories) for a detailed layout. Key directories include:

-   `Documentation/`: Detailed component documentation.
-   `job-data-acquisition/`: Job scraping component.
-   `process_cv/`: CV processing component.
-   `motivation_letters/`: Generated letters and templates.
-   `job_matches/`: Job match reports.
-   `static/`, `templates/`: Dashboard web files.

## Logging

Log files for each component are generated in the root directory or component-specific log directories (e.g., `job-data-acquisition/logs/`).

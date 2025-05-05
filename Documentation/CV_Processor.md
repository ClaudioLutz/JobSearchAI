# 2. CV Processor

**Purpose**: Extract, summarize, and convert information from candidate CVs.

**Key Files**:
- `process_cv/cv_processor.py`: Main script for processing and summarizing CVs
- `process_cv/cv_to_html_converter.py`: Script for converting CVs to HTML format
- `process_cv/.env`: Environment variables (OpenAI API key). The script specifically loads it from `c:/Codes/JobsearchAI/process_cv/.env`.

**Technologies**:
- PyMuPDF (fitz) for PDF text and structure extraction
- OpenAI GPT models:
  - `gpt-4.1` for CV summarization
  - `gpt-4.1-mini` for HTML conversion
- Logging system for tracking operations and debugging

**CV Processing Features**:

1. **Text Extraction and Summarization**:
   - Extracts text from PDF CV files using PyMuPDF
   - Uses OpenAI's `gpt-4.1` model (with `temperature=0.2`, `max_tokens=800`) to summarize the CV text using a detailed German prompt
   - The prompt specifically asks the model to extract information regarding:
     - Career path and development
     - Professional preferences (activities, industries, company size, environment)
     - Derivable career goals
     - Indicators of satisfaction in previous roles
     - Work values and cultural preferences
   - **Note:** The dashboard (`cv_routes.py`) calls `extract_cv_text` and then correctly passes the extracted text (not the file path) to `summarize_cv`. After the summary is generated and saved, the dashboard records the CV's metadata (paths, timestamps) into the central SQLite database (`jobsearchai.db`).

2. **HTML Conversion**:
   - Extracts detailed PDF structure including:
     - Document metadata (title, author, dimensions, etc.)
     - Text blocks with position and font information
     - Image blocks with position information
   - Converts CV to responsive HTML using GPT-4.1-mini with:
     - Layout preservation
     - Semantic HTML5 elements
     - Proper CSS styling
     - Print optimization for A4 paper
     - Responsive design principles

**Supported File Formats**:
- PDF (.pdf)

**Main Functions**:

CV Processing:
- `extract_text_from_pdf(pdf_path)`: Extracts text from PDF files
- `extract_cv_text(file_path)`: General function that handles PDF files
- `summarize_cv(cv_text)`: Uses OpenAI (`gpt-4.1`) to generate a structured summary

HTML Conversion:
- `extract_pdf_structure(pdf_path)`: Extracts detailed structural information from PDF
- `convert_cv_to_html(pdf_path)`: Converts CV to HTML while preserving layout
- `save_cv_html(html_content, output_path)`: Saves generated HTML to file
- `convert_pdf_to_html(pdf_path, output_dir)`: Main conversion function with error handling

**Output Directory Structure**:
- HTML files are saved in a 'html' subdirectory relative to the input PDF location
- Generated HTML preserves the original filename with .html extension

**Error Handling**:
- Comprehensive logging system with both file and console output
- Detailed error messages and stack traces
- Graceful error handling with informative return values

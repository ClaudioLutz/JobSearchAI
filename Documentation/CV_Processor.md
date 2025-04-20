# 2. CV Processor

**Purpose**: Extract and summarize information from candidate CVs.

**Key Files**:
- `process_cv/cv_processor.py`: Main script for processing CVs
- `process_cv/.env`: Environment variables (OpenAI API key). The script specifically loads it from `c:/Codes/JobsearchAI/process_cv/.env`.

**Technologies**:
- PyMuPDF (fitz) for PDF text extraction
- OpenAI GPT models (`gpt-4.1`) for CV summarization

**Process**:
1. Extracts text from PDF CV files using PyMuPDF.
2. Uses OpenAI's `gpt-4.1` model (with `temperature=0.2`, `max_tokens=800`) to summarize the CV text using a detailed German prompt.
3. The prompt specifically asks the model to extract information regarding:
    - Career path and development
    - Professional preferences (activities, industries, company size, environment)
    - Derivable career goals
    - Indicators of satisfaction in previous roles
    - Work values and cultural preferences
4. Returns a structured summary based on these points.

**Supported File Formats**:
- PDF (.pdf)

**Functions**:
- `extract_text_from_pdf(pdf_path)`: Extracts text from PDF files
- `extract_cv_text(file_path)`: General function that handles PDF files
- `summarize_cv(cv_text)`: Uses OpenAI (`gpt-4.1`) to generate a structured summary of the CV based on a detailed German prompt.

# 2. CV Processor

**Purpose**: Extract and summarize information from candidate CVs.

**Key Files**:
- `process_cv/cv_processor.py`: Main script for processing CVs
- `process_cv/.env`: Environment variables (OpenAI API key)

**Technologies**:
- PyMuPDF (fitz) for PDF text extraction
- OpenAI GPT models for CV summarization

**Process**:
1. Extracts text from PDF CV files
2. Uses OpenAI's GPT-4o model to summarize the CV text
3. Returns a structured summary of the candidate's skills, experience, education, and preferences

**Supported File Formats**:
- PDF (.pdf)

**Functions**:
- `extract_text_from_pdf(pdf_path)`: Extracts text from PDF files
- `extract_cv_text(file_path)`: General function that handles PDF files
- `summarize_cv(cv_text)`: Uses OpenAI to generate a structured summary of the CV

import os
import logging
import json
import openai
from pathlib import Path
from datetime import datetime
import importlib.util
import sys
import requests
from bs4 import BeautifulSoup
# openai is already imported later, but ensuring it's available early if needed
import openai
import traceback # Ensure traceback is imported for error logging
import fitz # PyMuPDF
import io
from urllib.parse import urljoin # Already imported below, but good to have here too
# Imports for OCR fallback
from PIL import Image
import numpy as np
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    logger.warning("easyocr library not found. OCR fallback for image-based PDFs will be disabled. Install with: pip install easyocr")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("motivation_letter_generator.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("motivation_letter_generator")

def load_cv_summary(cv_filename):
    """Load the CV summary from the processed CV file"""
    try:
        # Construct the summary file path directly from the CV filename
        summary_filename = f"{cv_filename}_summary.txt"
        summary_path = os.path.join('process_cv/cv-data/processed', summary_filename)
        
        # Check if the summary file exists
        if not os.path.exists(summary_path):
            logger.error(f"CV summary file not found: {summary_path}")
            return None
        
        # Load the CV summary
        with open(summary_path, 'r', encoding='utf-8') as f:
            summary = f.read()
        
        return summary
    except Exception as e:
        logger.error(f"Error loading CV summary: {str(e)}")
        return None

def get_job_details_using_scrapegraph(job_url):
    """
    Get job details from ostjob.ch URLs by extracting text from an iframe
    and structuring it using OpenAI.
    """
    logger.info(f"Attempting to get job details via iframe extraction for URL: {job_url}")
    try:
        # Step 1: Get the main job posting page
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        main_response = requests.get(job_url, headers=headers, timeout=15)
        main_response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        main_soup = BeautifulSoup(main_response.text, "html.parser")

        # Step 2: Find the iframe and extract the src URL
        iframe = main_soup.find("iframe", {"title": "vacancyDetailIFrame"})
        iframe_url = iframe["src"] if iframe and "src" in iframe.attrs else None

        if not iframe_url:
            logger.warning(f"No iframe 'vacancyDetailIFrame' found on page: {job_url}. Returning main page soup for PDF link check.")
            # Return the parsed main page soup instead of None
            return main_soup

        # --- If iframe IS found, proceed with iframe processing ---
        # Ensure iframe URL is absolute
        if iframe_url.startswith('/'):
            from urllib.parse import urljoin
            iframe_url = urljoin(job_url, iframe_url)
        logger.info(f"Found iframe URL: {iframe_url}")

        # Step 3: Load the iframe content
        iframe_response = requests.get(iframe_url, headers=headers, timeout=15)
        iframe_response.raise_for_status()
        iframe_soup = BeautifulSoup(iframe_response.text, "html.parser")

        # Step 4: Extract visible text from the iframe
        iframe_text = iframe_soup.get_text(separator="\n", strip=True)
        if not iframe_text:
            logger.warning(f"No text extracted from iframe: {iframe_url}")
            return None
        logger.info(f"Extracted {len(iframe_text)} characters from iframe.")
        # logger.debug(f"Iframe text:\n{iframe_text[:500]}...") # Log beginning of text

        # Step 5: Structure the text using OpenAI
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            env_path = os.path.join('process_cv', '.env')
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    for line in f:
                        if line.startswith('OPENAI_API_KEY='):
                            openai_api_key = line.strip().split('=')[1]
                            break
        if not openai_api_key:
            logger.error("OpenAI API key not found for structuring iframe text.")
            return None

        client = openai.OpenAI(api_key=openai_api_key)

        structuring_prompt = f"""
        Extrahiere die folgenden Informationen aus dem untenstehenden Text eines Stellenangebots und gib sie als JSON-Objekt zurück. Der Text wurde aus einem Iframe einer Jobseite extrahiert.
        Beachte, dass es sich um einen "Arbeitsvermittler" handeln könnte, was nicht das direkte Unternehmen wäre, bei dem man sich bewirbt.

        Felder zum Extrahieren:
        1. Job Title (Stellentitel)
        2. Company Name (Firmenname - oft oben oder im Text erwähnt)
        3. Job Description (Stellenbeschreibung - eine detaillierte Zusammenfassung)
        4. Required Skills (Erforderliche Fähigkeiten/Qualifikationen)
        5. Responsibilities (Verantwortlichkeiten/Aufgaben)
        6. Company Information (Informationen über das Unternehmen, Kultur, etc., falls vorhanden)
        7. Location (Standort/Arbeitsort)
        8. Salary Range (Gehaltsspanne - falls erwähnt)
        9. Posting Date (Veröffentlichungsdatum - falls erwähnt)
        10. Application URL (Die ursprüngliche URL des Haupt-Jobs: {job_url})
        11. Contact Person (Ansprechpartner für die Bewerbung, falls genannt)
        12. Application Email (E-Mail-Adresse für die Bewerbung, falls genannt)

        Stelle sicher, dass die extrahierten Informationen korrekt sind und im JSON-Format vorliegen. Wenn Informationen nicht gefunden werden, setze den Wert auf null oder einen leeren String.

        **Text des Stellenangebots:**
        ---
        {iframe_text}
        ---

        **Ausgabe** muss ein **JSON-Objekt** sein.
        """

        response = client.chat.completions.create(
            model="gpt-4.1", # Or your preferred model
            messages=[
                {"role": "system", "content": "Du bist ein Experte für die Extraktion strukturierter Daten aus Stellenanzeigen. Gib deine Antwort als valides JSON-Objekt zurück."},
                {"role": "user", "content": structuring_prompt}
            ],
            temperature=0.2,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )

        job_details_str = response.choices[0].message.content
        job_details = json.loads(job_details_str)

        # Ensure essential fields have fallbacks and add original URL
        if not job_details.get('Job Title'):
            job_details['Job Title'] = 'Unknown_Job'
        if not job_details.get('Company Name'):
            job_details['Company Name'] = 'Unknown_Company'
        if not job_details.get('Location'):
            job_details['Location'] = 'Unknown_Location'
        if not job_details.get('Job Description'):
            job_details['Job Description'] = 'No description available'
        if not job_details.get('Required Skills'):
            job_details['Required Skills'] = 'No specific skills listed'
        job_details['Application URL'] = job_url # Ensure original URL is present

        logger.info(f"Successfully extracted and structured job details via iframe/OpenAI.")
        logger.info(f"Job Title: {job_details['Job Title']}")
        logger.info(f"Company Name: {job_details['Company Name']}")
        # Log all extracted fields for debugging
        logger.info("--- Extracted Job Details (Iframe Method) ---")
        for key, value in job_details.items():
            log_value = value
            if isinstance(log_value, str) and len(log_value) > 100:
                log_value = log_value[:100] + "... [truncated]"
            logger.info(f"{key}: {log_value}")
        logger.info("---------------------------------------------")

        return job_details

    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP Request error during iframe extraction for {job_url}: {e}")
        return None
    except (AttributeError, KeyError) as e:
        logger.error(f"HTML Parsing error during iframe extraction for {job_url}: {e}")
        return None
    except openai.OpenAIError as e:
        logger.error(f"OpenAI API error during structuring for {job_url}: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"JSON Parsing error after OpenAI structuring for {job_url}: {e}")
        logger.error(f"Raw OpenAI response: {job_details_str}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in get_job_details_using_scrapegraph (iframe method) for {job_url}: {e}")
        logger.error(traceback.format_exc())
        # Return None on unexpected error during iframe processing
        return None

def get_job_details_from_pdf(job_url):
    """
    Get job details from a PDF URL by downloading, extracting text,
    and structuring it using OpenAI.
    """
    logger.info(f"Attempting to get job details from PDF URL: {job_url}")
    try:
        # Step 1: Download the PDF content
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        pdf_response = requests.get(job_url, headers=headers, timeout=20, stream=True) # Use stream=True for potentially large files
        pdf_response.raise_for_status()

        # Check content type if possible (optional but good practice)
        content_type = pdf_response.headers.get('Content-Type', '').lower()
        if 'application/pdf' not in content_type:
            logger.warning(f"URL {job_url} did not return PDF content type (got: {content_type}). Aborting PDF processing.")
            return None

        pdf_content = pdf_response.content # Read content after checks
        logger.info(f"Downloaded {len(pdf_content)} bytes of PDF content.")

        # Step 2: Extract text from PDF using PyMuPDF (fitz)
        pdf_text = ""
        MIN_TEXT_LENGTH_FOR_PYMUPDF = 100 # Heuristic: If less text than this, try OCR
        try_ocr = False
        with fitz.open(stream=pdf_content, filetype="pdf") as doc:
            for page_num, page in enumerate(doc):
                page_text = page.get_text()
                pdf_text += page_text
                # Check if text extraction seems insufficient and OCR is available
                if len(pdf_text.strip()) < MIN_TEXT_LENGTH_FOR_PYMUPDF and EASYOCR_AVAILABLE:
                    logger.warning(f"PyMuPDF extracted very little text ({len(pdf_text.strip())} chars) from page {page_num+1} of {job_url}. Will attempt OCR fallback.")
                    try_ocr = True
                    break # Stop PyMuPDF extraction if OCR is needed

            if try_ocr:
                pdf_text = "" # Reset text, OCR will provide it
                logger.info("Attempting OCR extraction...")
                # Initialize reader once if needed (consider moving outside function if called often)
                # For simplicity here, initialize inside. Adjust language list as needed.
                reader = easyocr.Reader(['de','en'], gpu=True) # Or gpu=False if no GPU/CUDA
                for page_num, page in enumerate(doc):
                    logger.info(f"Performing OCR on page {page_num+1}...")
                    pix = page.get_pixmap()
                    img_bytes = pix.tobytes("png") # Get image bytes
                    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                    results = reader.readtext(np.array(img), detail=0, paragraph=True) # Use paragraph=True for better text flow
                    page_ocr_text = "\n".join(results)
                    pdf_text += page_ocr_text + "\n\n" # Add page breaks
                logger.info(f"OCR extracted {len(pdf_text)} characters.")

        # Check final extracted text length (either from PyMuPDF or OCR)
        if len(pdf_text.strip()) < MIN_TEXT_LENGTH_FOR_PYMUPDF: # Use threshold again
            logger.warning(f"Extracted text length ({len(pdf_text.strip())} chars) is below threshold after all attempts for {job_url}. Aborting.")
            return None

        logger.info(f"Final extracted text length: {len(pdf_text)} characters.")
        # logger.debug(f"Final PDF text:\n{pdf_text[:500]}...")

        # Step 3: Structure the text using OpenAI
        openai_api_key = os.getenv('OPENAI_API_KEY')
        # (API key loading logic omitted for brevity - assuming it's handled as before)
        if not openai_api_key:
             env_path = os.path.join('process_cv', '.env')
             if os.path.exists(env_path):
                 with open(env_path, 'r') as f:
                     for line in f:
                         if line.startswith('OPENAI_API_KEY='):
                             openai_api_key = line.strip().split('=')[1]
                             break
        if not openai_api_key:
            logger.error("OpenAI API key not found for structuring PDF text.")
            return None

        client = openai.OpenAI(api_key=openai_api_key)

        structuring_prompt = f"""
        Extrahiere die folgenden Informationen aus dem untenstehenden Text eines Stellenangebots und gib sie als JSON-Objekt zurück. Der Text wurde aus einem PDF-Dokument extrahiert.
        Beachte, dass es sich um einen "Arbeitsvermittler" handeln könnte, was nicht das direkte Unternehmen wäre, bei dem man sich bewirbt.

        Felder zum Extrahieren:
        1. Job Title (Stellentitel)
        2. Company Name (Firmenname - oft oben oder im Text erwähnt)
        3. Job Description (Stellenbeschreibung - eine detaillierte Zusammenfassung)
        4. Required Skills (Erforderliche Fähigkeiten/Qualifikationen)
        5. Responsibilities (Verantwortlichkeiten/Aufgaben)
        6. Company Information (Informationen über das Unternehmen, Kultur, etc., falls vorhanden)
        7. Location (Standort/Arbeitsort)
        8. Salary Range (Gehaltsspanne - falls erwähnt)
        9. Posting Date (Veröffentlichungsdatum - falls erwähnt)
        10. Application URL (Die ursprüngliche URL des PDFs: {job_url})
        11. Contact Person (Ansprechpartner für die Bewerbung, falls genannt)
        12. Application Email (E-Mail-Adresse für die Bewerbung, falls genannt)

        Stelle sicher, dass die extrahierten Informationen korrekt sind und im JSON-Format vorliegen. Wenn Informationen nicht gefunden werden, setze den Wert auf null oder einen leeren String.

        **Text des Stellenangebots (aus PDF):**
        ---
        {pdf_text}
        ---

        **Ausgabe** muss ein **JSON-Objekt** sein.
        """

        response = client.chat.completions.create(
            model="gpt-4.1", # Or your preferred model
            messages=[
                {"role": "system", "content": "Du bist ein Experte für die Extraktion strukturierter Daten aus Stellenanzeigen (PDFs). Gib deine Antwort als valides JSON-Objekt zurück."},
                {"role": "user", "content": structuring_prompt}
            ],
            temperature=0.2,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )

        job_details_str = response.choices[0].message.content
        job_details = json.loads(job_details_str)

        # Ensure essential fields have fallbacks and add original URL
        if not job_details.get('Job Title'):
            job_details['Job Title'] = 'Unknown_Job'
        if not job_details.get('Company Name'):
            job_details['Company Name'] = 'Unknown_Company'
        # ... (add other fallbacks as needed) ...
        job_details['Application URL'] = job_url # Ensure original URL is present

        logger.info(f"Successfully extracted and structured job details from PDF.")
        logger.info(f"Job Title: {job_details['Job Title']}")
        logger.info(f"Company Name: {job_details['Company Name']}")
        # Log details...

        return job_details

    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP Request error during PDF download for {job_url}: {e}")
        return None
    except fitz.fitz.FitzError as e:
        logger.error(f"PyMuPDF error processing PDF from {job_url}: {e}")
        return None
    except openai.OpenAIError as e:
        logger.error(f"OpenAI API error during PDF structuring for {job_url}: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"JSON Parsing error after OpenAI PDF structuring for {job_url}: {e}")
        logger.error(f"Raw OpenAI response: {job_details_str}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in get_job_details_from_pdf for {job_url}: {e}")
        logger.error(traceback.format_exc())
        return None

def get_job_details_from_scraped_data(job_url):
    """Get job details from pre-scraped data"""
    try:
        # Extract the job ID from the URL
        # Example URL: https://www.ostjob.ch/jobs/detail/12345
        logger.info(f"Getting job details from pre-scraped data for URL: {job_url}")
        job_id = job_url.split('/')[-1]
        logger.info(f"Extracted job ID: {job_id}")
        
        # Find the job data file
        job_data_dir = Path('job-data-acquisition/job-data-acquisition/data')
        logger.info(f"Job data directory: {job_data_dir}")
        if not job_data_dir.exists():
            logger.error(f"Job data directory not found: {job_data_dir}")
            return None
        
        # Get the latest job data file
        job_data_files = list(job_data_dir.glob('job_data_*.json'))
        logger.info(f"Found {len(job_data_files)} job data files")
        if not job_data_files:
            logger.error("No job data files found")
            return None
        
        latest_job_data_file = max(job_data_files, key=os.path.getctime)
        logger.info(f"Latest job data file: {latest_job_data_file}")
        
        # Load the job data
        with open(latest_job_data_file, 'r', encoding='utf-8') as f:
            job_data_pages = json.load(f) # Rename to reflect it's a list of pages

        # Flatten the list of lists into a single list of job dictionaries
        all_jobs = []
        if isinstance(job_data_pages, list):
            for page_list in job_data_pages:
                if isinstance(page_list, list):
                    all_jobs.extend(page_list)
                elif isinstance(page_list, dict): # Handle potential single job dict per page?
                    all_jobs.append(page_list)
            logger.info(f"Loaded and flattened job data with {len(all_jobs)} total jobs from {len(job_data_pages)} pages.")
        else:
            logger.error(f"Unexpected data structure in {latest_job_data_file}. Expected list of lists.")
            return None

        # Find the job with the matching ID in the flattened list
        found_job = None
        for i, job in enumerate(all_jobs):
            if not isinstance(job, dict): # Skip if item is not a dictionary
                logger.warning(f"Skipping non-dictionary item at index {i} in flattened job list.")
                continue

            job_application_url = job.get('Application URL', '')
            # logger.debug(f"Checking Job {i+1} Application URL: {job_application_url}") # Use debug level

            if job_id in job_application_url:
                logger.info(f"Found matching job: {job.get('Job Title', 'N/A')} at {job.get('Company Name', 'N/A')}")
                found_job = job
                # Log all extracted fields for debugging
                logger.info("--- Extracted Job Details from Pre-scraped Data ---")
                for key, value in found_job.items():
                    # Truncate long values for logging
                    log_value = value
                    if isinstance(log_value, str) and len(log_value) > 100:
                        log_value = log_value[:100] + "... [truncated]"
                    logger.info(f"{key}: {log_value}")
                logger.info("------------------------------------------")
                break # Exit loop once found

        if found_job:
            return found_job

        # If no exact match found, use the first job in the flattened list as a fallback
        logger.warning(f"Job with ID {job_id} not found in pre-scraped data. Using first available job as fallback.")
        if all_jobs:
            first_job = all_jobs[0]
            if isinstance(first_job, dict):
                 logger.info(f"Using first job as fallback: {first_job.get('Job Title', 'N/A')} at {first_job.get('Company Name', 'N/A')}")
                 return first_job
            else:
                 logger.error("First item in flattened job list is not a dictionary, cannot use as fallback.")
                 return None
        else:
            logger.error("No jobs found in the pre-scraped data file after processing.")
        return None
    except Exception as e:
        logger.error(f"Error getting job details from pre-scraped data: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def get_job_details(job_url):
    """
    Get job details from the job URL using multiple methods:
    1. Try iframe/HTML extraction + OpenAI structuring.
    2. If URL suggests PDF, try PDF download/extraction + OpenAI structuring.
    3. Fallback to pre-scraped data file.
    """
    try:
        # --- Attempt 1: Iframe Method ---
        logger.info(f"Attempt 1: Trying iframe/HTML extraction for URL: {job_url}")
        iframe_or_soup_result = get_job_details_using_scrapegraph(job_url)

        if isinstance(iframe_or_soup_result, dict):
            # Success: iframe found and processed by get_job_details_using_scrapegraph
            logger.info("Success with iframe/OpenAI extraction method.")
            return iframe_or_soup_result

        # --- Attempt 2: Search HTML for PDF Link (if iframe failed but page loaded) ---
        job_details = None # Reset job_details
        if isinstance(iframe_or_soup_result, BeautifulSoup):
            main_soup = iframe_or_soup_result
            logger.info("Attempt 2: Iframe method failed (no iframe found). Checking main page HTML for PDF links.")
            pdf_link_found = False
            # Search for links containing '/preview/pdf' or ending in '.pdf'
            for link in main_soup.find_all('a', href=True):
                href = link['href']
                # Prioritize links specifically containing '/preview/pdf' as seen in examples
                if '/preview/pdf' in href or href.lower().endswith('.pdf'):
                    pdf_url = urljoin(job_url, href) # Ensure absolute URL
                    logger.info(f"Found potential PDF link in HTML: {pdf_url}. Attempting PDF/OCR processing.")
                    job_details = get_job_details_from_pdf(pdf_url) # Try processing this PDF URL
                    if job_details:
                        logger.info("Success extracting details from linked PDF.")
                        return job_details # Return immediately if PDF processing successful
                    else:
                        logger.warning(f"Failed to extract details from linked PDF: {pdf_url}")
                    pdf_link_found = True
                    break # Stop after finding the first likely PDF link
            if not pdf_link_found:
                 logger.info("No direct PDF link found in main page HTML.")
        elif iframe_or_soup_result is None:
             # Initial request or parsing failed in get_job_details_using_scrapegraph
             logger.info("Iframe/HTML extraction method failed completely (request/parse error).")
        # If we reach here, either iframe failed and no PDF link worked, or the initial page load failed.

        # --- Attempt 3: Check Content-Type of the *original* URL via HEAD request ---
        # This is a fallback in case the main URL itself is a direct PDF link,
        # or if the HTML parsing for links failed unexpectedly.
        is_pdf = False
        try:
            logger.info(f"Attempt 2: Checking Content-Type via HEAD request for URL: {job_url}")
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            head_response = requests.head(job_url, headers=headers, timeout=10, allow_redirects=True) # Allow redirects for HEAD
            head_response.raise_for_status()
            content_type = head_response.headers.get('Content-Type', '').lower()
            logger.info(f"HEAD request successful. Content-Type: {content_type}")
            if 'application/pdf' in content_type:
                is_pdf = True
        except requests.exceptions.RequestException as head_err:
            logger.warning(f"HEAD request failed for {job_url}: {head_err}. Cannot determine content type via HEAD.")
        except Exception as head_exc:
             logger.error(f"Unexpected error during HEAD request for {job_url}: {head_exc}")

        if is_pdf:
            logger.info(f"Content-Type of original URL indicates PDF. Trying PDF/OCR extraction for URL: {job_url}")
            job_details = get_job_details_from_pdf(job_url) # Try processing original URL as PDF
            if job_details:
                logger.info("Success with PDF/OCR extraction method on original URL.")
                return job_details
            else:
                logger.info("PDF/OCR extraction method failed on original URL.")
        else:
             logger.info("Content-Type of original URL is not PDF or HEAD request failed.")

        # --- Attempt 4: Fallback to pre-scraped data ---
        logger.info("Attempt 3: Falling back to pre-scraped data.")
        job_details = get_job_details_from_scraped_data(job_url)

        if job_details:
            logger.info("Success with pre-scraped data fallback.")
            return job_details
        
        # If all methods fail, return a default job details object
        logger.warning("All methods to get job details failed, using default values")
        return {
            'Job Title': 'Unknown_Job',
            'Company Name': 'Unknown_Company',
            'Location': 'Unknown_Location',
            'Job Description': 'No description available',
            'Required Skills': 'No specific skills listed',
            'Application URL': job_url
        }
    except Exception as e:
        logger.error(f"Error getting job details: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Return default values in case of error
        return {
            'Job Title': 'Unknown_Job',
            'Company Name': 'Unknown_Company',
            'Location': 'Unknown_Location',
            'Job Description': 'No description available',
            'Required Skills': 'No specific skills listed',
            'Application URL': job_url
        }

def json_to_html(motivation_letter_json):
    """Convert motivation letter JSON to HTML format"""
    try:
        # Extract fields from JSON
        candidate_name = motivation_letter_json.get('candidate_name', '')
        candidate_address = motivation_letter_json.get('candidate_address', '')
        candidate_city = motivation_letter_json.get('candidate_city', '')
        candidate_email = motivation_letter_json.get('candidate_email', '')
        candidate_phone = motivation_letter_json.get('candidate_phone', '')
        
        company_name = motivation_letter_json.get('company_name', '')
        company_department = motivation_letter_json.get('company_department', '')
        company_street_number = motivation_letter_json.get('company_street_number', '')
        company_plz_city = motivation_letter_json.get('company_plz_city', '')
        
        date = motivation_letter_json.get('date', '')
        subject = motivation_letter_json.get('subject', '')
        greeting = motivation_letter_json.get('greeting', '')
        introduction = motivation_letter_json.get('introduction', '')
        
        body_paragraphs = motivation_letter_json.get('body_paragraphs', [])
        
        closing = motivation_letter_json.get('closing', '')
        signature = motivation_letter_json.get('signature', '')
        full_name = motivation_letter_json.get('full_name', '')
        
        # Create HTML content
        html_content = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Motivationsschreiben</title>
</head>
<body>
    <p>{candidate_name}<br>
    {candidate_address}<br>
    {candidate_city}<br>
    {candidate_email}<br>
    {candidate_phone}</p>

    <p>{company_name}<br>
    {company_department}<br>
    {company_street_number}<br>
    {company_plz_city}</p>

    <p>{date}</p>

    <h2>{subject}</h2>

    <p>{greeting},</p>

    <p>{introduction}</p>
"""
        
        # Add body paragraphs
        for paragraph in body_paragraphs:
            html_content += f"    <p>{paragraph}</p>\n"
        
        # Add closing and signature
        html_content += f"""
    <p>{closing}</p>

    <p>{signature},<br>
    {full_name}</p>
</body>
</html>
"""
        
        return html_content
    except Exception as e:
        logger.error(f"Error converting JSON to HTML: {str(e)}")
        return "<p>Error generating HTML content</p>"

def generate_motivation_letter(cv_summary, job_details):
    """Generate a motivation letter using GPT-4o"""
    try:
        # Get OpenAI API key from environment variable
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            # Try to get it from the .env file in process_cv directory
            env_path = os.path.join('process_cv', '.env')
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    for line in f:
                        if line.startswith('OPENAI_API_KEY='):
                            openai_api_key = line.strip().split('=')[1]
                            break
        
        if not openai_api_key:
            logger.error("OpenAI API key not found")
            return None
        
        # Initialize OpenAI client
        client = openai.OpenAI(api_key=openai_api_key)
        
        # Prepare the prompt
        prompt = """
        Schreibe ein Motivationsschreiben aus den Informationen von der Webseite und dem Lebenslauf:
        
        ## Lebenslauf des Bewerbers:
        {}
        
        ## Stellenangebot (von der Webseite):
        Titel: {}
        Firma: {}
        Ort: {}
        
        Beschreibung: 
        {}
        
        Erforderliche Fähigkeiten: 
        {}
        
        Verantwortlichkeiten: 
        {}
        
        Unternehmensinformationen: 
        {}
        
        Das Motivationsschreiben sollte:
        1. Professionell und überzeugend sein
        2. Die Qualifikationen und Erfahrungen des Bewerbers KONKRET mit den Anforderungen der Stelle verknüpfen
        3. Die Motivation des Bewerbers für die Stelle und das Unternehmen zum Ausdruck bringen
        4. Etwa eine halbe Seite lang sein (ca. 150-200 Wörter)
        5. Auf Deutsch verfasst sein
        6. Im formalen Bewerbungsstil mit Anrede, Einleitung, Hauptteil, Schluss und Grußformel sein
        7. SPEZIFISCH auf die Stellenanforderungen und Verantwortlichkeiten eingehen, die aus der Webseite extrahiert wurden
        8. Die Stärken des Bewerbers hervorheben, die besonders relevant für diese Position sind
        9. Auf die Unternehmenskultur und -werte eingehen, wenn diese Informationen verfügbar sind
        10. KONKRETE BEISPIELE aus dem Lebenslauf des Bewerbers verwenden, die zeigen, wie er/sie die Anforderungen erfüllt
        
        WICHTIG: Falls die Firma der ausgeschriebenen Stell die "Universal-Job AG" ist, behandle sie als Personalvermittler in deinem Schreiben und passe den Inhalt entsprechend an. In diesem Fall wissen wir nicht wer die Stelle schlussendlich ausgeschrieben hat.
        
        WICHTIG: Verwende die detaillierten Informationen aus der Stellenbeschreibung, um ein personalisiertes und spezifisches Motivationsschreiben zu erstellen. Gehe auf konkrete Anforderungen und Verantwortlichkeiten ein und zeige, wie der Bewerber diese erfüllen kann.
        
        WICHTIG: Der Motivtions Text darf maximal 200-300 Wörter beinhalten. 

        "ß" soll als "ss" geschrieben werden. 

        Gib das Motivationsschreiben als JSON-Objekt mit folgender Struktur zurück:
        
        ```json
        {{
          "candidate_name": "Vollständiger Name des Bewerbers",
          "candidate_address": "Straße und Hausnummer",
          "candidate_city": "PLZ und Ort",
          "candidate_email": "E-Mail-Adresse",
          "candidate_phone": "Telefonnummer",
          "company_name": "Name des Unternehmens",
          "company_department": "Abteilung (falls bekannt, sonst 'Personalabteilung')",
          "company_street_number": "Strasse und Hausnummerdes Unternehmens (falls bekannt)",
          "company_plz_city": "Postleitzahl und Stadt (falls bekannt)",
          "date": "Ort, den [aktuelles Datum]",
          "subject": "Bewerbung als [Stellentitel]",
          "greeting": "Anrede (z.B. 'Sehr geehrte Damen und Herren')",
          "introduction": "Einleitungsabsatz",
          "body_paragraphs": [
            "Erster Hauptabsatz",
            "Zweiter Hauptabsatz",
            "Dritter Hauptabsatz (falls nötig)"
          ],
          "closing": "Schlussabsatz",
          "signature": "Grussformel (z.B. 'Mit freundlichen Grüssen')",
          "full_name": "Vollständiger Name des Bewerbers"
        }}
        ```
        
        Stelle sicher, dass alle Felder korrekt befüllt sind und das JSON-Format gültig ist.
        """.format(
            cv_summary,
            job_details.get('Job Title', 'N/A'),
            job_details.get('Company Name', 'N/A'),
            job_details.get('Location', 'N/A'),
            job_details.get('Job Description', 'N/A'),
            job_details.get('Required Skills', 'N/A'),
            job_details.get('Responsibilities', 'Keine spezifischen Verantwortlichkeiten aufgeführt.'),
            job_details.get('Company Information', 'Keine spezifischen Unternehmensinformationen verfügbar.')
        )
        
        # Generate the motivation letter using GPT-4o
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": "Du bist ein professioneller Bewerbungsberater, der Motivationsschreiben für Stellenbewerbungen erstellt. Gib deine Antwort als valides JSON-Objekt zurück."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500,
            response_format={"type": "json_object"}  # Ensure JSON response
        )
        
        # Extract the generated motivation letter as JSON
        motivation_letter_json_str = response.choices[0].message.content
        
        try:
            # Parse the JSON response
            motivation_letter_json = json.loads(motivation_letter_json_str)
            logger.info("Successfully parsed motivation letter JSON")
            
            # Convert JSON to HTML for backward compatibility
            html_content = json_to_html(motivation_letter_json)
            
            # Save the motivation letter (both JSON and HTML)
            # Sanitize job title and company name to avoid path issues
            job_title = job_details.get('Job Title', 'job')
            company_name = job_details.get('Company Name', 'company')
            
            # Replace problematic characters and limit length
            job_title = ''.join(c if c.isalnum() or c in [' ', '_', '-'] else '_' for c in job_title)
            company_name = ''.join(c if c.isalnum() or c in [' ', '_', '-'] else '_' for c in company_name)
            
            # Limit length to avoid excessively long filenames
            job_title = job_title.replace(' ', '_')[:30]
            company_name = company_name.replace(' ', '_')[:30]
            
            # Create the motivation letters directory if it doesn't exist
            motivation_letters_dir = Path('motivation_letters')
            motivation_letters_dir.mkdir(exist_ok=True)
            
            # Save the HTML version - use job title as the primary identifier
            html_filename = f"motivation_letter_{job_title}.html"
            html_file_path = motivation_letters_dir / html_filename
            
            logger.info(f"Saving HTML motivation letter to file: {html_file_path}")
            with open(html_file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Save the JSON version - use job title as the primary identifier
            json_filename = f"motivation_letter_{job_title}.json"
            json_file_path = motivation_letters_dir / json_filename
            
            logger.info(f"Saving JSON motivation letter to file: {json_file_path}")
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(motivation_letter_json, f, ensure_ascii=False, indent=2)

            # Save the scraped job details as well
            scraped_data_filename = f"motivation_letter_{job_title}_scraped_data.json"
            scraped_data_path = motivation_letters_dir / scraped_data_filename
            logger.info(f"Saving scraped job details to file: {scraped_data_path}")
            with open(scraped_data_path, 'w', encoding='utf-8') as f:
                json.dump(job_details, f, ensure_ascii=False, indent=2) # Save the original job_details dict
            
            return {
                'motivation_letter_json': motivation_letter_json,
                'motivation_letter_html': html_content,
                'html_file_path': str(html_file_path),
                'json_file_path': str(json_file_path),
                'scraped_data_path': str(scraped_data_path) # Add path to scraped data
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON response: {str(e)}")
            logger.error(f"Raw response: {motivation_letter_json_str}")
            
            # Fallback: treat the response as HTML directly
            logger.warning("Falling back to treating response as HTML")
            
            # Sanitize job title and company name to avoid path issues
            job_title = job_details.get('Job Title', 'job')
            company_name = job_details.get('Company Name', 'company')
            
            # Replace problematic characters and limit length
            job_title = ''.join(c if c.isalnum() or c in [' ', '_', '-'] else '_' for c in job_title)
            company_name = ''.join(c if c.isalnum() or c in [' ', '_', '-'] else '_' for c in company_name)
            
            # Limit length to avoid excessively long filenames
            job_title = job_title.replace(' ', '_')[:30]
            company_name = company_name.replace(' ', '_')[:30]
            
            # Create the motivation letters directory if it doesn't exist
            motivation_letters_dir = Path('motivation_letters')
            motivation_letters_dir.mkdir(exist_ok=True)
            
            # Save the motivation letter to a file - use job title as the primary identifier
            filename = f"motivation_letter_{job_title}.html"
            motivation_letter_file = motivation_letters_dir / filename
            
            logger.info(f"Saving motivation letter to file: {motivation_letter_file}")
            with open(motivation_letter_file, 'w', encoding='utf-8') as f:
                f.write(motivation_letter_json_str)
            
            return {
                'motivation_letter': motivation_letter_json_str,
                'file_path': str(motivation_letter_file)
            }
    except Exception as e:
        logger.error(f"Error generating motivation letter: {str(e)}")
        return None

def main(cv_filename, job_url, existing_job_details=None):
    """Main function to generate a motivation letter"""
    logger.info(f"Starting motivation letter generation for CV: {cv_filename} and job URL: {job_url}")
    
    # Load the CV summary
    cv_summary = load_cv_summary(cv_filename)
    if not cv_summary:
        logger.error("Failed to load CV summary")
        return None
    
    logger.info("Successfully loaded CV summary")
    
    # Get the job details - use existing details if provided
    if existing_job_details:
        job_details = existing_job_details
        logger.info(f"Using provided job details instead of extracting again. Job Title: {job_details.get('Job Title', 'N/A')}")
    else:
        job_details = get_job_details(job_url)
        if not job_details:
            logger.error("Failed to get job details")
            return None
    
    logger.info("Successfully got job details")
    
    # Generate the motivation letter
    result = generate_motivation_letter(cv_summary, job_details)
    if not result:
        logger.error("Failed to generate motivation letter")
        return None
    
    # Check which format we have (JSON or HTML)
    if 'json_file_path' in result:
        logger.info(f"Successfully generated motivation letter: {result['json_file_path']}")
    else:
        logger.info(f"Successfully generated motivation letter: {result['file_path']}")
    return result

if __name__ == "__main__":
    # Example usage
    cv_filename = "Lebenslauf"
    job_url = "https://www.ostjob.ch/jobs/detail/12345"
    result = main(cv_filename, job_url)
    
    if result:
        if 'json_file_path' in result:
            print(f"Motivation letter generated successfully: {result['json_file_path']}")
        else:
            print(f"Motivation letter generated successfully: {result['file_path']}")
    else:
        print("Failed to generate motivation letter")

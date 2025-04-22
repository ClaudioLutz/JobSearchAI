import os
import logging
import json
import openai
from pathlib import Path
from datetime import datetime
import importlib.util
import sys
# Removed requests, BeautifulSoup, fitz, io, urljoin, PIL, numpy
import openai
import traceback
import logging
from urllib.parse import urljoin # Re-add urljoin for the fallback function
# Kept os, json, Path, datetime, importlib.util

# Import the structured extraction utility function (renamed back)
from graph_scraper_utils import get_job_details_with_graphscrapeai

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Removed easyocr check

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

# Helper function to check quality of extracted details
def has_sufficient_content(details_dict):
    """Checks if extracted details have meaningful content for key fields."""
    if not isinstance(details_dict, dict):
        return False

    description = details_dict.get('Job Description')
    responsibilities = details_dict.get('Responsibilities')
    skills = details_dict.get('Required Skills')

    # Check description (allow for slightly longer placeholders, check length)
    has_desc = description and isinstance(description, str) and len(description.strip()) > 25 and "No description available" not in description
    # Check responsibilities (allow for slightly longer placeholders, check length)
    has_resp = responsibilities and isinstance(responsibilities, str) and len(responsibilities.strip()) > 25 and "No specific responsibilities listed" not in responsibilities
    # Check skills (check against common placeholders, check length)
    has_skills = skills and isinstance(skills, str) and len(skills.strip()) > 10 and "No specific skills listed" not in skills and skills.upper() not in ["N/A", "NA"]

    # Require description OR (responsibilities OR skills) to be considered sufficient
    # This ensures we have *some* content to base the motivation letter on.
    return has_desc or has_resp or has_skills

def load_cv_summary(cv_filename):
    """Load the CV summary from the processed CV file"""
    try:
        summary_filename = f"{cv_filename}_summary.txt"
        summary_path = os.path.join('process_cv/cv-data/processed', summary_filename)
        if not os.path.exists(summary_path):
            logger.error(f"CV summary file not found: {summary_path}")
            return None
        with open(summary_path, 'r', encoding='utf-8') as f:
            summary = f.read()
        return summary
    except Exception as e:
        logger.error(f"Error loading CV summary: {str(e)}")
        return None

def structure_text_with_openai(text_content, source_url, source_type="HTML"):
    """Uses OpenAI to structure extracted text from HTML or PDF."""
    logger.info(f"Structuring text from {source_type} using OpenAI...")
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
        logger.error(f"OpenAI API key not found for structuring {source_type} text.")
        return None

    client = openai.OpenAI(api_key=openai_api_key)

    structuring_prompt = f"""
    Extrahiere die folgenden Informationen aus dem untenstehenden Text eines Stellenangebots und gib sie als JSON-Objekt zurück. Der Text wurde aus {source_type} extrahiert.
    Beachte, dass es sich um einen "Arbeitsvermittler" handeln könnte, was nicht das direkte Unternehmen wäre, bei dem man sich bewirbt.

    Felder zum Extrahieren:
    1. Job Title (Stellentitel)
    2. Company Name (Firmenname - oft oben oder im Text erwähnt, könnte auch der Arbeitsvermittler sein)
    3. Job Description (Stellenbeschreibung - eine detaillierte Zusammenfassung der Aufgaben und Anforderungen)
    4. Required Skills (Erforderliche Fähigkeiten/Qualifikationen)
    5. Responsibilities (Verantwortlichkeiten/Aufgaben)
    6. Company Information (Informationen über das Unternehmen, Kultur, Vorteile etc., falls vorhanden)
    7. Location (Standort/Arbeitsort)
    8. Salary Range (Gehaltsspanne - falls erwähnt)
    9. Posting Date (Veröffentlichungsdatum - falls erwähnt)
    10. Application URL (Die ursprüngliche URL der Quelle: {source_url})
    11. Contact Person (Ansprechpartner für die Bewerbung, falls genannt)
    12. Application Email (E-Mail-Adresse für die Bewerbung, falls genannt)

    Stelle sicher, dass die extrahierten Informationen korrekt sind und im JSON-Format vorliegen. Wenn Informationen nicht gefunden werden, setze den Wert auf null oder einen leeren String.

    **Text des Stellenangebots (aus {source_type}):**
    ---
    {text_content}
    ---

    **Ausgabe** muss ein **JSON-Objekt** sein.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4.1", # Or your preferred model
            messages=[
                {"role": "system", "content": f"Du bist ein Experte für die Extraktion strukturierter Daten aus Stellenanzeigen ({source_type}). Gib deine Antwort als valides JSON-Objekt zurück."},
                {"role": "user", "content": structuring_prompt}
            ],
            temperature=0.2,
            max_tokens=1500, # Increased slightly for potentially more detailed extraction
            response_format={"type": "json_object"}
        )

        job_details_str = response.choices[0].message.content
        job_details = json.loads(job_details_str)

        # Ensure essential fields have fallbacks and add original URL
        if not job_details.get('Job Title'):
            job_details['Job Title'] = 'Unknown_Job' # Keep fallback
        if not job_details.get('Company Name'):
            job_details['Company Name'] = 'Unknown_Company' # Keep fallback
        # Add other fallbacks if needed
        job_details['Application URL'] = source_url # Ensure original URL is present

        logger.info(f"Successfully structured job details from {source_type} via OpenAI.")
        logger.info(f"Job Title: {job_details.get('Job Title')}")
        logger.info(f"Company Name: {job_details.get('Company Name')}")
        # Log all extracted fields for debugging
        logger.info(f"--- Extracted Job Details ({source_type} Method) ---")
        for key, value in job_details.items():
            log_value = value
            if isinstance(log_value, str) and len(log_value) > 100:
                log_value = log_value[:100] + "... [truncated]"
            logger.info(f"{key}: {log_value}")
        logger.info("---------------------------------------------")

        return job_details

    except openai.OpenAIError as e:
        logger.error(f"OpenAI API error during structuring for {source_url}: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"JSON Parsing error after OpenAI structuring for {source_url}: {e}")
        logger.error(f"Raw OpenAI response: {job_details_str}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error structuring text for {source_url}: {e}")
        logger.error(traceback.format_exc())
        return None

# Removed extract_details_from_html function (no longer used)

# Removed get_job_details_using_scrapegraph function (no longer used)

# Removed get_job_details_from_pdf function (no longer used)

def get_job_details_from_scraped_data(job_url):
    """Get job details from pre-scraped data"""
    try:
        logger.info(f"Getting job details from pre-scraped data for URL: {job_url}")
        # Extract a unique identifier from the URL, often the last part
        # Handle potential trailing slashes
        url_parts = job_url.strip('/').split('/')
        job_id = url_parts[-1] if url_parts else None
        if not job_id:
             logger.warning(f"Could not extract job ID from URL: {job_url}")
             return None # Return None if job_id cannot be extracted

        job_data_dir = Path('job-data-acquisition/job-data-acquisition/data')
        if not job_data_dir.exists():
            logger.error(f"Job data directory not found: {job_data_dir}")
            return None
        job_data_files = list(job_data_dir.glob('job_data_*.json'))
        if not job_data_files:
            logger.error("No job data files found in pre-scraped data directory.")
            return None

        latest_job_data_file = max(job_data_files, key=lambda p: p.stat().st_mtime)
        # Removed timestamp logic as recency check is removed from this flow
        logger.info(f"Using latest pre-scraped data file: {latest_job_data_file}")

        with open(latest_job_data_file, 'r', encoding='utf-8') as f:
            job_data_pages = json.load(f)

        all_jobs = []
        if isinstance(job_data_pages, list):
            for page_list in job_data_pages:
                if isinstance(page_list, list):
                    all_jobs.extend(page_list)
                elif isinstance(page_list, dict):
                    all_jobs.append(page_list)
            logger.info(f"Loaded and flattened job data with {len(all_jobs)} total jobs from {len(job_data_pages)} pages.")
        else:
            logger.error(f"Unexpected data structure in {latest_job_data_file}. Expected list of lists.")
            return None

        found_job = None
        for i, job in enumerate(all_jobs):
            if not isinstance(job, dict):
                logger.warning(f"Skipping non-dictionary item at index {i} in flattened job list.")
                continue
            # Match based on the extracted job_id being present in the stored URL
            job_application_url = job.get('Application URL', '')
            # Ensure comparison is robust against missing/non-string URLs
            if isinstance(job_application_url, str) and job_id in job_application_url.split('/')[-1]:
                logger.info(f"Found matching job in pre-scraped data: {job.get('Job Title', 'N/A')} at {job.get('Company Name', 'N/A')}")
                found_job = job
                logger.info("--- Extracted Job Details from Pre-scraped Data ---")
                for key, value in found_job.items():
                    log_value = value
                    if isinstance(log_value, str) and len(log_value) > 100:
                        log_value = log_value[:100] + "... [truncated]"
                    logger.info(f"{key}: {log_value}")
                logger.info("------------------------------------------")
                break

        if found_job:
            # Ensure Application URL is absolute if it's relative
            if isinstance(found_job.get('Application URL'), str) and found_job['Application URL'].startswith('/'):
                 # Need urljoin, let's re-add the import temporarily or handle manually
                 base_url = "https://www.ostjob.ch/" # Assuming base URL
                 found_job['Application URL'] = base_url + found_job['Application URL'].lstrip('/')
            return found_job # Return data dictionary

        logger.warning(f"Job with ID '{job_id}' not found in latest pre-scraped data file: {latest_job_data_file}")
        return None # Indicate not found

    except Exception as e:
        logger.error(f"Error getting job details from pre-scraped data: {str(e)}", exc_info=True)
        return None # Return None on error


def get_job_details(job_url):
    """
    Get job details for a given URL using the simplified ScrapeGraphAI-first approach.

    Order of operations:
    1. Attempt live fetch: GraphScrapeAI Text Extraction + OpenAI Structuring.
    2. Fallback to pre-scraped data.
    """
    # --- Attempt 1: GraphScrapeAI Text Extraction + OpenAI Structuring ---
    logger.info(f"Attempt 1: Trying GraphScrapeAI text extraction for URL: {job_url}")
    structured_details = None
    try:
        graphscrape_text = extract_text_with_graphscrapeai(job_url)

        if graphscrape_text:
            logger.info(f"GraphScrapeAI extracted text ({len(graphscrape_text)} chars). Now structuring with OpenAI.")
            structured_details_graph = structure_text_with_openai(graphscrape_text, job_url, source_type="GraphScrapeAI Text")

            if structured_details_graph:
                if has_sufficient_content(structured_details_graph):
                    logger.info("GraphScrapeAI text extraction + OpenAI structuring yielded sufficient content.")
                    structured_details = structured_details_graph # Store the good result
                else:
                    logger.warning("GraphScrapeAI text extraction + OpenAI structuring did NOT yield sufficient content.")
            else:
                logger.warning("Failed to structure text obtained from GraphScrapeAI using OpenAI.")
        else:
            logger.warning("GraphScrapeAI text extraction failed or returned insufficient text.")

    except Exception as live_fetch_err:
         logger.error(f"Error during GraphScrapeAI/Structuring attempt for {job_url}: {live_fetch_err}", exc_info=True)
         structured_details = None # Ensure it's None if the fetch/structure itself failed

    # If live fetch and structuring succeeded, return the result
    if structured_details:
        return structured_details

    # --- Attempt 2: Fallback to Pre-scraped Data ---
    logger.info("Attempt 2: Falling back to pre-scraped data.")
    job_details = get_job_details_from_scraped_data(job_url)
    if job_details:
        logger.info("Success with pre-scraped data fallback.")
        return job_details

    # --- Final Default ---
    logger.warning(f"All methods failed for {job_url}. Returning default values.")
    return {
        'Job Title': 'Unknown_Job', 'Company Name': 'Unknown_Company',
        'Location': 'Unknown_Location', 'Job Description': 'No description available',
        'Required Skills': 'No specific skills listed', 'Application URL': job_url
    }


def json_to_html(motivation_letter_json):
    title_tag = soup.find('h1', class_='vacancy-title')
    title_text = title_tag.get_text(strip=True) if title_tag else None
    logger.info(f"Direct HTML - Found title tag: {title_tag is not None}, Text: '{title_text}'")
    job_details['Job Title'] = title_text if title_text else 'Unknown_Job'

    # Company Name (Needs specific logic - might be in contact card or inferred)
    # Try contact card first
    contact_card = soup.find('app-vacancy-contact-card')
    company_name = "Unknown_Company"
    if contact_card:
        # Look for text like "Universal-Job Buchs" within the card
        company_div = contact_card.find('div', class_='mt-2') # Find the div containing address lines
        if company_div:
             lines = [line.strip() for line in company_div.get_text(separator='\n').split('\n') if line.strip()]
             if lines and "Universal-Job" in lines[0]: # Check first line for agency name
                  company_name = lines[0]

    job_details['Company Name'] = company_name

    # Location (from "Auf einen Blick" section)
    location = "Unknown_Location"
    # Find the property div containing the location icon first
    location_icon_prop = soup.find('app-uni-icon', {'icon': 'icon-pin-location'})
    if location_icon_prop:
        location_property_div = location_icon_prop.find_parent('div', class_='job-property')
        if location_property_div:
            location_value_div = location_property_div.find('div', class_='property-value')
            if location_value_div:
                location = location_value_div.get_text(strip=True)
    logger.info(f"Direct HTML - Found location: '{location}'")
    job_details['Location'] = location

    # Description, Skills, Responsibilities (Combine sections)
    description_text = ""
    skills_text = ""
    responsibilities_text = ""

    description_sections = soup.find_all('div', class_='vacancy-description')
    logger.info(f"Direct HTML - Found {len(description_sections)} description sections.")
    for i, section in enumerate(description_sections):
        title_tag = section.find('h2', class_='vacancy-description-title')
        text_div = section.find('div', class_='vacancy-description-text')
        title_text_log = title_tag.get_text(strip=True) if title_tag else "No Title Tag"
        text_log = text_div.get_text(strip=True)[:100] + "..." if text_div else "No Text Div" # Log snippet
        logger.info(f"Direct HTML - Section {i+1}: Title='{title_text_log}', Text Snippet='{text_log}'")
        if title_tag and text_div:
            title = title_tag.get_text(strip=True).lower()
            text = text_div.get_text(separator='\n', strip=True)
            if "funktion" in title:
                responsibilities_text += text + "\n\n"
            elif "erfolgreich" in title or "profil" in title:
                skills_text += text + "\n\n"
            elif "vorteile" in title:
                 job_details['Company Information'] = job_details.get('Company Information', '') + "Vorteile:\n" + text + "\n\n"
            # Capture general description text even if title isn't specific
            elif title not in ["sprachen", "vakanz-nummer"]: # Avoid adding these as description
                 description_text += f"## {title_tag.get_text(strip=True)}\n{text}\n\n"

    job_details['Job Description'] = description_text.strip() if description_text else "No description available"
    job_details['Required Skills'] = skills_text.strip() if skills_text else "No specific skills listed"
    job_details['Responsibilities'] = responsibilities_text.strip() if responsibilities_text else "No specific responsibilities listed"
    logger.info(f"Direct HTML - Extracted Responsibilities: {len(job_details['Responsibilities'])} chars")
    logger.info(f"Direct HTML - Extracted Skills: {len(job_details['Required Skills'])} chars")
    logger.info(f"Direct HTML - Extracted Description: {len(job_details['Job Description'])} chars")

    # Contact Person / Email (from contact card)
    contact_person = None
    contact_email = None
    if contact_card:
         name_tag = contact_card.find('h3')
         contact_person = name_tag.get_text(strip=True) if name_tag else None
         logger.info(f"Direct HTML - Found Contact Person: '{contact_person}'")
         # Email might be behind a "Bewerben" link/button - harder to get reliably without JS interaction
         # Look for mailto links or specific email patterns if available
         email_link = contact_card.find('a', href=lambda h: h and h.startswith('mailto:'))
         if email_link:
              contact_email = email_link['href'].replace('mailto:', '')
         # Fallback: Check for email in text if no mailto link
         elif company_div: # Reuse the address div
              email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
              import re
              email_match = re.search(email_pattern, company_div.get_text())
              if email_match:
                   contact_email = email_match.group(0) # Correct indentation
    logger.info(f"Direct HTML - Found Contact Email: '{contact_email}'")

    job_details['Contact Person'] = contact_person
    job_details['Application Email'] = contact_email

    # Check if enough details were extracted
    if job_details['Job Title'] == 'Unknown_Job' and job_details['Company Name'] == 'Unknown_Company':
        logger.warning("Direct HTML extraction failed to find essential details (Title, Company).")
        return None # Signal failure

    logger.info("Successfully extracted details directly from HTML.")
    logger.info(f"Job Title: {job_details['Job Title']}")
    logger.info(f"Company Name: {job_details['Company Name']}")
    logger.info(f"Location: {job_details['Location']}")
    # Log other extracted fields...
    logger.info("--- Extracted Job Details (Direct HTML Method) ---")
    for key, value in job_details.items():
        log_value = value
        if isinstance(log_value, str) and len(log_value) > 100:
            log_value = log_value[:100] + "... [truncated]"
        logger.info(f"{key}: {log_value}")
    logger.info("---------------------------------------------")

    return job_details


def get_job_details_using_scrapegraph(job_url):
    """
    Get job details from ostjob.ch URLs. Tries iframe first, then direct HTML parsing.
    Returns structured dict on success, BeautifulSoup object if only HTML page loaded, None on error.
    """
    logger.info(f"Attempting to get job details via iframe/HTML extraction for URL: {job_url}")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        # Increased timeout from 15 to 30 seconds
        main_response = requests.get(job_url, headers=headers, timeout=30)
        main_response.raise_for_status()
        main_soup = BeautifulSoup(main_response.text, "html.parser")

        # --- Attempt 1: Iframe Method ---
        iframe = main_soup.find("iframe", {"title": "vacancyDetailIFrame"})
        if iframe and "src" in iframe.attrs:
            iframe_url = iframe["src"]
            if iframe_url.startswith('/'):
                iframe_url = urljoin(job_url, iframe_url)
            logger.info(f"Found iframe URL: {iframe_url}. Processing iframe content.")
            iframe_response = requests.get(iframe_url, headers=headers, timeout=15)
            iframe_response.raise_for_status()
            iframe_soup = BeautifulSoup(iframe_response.text, "html.parser")
            iframe_text = iframe_soup.get_text(separator="\n", strip=True)

            if iframe_text:
                logger.info(f"Extracted {len(iframe_text)} characters from iframe. Structuring with OpenAI.")
                structured_details_iframe = structure_text_with_openai(iframe_text, job_url, source_type="Iframe HTML")
                if structured_details_iframe:
                    # Check if the extracted content is sufficient
                    if has_sufficient_content(structured_details_iframe):
                        logger.info("Iframe extraction via OpenAI yielded sufficient content.")
                        return structured_details_iframe # Return good result
                    else:
                        logger.warning("Iframe extraction via OpenAI did NOT yield sufficient content (Description/Responsibilities/Skills).")
                else:
                    logger.warning("Failed to structure iframe text with OpenAI.")
            else:
                logger.warning(f"No text extracted from iframe: {iframe_url}")
        else:
            logger.info("No iframe 'vacancyDetailIFrame' found.")

        # --- Attempt 2: Direct HTML Extraction (if iframe failed or yielded insufficient content) ---
        logger.info("Attempting direct extraction from main page HTML.")
        direct_html_details = extract_details_from_html(main_soup, job_url)
        if direct_html_details:
            # Check if the extracted content is sufficient
            if has_sufficient_content(direct_html_details):
                 logger.info("Direct HTML extraction yielded sufficient content.")
                 return direct_html_details # Return good result
            else:
                 logger.warning("Direct HTML extraction did NOT yield sufficient content (Description/Responsibilities/Skills).")

        # --- Attempt 3: GraphScrapeAI Text Extraction + OpenAI Structuring ---
        logger.info("Previous methods failed or yielded insufficient content. Attempting GraphScrapeAI text extraction.")
        graphscrape_text = extract_text_with_graphscrapeai(job_url) # Call the text extraction function

        if graphscrape_text:
            logger.info(f"GraphScrapeAI extracted text ({len(graphscrape_text)} chars). Now structuring with OpenAI.")
            # Pass the extracted text to the existing structuring function
            structured_details_graph = structure_text_with_openai(graphscrape_text, job_url, source_type="GraphScrapeAI Text")

            if structured_details_graph:
                # Check if the structured content is sufficient
                if has_sufficient_content(structured_details_graph):
                    logger.info("GraphScrapeAI text extraction + OpenAI structuring yielded sufficient content.")
                    return structured_details_graph # Return good result
                else:
                    logger.warning("GraphScrapeAI text extraction + OpenAI structuring did NOT yield sufficient content.")
            else:
                logger.warning("Failed to structure text obtained from GraphScrapeAI using OpenAI.")
        else:
            logger.warning("GraphScrapeAI text extraction failed or returned insufficient text.")


        # If all extraction methods (iframe, direct HTML, GraphScrapeAI+Structure) fail or are insufficient,
        # return the soup object so the caller can check for PDF links.
        logger.warning("All text/structured extraction methods failed or insufficient. Returning soup object for PDF check.")
        return main_soup # Proceed to PDF checks etc.

    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP Request error during HTML/iframe extraction for {job_url}: {e}")
        return None # Signal request error
    except Exception as e:
        logger.error(f"Unexpected error in get_job_details_using_scrapegraph for {job_url}: {e}")
        logger.error(traceback.format_exc())
        return None # Signal other errors


def get_job_details_from_pdf(job_url):
    """
    Get job details from a PDF URL by downloading, extracting text,
    and structuring it using OpenAI.
    """
    logger.info(f"Attempting to get job details from PDF URL: {job_url}")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        pdf_response = requests.get(job_url, headers=headers, timeout=20, stream=True)
        pdf_response.raise_for_status()
        content_type = pdf_response.headers.get('Content-Type', '').lower()
        if 'application/pdf' not in content_type:
            logger.warning(f"URL {job_url} did not return PDF content type (got: {content_type}). Aborting PDF processing.")
            return None
        pdf_content = pdf_response.content
        logger.info(f"Downloaded {len(pdf_content)} bytes of PDF content.")

        pdf_text = ""
        MIN_TEXT_LENGTH_FOR_PYMUPDF = 100
        try_ocr = False
        with fitz.open(stream=pdf_content, filetype="pdf") as doc:
            for page_num, page in enumerate(doc):
                page_text = page.get_text()
                pdf_text += page_text
                if len(pdf_text.strip()) < MIN_TEXT_LENGTH_FOR_PYMUPDF and EASYOCR_AVAILABLE:
                    logger.warning(f"PyMuPDF extracted very little text ({len(pdf_text.strip())} chars) from page {page_num+1} of {job_url}. Will attempt OCR fallback.")
                    try_ocr = True
                    break
            if try_ocr:
                pdf_text = ""
                logger.info("Attempting OCR extraction...")
                reader = easyocr.Reader(['de','en'], gpu=True)
                for page_num, page in enumerate(doc):
                    logger.info(f"Performing OCR on page {page_num+1}...")
                    pix = page.get_pixmap()
                    img_bytes = pix.tobytes("png")
                    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                    results = reader.readtext(np.array(img), detail=0, paragraph=True)
                    page_ocr_text = "\n".join(results)
                    pdf_text += page_ocr_text + "\n\n"
                logger.info(f"OCR extracted {len(pdf_text)} characters.")

        if len(pdf_text.strip()) < MIN_TEXT_LENGTH_FOR_PYMUPDF:
            logger.warning(f"Extracted text length ({len(pdf_text.strip())} chars) is below threshold after all attempts for {job_url}. Aborting.")
            return None
        logger.info(f"Final extracted text length: {len(pdf_text)} characters.")

        # Structure text using OpenAI
        structured_details = structure_text_with_openai(pdf_text, job_url, source_type="PDF")
        if structured_details:
            return structured_details
        else:
            logger.error(f"Failed to structure text from PDF: {job_url}")
            return None

    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP Request error during PDF download for {job_url}: {e}")
        return None
    except fitz.fitz.FitzError as e:
        logger.error(f"PyMuPDF error processing PDF from {job_url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in get_job_details_from_pdf for {job_url}: {e}")
        logger.error(traceback.format_exc())
        return None

def get_job_details_from_scraped_data(job_url):
    """Get job details from pre-scraped data"""
    try:
        logger.info(f"Getting job details from pre-scraped data for URL: {job_url}")
        job_id = job_url.split('/')[-1]
        job_data_dir = Path('job-data-acquisition/job-data-acquisition/data')
        if not job_data_dir.exists():
            logger.error(f"Job data directory not found: {job_data_dir}")
            return None
        job_data_files = list(job_data_dir.glob('job_data_*.json'))
        if not job_data_files:
            logger.error("No job data files found")
            return None
        latest_job_data_file = max(job_data_files, key=os.path.getctime)
        logger.info(f"Latest job data file: {latest_job_data_file}")
        with open(latest_job_data_file, 'r', encoding='utf-8') as f:
            job_data_pages = json.load(f)

        all_jobs = []
        if isinstance(job_data_pages, list):
            for page_list in job_data_pages:
                if isinstance(page_list, list):
                    all_jobs.extend(page_list)
                elif isinstance(page_list, dict):
                    all_jobs.append(page_list)
            logger.info(f"Loaded and flattened job data with {len(all_jobs)} total jobs from {len(job_data_pages)} pages.")
        else:
            logger.error(f"Unexpected data structure in {latest_job_data_file}. Expected list of lists.")
            return None

        found_job = None
        for i, job in enumerate(all_jobs):
            if not isinstance(job, dict):
                logger.warning(f"Skipping non-dictionary item at index {i} in flattened job list.")
                continue
            job_application_url = job.get('Application URL', '')
            if job_id in job_application_url:
                logger.info(f"Found matching job: {job.get('Job Title', 'N/A')} at {job.get('Company Name', 'N/A')}")
                found_job = job
                logger.info("--- Extracted Job Details from Pre-scraped Data ---")
                for key, value in found_job.items():
                    log_value = value
                    if isinstance(log_value, str) and len(log_value) > 100:
                        log_value = log_value[:100] + "... [truncated]"
                    logger.info(f"{key}: {log_value}")
                logger.info("------------------------------------------")
                break

        if found_job:
            return found_job

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
        logger.error(traceback.format_exc())
        return None

def get_job_details(job_url):
    """
    Get job details for a given URL using the ScrapeGraphAI-first approach (headless=False).

    Order of operations:
    1. Attempt live fetch: GraphScrapeAI Structured Extraction (headless=False).
    2. Fallback to pre-scraped data.
    """
    # --- Attempt 1: GraphScrapeAI Structured Extraction (headless=False) ---
    logger.info(f"Attempt 1: Trying GraphScrapeAI structured extraction (headless=False) for URL: {job_url}")
    structured_details = None
    try:
        # Directly call the function that attempts structured extraction with headless=False
        structured_details = get_job_details_with_graphscrapeai(job_url)

        if structured_details:
            # The function already performs validation including has_sufficient_content check
            logger.info("GraphScrapeAI (headless=False) extraction successful and content sufficient.")
            # Ensure Application URL is absolute (might be redundant if handled in util, but safe)
            if isinstance(structured_details.get('Application URL'), str) and not structured_details['Application URL'].startswith('http'):
                 from urllib.parse import urljoin # Add import back if needed here
                 base_url = "https://www.ostjob.ch/" # Assuming base URL
                 structured_details['Application URL'] = urljoin(base_url, structured_details['Application URL'].lstrip('/'))
            return structured_details
        else:
            # Log message already handled within get_job_details_with_graphscrapeai if it failed
            logger.warning("GraphScrapeAI (headless=False) extraction failed or returned insufficient content.")

    except Exception as live_fetch_err:
         logger.error(f"Error during GraphScrapeAI attempt for {job_url}: {live_fetch_err}", exc_info=True)
         structured_details = None # Ensure it's None if the fetch itself failed

    # --- Attempt 2: Fallback to Pre-scraped Data ---
    # This runs only if structured_details is still None after Attempt 1
    logger.info("Attempt 2: Falling back to pre-scraped data.")
    job_details_scraped = get_job_details_from_scraped_data(job_url) # This function now returns dict or None
    if job_details_scraped:
        logger.info("Success with pre-scraped data fallback.")
        # Ensure Application URL is absolute (handled within get_job_details_from_scraped_data now)
        return job_details_scraped

    # --- Final Default ---
    logger.warning(f"All methods (GraphScrapeAI live, Pre-scraped) failed for {job_url}. Returning default values.")
    return {
        'Job Title': 'Unknown_Job', 'Company Name': 'Unknown_Company',
        'Location': 'Unknown_Location', 'Job Description': 'No description available',
        'Required Skills': 'No specific skills listed', 'Application URL': job_url
    }


def json_to_html(motivation_letter_json):
    """Convert motivation letter JSON to HTML format"""
    try:
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

        html_content = f"""<!DOCTYPE html>
<html lang="de">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Motivationsschreiben</title></head>
<body>
    <p>{candidate_name}<br>{candidate_address}<br>{candidate_city}<br>{candidate_email}<br>{candidate_phone}</p>
    <p>{company_name}<br>{company_department}<br>{company_street_number}<br>{company_plz_city}</p>
    <p>{date}</p>
    <h2>{subject}</h2>
    <p>{greeting},</p>
    <p>{introduction}</p>
"""
        for paragraph in body_paragraphs: html_content += f"    <p>{paragraph}</p>\n"
        html_content += f"""
    <p>{closing}</p>
    <p>{signature},<br>{full_name}</p>
</body></html>"""
        return html_content
    except Exception as e:
        logger.error(f"Error converting JSON to HTML: {str(e)}")
        return "<p>Error generating HTML content</p>"

def generate_motivation_letter(cv_summary, job_details):
    """Generate a motivation letter using GPT-4o"""
    try:
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            env_path = os.path.join('process_cv', '.env')
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    for line in f:
                        if line.startswith('OPENAI_API_KEY='):
                            openai_api_key = line.strip().split('=')[1]; break
        if not openai_api_key: logger.error("OpenAI API key not found"); return None
        client = openai.OpenAI(api_key=openai_api_key)
        prompt = """
        Schreibe ein Motivationsschreiben aus den Informationen von der Webseite und dem Lebenslauf:
        ## Lebenslauf des Bewerbers:\n{}\n
        ## Stellenangebot (von der Webseite):\nTitel: {}\nFirma: {}\nOrt: {}\nBeschreibung: \n{}\nErforderliche Fähigkeiten: \n{}\nVerantwortlichkeiten: \n{}\nUnternehmensinformationen: \n{}\n
        Das Motivationsschreiben sollte:\n1. Professionell und überzeugend sein\n2. Die Qualifikationen und Erfahrungen des Bewerbers KONKRET mit den Anforderungen der Stelle verknüpfen\n3. Die Motivation des Bewerbers für die Stelle und das Unternehmen zum Ausdruck bringen\n4. Etwa eine halbe Seite lang sein (ca. 150-200 Wörter)\n5. Auf Deutsch verfasst sein\n6. Im formalen Bewerbungsstil mit Anrede, Einleitung, Hauptteil, Schluss und Grußformel sein\n7. SPEZIFISCH auf die Stellenanforderungen und Verantwortlichkeiten eingehen, die aus der Webseite extrahiert wurden\n8. Die Stärken des Bewerbers hervorheben, die besonders relevant für diese Position sind\n9. Auf die Unternehmenskultur und -werte eingehen, wenn diese Informationen verfügbar sind\n10. KONKRETE BEISPIELE aus dem Lebenslauf des Bewerbers verwenden, die zeigen, wie er/sie die Anforderungen erfüllt\n
        WICHTIG: Falls die Firma der ausgeschriebenen Stell die "Universal-Job AG" ist, behandle sie als Personalvermittler in deinem Schreiben und passe den Inhalt entsprechend an. In diesem Fall wissen wir nicht wer die Stelle schlussendlich ausgeschrieben hat.\n
        WICHTIG: Verwende die detaillierten Informationen aus der Stellenbeschreibung, um ein personalisiertes und spezifisches Motivationsschreiben zu erstellen. Gehe auf konkrete Anforderungen und Verantwortlichkeiten ein und zeige, wie der Bewerber diese erfüllen kann.\n
        WICHTIG: Der Motivtions Text darf maximal 200-300 Wörter beinhalten.\n"ß" soll als "ss" geschrieben werden.\n
        Gib das Motivationsschreiben als JSON-Objekt mit folgender Struktur zurück:\n```json\n{{\n  "candidate_name": "Vollständiger Name des Bewerbers",\n  "candidate_address": "Straße und Hausnummer",\n  "candidate_city": "PLZ und Ort",\n  "candidate_email": "E-Mail-Adresse",\n  "candidate_phone": "Telefonnummer",\n  "company_name": "Name des Unternehmens",\n  "company_department": "Abteilung (falls bekannt, sonst 'Personalabteilung')",\n  "company_street_number": "Strasse und Hausnummerdes Unternehmens (falls bekannt)",\n  "company_plz_city": "Postleitzahl und Stadt (falls bekannt)",\n  "date": "Ort, den [aktuelles Datum]",\n  "subject": "Bewerbung als [Stellentitel]",\n  "greeting": "Anrede (z.B. 'Sehr geehrte Damen und Herren')",\n  "introduction": "Einleitungsabsatz",\n  "body_paragraphs": [\n    "Erster Hauptabsatz",\n    "Zweiter Hauptabsatz",\n    "Dritter Hauptabsatz (falls nötig)"\n  ],\n  "closing": "Schlussabsatz",\n  "signature": "Grussformel (z.B. 'Mit freundlichen Grüssen')",\n  "full_name": "Vollständiger Name des Bewerbers"\n}}\n```\nStelle sicher, dass alle Felder korrekt befüllt sind und das JSON-Format gültig ist.
        """.format(
            cv_summary, job_details.get('Job Title', 'N/A'), job_details.get('Company Name', 'N/A'),
            job_details.get('Location', 'N/A'), job_details.get('Job Description', 'N/A'),
            job_details.get('Required Skills', 'N/A'), job_details.get('Responsibilities', 'Keine spezifischen Verantwortlichkeiten aufgeführt.'),
            job_details.get('Company Information', 'Keine spezifischen Unternehmensinformationen verfügbar.')
        )
        response = client.chat.completions.create(
            model="gpt-4.1", messages=[{"role": "system", "content": "Du bist ein professioneller Bewerbungsberater..."}, {"role": "user", "content": prompt}],
            temperature=0.7, max_tokens=1500, response_format={"type": "json_object"}
        )
        motivation_letter_json_str = response.choices[0].message.content
        try:
            motivation_letter_json = json.loads(motivation_letter_json_str)
            logger.info("Successfully parsed motivation letter JSON")
            html_content = json_to_html(motivation_letter_json)
            job_title = job_details.get('Job Title', 'job')
            job_title = ''.join(c if c.isalnum() or c in [' ', '_', '-'] else '_' for c in job_title)
            job_title = job_title.replace(' ', '_')[:30]
            motivation_letters_dir = Path('motivation_letters'); motivation_letters_dir.mkdir(exist_ok=True)
            html_filename = f"motivation_letter_{job_title}.html"; html_file_path = motivation_letters_dir / html_filename
            logger.info(f"Saving HTML motivation letter to file: {html_file_path}")
            with open(html_file_path, 'w', encoding='utf-8') as f: f.write(html_content)
            json_filename = f"motivation_letter_{job_title}.json"; json_file_path = motivation_letters_dir / json_filename
            logger.info(f"Saving JSON motivation letter to file: {json_file_path}")
            with open(json_file_path, 'w', encoding='utf-8') as f: json.dump(motivation_letter_json, f, ensure_ascii=False, indent=2)
            scraped_data_filename = f"motivation_letter_{job_title}_scraped_data.json"; scraped_data_path = motivation_letters_dir / scraped_data_filename
            logger.info(f"Saving scraped job details to file: {scraped_data_path}")
            with open(scraped_data_path, 'w', encoding='utf-8') as f: json.dump(job_details, f, ensure_ascii=False, indent=2)
            return {'motivation_letter_json': motivation_letter_json, 'motivation_letter_html': html_content,
                    'html_file_path': str(html_file_path), 'json_file_path': str(json_file_path),
                    'scraped_data_path': str(scraped_data_path)}
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON response: {str(e)}"); logger.error(f"Raw response: {motivation_letter_json_str}")
            logger.warning("Falling back to treating response as HTML")
            job_title = job_details.get('Job Title', 'job'); job_title = ''.join(c if c.isalnum() or c in [' ', '_', '-'] else '_' for c in job_title); job_title = job_title.replace(' ', '_')[:30]
            motivation_letters_dir = Path('motivation_letters'); motivation_letters_dir.mkdir(exist_ok=True)
            filename = f"motivation_letter_{job_title}.html"; motivation_letter_file = motivation_letters_dir / filename
            logger.info(f"Saving motivation letter to file: {motivation_letter_file}")
            with open(motivation_letter_file, 'w', encoding='utf-8') as f: f.write(motivation_letter_json_str)
            return {'motivation_letter': motivation_letter_json_str, 'file_path': str(motivation_letter_file)}
    except Exception as e:
        logger.error(f"Error generating motivation letter: {str(e)}"); return None

# Removed existing_job_details parameter
def main(cv_filename, job_url):
    """Main function to generate a motivation letter"""
    logger.info(f"Starting motivation letter generation for CV: {cv_filename} and job URL: {job_url}")
    cv_summary = load_cv_summary(cv_filename)
    if not cv_summary: logger.error("Failed to load CV summary"); return None
    logger.info("Successfully loaded CV summary")
    logger.info(f"Fetching live job details for URL: {job_url}")
    job_details = get_job_details(job_url) # Always fetch live details
    if not job_details: logger.error("Failed to get job details"); return None
    logger.info("Successfully got job details")
    result = generate_motivation_letter(cv_summary, job_details)
    if not result: logger.error("Failed to generate motivation letter"); return None
    if 'json_file_path' in result: logger.info(f"Successfully generated motivation letter: {result['json_file_path']}")
    else: logger.info(f"Successfully generated motivation letter: {result['file_path']}")
    return result

if __name__ == "__main__":
    cv_filename = "Lebenslauf"
    job_url = "https://www.ostjob.ch/jobs/detail/12345" # Example URL
    result = main(cv_filename, job_url)
    if result:
        if 'json_file_path' in result: print(f"Motivation letter generated successfully: {result['json_file_path']}")
        else: print(f"Motivation letter generated successfully: {result['file_path']}")
    else: print("Failed to generate motivation letter")

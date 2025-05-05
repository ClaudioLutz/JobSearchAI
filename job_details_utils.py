import logging
import json
import openai
import requests # Import requests for exception handling
from pathlib import Path
from datetime import datetime
import traceback
from urllib.parse import urljoin

# Import from centralized configuration
from config import config, get_openai_api_key, get_openai_defaults, get_latest_job_data_file

# Import utilities
from utils.file_utils import load_json_file, flatten_nested_job_data
from utils.api_utils import openai_client, generate_json_from_prompt
from utils.decorators import handle_exceptions, log_execution_time, retry

# Set up logger for this module
logger = logging.getLogger("job_details_utils")
# Configure logging basic setup if needed when run standalone
if not logger.hasHandlers():
     logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Import the graph scraper utility
# Assuming the function is now get_job_details_with_graphscrapeai based on previous steps
try:
    from graph_scraper_utils import get_job_details_with_graphscrapeai
except ImportError:
    # Fallback if the previous rename didn't stick or was reverted
    try:
        from graph_scraper_utils import extract_text_with_graphscrapeai as get_job_details_with_graphscrapeai
        logger.warning("Imported extract_text_with_graphscrapeai as get_job_details_with_graphscrapeai")
    except ImportError:
         # If neither exists, log an error, but allow the rest of the file to load
         # The get_job_details function will fail later if it's actually called without this import
         logger.error("Failed to import function from graph_scraper_utils.", exc_info=True)
         get_job_details_with_graphscrapeai = None


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

@handle_exceptions(default_return=None)
@log_execution_time()
def structure_text_with_openai(text_content, source_url, source_type="HTML"):
    """
    Uses OpenAI to structure extracted text from HTML or PDF.
    
    Args:
        text_content (str): The raw text content from the job posting
        source_url (str): The URL of the job posting
        source_type (str): The type of source (HTML, PDF, etc.)
        
    Returns:
        dict: Structured job details or None if extraction fails
    """
    logger.info(f"Structuring text from {source_type} using OpenAI...")
    
    structuring_prompt = f"""
    Extrahiere die folgenden Informationen aus dem untenstehenden Text eines Stellenangebots und gib sie als JSON-Objekt IN DER GLEICHEN SPRACHE WIE DER TEXT DES STELLENANGEBOTES zurück. Der Text wurde aus {source_type} extrahiert.
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
    13. Salutation (Anrede - z.B. 'Sehr geehrter Herr Müller', 'Sehr geehrte Frau Meier', oder 'Sehr geehrte Damen und Herren', falls kein spezifischer Kontakt gefunden wird)

    Stelle sicher, dass die extrahierten Informationen korrekt sind und im JSON-Format vorliegen. Wenn Informationen nicht gefunden werden, setze den Wert auf null oder einen leeren String.

    **Text des Stellenangebots (aus {source_type}):**
    ---
    {text_content}
    ---

    **Ausgabe** muss ein **JSON-Objekt** sein UND IN DER GLEICHEN SPRACHE WIE DER TEXT DES STELLENANGEBOTES.
    """

    # Set up system prompt for job details extraction
    system_prompt = f"Du bist ein Experte für die Extraktion strukturierter Daten aus Stellenanzeigen ({source_type}). Gib deine Antwort als valides JSON-Objekt zurück."
    
    # Use the utility function to generate JSON with built-in retries and error handling
    job_details = generate_json_from_prompt(
        prompt=structuring_prompt,
        system_prompt=system_prompt,
        default=None
    )
    
    if not job_details:
        logger.error(f"Failed to extract job details from {source_url}")
        return None
    
    # Ensure essential fields have fallbacks and add original URL
    if not job_details.get('Job Title'):
        job_details['Job Title'] = 'Unknown_Job'
    if not job_details.get('Company Name'):
        job_details['Company Name'] = 'Unknown_Company'
    # Add other fallbacks if needed
    job_details['Application URL'] = source_url  # Ensure original URL is present

    # Log the results
    logger.info(f"Successfully structured job details from {source_type} via OpenAI.")
    logger.info(f"Job Title: {job_details.get('Job Title')}")
    logger.info(f"Company Name: {job_details.get('Company Name')}")
    
    return job_details

@handle_exceptions(default_return=None)
@log_execution_time()
def get_job_details_from_scraped_data(job_url):
    """Get job details from pre-scraped data"""
    logger.info(f"Getting job details from pre-scraped data for URL: {job_url}")
    # Extract a unique identifier from the URL, often the last part
    url_parts = job_url.strip('/').split('/')
    job_id = url_parts[-1] if url_parts else None
    if not job_id:
        logger.warning(f"Could not extract job ID from URL: {job_url}")
        return None

    # Get job data directory from config
    job_data_dir = config.get_path("job_data")
    if not job_data_dir:
        logger.error("Job data directory not found in configuration.")
        return None

    # Get latest job data file using utility function
    latest_job_data_file = get_latest_job_data_file()
    if not latest_job_data_file:
        logger.error("No job data files found.")
        return None

    logger.info(f"Using latest pre-scraped data file: {latest_job_data_file}")

    # Load job data using utility function
    job_data_pages = load_json_file(latest_job_data_file)
    if not job_data_pages:
        logger.error(f"Failed to load job data from {latest_job_data_file}")
        return None

    # Flatten job data structure
    all_jobs = flatten_nested_job_data(job_data_pages)
    if not all_jobs:
        logger.error("Failed to flatten job data, or data is empty.")
        return None

    logger.info(f"Loaded and flattened job data with {len(all_jobs)} total jobs.")

    # Search for matching job
    found_job = None
    for i, job in enumerate(all_jobs):
        if not isinstance(job, dict):
            logger.warning(f"Skipping non-dictionary item at index {i} in flattened job list.")
            continue
        job_application_url = job.get('Application URL', '')
        if isinstance(job_application_url, str) and job_id in job_application_url.split('/')[-1]:
            logger.info(f"Found matching job: {job.get('Job Title', 'N/A')} at {job.get('Company Name', 'N/A')}")
            found_job = job
            break

    if found_job:
        # Make URL absolute if needed
        if isinstance(found_job.get('Application URL'), str) and found_job['Application URL'].startswith('/'):
            base_url = "https://www.ostjob.ch/"
            found_job['Application URL'] = urljoin(base_url, found_job['Application URL'])
        return found_job

    logger.warning(f"Job with ID '{job_id}' not found in latest pre-scraped data file: {latest_job_data_file}")
    return None

@handle_exceptions(default_return=None)
@log_execution_time()
def get_job_details(job_url):
    """
    Get job details for a given URL using the simplified ScrapeGraphAI-first approach.

    Order of operations:
    1. Attempt live fetch: GraphScrapeAI Structured Extraction (headless=False).
    2. Fallback to pre-scraped data.
    
    Args:
        job_url (str): URL of the job posting
        
    Returns:
        dict: Job details dictionary or None if all methods fail
    """
    # --- Attempt 1: GraphScrapeAI Structured Extraction (headless=False) ---
    logger.info(f"Attempt 1: Trying GraphScrapeAI structured extraction (headless=False) for URL: {job_url}")
    structured_details = None
    if get_job_details_with_graphscrapeai is None:
         logger.error("GraphScrapeAI function not imported correctly. Skipping live fetch.")
    else:
        try:
            # Directly call the function that attempts structured extraction with headless=False
            structured_details = get_job_details_with_graphscrapeai(job_url)

            if structured_details:
                # The function already performs validation including has_sufficient_content check
                logger.info("GraphScrapeAI (headless=False) extraction successful and content sufficient.")
                # Ensure Application URL is absolute (might be redundant if handled in util, but safe)
                if isinstance(structured_details.get('Application URL'), str) and not structured_details['Application URL'].startswith('http'):
                     base_url = "https://www.ostjob.ch/" # Assuming base URL
                     structured_details['Application URL'] = urljoin(base_url, structured_details['Application URL'].lstrip('/'))
                # Return the successful result immediately
                return structured_details
            else:
                 # Log message already handled within get_job_details_with_graphscrapeai if it failed
                 logger.warning("GraphScrapeAI (headless=False) extraction failed or returned insufficient content.")

        except requests.exceptions.RequestException as network_err:
            logger.error(f"Network error during GraphScrapeAI attempt for {job_url}: {type(network_err).__name__} - {network_err}", exc_info=False) # Log specific network error, no need for full traceback usually
            structured_details = None # Ensure it's None on network failure
        except Exception as live_fetch_err:
            logger.error(f"Unexpected error during GraphScrapeAI attempt for {job_url}: {type(live_fetch_err).__name__} - {live_fetch_err}", exc_info=True) # Log other errors with traceback
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

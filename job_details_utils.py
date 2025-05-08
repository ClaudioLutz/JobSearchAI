import logging
import json
import openai
import requests # Import requests for exception handling
from pathlib import Path
from datetime import datetime
import traceback
from urllib.parse import urljoin, urlparse # Ensure urlparse is imported

# Import from centralized configuration
from config import config, get_openai_api_key, get_openai_defaults, get_latest_job_data_file

# Import utilities
from utils.file_utils import load_json_file, flatten_nested_job_data as flatten_job_data
from utils.api_utils import openai_client, generate_json_from_prompt
from utils.decorators import handle_exceptions, log_execution_time, retry

# Set up logger for this module
logger = logging.getLogger("job_details_utils")
# Configure logging basic setup if needed when run standalone
if not logger.hasHandlers():
     logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

__all__ = ["flatten_job_data", "get_job_details"] # get_job_details is now the dispatcher, handling both cases

# New dispatcher function
def get_job_details(*args, **kwargs):
    """
    Dispatcher function to get job details.
    Calls the appropriate implementation based on arguments provided.
    - If 1 argument (job_url) or keyword arg (job_url=...) is provided,
      it fetches details live or from pre-scraped data by URL.
    - If 2 arguments (job_ref, scraped_data) or keyword args (job_ref=..., scraped_data=...) are provided,
      it extracts details from the given scraped_data.

    This function replaces the previous separate get_job_details(job_url) and
    get_job_from_scraped_data(job_ref, scraped_data) by routing to internal implementations.
    """
    # Check for 1-argument call (job_url)
    if len(args) == 1 and not kwargs and isinstance(args[0], str):
        job_url = args[0]
        logger.debug(f"Dispatcher: calling _fetch_job_details_by_url_impl for job_url (positional): {job_url}")
        return _fetch_job_details_by_url_impl(job_url)
    elif not args and 'job_url' in kwargs and len(kwargs) == 1 and isinstance(kwargs['job_url'], str):
        job_url = kwargs['job_url']
        logger.debug(f"Dispatcher: calling _fetch_job_details_by_url_impl for job_url (keyword): {job_url}")
        return _fetch_job_details_by_url_impl(job_url)

    # Check for 2-argument call (job_ref, scraped_data)
    elif len(args) == 2 and not kwargs and isinstance(args[0], str) and isinstance(args[1], list):
        job_ref, scraped_data = args
        logger.debug(f"Dispatcher: calling _get_job_details_from_scraped_data_impl for job_ref, scraped_data (positional)")
        return _get_job_details_from_scraped_data_impl(job_ref, scraped_data)
    elif not args and 'job_ref' in kwargs and 'scraped_data' in kwargs and len(kwargs) == 2 and \
         isinstance(kwargs['job_ref'], str) and isinstance(kwargs['scraped_data'], list):
        job_ref = kwargs['job_ref']
        scraped_data = kwargs['scraped_data']
        logger.debug(f"Dispatcher: calling _get_job_details_from_scraped_data_impl for job_ref, scraped_data (keyword)")
        return _get_job_details_from_scraped_data_impl(job_ref, scraped_data)

    # If none of the above matched, raise an error
    err_msg = (
        "get_job_details called with incompatible arguments. "
        "Expected (job_url: str) OR (job_ref: str, scraped_data: list). "
        f"Received: args={args}, kwargs={kwargs}"
    )
    logger.error(err_msg)
    raise TypeError(err_msg)


# Import the graph scraper utility
try:
    from graph_scraper_utils import get_job_details_with_graphscrapeai
except ImportError:
    try:
        from graph_scraper_utils import extract_text_with_graphscrapeai as get_job_details_with_graphscrapeai
        logger.warning("Imported extract_text_with_graphscrapeai as get_job_details_with_graphscrapeai")
    except ImportError:
         logger.error("Failed to import function from graph_scraper_utils.", exc_info=True)
         get_job_details_with_graphscrapeai = None


def has_sufficient_content(details_dict):
    if not isinstance(details_dict, dict):
        return False
    description = details_dict.get('Job Description')
    responsibilities = details_dict.get('Responsibilities')
    skills = details_dict.get('Required Skills')
    has_desc = description and isinstance(description, str) and len(description.strip()) > 25 and "No description available" not in description
    has_resp = responsibilities and isinstance(responsibilities, str) and len(responsibilities.strip()) > 25 and "No specific responsibilities listed" not in responsibilities
    has_skills = skills and isinstance(skills, str) and len(skills.strip()) > 10 and "No specific skills listed" not in skills and skills.upper() not in ["N/A", "NA"]
    return has_desc or has_resp or has_skills


def _get_job_details_from_scraped_data_impl(job_ref: str, scraped_data: list[dict]) -> dict:
    """
    Return the job dict whose `id` matches job_ref, or whose 'Application URL' path matches job_ref.
    """
    flat_jobs = flatten_job_data(scraped_data)
    if not isinstance(flat_jobs, list):
        logger.error(f"flatten_job_data did not return a list for job_ref {job_ref!r}. Got: {type(flat_jobs)}")
        raise KeyError(f"Could not process scraped_data for job_ref {job_ref!r} (flattening failed)")

    # --- MODIFICATION START ---
    # Determine if job_ref is a full URL, an ID, or a path.
    # Prioritize path extraction if it looks like a URL, otherwise treat as ID or pre-normalized path.
    processed_job_ref_for_match = ""
    is_likely_url = "://" in job_ref and "/" in job_ref # Basic check for a scheme and path component

    if is_likely_url:
        try:
            parsed_ref_url = urlparse(job_ref)
            processed_job_ref_for_match = parsed_ref_url.path.strip('/')
            logger.debug(f"job_ref '{job_ref}' parsed as URL, using path for matching: '{processed_job_ref_for_match}'")
        except Exception as e:
            logger.warning(f"Could not parse job_ref '{job_ref}' as URL, falling back to direct string comparison. Error: {e}")
            processed_job_ref_for_match = job_ref.strip('/') # Fallback for safety
    else:
        # If not a URL, it could be an ID or an already normalized path.
        # Normalize it just in case it's a path with leading/trailing slashes.
        processed_job_ref_for_match = job_ref.strip('/')
        logger.debug(f"job_ref '{job_ref}' treated as ID or pre-normalized path: '{processed_job_ref_for_match}'")
    # --- MODIFICATION END ---

    for job in flat_jobs:
        if not isinstance(job, dict):
            logger.warning(f"Skipping non-dictionary item in flat_jobs for job_ref {job_ref!r}: {type(job)}")
            continue

        # Check 1: Match by job ID field (if job_ref was intended as an ID)
        job_id_from_data = str(job.get("id", ""))
        if not is_likely_url and job_id_from_data == processed_job_ref_for_match: # Only match ID if job_ref wasn't a URL
            logger.debug(f"Matched job by ID field: {job_id_from_data} for job_ref {job_ref!r} (processed as {processed_job_ref_for_match})")
            return job

        # Check 2: Match by Application URL path
        application_url_from_data = job.get("Application URL", job.get("url", ""))
        if isinstance(application_url_from_data, str) and application_url_from_data:
            try:
                parsed_stored_url = urlparse(application_url_from_data)
                stored_path_normalized = parsed_stored_url.path.strip('/')
            except Exception:
                 stored_path_normalized = application_url_from_data.strip('/')

            if processed_job_ref_for_match == stored_path_normalized:
                logger.debug(f"Matched job by URL path: '{stored_path_normalized}' for job_ref {job_ref!r} (processed as {processed_job_ref_for_match})")
                return job

    raise KeyError(f"No job matches {job_ref!r} (processed as '{processed_job_ref_for_match}') either by ID or by URL path.")


@handle_exceptions(default_return=None)
@log_execution_time()
def structure_text_with_openai(text_content, source_url, source_type="HTML"):
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
    system_prompt = f"Du bist ein Experte für die Extraktion strukturierter Daten aus Stellenanzeigen ({source_type}). Gib deine Antwort als valides JSON-Objekt zurück."
    job_details = generate_json_from_prompt(
        prompt=structuring_prompt,
        system_prompt=system_prompt,
        default=None
    )
    if not job_details:
        logger.error(f"Failed to extract job details from {source_url}")
        return None
    if not job_details.get('Job Title'):
        job_details['Job Title'] = 'Unknown_Job'
    if not job_details.get('Company Name'):
        job_details['Company Name'] = 'Unknown_Company'
    job_details['Application URL'] = source_url
    logger.info(f"Successfully structured job details from {source_type} via OpenAI.")
    logger.info(f"Job Title: {job_details.get('Job Title')}")
    logger.info(f"Company Name: {job_details.get('Company Name')}")
    return job_details

@handle_exceptions(default_return=None)
@log_execution_time()
def get_job_details_from_scraped_data(job_url: str):
    logger.info(f"Getting job details from pre-scraped data for URL: {job_url}")
    try:
        parsed_input_url = urlparse(job_url)
        input_url_path = parsed_input_url.path
        if not input_url_path:
            logger.warning(f"Could not extract path from input URL: {job_url}")
            return None
    except Exception as e:
        logger.error(f"Error parsing input URL {job_url}: {e}")
        return None

    normalized_input_path = input_url_path.strip('/')
    latest_job_data_file = get_latest_job_data_file()
    if not latest_job_data_file:
        logger.error("No job data files found.")
        return None
    logger.info(f"Using latest pre-scraped data file: {latest_job_data_file}")
    job_data_pages = load_json_file(latest_job_data_file)
    if not job_data_pages:
        logger.error(f"Failed to load job data from {latest_job_data_file}")
        return None
    all_jobs = flatten_job_data(job_data_pages) # Corrected: was flatten_nested_job_data
    if not all_jobs:
        logger.error("Failed to flatten job data, or data is empty.")
        return None
    logger.info(f"Loaded and flattened job data with {len(all_jobs)} total jobs for path matching.")
    found_job = None
    for i, job in enumerate(all_jobs):
        if not isinstance(job, dict):
            logger.warning(f"Skipping non-dictionary item at index {i} in flattened job list.")
            continue
        job_application_url_from_json = job.get('Application URL', '')
        if isinstance(job_application_url_from_json, str) and job_application_url_from_json:
            try:
                parsed_stored_url = urlparse(job_application_url_from_json)
                stored_url_path = parsed_stored_url.path
            except Exception:
                stored_url_path = job_application_url_from_json
            normalized_stored_path = stored_url_path.strip('/')
            if normalized_input_path == normalized_stored_path:
                logger.info(f"Found matching job by path: '{normalized_input_path}' for {job.get('Job Title', 'N/A')}")
                found_job = job
                break
        if not found_job:
            url_parts = job_url.strip('/').split('/')
            job_id_from_input_url = url_parts[-1].split('?')[0].split('#')[0] if url_parts else None
            if job_id_from_input_url:
                id_from_json = str(job.get("id", ""))
                if id_from_json == job_id_from_input_url:
                    logger.info(f"Found matching job by ID field: '{job_id_from_input_url}' for {job.get('Job Title', 'N/A')}")
                    found_job = job
                    break
                if isinstance(job_application_url_from_json, str):
                    json_url_parts = job_application_url_from_json.strip('/').split('/')
                    id_from_json_url = json_url_parts[-1].split('?')[0].split('#')[0] if json_url_parts else None
                    if job_id_from_input_url == id_from_json_url:
                        logger.info(f"Found matching job by ID in URL path: '{job_id_from_input_url}' for {job.get('Job Title', 'N/A')}")
                        found_job = job
                        break
    if found_job:
        if isinstance(found_job.get('Application URL'), str) and found_job['Application URL'].startswith('/'):
            base_url = "https://www.ostjob.ch/"
            found_job['Application URL'] = urljoin(base_url, found_job['Application URL'])
        return found_job
    logger.warning(f"Job with URL '{job_url}' (path: '{normalized_input_path}') not found in pre-scraped data: {latest_job_data_file}")
    return None

@handle_exceptions(default_return=None)
@log_execution_time()
def _fetch_job_details_by_url_impl(job_url):
    logger.info(f"Attempt 1: Trying GraphScrapeAI structured extraction (headless=False) for URL: {job_url}")
    structured_details = None
    if get_job_details_with_graphscrapeai is None:
         logger.error("GraphScrapeAI function not imported correctly. Skipping live fetch.")
    else:
        try:
            structured_details = get_job_details_with_graphscrapeai(job_url)
            if structured_details:
                logger.info("GraphScrapeAI (headless=False) extraction successful and content sufficient.")
                if isinstance(structured_details.get('Application URL'), str) and not structured_details['Application URL'].startswith('http'):
                     base_url = "https://www.ostjob.ch/"
                     structured_details['Application URL'] = urljoin(base_url, structured_details['Application URL'].lstrip('/'))
                return structured_details
            else:
                 logger.warning("GraphScrapeAI (headless=False) extraction failed or returned insufficient content.")
        except requests.exceptions.RequestException as network_err:
            logger.error(f"Network error during GraphScrapeAI attempt for {job_url}: {type(network_err).__name__} - {network_err}", exc_info=False)
            structured_details = None
        except Exception as live_fetch_err:
            logger.error(f"Unexpected error during GraphScrapeAI attempt for {job_url}: {type(live_fetch_err).__name__} - {live_fetch_err}", exc_info=True)
            structured_details = None
    logger.info("Attempt 2: Falling back to pre-scraped data.")
    job_details_scraped = get_job_details_from_scraped_data(job_url)
    if job_details_scraped:
        logger.info("Success with pre-scraped data fallback.")
        return job_details_scraped
    logger.warning(f"All methods (GraphScrapeAI live, Pre-scraped) failed for {job_url}. Returning default values.")
    return {
        'Job Title': 'Unknown_Job', 'Company Name': 'Unknown_Company',
        'Location': 'Unknown_Location', 'Job Description': 'No description available',
        'Required Skills': 'No specific skills listed', 'Application URL': job_url
    }

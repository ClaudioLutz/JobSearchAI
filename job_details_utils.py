import os
import logging
import json
import openai
from pathlib import Path
from datetime import datetime
import traceback
from urllib.parse import urljoin

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
         logging.getLogger("job_details_utils").error("Failed to import function from graph_scraper_utils.", exc_info=True)
         get_job_details_with_graphscrapeai = None


# Set up logger for this module
logger = logging.getLogger("job_details_utils")
# Configure logging basic setup if needed when run standalone
if not logger.hasHandlers():
     logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


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

def structure_text_with_openai(text_content, source_url, source_type="HTML"):
    """Uses OpenAI to structure extracted text from HTML or PDF."""
    logger.info(f"Structuring text from {source_type} using OpenAI...")
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if not openai_api_key:
        # Assuming .env is in 'process_cv' relative to project root
        env_path = Path(__file__).parent / 'process_cv' / '.env'
        if env_path.exists():
            from dotenv import load_dotenv # Load only if needed
            load_dotenv(dotenv_path=env_path)
            openai_api_key = os.getenv('OPENAI_API_KEY')

    if not openai_api_key:
        logger.error(f"OpenAI API key not found for structuring {source_type} text.")
        return None

    try:
        client = openai.OpenAI(api_key=openai_api_key)
    except ImportError:
        logger.error("OpenAI library not found. Please install it: pip install openai")
        return None


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

        # Construct path relative to this script's directory or project root
        base_path = Path(__file__).parent
        job_data_dir = base_path / 'job-data-acquisition/job-data-acquisition/data'
        if not job_data_dir.exists():
             # Try path relative to project root as fallback
             job_data_dir = Path('job-data-acquisition/job-data-acquisition/data')
             if not job_data_dir.exists():
                  logger.error(f"Job data directory not found in standard locations: {job_data_dir}")
                  return None

        job_data_files = list(job_data_dir.glob('job_data_*.json'))
        if not job_data_files:
            logger.error("No job data files found in pre-scraped data directory.")
            return None

        latest_job_data_file = max(job_data_files, key=lambda p: p.stat().st_mtime)
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
                 base_url = "https://www.ostjob.ch/" # Assuming base URL
                 found_job['Application URL'] = urljoin(base_url, found_job['Application URL']) # Use urljoin
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
    1. Attempt live fetch: GraphScrapeAI Structured Extraction (headless=False).
    2. Fallback to pre-scraped data.
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

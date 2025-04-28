import os
import json
import logging
from scrapegraphai.graphs import SmartScraperGraph
# Removed dotenv import as config file should handle API key
from pathlib import Path

# Set up logger for this module
logger = logging.getLogger("graph_scraper_utils")

# Load configuration from settings.json (relative to this file's location)
def load_config():
    """Loads configuration from job-data-acquisition/settings.json"""
    try:
        # Construct path relative to this script's directory
        script_dir = Path(__file__).parent
        config_path = script_dir / "job-data-acquisition" / "settings.json"
        if not config_path.is_file():
             logger.error(f"Configuration file not found at expected path: {config_path}")
             # Try path relative to project root as fallback (if script is run from root)
             config_path_alt = Path("job-data-acquisition") / "settings.json"
             if config_path_alt.is_file():
                  config_path = config_path_alt
                  logger.info(f"Using alternative config path: {config_path}")
             else:
                  logger.error(f"Alternative config path also not found: {config_path_alt}")
                  return None

        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            logger.info(f"Successfully loaded configuration from {config_path}")
            return config
    except Exception as e:
        logger.error(f"Error loading configuration: {e}", exc_info=True)
        return None

# Load config at module level
CONFIG = load_config()

# Define the structured extraction prompt (in German) - Reverted
SINGLE_JOB_EXTRACTION_PROMPT = """
Extrahiere die Details des Stellenangebots von dieser Seite IN DER GLEICHEN SPRACHE WIE DIE JOB-AUSSCHREIBUNG. Gib ein JSON-Objekt mit den folgenden Feldern zurück:
1. Job Title (Stellentitel)
2. Company Name (Firmenname)
3. Job Description (Stellenbeschreibung - Erstelle eine umfassende Zusammenfassung, falls möglich)
4. Required Skills (Erforderliche Fähigkeiten - Liste spezifische erwähnte Fähigkeiten auf)
5. Responsibilities (Verantwortlichkeiten - Detailliere die Hauptaufgaben und Pflichten)
6. Company Information (Unternehmensinformationen - Füge Details zur Unternehmenskultur, Vorteilen usw. hinzu, falls verfügbar)
7. Location (Standort/Arbeitsort)
8. Salary Range (Gehaltsspanne - Falls erwähnt)
9. Posting Date (Veröffentlichungsdatum - Falls erwähnt)
10. Application URL (Verwende die ursprüngliche Quell-URL)
11. Contact Person (Ansprechpartner - Falls erwähnt)
12. Application Email (Bewerbungs-E-Mail - Falls erwähnt)
13. Salutation (Anrede - z.B. 'Sehr geehrter Herr **Nachname Contact Person**', 'Sehr geehrte Frau **Nachname Contact Person**', oder 'Sehr geehrte Damen und Herren', falls kein spezifischer Kontakt gefunden wird)

Die Ausgabe muss ein einzelnes JSON-Objekt sein. Wenn ein Feld nicht gefunden wird, verwende null oder einen leeren String.
Priorisiere die Extraktion aussagekräftiger Inhalte für 'Job Description', 'Required Skills' und 'Responsibilities'.

AUSGABE IN DER GLEICHEN SPRACHE WIE DER TEXT DES STELLENANGEBOTES!
"""

# Removed get_openai_api_key function

# Renamed function back
def get_job_details_with_graphscrapeai(job_url):
    """
    Attempts to extract structured job details using ScrapeGraphAI, forcing headless=False.

    Args:
        job_url (str): The URL of the job posting page.

    Returns:
        dict or None: A dictionary containing the extracted job details,
                      or None if extraction fails or is incomplete.
    """
    logger.info(f"Attempting GraphScrapeAI structured extraction (headless=False) for URL: {job_url}")

    if CONFIG is None:
        logger.error("Configuration not loaded. Cannot proceed with GraphScrapeAI.")
        return None
    if 'scraper' not in CONFIG or 'llm' not in CONFIG['scraper']:
         logger.error("Scraper or LLM configuration missing in settings.json.")
         return None

    try:
        # Use configuration loaded from settings.json
        scraper_config = CONFIG["scraper"]
        # Ensure essential LLM details are present
        if not scraper_config['llm'].get('api_key') or not scraper_config['llm'].get('model'):
             logger.error("API key or model missing in LLM configuration within settings.json.")
             return None

        # Construct graph_config using loaded settings
        # Add model_provider if missing in config (for backward compatibility or flexibility)
        llm_config = scraper_config['llm'].copy() # Avoid modifying original CONFIG dict
        if 'model_provider' not in llm_config:
             if 'openai' in llm_config.get('model', ''):
                  llm_config['model_provider'] = 'openai'
                  logger.info("Automatically added 'model_provider': 'openai' to LLM config.")
             # Add other providers if needed (e.g., 'groq', 'gemini') based on model name
             else:
                  logger.warning(f"Could not determine model_provider for model: {llm_config.get('model')}. Scraper might fail.")
                  # Optionally default to openai or raise error

        graph_config = {
            "llm": llm_config,
            "verbose": scraper_config.get("verbose", True), # Keep verbose for debugging
            "headless": False, # Force headless=False to mimic successful test
            "output_format": "json" # Expect JSON output for structured prompt
        }
        logger.debug(f"Using GraphScrapeAI config (headless=False): {graph_config}")

        # Use the structured extraction prompt
        scraper = SmartScraperGraph(
            prompt=SINGLE_JOB_EXTRACTION_PROMPT,
            source=job_url,
            config=graph_config
        )

        result = scraper.run()
        # Log the raw dictionary result for detailed diagnosis
        try:
            # Log the full result now to see the structure
            logger.info(f"GraphScrapeAI raw result dictionary (headless=False): {json.dumps(result, indent=2, ensure_ascii=False)}")
        except Exception as log_e:
            logger.error(f"Could not serialize GraphScrapeAI result for logging: {log_e}")
            logger.info(f"GraphScrapeAI raw result (non-JSON, headless=False): {result}") # Fallback log

        # --- Validate the result ---
        if not isinstance(result, dict):
            logger.warning(f"GraphScrapeAI (headless=False) did not return a dictionary for {job_url}. Type: {type(result)}")
            return None

        # --- Check if the actual content is nested ---
        job_details = None # Initialize as None
        if 'content' in result and isinstance(result['content'], dict):
            logger.info("Found nested 'content' key in GraphScrapeAI result. Using nested dictionary.")
            job_details = result['content']
        elif len(result) == 1 and isinstance(list(result.values())[0], list) and len(list(result.values())[0]) > 0 and isinstance(list(result.values())[0][0], dict):
             # Handle cases where result might be {"jobs": [{...}]}
             logger.info("Found result nested within a list under a single key. Using first item from list.")
             job_details = list(result.values())[0][0]
        elif 'Job Title' in result: # Check if result itself is the details dict (less likely now but possible)
             logger.info("Result dictionary seems to be the job details directly.")
             job_details = result
        else:
             logger.warning(f"GraphScrapeAI result dictionary does not contain 'content' key or expected structure for {job_url}.")
             return None
        # --- End Nested Check ---


        # Check for essential fields within the job_details dictionary
        title = job_details.get('Job Title')
        description = job_details.get('Job Description')
        responsibilities = job_details.get('Responsibilities')
        skills = job_details.get('Required Skills')

        if not title:
            logger.warning(f"GraphScrapeAI failed to extract 'Job Title' from the result structure for {job_url}.")
            return None

        # Check if at least one of the key content fields has meaningful data
        # Using the existing has_sufficient_content logic (assuming it's defined elsewhere or we add it here)
        # For now, just check if description is present and non-trivial
        has_meaningful_content = False
        if description and isinstance(description, str) and len(description.strip()) > 10: # Arbitrary length check
            has_meaningful_content = True
        if not has_meaningful_content and responsibilities and isinstance(responsibilities, str) and len(responsibilities.strip()) > 10:
            has_meaningful_content = True
        if not has_meaningful_content and skills and isinstance(skills, str) and len(skills.strip()) > 5:
            has_meaningful_content = True

        if not has_meaningful_content:
            logger.warning(f"GraphScrapeAI extracted a title but failed to find meaningful Description/Responsibilities/Skills for {job_url}.")
            # Return None as content is key for motivation letters
            return None
        # --- End Validation ---

        logger.info(f"GraphScrapeAI successfully extracted details (headless=False) for {job_url}")
        # Ensure the original Application URL is preserved/added to the final job_details dict
        job_details['Application URL'] = job_url

        # Log extracted details (similar format to other methods)
        logger.info(f"--- Extracted Job Details (GraphScrapeAI Method, headless=False) ---")
        for key, value in job_details.items(): # Log from the final job_details dict
            log_value = value
            if isinstance(log_value, str) and len(log_value) > 100:
                log_value = log_value[:100] + "... [truncated]"
            logger.info(f"{key}: {log_value}")
        logger.info("---------------------------------------------")
        return job_details # Return the potentially nested dictionary

    except ImportError as ie:
         logger.error(f"ImportError during GraphScrapeAI: {ie}. Is scrapegraphai installed correctly?")
         return None
    except Exception as e:
        logger.error(f"Error during GraphScrapeAI extraction for {job_url}: {e}", exc_info=True)
        return None

if __name__ == '__main__':
    # Example usage for testing structured extraction with headless=False
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    # Replace with a real URL for testing
    test_url = "https://www.ostjob.ch/job/sachbearbeiterin-rechnungswesen-administration-80-100-m-w-d/994155" # Use the one from the log
    details = get_job_details_with_graphscrapeai(test_url)
    if details:
        print("\n--- Test Result (Structured Extraction, headless=False) ---")
        print(json.dumps(details, indent=2, ensure_ascii=False))
        print("----------------------------------------------------------")
    else:
        print(f"\nFailed to extract details for {test_url} using GraphScrapeAI (headless=False).")

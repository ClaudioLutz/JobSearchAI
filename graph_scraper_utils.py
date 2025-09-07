import os
import json
import logging
from scrapegraphai.graphs import SmartScraperGraph
# Removed dotenv import as config file should handle API key
from pathlib import Path

# Set up logger for this module
logger = logging.getLogger("graph_scraper_utils")

# Load configuration from settings.json
def load_config():
    """Loads configuration from job-data-acquisition/settings.json"""
    try:
        # Get the current working directory (project root)
        project_root = Path.cwd()
        
        # Try multiple possible paths for the settings file
        possible_paths = [
            project_root / "job-data-acquisition" / "settings.json",
            Path(__file__).parent / "job-data-acquisition" / "settings.json",
            Path("job-data-acquisition") / "settings.json"
        ]
        
        config_path = None
        for path in possible_paths:
            if path.is_file():
                config_path = path
                logger.info(f"Found configuration file at: {config_path}")
                break
        
        if config_path is None:
            logger.error("Configuration file not found in any expected locations:")
            for path in possible_paths:
                logger.error(f"  - {path}")
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
    Attempts to extract structured job details using optimized headless ScrapeGraphAI.

    Args:
        job_url (str): The URL of the job posting page.

    Returns:
        dict or None: A dictionary containing the extracted job details,
                      or None if extraction fails or is incomplete.
    """
    logger.info(f"Attempting optimized GraphScrapeAI extraction (headless=True) for URL: {job_url}")

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

        # Construct OPTIMIZED graph_config with quality improvements
        llm_config = scraper_config['llm'].copy() # Avoid modifying original CONFIG dict
        if 'model_provider' not in llm_config:
             if 'openai' in llm_config.get('model', ''):
                  llm_config['model_provider'] = 'openai'
                  logger.info("Automatically added 'model_provider': 'openai' to LLM config.")
             else:
                  logger.warning(f"Could not determine model_provider for model: {llm_config.get('model')}. Scraper might fail.")

        # OPTIMIZED CONFIGURATION based on quality analysis
        graph_config = {
            "llm": llm_config,
            "verbose": scraper_config.get("verbose", True),
            "headless": True, # Deployment-ready
            "output_format": "json",
            "wait_time": 5,  # KEY OPTIMIZATION: Increased wait time for dynamic content
            "browser_config": {
                "args": [
                    "--disable-blink-features=AutomationControlled",  # Avoid bot detection
                    "--disable-dev-shm-usage",  # Better memory management
                    "--no-sandbox",  # Required for some server environments
                    "--disable-setuid-sandbox",
                    "--disable-extensions",
                    "--disable-plugins",
                    "--disable-background-timer-throttling",  # Ensure JS runs properly
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                    "--disable-features=TranslateUI",
                    "--disable-ipc-flooding-protection"
                ],
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "viewport": {"width": 1920, "height": 1080}  # Standard desktop viewport
            },
            "timeout": 30000,  # 30 second timeout
            "load_wait": "networkidle"  # Wait for network to be idle
        }
        logger.debug(f"Using OPTIMIZED GraphScrapeAI config: {graph_config}")

        # Use the structured extraction prompt
        scraper = SmartScraperGraph(
            prompt=SINGLE_JOB_EXTRACTION_PROMPT,
            source=job_url,
            config=graph_config
        )

        result = scraper.run()
        
        # Process and validate result
        job_details = process_scraper_result(result, job_url)
        
        if job_details:
            # Calculate quality score for monitoring
            quality_score = calculate_quality_score(job_details)
            logger.info(f"GraphScrapeAI successfully extracted details (OPTIMIZED headless=True) - Quality Score: {quality_score}")
            
            # Log extracted details
            logger.info(f"--- Extracted Job Details (Optimized GraphScrapeAI Method) ---")
            for key, value in job_details.items():
                log_value = value
                if isinstance(log_value, str) and len(log_value) > 100:
                    log_value = log_value[:100] + "... [truncated]"
                logger.info(f"{key}: {log_value}")
            logger.info("---------------------------------------------")
            
            return job_details
        else:
            logger.warning(f"Failed to extract meaningful job details from {job_url}")
            return None

    except ImportError as ie:
         logger.error(f"ImportError during GraphScrapeAI: {ie}. Is scrapegraphai installed correctly?")
         return None
    except Exception as e:
        logger.error(f"Error during GraphScrapeAI extraction for {job_url}: {e}", exc_info=True)
        return None

def process_scraper_result(result, job_url):
    """Process and validate scraper result"""
    if not isinstance(result, dict):
        logger.warning(f"GraphScrapeAI did not return a dictionary for {job_url}. Type: {type(result)}")
        return None

    job_details = None
    if 'content' in result and isinstance(result['content'], dict):
        logger.info("Found nested 'content' key in GraphScrapeAI result.")
        job_details = result['content']
    elif len(result) == 1 and isinstance(list(result.values())[0], list) and len(list(result.values())[0]) > 0 and isinstance(list(result.values())[0][0], dict):
        logger.info("Found result nested within a list under a single key.")
        job_details = list(result.values())[0][0]
    elif 'Job Title' in result:
        logger.info("Result dictionary contains job details directly.")
        job_details = result
    else:
        logger.warning(f"GraphScrapeAI result dictionary does not contain expected structure for {job_url}.")
        return None

    if not isinstance(job_details, dict):
        logger.warning(f"job_details is not a dictionary after processing result for {job_url}. Type: {type(job_details)}")
        return None

    # Basic validation
    title = job_details.get('Job Title')
    if not title:
        logger.warning(f"GraphScrapeAI failed to extract 'Job Title' from {job_url}.")
        return None

    # Check for meaningful content
    description = job_details.get('Job Description')
    responsibilities = job_details.get('Responsibilities')
    skills = job_details.get('Required Skills')

    has_meaningful_content = False
    if description and isinstance(description, str) and len(description.strip()) > 10:
        has_meaningful_content = True
    if not has_meaningful_content and responsibilities and isinstance(responsibilities, (str, list)) and len(str(responsibilities).strip()) > 10:
        has_meaningful_content = True
    if not has_meaningful_content and skills and isinstance(skills, (str, list)) and len(str(skills).strip()) > 5:
        has_meaningful_content = True

    if not has_meaningful_content:
        logger.warning(f"GraphScrapeAI extracted a title but failed to find meaningful Description/Responsibilities/Skills for {job_url}.")
        return None

    # Ensure URL is preserved
    job_details['Application URL'] = job_url
    return job_details

def calculate_quality_score(details):
    """Calculate quality score for monitoring"""
    if not details:
        return 0
    
    score = 0
    weights = {
        'Job Title': 10,
        'Company Name': 8,
        'Job Description': 15,
        'Required Skills': 12,
        'Responsibilities': 12,
        'Company Information': 8,
        'Contact Person': 5,
        'Location': 5,
        'Application Email': 3,
        'Salary Range': 3
    }
    
    for field, weight in weights.items():
        value = details.get(field, "")
        if value and str(value).strip():
            # Base score for having the field
            field_score = weight * 0.5
            # Additional score based on content length
            content_length = len(str(value).strip())
            if content_length > 10:
                field_score += min(weight * 0.5, content_length / 100 * weight * 0.5)
            score += field_score
    
    return round(score, 2)

if __name__ == '__main__':
    # Example usage for testing structured extraction with headless=True
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    # Use one of the test URLs from the task description
    test_url = "https://www.ostjob.ch/job/kundenberater-im-aussendienst-80-100-m-w-d/1023929"
    details = get_job_details_with_graphscrapeai(test_url)
    if details:
        print("\n--- Test Result (Structured Extraction, headless=True) ---")
        print(json.dumps(details, indent=2, ensure_ascii=False))
        print("----------------------------------------------------------")
    else:
        print(f"\nFailed to extract details for {test_url} using GraphScrapeAI (headless=True).")

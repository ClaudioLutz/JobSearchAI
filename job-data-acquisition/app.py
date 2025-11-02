
import os
import sys
import json
import re
import logging
import time
import warnings
from datetime import datetime
from functools import wraps
from flask import Flask, jsonify, request
from scrapegraphai.graphs import SmartScraperGraph

# Add the parent directory to the Python path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Create Flask app for health checks and API endpoints
app = Flask(__name__)

# Import the config manager to get the correct environment variables
try:
    from config import ConfigManager
    config_manager = ConfigManager()
    # Override the environment variable with the correct one from config
    api_key = config_manager.get_env("OPENAI_API_KEY")
    if api_key:
        os.environ['OPENAI_API_KEY'] = api_key
    else:
        logging.error("No OpenAI API key found in configuration")
except Exception as e:
    logging.error(f"Failed to load config manager: {e}")

# Import database and utilities for deduplication
try:
    from utils.db_utils import JobMatchDatabase
    from utils.cv_utils import generate_cv_key
    from utils.url_utils import URLNormalizer
except ImportError as e:
    logging.warning(f"Could not import deduplication utilities: {e}")
    JobMatchDatabase = None
    generate_cv_key = None
    URLNormalizer = None

def substitute_env_vars(config_str):
    """
    Substitute environment variable placeholders in configuration string.
    Replaces ${VAR_NAME} with the actual environment variable value.
    """
    def replace_var(match):
        var_name = match.group(1)
        env_value = os.getenv(var_name)
        if env_value:
            print(f"Substituting ${var_name} with env value: {env_value[:15]}...")
            return env_value
        else:
            print(f"Environment variable ${var_name} not found, keeping placeholder")
            return match.group(0)
    
    # Pattern to match ${VAR_NAME}
    pattern = r'\$\{([^}]+)\}'
    return re.sub(pattern, replace_var, config_str)

def substitute_env_vars_in_dict(config_dict):
    """
    Recursively substitute environment variables in a configuration dictionary.
    """
    if isinstance(config_dict, dict):
        return {k: substitute_env_vars_in_dict(v) for k, v in config_dict.items()}
    elif isinstance(config_dict, list):
        return [substitute_env_vars_in_dict(item) for item in config_dict]
    elif isinstance(config_dict, str):
        return substitute_env_vars(config_dict)
    else:
        return config_dict

# Load configuration from settings.json
def load_config():
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "settings.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            
        # Apply environment variable substitution
        print("Applying environment variable substitution to job-data-acquisition config...")
        config = substitute_env_vars_in_dict(config)
        print("Environment variable substitution complete")
        
        return config
    except Exception as e:
        print(f"Error loading configuration: {e}")
        return None

# Get configuration
CONFIG = load_config()

# Set up logging
def setup_logging():
    if CONFIG is None:
        # Default logging configuration if CONFIG is None
        log_dir = "job-data-acquisition/logs"
        log_level = "INFO"
    else:
        log_dir = CONFIG["logging"]["log_directory"]
        log_level = CONFIG["logging"]["log_level"]
    
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"{log_dir}/scraper_{timestamp}.log"
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger("job_scraper")
    if CONFIG is None:
        logger.error("Configuration not loaded. Using default logging settings.")
    
    return logger

# Define the extraction prompt
EXTRACTION_PROMPT = """
IMPORTANT: If there is a cookie consent banner or popup, ignore it and focus on the job listings content below it.

Extract **all** job postings from the current page. Look for job listings that typically contain:
- Job titles (like "Kundenberater", "Software Engineer", etc.)
- Company names 
- Location information (like "Bern", "Zürich", "Appenzellerland", etc.)
- Job descriptions or snippets
- Application links/URLs

For each job listing found, return a JSON object with these exact fields:
- "Job Title": The job position title
- "Company Name": The company/employer name  
- "Job Description": Description text or summary
- "Required Skills": Skills mentioned (if any, otherwise "N/A")
- "Location": Job location/region
- "Salary Range": Salary info if mentioned (otherwise "N/A") 
- "Posting Date": Date posted if available (otherwise "N/A")
- "Application URL": Link to apply or view full job details

**Output format**: Return a JSON array containing all job objects found on this page.
**If no job listings are found**, return an empty array: []

Example output:
[
    {
        "Job Title": "Kundenberater im Aussendienst",
        "Company Name": "Universal-Job AG",
        "Job Description": "Du bist ein Kommunikationstalent und liebst den direkten Kontakt zu Menschen...",
        "Required Skills": "Kommunikation, Verkauf",
        "Location": "Appenzellerland",
        "Salary Range": "80-100%",
        "Posting Date": "07.09.2025",
        "Application URL": "https://www.ostjob.ch/job/details/12345"
    }
]
"""

# Configure the ScrapeGraph pipeline with page number
def configure_scraper(source_url, page):
    if CONFIG is None:
        raise ValueError("Configuration not loaded. Cannot configure scraper.")
    
    scraper_config = CONFIG["scraper"]
    
    # Use the updated configuration from settings.json
    graph_config = {
        "llm": scraper_config["llm"],
        "verbose": scraper_config["verbose"],
        "headless": scraper_config["headless"],
        "output_format": scraper_config["output_format"]
    }
    
    # Add additional config options if they exist in settings.json
    if "wait_time" in scraper_config:
        graph_config["wait_time"] = scraper_config["wait_time"]
    if "timeout" in scraper_config:
        graph_config["timeout"] = scraper_config["timeout"]
    if "load_wait" in scraper_config:
        graph_config["load_wait"] = scraper_config["load_wait"]
    if "browser_config" in scraper_config:
        graph_config["browser_config"] = scraper_config["browser_config"]

    # Construct the URL using proper pagination query parameter
    paginated_url = f"{source_url}{page}"

    scraper = SmartScraperGraph(
        prompt=EXTRACTION_PROMPT,
        source=paginated_url,
        config=graph_config
    )

    return scraper


# Flask health check endpoint
@app.route('/health')
def health_check():
    """Enhanced health check endpoint for Docker and Cloud Run"""
    try:
        # Basic health check - verify config is loaded
        if CONFIG is None:
            return jsonify({
                "status": "unhealthy",
                "message": "Configuration not loaded",
                "timestamp": datetime.now().isoformat()
            }), 503
        
        # Check if we can access the display (Xvfb check)
        display = os.environ.get('DISPLAY')
        
        # Test Playwright browser availability
        browser_status = "unknown"
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
                browser.close()
                browser_status = "available"
        except Exception as browser_error:
            browser_status = f"error: {str(browser_error)}"
        
        # Test OpenAI API key
        api_key_status = "configured" if os.environ.get('OPENAI_API_KEY') else "missing"
        
        return jsonify({
            "status": "healthy",
            "message": "JobSearchAI scraper is running",
            "display": display,
            "headless_mode": CONFIG["scraper"]["headless"],
            "browser_status": browser_status,
            "api_key_status": api_key_status,
            "environment": "production" if os.environ.get('FLASK_ENV') == 'production' else "development",
            "memory_usage": f"{os.popen('free -m').read().split()[9]}MB" if os.name != 'nt' else "N/A",
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "unhealthy", 
            "message": f"Health check failed: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 503

@app.route('/scrape', methods=['POST'])
def scrape_endpoint():
    """API endpoint to trigger scraping"""
    try:
        logger = setup_logging()
        logger.info("Scraping request received via API")
        
        output_file = run_scraper()
        
        return jsonify({
            "status": "success",
            "message": "Scraping completed",
            "output_file": output_file,
            "timestamp": datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Scraping failed: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/')
def home():
    """Root endpoint with basic information"""
    return jsonify({
        "service": "JobSearchAI Scraper",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "scrape": "/scrape (POST)",
            "home": "/"
        },
        "headless_mode": CONFIG["scraper"]["headless"] if CONFIG else None,
        "timestamp": datetime.now().isoformat()
    })

def deprecated(alternative=None):
    """Decorator to mark functions as deprecated"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            message = f"{func.__name__} is deprecated and will be removed in v3.0."
            if alternative:
                message += f" Use {alternative} instead."
            warnings.warn(message, DeprecationWarning, stacklevel=2)
            logger = logging.getLogger("job_scraper")
            logger.warning(message)
            return func(*args, **kwargs)
        return wrapper
    return decorator


# Function to run the scraper and save results
@deprecated(alternative="run_scraper_with_deduplication")
def run_scraper():
    """
    Legacy scraper function - DEPRECATED
    
    This function is deprecated and will be removed in version 3.0.
    Use run_scraper_with_deduplication() instead for:
    - Database-backed deduplication
    - Early exit optimization  
    - Correct search term handling
    - Better performance and cost efficiency
    """
    logger = setup_logging()
    logger.warning("Using deprecated run_scraper() function")
    
    if CONFIG is None:
        logger.error("Configuration not loaded. Cannot run scraper.")
        return None
    
    target_urls = CONFIG["target_urls"]
    all_results = []
    max_pages = CONFIG["scraper"].get("max_pages", 50)  # Default to 50 if not specified
    
    logger.info(f"Starting scraping with max_pages set to: {max_pages}")

    for url in target_urls:
        for page in range(1, max_pages + 1):  # Loop from page 1 to max_pages
            try:
                logger.info(f"Starting scraping job for: {url}{page}")
                
                scraper = configure_scraper(url, page)
                results = scraper.run()

                all_results.append(results)

                logger.info(f"Successfully scraped data from {url}{page}")

            except Exception as e:
                logger.error(f"Error scraping {url}{page}: {e}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = CONFIG["data_storage"]["output_directory"]
    file_prefix = CONFIG["data_storage"]["file_prefix"]
    output_file = f"{output_dir}/{file_prefix}{timestamp}.json"

    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # --- Clean Application URLs before saving ---
    cleaned_results = []
    for page_result in all_results:
        cleaned_page = []
        if isinstance(page_result, list): # Check if the page result is a list of jobs
            for job in page_result:
                if isinstance(job, dict) and 'Application URL' in job and isinstance(job['Application URL'], str):
                    original_url = job['Application URL']
                    # Replace double slashes after the protocol part
                    protocol_part, rest_of_url = original_url.split('://', 1) if '://' in original_url else ('', original_url)
                    cleaned_rest = rest_of_url.replace('//', '/')
                    job['Application URL'] = f"{protocol_part}://{cleaned_rest}" if protocol_part else cleaned_rest
                    if original_url != job['Application URL']:
                         logger.debug(f"Cleaned URL: '{original_url}' -> '{job['Application URL']}'")
                cleaned_page.append(job)
        else:
             logger.warning(f"Unexpected page result format, skipping cleaning for this page: {type(page_result)}")
             cleaned_page = page_result # Keep original if format is unexpected
        cleaned_results.append(cleaned_page)
    # --- End URL Cleaning ---

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(cleaned_results, f, indent=2, ensure_ascii=False) # Save cleaned results

    logger.info(f"Scraping completed. Results saved to: {output_file}")
    return output_file


def log_deduplication_metrics(metrics):
    """Log deduplication metrics for analysis"""
    logger = logging.getLogger("job_scraper")
    logger.info(f"=== Deduplication Metrics ===")
    logger.info(f"Search Term: {metrics['search_term']}")
    logger.info(f"Pages Scraped: {metrics['pages_scraped']}")
    logger.info(f"New Jobs: {metrics['new_jobs']}")
    logger.info(f"Duplicates: {metrics['duplicate_jobs']}")
    logger.info(f"Early Exit: {metrics['early_exit']}")
    if metrics['early_exit']:
        logger.info(f"Early Exit at Page: {metrics['early_exit_page']}")
        logger.info(f"Pages Saved: {metrics['estimated_pages_saved']}")
        logger.info(f"API Calls Saved: {metrics['estimated_api_calls_saved']}")
        logger.info(f"Estimated Cost Saved: ${metrics['estimated_cost_saved_usd']:.4f}")
    logger.info(f"Duration: {metrics['duration_seconds']:.2f}s")
    logger.info(f"============================")


def run_scraper_with_deduplication(search_term, cv_path, max_pages=None):
    """
    Run scraper with database deduplication and early exit optimization.
    
    Args:
        search_term: Search term to use in URL (e.g., "IT", "Data-Analyst")
        cv_path: Path to CV file for generating CV key
        max_pages: Maximum pages to scrape (defaults to CONFIG max_pages)
        
    Returns:
        List of new (non-duplicate) jobs found
        
    Features:
        - Checks each job against database before adding
        - Early exit when entire page is duplicates
        - Logs scrape history to database
        - URL normalization for accurate matching
        - Comprehensive metrics tracking and logging
    """
    logger = setup_logging()
    
    # Initialize metrics
    metrics = {
        'search_term': search_term,
        'start_time': datetime.now(),
        'pages_scraped': 0,
        'total_jobs_found': 0,
        'new_jobs': 0,
        'duplicate_jobs': 0,
        'early_exit': False,
        'early_exit_page': None,
        'estimated_pages_saved': 0,
        'estimated_api_calls_saved': 0,
        'estimated_cost_saved_usd': 0
    }
    
    # Validate configuration
    if CONFIG is None:
        logger.error("Configuration not loaded. Cannot run scraper.")
        return []
    
    # Validate dependencies
    if not all([JobMatchDatabase, generate_cv_key, URLNormalizer]):
        logger.error("Required utilities not available. Cannot use deduplication.")
        return []
    
    # Check if base_url is configured
    if "base_url" not in CONFIG:
        logger.error("base_url not configured in settings.json")
        return []
    
    # Initialize
    logger.info(f"Starting scraper with deduplication for search term: {search_term}")
    
    try:
        # Generate CV key
        cv_key = generate_cv_key(cv_path)
        logger.info(f"Generated CV key: {cv_key}")
    except Exception as e:
        logger.error(f"Failed to generate CV key from {cv_path}: {e}")
        return []
    
    # Initialize database
    db = JobMatchDatabase()
    try:
        db.connect()
        db.init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return []
    
    # Initialize URL normalizer
    normalizer = URLNormalizer()
    
    # Build base URL
    base_url = CONFIG["base_url"].format(search_term=search_term)
    logger.info(f"Base URL: {base_url}")
    
    # Get max pages
    if max_pages is None:
        max_pages = CONFIG["scraper"].get("max_pages", 10)
    
    logger.info(f"Max pages to scrape: {max_pages}")
    
    all_new_jobs = []
    
    # Page scraping loop
    for page in range(1, max_pages + 1):
        page_start_time = time.time()
        
        try:
            logger.info(f"Scraping page {page}...")
            
            # Configure and run scraper for this page
            scraper = configure_scraper(base_url, page)
            page_results = scraper.run()
            
            # Handle different result formats
            if not isinstance(page_results, list):
                logger.warning(f"Page {page}: Unexpected result format: {type(page_results)}")
                page_results = []
            
            jobs_found = len(page_results)
            new_jobs = []
            duplicate_count = 0
            
            # Update metrics
            metrics['pages_scraped'] = page
            metrics['total_jobs_found'] += jobs_found
            
            # Check each job for duplicates
            for job in page_results:
                if not isinstance(job, dict):
                    logger.warning(f"Skipping non-dict job: {type(job)}")
                    continue
                
                # Get and normalize job URL
                raw_url = job.get('Application URL', '')
                if not raw_url:
                    logger.warning(f"Job missing Application URL: {job.get('Job Title', 'Unknown')}")
                    continue
                
                # Clean and normalize URL
                cleaned_url = normalizer.clean_malformed_url(raw_url)
                normalized_url = normalizer.to_full_url(cleaned_url)
                
                # Check for duplicate
                try:
                    if db.job_exists(normalized_url, search_term, cv_key):
                        duplicate_count += 1
                        logger.debug(f"Duplicate job: {job.get('Job Title', 'Unknown')} - {normalized_url}")
                    else:
                        # Update job with normalized URL
                        job['Application URL'] = normalized_url
                        new_jobs.append(job)
                        logger.info(f"New job: {job.get('Job Title', 'Unknown')} - {normalized_url}")
                except Exception as e:
                    logger.error(f"Error checking duplicate for {normalized_url}: {e}")
                    # On error, treat as new to avoid losing data
                    new_jobs.append(job)
            
            # Add new jobs to results
            all_new_jobs.extend(new_jobs)
            
            # Update metrics with new jobs and duplicates
            metrics['new_jobs'] += len(new_jobs)
            metrics['duplicate_jobs'] += duplicate_count
            
            # Calculate page duration
            page_duration = time.time() - page_start_time
            
            # Log scrape history
            try:
                db.insert_scrape_history({
                    'search_term': search_term,
                    'page_number': page,
                    'jobs_found': jobs_found,
                    'new_jobs': len(new_jobs),
                    'duplicate_jobs': duplicate_count,
                    'duration_seconds': page_duration
                })
            except Exception as e:
                logger.warning(f"Failed to log scrape history for page {page}: {e}")
            
            # Log page summary
            logger.info(
                f"Page {page} summary: {jobs_found} jobs found, "
                f"{len(new_jobs)} new, {duplicate_count} duplicates, "
                f"{page_duration:.2f}s"
            )
            
            # Early exit check: if all jobs are duplicates, stop scraping
            if len(new_jobs) == 0 and duplicate_count > 0:
                # Track early exit metrics
                metrics['early_exit'] = True
                metrics['early_exit_page'] = page
                metrics['estimated_pages_saved'] = max_pages - page
                # Estimate ~50 jobs per page average
                metrics['estimated_api_calls_saved'] = metrics['estimated_pages_saved'] * 50
                # Estimate cost: $0.10 per 1000 API calls for gpt-4o-mini
                metrics['estimated_cost_saved_usd'] = metrics['estimated_api_calls_saved'] * 0.0001
                
                logger.info(
                    f"Early exit at page {page}: All {duplicate_count} jobs are duplicates. "
                    f"No need to scrape further pages."
                )
                break
            
            # If page returned no jobs at all, we may have reached the end
            if jobs_found == 0:
                logger.info(f"Page {page} returned no jobs. Reached end of results.")
                break
                
        except Exception as e:
            logger.error(f"Error scraping page {page}: {e}")
            # Continue to next page rather than failing completely
            continue
    
    # Close database connection
    try:
        db.close()
        logger.info("Database connection closed")
    except Exception as e:
        logger.warning(f"Error closing database: {e}")
    
    # Finalize metrics
    metrics['end_time'] = datetime.now()
    metrics['duration_seconds'] = (metrics['end_time'] - metrics['start_time']).total_seconds()
    
    # Log comprehensive metrics
    log_deduplication_metrics(metrics)
    
    # Log final summary
    logger.info(
        f"Scraping completed for '{search_term}': "
        f"{len(all_new_jobs)} new jobs found across {page} pages"
    )
    
    return all_new_jobs


# Main execution
if __name__ == "__main__":
    if CONFIG is None:
        print("Failed to load configuration. Exiting.")
        sys.exit(1)
    
    # Get port from environment variable (for Cloud Run compatibility)
    port = int(os.environ.get('PORT', 8080))
    
    print(f"Starting JobSearchAI Scraper API server on port {port}")
    print(f"Headless mode: {CONFIG['scraper']['headless']}")
    print(f"Display: {os.environ.get('DISPLAY', 'Not set')}")
    
    # Run Flask server
    app.run(
        host='0.0.0.0',  # Accept connections from any IP (required for Cloud Run)
        port=port,
        debug=False,     # Disable debug mode in production
        threaded=True    # Enable threading for concurrent requests
    )

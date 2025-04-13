
import os
import json
import logging
from datetime import datetime
from scrapegraphai.graphs import SmartScraperGraph

# Load configuration from settings.json
def load_config():
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "settings.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
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
Extract **all** job postings from the page. For each job listing, return a JSON object with the following fields:
1. Job Title
2. Company Name
3. Job Description
4. Required Skills
5. Location
6. Salary Range
7. Posting Date
8. Application URL

**Output** should be a **JSON array** of objects, one for each of the job listing found on the page.
"""

# Configure the ScrapeGraph pipeline with page number
def configure_scraper(source_url, page):
    if CONFIG is None:
        raise ValueError("Configuration not loaded. Cannot configure scraper.")
    
    scraper_config = CONFIG["scraper"]
    graph_config = {
        "llm": scraper_config["llm"],
        "verbose": scraper_config["verbose"],
        "headless": scraper_config["headless"],
        "output_format": scraper_config["output_format"]
    }

    # Construct the URL using proper pagination query parameter
    paginated_url = f"{source_url}{page}"

    scraper = SmartScraperGraph(
        prompt=EXTRACTION_PROMPT,
        source=paginated_url,
        config=graph_config
    )

    return scraper


# Function to run the scraper and save results
def run_scraper():
    logger = setup_logging()
    
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

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    logger.info(f"Scraping completed. Results saved to: {output_file}")
    return output_file

# Main execution
if __name__ == "__main__":
    if CONFIG is None:
        print("Failed to load configuration. Exiting.")
    else:
        output_file = run_scraper()
        print(f"Job data extraction complete. Data saved to: {output_file}")

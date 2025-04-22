import os
import logging
from pathlib import Path
import sys

# Set up logging for the main orchestrator
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("motivation_letter_generator.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("motivation_letter_generator")

# Import functions from the new utility modules
try:
    # job_details_utils should contain get_job_details
    from job_details_utils import get_job_details
    # letter_generation_utils should contain generate_motivation_letter
    from letter_generation_utils import generate_motivation_letter
except ImportError as e:
    logger.critical(f"Failed to import utility functions: {e}", exc_info=True)
    # Define dummy functions to prevent NameError if imports fail,
    # allowing the script to load but fail gracefully if main is called.
    def get_job_details(*args, **kwargs):
        logger.critical("get_job_details function not loaded due to import error.")
        return None
    def generate_motivation_letter(*args, **kwargs):
        logger.critical("generate_motivation_letter function not loaded due to import error.")
        return None


def load_cv_summary(cv_filename):
    """Load the CV summary from the processed CV file"""
    # Construct path relative to this script's parent directory
    # Assumes this script is in the project root
    base_path = Path(__file__).parent
    summary_filename = f"{cv_filename}_summary.txt"
    summary_path = base_path / 'process_cv/cv-data/processed' / summary_filename
    try:
        if not summary_path.exists():
            logger.error(f"CV summary file not found: {summary_path}")
            return None
        with open(summary_path, 'r', encoding='utf-8') as f:
            summary = f.read()
        logger.info(f"Successfully loaded CV summary from {summary_path}")
        return summary
    except Exception as e:
        logger.error(f"Error loading CV summary from {summary_path}: {str(e)}", exc_info=True)
        return None

# Main orchestration function
def main(cv_filename, job_url):
    """Main function to generate a motivation letter"""
    logger.info(f"Starting motivation letter generation for CV: {cv_filename} and job URL: {job_url}")

    # Step 1: Load CV Summary
    cv_summary = load_cv_summary(cv_filename)
    if not cv_summary:
        logger.error("Failed to load CV summary. Aborting.")
        return None
    logger.info("Successfully loaded CV summary")

    # Step 2: Get Job Details (using the refactored function from job_details_utils)
    logger.info(f"Fetching job details for URL: {job_url}")
    job_details = get_job_details(job_url) # This now calls the logic in job_details_utils.py
    if not job_details:
        logger.error("Failed to get job details. Aborting.")
        return None
    logger.info("Successfully got job details")

    # Step 3: Generate Motivation Letter (using the refactored function from letter_generation_utils)
    logger.info("Generating motivation letter content...")
    result = generate_motivation_letter(cv_summary, job_details) # This calls the logic in letter_generation_utils.py
    if not result:
        logger.error("Failed to generate motivation letter content.")
        return None

    # Log success based on the structure of the result dictionary
    if 'json_file_path' in result:
        logger.info(f"Successfully generated and saved motivation letter: {result['json_file_path']}")
    elif 'file_path' in result: # Fallback case from original code if JSON parsing failed
         logger.info(f"Successfully generated motivation letter (HTML fallback): {result['file_path']}")
    else:
         logger.warning("Motivation letter generation finished, but result structure unexpected.")

    return result

if __name__ == "__main__":
    # Example usage
    cv_file = "Lebenslauf" # Example CV filename base
    # Example URL - replace with a real one for testing
    test_job_url = "https://www.ostjob.ch/job/sachbearbeiterin-rechnungswesen-administration-80-100-m-w-d/994155"

    print(f"Running test generation for CV '{cv_file}' and URL '{test_job_url}'...")
    generation_result = main(cv_file, test_job_url)

    if generation_result:
        print("\n--- Generation Result ---")
        # Print paths if available
        if 'json_file_path' in generation_result:
            print(f"  JSON Path: {generation_result['json_file_path']}")
        if 'html_file_path' in generation_result:
            print(f"  HTML Path: {generation_result['html_file_path']}")
        if 'scraped_data_path' in generation_result:
             print(f"  Scraped Data Path: {generation_result['scraped_data_path']}")
        print("-------------------------")
    else:
        print("\nFailed to generate motivation letter.")

import json
import logging
from datetime import datetime
from pathlib import Path

# Add the current directory to the Python path to find modules
import sys
sys.path.append('.')

# Import from existing modules
from process_cv.cv_processor import extract_cv_text, summarize_cv

# Import from centralized configuration and utilities
from config import config, get_job_matcher_defaults
from utils.file_utils import (
    get_latest_file, 
    load_json_file, 
    save_json_file, 
    flatten_nested_job_data, 
    ensure_output_directory,
    create_timestamped_filename
)
from utils.api_utils import openai_client, generate_json_from_prompt
from utils.decorators import handle_exceptions, retry, log_execution_time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("job_matcher.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("job_matcher")

# OpenAI client is imported from api_utils and already initialized

@handle_exceptions(default_return=[])
@log_execution_time()
def load_latest_job_data(max_jobs=50):
    """
    Load the most recent job data file
    
    Args:
        max_jobs (int): Maximum number of job listings to return (default: 50)
    """
    # Get the latest job data file
    job_data_dir = config.get_path("job_data")
    logger.info(f"Looking for job data files in: {job_data_dir}")
    
    latest_file = get_latest_file(job_data_dir, "job_data_*.json")
    if latest_file is None:
        logger.error("No job data files found")
        return sample_job_data()
    
    logger.info(f"Loading job data from {latest_file}")
    
    # Load the file with error handling
    job_data = load_json_file(latest_file)
    if job_data is None:
        logger.error(f"Error loading job data from {latest_file}")
        return sample_job_data()
    
    # Flatten the nested structure
    job_listings = flatten_nested_job_data(job_data)
    
    # Limit the number of job listings to process
    limited_data = job_listings[:max_jobs] if max_jobs > 0 else job_listings
    
    # Print the first job listing to see its structure
    if limited_data:
        logger.info(f"Processing {len(limited_data)} job listings (limited by max_jobs={max_jobs})")
    
    return limited_data

def sample_job_data():
    """
    Return sample job data for testing when no real data is available
    
    Returns:
        list: Sample job listings
    """
    logger.warning("Falling back to sample job data for testing")
    
    # Fallback to sample data if loading fails
    sample_jobs = [
        {
            "Job Title": "Data Analyst",
            "Company Name": "Tech Solutions AG",
            "Job Description": "Analyzing data and creating reports using SQL and Python. Working with Power BI dashboards.",
            "Required Skills": "SQL, Python, Power BI, Excel",
            "Location": "St. Gallen",
            "Salary Range": "80,000 - 95,000 CHF",
            "Posting Date": "01.04.2025",
            "Application URL": "https://example.com/jobs/data-analyst"
        },
        {
            "Job Title": "Product Manager",
            "Company Name": "Innovative Systems GmbH",
            "Job Description": "Managing product lifecycle and working with development teams to create new features.",
            "Required Skills": "Product Management, Agile, JIRA",
            "Location": "Zürich",
            "Salary Range": "110,000 - 130,000 CHF",
            "Posting Date": "02.04.2025",
            "Application URL": "https://example.com/jobs/product-manager"
        },
        {
            "Job Title": "Financial Analyst",
            "Company Name": "Swiss Banking AG",
            "Job Description": "Preparing financial reports and analyzing financial data for decision making.",
            "Required Skills": "Financial Analysis, Excel, SAP",
            "Location": "Basel",
            "Salary Range": "90,000 - 105,000 CHF",
            "Posting Date": "03.04.2025",
            "Application URL": "https://example.com/jobs/financial-analyst"
        }
    ]
    
    logger.info("Using sample job data for testing")
    return sample_jobs

def evaluate_job_match(cv_summary, job_listing):
    """
    Use ChatGPT to evaluate how well a job matches the candidate's profile
    and if the candidate would like the job based on their career trajectory
    """
    # Create the prompt with the JSON structure explicitly defined
    profile_part = f"""
    Given this candidate profile:
    {cv_summary}

    And this job listing:
    Job Title: {job_listing.get('Job Title', 'N/A')}
    Company Name: {job_listing.get('Company Name', 'N/A')}
    Job Description: {job_listing.get('Job Description', 'N/A')}
    Required Skills: {job_listing.get('Required Skills', 'N/A')}
    Location: {job_listing.get('Location', 'N/A')}
    Salary Range: {job_listing.get('Salary Range', 'N/A')}
    Posting Date: {job_listing.get('Posting Date', 'N/A')}

    # Bewertung:
    # 1. Fähigkeiten-Übereinstimmung (1-10): Wie gut passen die Fähigkeiten des Kandidaten zu den Anforderungen der Stelle?
    # 2. Erfahrungspassung (1-10): Ist das Erfahrungsniveau des Kandidaten angemessen?
    # 3. Standortkompatibilität (Yes/No): Entspricht der Arbeitsort den Präferenzen des Kandidaten?
    # 4. Ausbildungsübereinstimmung (1-10): Wie gut passt die Ausbildung des Kandidaten zu den Anforderungen?
    # 5. Karriereverlauf-Übereinstimmung (1-10): Wie gut passt die Stelle zur bisherigen Karriereentwicklung des Kandidaten?
    # 6. Präferenzen-Übereinstimmung (1-10): Wie gut entspricht die Stelle den beruflichen Präferenzen des Kandidaten?
    # 7. Potenzielle Zufriedenheit (1-10): Wie wahrscheinlich ist es, dass der Kandidat in dieser Position zufrieden wäre?
    # 8. Gesamtübereinstimmung (1-10): Wie geeignet ist der Kandidat insgesamt, unter Berücksichtigung aller Faktoren?
    # 9. Begründung: Erklären Sie kurz Ihre Bewertung.

    Provide your evaluation as a JSON object with the following exact keys:
    {{
        "skills_match": 8,
        "experience_match": 7,
        "location_compatibility": "Yes",
        "education_fit": 9,
        "career_trajectory_alignment": 7,
        "preference_match": 8,
        "potential_satisfaction": 8,
        "overall_match": 8,
        "reasoning": "Ihre Begründung hier"
    }}
    """

    # System prompt for the job evaluation (including the word 'json' to make response_format work)
    system_prompt = "You are an AI assistant that evaluates job matches for candidates based on their CV and job listings. Return your assessment as a JSON object."
    
    # Default values if generation fails
    default_result = {
        "skills_match": 0,
        "experience_match": 0,
        "location_compatibility": "No",
        "education_fit": 0,
        "career_trajectory_alignment": 0,
        "preference_match": 0,
        "potential_satisfaction": 0,
        "overall_match": 0,
        "reasoning": "Error evaluating match"
    }
    
    # Use the utility function to generate JSON with built-in retries and error handling
    result = generate_json_from_prompt(
        prompt=profile_part,
        system_prompt=system_prompt,
        default=default_result
    )
    
    return result

@log_execution_time()
def match_jobs_with_cv(cv_path, min_score=6, max_jobs=50, max_results=10):
    """
    Match jobs with a CV and return the top matches
    
    Args:
        cv_path (str): Path to the CV file
        min_score (int): Minimum overall match score (default: 6)
        max_jobs (int): Maximum number of job listings to process (default: 50)
        max_results (int): Maximum number of results to return (default: 10)
    """
    try:
        # Extract and summarize CV
        logger.info(f"Processing CV: {cv_path}")
        cv_path_obj = Path(cv_path)
        if not cv_path_obj.exists():
            logger.error(f"CV file does not exist: {cv_path_obj.absolute()}")
            return []
            
        cv_text = extract_cv_text(cv_path)
        logger.info(f"Successfully extracted text from CV, length: {len(cv_text)} characters")
        
        cv_summary = summarize_cv(cv_text)
        logger.info(f"Successfully summarized CV, length: {len(cv_summary)} characters")
        
        # Load job data - pass max_jobs to load_latest_job_data to control how many job listings to process
        job_listings = load_latest_job_data(max_jobs=max_jobs)
        if not job_listings:
            logger.error("No job listings found")
            return []
    except Exception as e:
        logger.error(f"Error in initial processing: {str(e)}")
        return []
    
    logger.info(f"Evaluating {len(job_listings)} job listings")
    
    # Evaluate each job listing
    matches = []
    for job in job_listings:
        logger.info(f"Evaluating job: {job.get('Job Title', 'Unknown')}")
        evaluation = evaluate_job_match(cv_summary, job)
        
        # Add job details to evaluation
        evaluation["job_title"] = job.get("Job Title", "N/A")
        evaluation["company_name"] = job.get("Company Name", "N/A")
        evaluation["job_description"] = job.get("Job Description", "N/A")
        evaluation["location"] = job.get("Location", "N/A")
        evaluation["application_url"] = job.get("Application URL", "N/A")
        
        matches.append(evaluation)
    
    # Filter and sort matches
    filtered_matches = [m for m in matches if m["overall_match"] >= min_score]
    sorted_matches = sorted(filtered_matches, key=lambda x: x["overall_match"], reverse=True)
    
    # Return top matches
    return sorted_matches[:max_results]

# Renamed to avoid conflict with the imported function
def ensure_output_dir(output_dir="job_matches"):
    """
    Ensure the output directory exists
    
    Args:
        output_dir (str): Path to the output directory
    
    Returns:
        Path: Path object for the output directory
    """
    # Use the path from config if it exists, otherwise use the provided path
    output_path = config.get_path(output_dir) or Path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)
    logger.info(f"Ensuring output directory exists: {output_path.absolute()}")
    return output_path

@handle_exceptions(default_return=None)
def generate_report(matches, output_file=None, output_dir="job_matches"):
    """
    Generate a report with the top job matches
    
    Args:
        matches (list): List of job matches
        output_file (str, optional): Output file name. Defaults to None.
        output_dir (str, optional): Output directory. Defaults to "job_matches".
    
    Returns:
        str: Path to the generated report file
    """
    # Ensure output directory exists
    output_path = ensure_output_dir(output_dir)
    
    # Create a timestamped filename if none is provided
    if not output_file:
        output_file = create_timestamped_filename("job_matches", "json")
    
    # Create full path for output files
    json_file_path = output_path / output_file
    
    # Save detailed results to JSON using utility function
    save_json_file(matches, json_file_path, indent=2, ensure_ascii=False)
    
    # Generate a human-readable report
    report = "# Top Job Matches\n\n"
    
    for i, match in enumerate(matches, 1):
        report += f"## {i}. {match['job_title']} at {match['company_name']}\n"
        report += f"**Overall Match Score:** {match['overall_match']}/10\n"
        report += f"**Location:** {match['location']}\n"
        report += f"**Skills Match:** {match['skills_match']}/10\n"
        report += f"**Experience Match:** {match['experience_match']}/10\n"
        report += f"**Education Fit:** {match['education_fit']}/10\n"
        report += f"**Location Compatibility:** {match['location_compatibility']}\n"
        report += f"**Career Trajectory Alignment:** {match.get('career_trajectory_alignment', 'N/A')}/10\n"
        report += f"**Preference Match:** {match.get('preference_match', 'N/A')}/10\n"
        report += f"**Potential Satisfaction:** {match.get('potential_satisfaction', 'N/A')}/10\n"
        report += f"**Reasoning:** {match['reasoning']}\n"
        # Extract path and create proper ostjob.ch URL
        application_url = match['application_url']
        if application_url != 'N/A':
            if application_url.startswith("http://127.0.0.1:5000/") and application_url.count('/') >= 3:
                # Extract path from http://127.0.0.1:5000/path
                path = application_url.split('/', 3)[3]
                application_url = f"https://www.ostjob.ch/{path}"
            elif application_url.startswith("127.0.0.1:5000/") and application_url.count('/') >= 1:
                # Extract path from 127.0.0.1:5000/path
                path = application_url.split('/', 1)[1]
                application_url = f"https://www.ostjob.ch/{path}"
        report += f"**Application URL:** {application_url}\n\n"
    
    # Save the report
    report_file = str(json_file_path).replace(".json", ".md")
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    
    logger.info(f"Report generated: {report_file}")
    return report_file

if __name__ == "__main__":
    # Path to the CV using centralized configuration
    cv_path = str(config.get_path("cv_data_input") / "Lebenslauf_Claudio Lutz.pdf")
    
    # Get default parameters from centralized configuration
    job_matcher_defaults = get_job_matcher_defaults()
    
    # Set parameters for job matching
    max_jobs = job_matcher_defaults.get("max_jobs", 50)
    max_results = job_matcher_defaults.get("max_results", 10)
    min_score = job_matcher_defaults.get("cli_min_score", 3)  # Use CLI min score for command-line usage
    
    # Match jobs with CV
    matches = match_jobs_with_cv(cv_path, min_score=min_score, max_jobs=max_jobs, max_results=max_results)
    
    # Generate report
    report_file = generate_report(matches)
    
    print(f"Job matching completed. Results saved to: {report_file}")

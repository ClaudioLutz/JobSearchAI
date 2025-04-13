import json
import os
import logging
from datetime import datetime
from pathlib import Path
import openai
from dotenv import load_dotenv

# Add the current directory to the Python path to find modules
import sys
sys.path.append('.')

# Import from existing modules
from process_cv.cv_processor import extract_cv_text, summarize_cv

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

# Load environment variables
env_path = Path("process_cv/.env")
load_dotenv(dotenv_path=env_path)

# Initialize the OpenAI client
client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def load_latest_job_data(max_jobs=10):
    """
    Load the most recent job data file
    
    Args:
        max_jobs (int): Maximum number of job listings to return (default: 10)
    """
    job_data_dir = Path("job-data-acquisition/job-data-acquisition/data")
    logger.info(f"Looking for job data files in: {job_data_dir.absolute()}")
    
    if not job_data_dir.exists():
        logger.error(f"Job data directory does not exist: {job_data_dir.absolute()}")
        return None
        
    job_files = list(job_data_dir.glob("job_data_*.json"))
    logger.info(f"Found {len(job_files)} job data files")
    
    if not job_files:
        logger.error("No job data files found")
        return None
    
    # Sort by modification time (newest first)
    latest_file = max(job_files, key=lambda x: x.stat().st_mtime)
    logger.info(f"Loading job data from {latest_file}")
    
    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            job_data = json.load(f)
        
        # Check if the data has a nested structure with a "content" array
        if isinstance(job_data, dict) and "content" in job_data:
            # The content field contains an array of job listings
            job_listings = job_data["content"]
            logger.info(f"Found nested structure with {len(job_listings)} job listings in 'content' array")
        elif isinstance(job_data, list) and len(job_data) > 0 and isinstance(job_data[0], dict) and "content" in job_data[0]:
            # The first item in the array has a content field that contains job listings
            job_listings = job_data[0]["content"]
            logger.info(f"Found nested structure with {len(job_listings)} job listings in first item's 'content' array")
        else:
            # Assume the data is a flat array of job listings
            job_listings = job_data
            logger.info("Using flat job data structure")
        
        # Limit the number of job listings to process
        limited_data = job_listings[:max_jobs] if max_jobs > 0 else job_listings
        
        # Print the first job listing to see its structure
        if limited_data:
            logger.info(f"First job listing structure: {json.dumps(limited_data[0], indent=2)}")
        
        logger.info(f"Successfully loaded {len(job_listings)} job listings from {latest_file}")
        logger.info(f"Processing {len(limited_data)} job listings (limited by max_jobs={max_jobs})")
        return limited_data
    except Exception as e:
        logger.error(f"Error loading job data from {latest_file}: {str(e)}")
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
    """
    # Create the prompt without using f-string for the JSON structure part
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
    # 5. Gesamtübereinstimmung (1-10): Wie geeignet ist der Kandidat insgesamt, unter Berücksichtigung aller Faktoren?
    # 6. Begründung: Erklären Sie kurz Ihre Bewertung.
    """

    json_part = """
    Geben Sie Ihre Bewertung im JSON-Format mit folgender Struktur zurück:
    {
        "skills_match": 8,
        "experience_match": 7,
        "location_compatibility": "Yes",
        "education_fit": 9,
        "overall_match": 8,
        "reasoning": "Ihre Begründung hier"
    }
    """
    
    prompt = profile_part + json_part

    try:
        response = client.chat.completions.create(
            model='gpt-4o',
            messages=[
                {"role": "system", "content": "You are an AI assistant that evaluates job matches for candidates based on their CV and job listings."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
            max_tokens=800,
        )
        
        result = json.loads(response.choices[0].message.content.strip())
        return result
    except Exception as e:
        logger.error(f"Error evaluating job match: {e}")
        return {
            "skills_match": 0,
            "experience_match": 0,
            "location_compatibility": "No",
            "education_fit": 0,
            "overall_match": 0,
            "reasoning": f"Error evaluating match: {str(e)}"
        }

def match_jobs_with_cv(cv_path, min_score=6, max_results=10):
    """
    Match jobs with a CV and return the top matches
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
        
        # Load job data
        job_listings = load_latest_job_data()
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

def ensure_output_directory(output_dir="job_matches"):
    """
    Ensure the output directory exists
    
    Args:
        output_dir (str): Path to the output directory
    
    Returns:
        Path: Path object for the output directory
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)
    logger.info(f"Ensuring output directory exists: {output_path.absolute()}")
    return output_path

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
    output_path = ensure_output_directory(output_dir)
    
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"job_matches_{timestamp}.json"
    
    # Create full path for output files
    json_file_path = output_path / output_file
    
    # Save detailed results to JSON
    with open(json_file_path, "w", encoding="utf-8") as f:
        json.dump(matches, f, indent=2, ensure_ascii=False)
    
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
        report += f"**Reasoning:** {match['reasoning']}\n"
        report += f"**Application URL:** {match['application_url']}\n\n"
    
    # Save the report
    report_file = str(json_file_path).replace(".json", ".md")
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    
    logger.info(f"Report generated: {report_file}")
    return report_file

if __name__ == "__main__":
    # Path to the CV
    cv_path = "process_cv/cv-data/Lebenslauf_Claudio Lutz.pdf"
    
    # Set the maximum number of job listings to process
    max_jobs = 10
    
    # Lower the minimum score threshold to see more matches
    min_score = 3
    
    # Override the load_latest_job_data function to limit the number of jobs
    original_load_latest_job_data = load_latest_job_data
    load_latest_job_data = lambda: original_load_latest_job_data(max_jobs)
    
    # Match jobs with CV
    matches = match_jobs_with_cv(cv_path, min_score=min_score, max_results=10)
    
    # Generate report
    report_file = generate_report(matches)
    
    print(f"Job matching completed. Results saved to: {report_file}")

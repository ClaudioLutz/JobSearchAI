import os
import logging
import json
import openai
from pathlib import Path
from datetime import datetime
import importlib.util
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("motivation_letter_generator.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("motivation_letter_generator")

def load_cv_summary(cv_filename):
    """Load the CV summary from the processed CV file"""
    try:
        # Construct the summary file path directly from the CV filename
        summary_filename = f"{cv_filename}_summary.txt"
        summary_path = os.path.join('process_cv/cv-data/processed', summary_filename)
        
        # Check if the summary file exists
        if not os.path.exists(summary_path):
            logger.error(f"CV summary file not found: {summary_path}")
            return None
        
        # Load the CV summary
        with open(summary_path, 'r', encoding='utf-8') as f:
            summary = f.read()
        
        return summary
    except Exception as e:
        logger.error(f"Error loading CV summary: {str(e)}")
        return None

def get_job_details_using_scrapegraph(job_url):
    """Get job details using ScrapeGraph AI similar to job-data-acquisition/app.py"""
    try:
        logger.info(f"Getting job details using ScrapeGraph AI for URL: {job_url}")
        
        # Load the job-data-acquisition app module
        app_path = os.path.join(os.path.dirname(__file__), 'job-data-acquisition', 'app.py')
        
        if not os.path.exists(app_path):
            logger.error(f"Job data acquisition app not found at: {app_path}")
            return None
        
        # Load the module
        spec = importlib.util.spec_from_file_location("app_module", app_path)
        app_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(app_module)
        
        # Get the configuration
        config = app_module.load_config()
        if not config:
            logger.error("Failed to load ScrapeGraph configuration")
            return None
        
        # Define a specific extraction prompt for a single job page
        extraction_prompt = """
        Extract and summarize detailed information about this specific job posting. Focus on providing a comprehensive summary of the job requirements, responsibilities, and company expectations. Return a JSON object with the following fields:
        Mind you it could be "Arbeitsvermittler" which would not be the direct company to apply to.
        1. Job Title
        2. Company Name
        3. Job Description (provide a detailed summary of the job description)
        4. Required Skills (list all skills and qualifications mentioned in the posting)
        5. Responsibilities (summarize the main responsibilities of the role)
        6. Company Information (summarize any information about the company culture, values, or background)
        7. Location
        8. Salary Range (if available)
        9. Posting Date (if available)
        10. Application URL

        For the Job Description, Required Skills, Responsibilities, and Company Information fields, be thorough and include all relevant details from the posting. This information will be used to create a personalized motivation letter.

        **Output** should be a **JSON object** with these fields for this specific job posting.
        """
        
        # Configure the scraper
        scraper_config = config["scraper"]
        graph_config = {
            "llm": scraper_config["llm"],
            "verbose": scraper_config["verbose"],
            "headless": scraper_config["headless"],
            "output_format": scraper_config["output_format"]
        }
        
        # Import ScrapeGraph
        try:
            from scrapegraphai.graphs import SmartScraperGraph
        except ImportError:
            logger.error("ScrapeGraph AI library not installed. Please install it with: pip install scrapegraphai")
            return None
        
        # Create and run the scraper
        scraper = SmartScraperGraph(
            prompt=extraction_prompt,
            source=job_url,
            config=graph_config
        )
        
        # Run the scraper
        result = scraper.run()
        
        # Process the result
        if result and 'content' in result:
            # The result might be an array with one item or directly the job object
            job_details = result['content'][0] if isinstance(result['content'], list) else result['content']
            
            # Ensure all required fields are present
            if not job_details.get('Job Title'):
                job_details['Job Title'] = 'Unknown_Job'
            if not job_details.get('Company Name'):
                job_details['Company Name'] = 'Unknown_Company'
            if not job_details.get('Location'):
                job_details['Location'] = 'Unknown_Location'
            if not job_details.get('Job Description'):
                job_details['Job Description'] = 'No description available'
            if not job_details.get('Required Skills'):
                job_details['Required Skills'] = 'No specific skills listed'
            
            # Add the application URL if not present
            if not job_details.get('Application URL'):
                job_details['Application URL'] = job_url
            
            logger.info(f"Successfully extracted job details using ScrapeGraph AI")
            logger.info(f"Job Title: {job_details['Job Title']}")
            logger.info(f"Company Name: {job_details['Company Name']}")
            
            # Log all extracted fields for debugging
            logger.info("--- Extracted Job Details ---")
            for key, value in job_details.items():
                # Truncate long values for logging
                log_value = value
                if isinstance(log_value, str) and len(log_value) > 100:
                    log_value = log_value[:100] + "... [truncated]"
                logger.info(f"{key}: {log_value}")
            logger.info("---------------------------")
            
            return job_details
        else:
            logger.error("ScrapeGraph AI returned no content")
            return None
    except Exception as e:
        logger.error(f"Error getting job details using ScrapeGraph AI: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def get_job_details_from_scraped_data(job_url):
    """Get job details from pre-scraped data"""
    try:
        # Extract the job ID from the URL
        # Example URL: https://www.ostjob.ch/jobs/detail/12345
        logger.info(f"Getting job details from pre-scraped data for URL: {job_url}")
        job_id = job_url.split('/')[-1]
        logger.info(f"Extracted job ID: {job_id}")
        
        # Find the job data file
        job_data_dir = Path('job-data-acquisition/job-data-acquisition/data')
        logger.info(f"Job data directory: {job_data_dir}")
        if not job_data_dir.exists():
            logger.error(f"Job data directory not found: {job_data_dir}")
            return None
        
        # Get the latest job data file
        job_data_files = list(job_data_dir.glob('job_data_*.json'))
        logger.info(f"Found {len(job_data_files)} job data files")
        if not job_data_files:
            logger.error("No job data files found")
            return None
        
        latest_job_data_file = max(job_data_files, key=os.path.getctime)
        logger.info(f"Latest job data file: {latest_job_data_file}")
        
        # Load the job data
        with open(latest_job_data_file, 'r', encoding='utf-8') as f:
            job_data = json.load(f)
        
        logger.info(f"Loaded job data with {len(job_data[0]['content'])} jobs")
        
        # Find the job with the matching ID
        for i, job in enumerate(job_data[0]['content']):
            # Extract the job ID from the Application URL
            job_application_url = job.get('Application URL', '')
            logger.info(f"Job {i+1} Application URL: {job_application_url}")
            
            if job_id in job_application_url:
                logger.info(f"Found matching job: {job.get('Job Title', 'N/A')} at {job.get('Company Name', 'N/A')}")
                
                # Log all extracted fields for debugging
                logger.info("--- Extracted Job Details from Pre-scraped Data ---")
                for key, value in job.items():
                    # Truncate long values for logging
                    log_value = value
                    if isinstance(log_value, str) and len(log_value) > 100:
                        log_value = log_value[:100] + "... [truncated]"
                    logger.info(f"{key}: {log_value}")
                logger.info("------------------------------------------")
                
                return job
        
        # If no exact match found, try a more flexible approach
        logger.info("No exact match found, trying more flexible matching")
        for i, job in enumerate(job_data[0]['content']):
            # Try to match based on partial URL or other identifiers
            job_application_url = job.get('Application URL', '')
            job_title = job.get('Job Title', '')
            company_name = job.get('Company Name', '')
            
            logger.info(f"Checking job {i+1}: {job_title} at {company_name}")
            
            # Return the first job as a fallback
            if i == 0:
                logger.info(f"Using first job as fallback: {job_title} at {company_name}")
                return job
        
        logger.error(f"Job with ID {job_id} not found in job data")
        return None
    except Exception as e:
        logger.error(f"Error getting job details from pre-scraped data: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def get_job_details(job_url):
    """Get job details from the job URL, first trying to use ScrapeGraph AI, then falling back to pre-scraped data"""
    try:
        # First try to get job details using ScrapeGraph AI
        logger.info(f"Attempting to get job details using ScrapeGraph AI for URL: {job_url}")
        
        # Check if scrapegraphai is installed
        try:
            import scrapegraphai
            job_details = get_job_details_using_scrapegraph(job_url)
        except ImportError:
            logger.warning("ScrapeGraph AI library not installed, skipping direct scraping")
            job_details = None
        
        if job_details:
            logger.info("Successfully got job details using ScrapeGraph AI")
            return job_details
        
        # If ScrapeGraph AI fails or is not installed, fall back to pre-scraped data
        logger.info("Getting job details from pre-scraped data")
        job_details = get_job_details_from_scraped_data(job_url)
        
        if job_details:
            logger.info("Successfully got job details from pre-scraped data")
            return job_details
        
        # If all methods fail, return a default job details object
        logger.warning("All methods to get job details failed, using default values")
        return {
            'Job Title': 'Unknown_Job',
            'Company Name': 'Unknown_Company',
            'Location': 'Unknown_Location',
            'Job Description': 'No description available',
            'Required Skills': 'No specific skills listed',
            'Application URL': job_url
        }
    except Exception as e:
        logger.error(f"Error getting job details: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Return default values in case of error
        return {
            'Job Title': 'Unknown_Job',
            'Company Name': 'Unknown_Company',
            'Location': 'Unknown_Location',
            'Job Description': 'No description available',
            'Required Skills': 'No specific skills listed',
            'Application URL': job_url
        }

def json_to_html(motivation_letter_json):
    """Convert motivation letter JSON to HTML format"""
    try:
        # Extract fields from JSON
        candidate_name = motivation_letter_json.get('candidate_name', '')
        candidate_address = motivation_letter_json.get('candidate_address', '')
        candidate_city = motivation_letter_json.get('candidate_city', '')
        candidate_email = motivation_letter_json.get('candidate_email', '')
        candidate_phone = motivation_letter_json.get('candidate_phone', '')
        
        company_name = motivation_letter_json.get('company_name', '')
        company_department = motivation_letter_json.get('company_department', '')
        company_address = motivation_letter_json.get('company_address', '')
        
        date = motivation_letter_json.get('date', '')
        subject = motivation_letter_json.get('subject', '')
        greeting = motivation_letter_json.get('greeting', '')
        introduction = motivation_letter_json.get('introduction', '')
        
        body_paragraphs = motivation_letter_json.get('body_paragraphs', [])
        
        closing = motivation_letter_json.get('closing', '')
        signature = motivation_letter_json.get('signature', '')
        full_name = motivation_letter_json.get('full_name', '')
        
        # Create HTML content
        html_content = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Motivationsschreiben</title>
</head>
<body>
    <p>{candidate_name}<br>
    {candidate_address}<br>
    {candidate_city}<br>
    {candidate_email}<br>
    {candidate_phone}</p>

    <p>{company_name}<br>
    {company_department}<br>
    {company_address}</p>

    <p>{date}</p>

    <h2>{subject}</h2>

    <p>{greeting},</p>

    <p>{introduction}</p>
"""
        
        # Add body paragraphs
        for paragraph in body_paragraphs:
            html_content += f"    <p>{paragraph}</p>\n"
        
        # Add closing and signature
        html_content += f"""
    <p>{closing}</p>

    <p>{signature},<br>
    {full_name}</p>
</body>
</html>
"""
        
        return html_content
    except Exception as e:
        logger.error(f"Error converting JSON to HTML: {str(e)}")
        return "<p>Error generating HTML content</p>"

def generate_motivation_letter(cv_summary, job_details):
    """Generate a motivation letter using GPT-4o"""
    try:
        # Get OpenAI API key from environment variable
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            # Try to get it from the .env file in process_cv directory
            env_path = os.path.join('process_cv', '.env')
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    for line in f:
                        if line.startswith('OPENAI_API_KEY='):
                            openai_api_key = line.strip().split('=')[1]
                            break
        
        if not openai_api_key:
            logger.error("OpenAI API key not found")
            return None
        
        # Initialize OpenAI client
        client = openai.OpenAI(api_key=openai_api_key)
        
        # Prepare the prompt
        prompt = """
        Schreibe ein Motivationsschreiben aus den Informationen von der Webseite und dem Lebenslauf:
        
        ## Lebenslauf des Bewerbers:
        {}
        
        ## Stellenangebot (von der Webseite):
        Titel: {}
        Firma: {}
        Ort: {}
        
        Beschreibung: 
        {}
        
        Erforderliche Fähigkeiten: 
        {}
        
        Verantwortlichkeiten: 
        {}
        
        Unternehmensinformationen: 
        {}
        
        Das Motivationsschreiben sollte:
        1. Professionell und überzeugend sein
        2. Die Qualifikationen und Erfahrungen des Bewerbers KONKRET mit den Anforderungen der Stelle verknüpfen
        3. Die Motivation des Bewerbers für die Stelle und das Unternehmen zum Ausdruck bringen
        4. Etwa eine halbe Seite lang sein (ca. 200-300 Wörter)
        5. Auf Deutsch verfasst sein
        6. Im formalen Bewerbungsstil mit Anrede, Einleitung, Hauptteil, Schluss und Grußformel sein
        7. SPEZIFISCH auf die Stellenanforderungen und Verantwortlichkeiten eingehen, die aus der Webseite extrahiert wurden
        8. Die Stärken des Bewerbers hervorheben, die besonders relevant für diese Position sind
        9. Auf die Unternehmenskultur und -werte eingehen, wenn diese Informationen verfügbar sind
        10. KONKRETE BEISPIELE aus dem Lebenslauf des Bewerbers verwenden, die zeigen, wie er/sie die Anforderungen erfüllt
        
        WICHTIG: Falls die Firma der ausgeschriebenen Stell die "Universal-Job AG" ist, behandle sie als Personalvermittler in deinem Schreiben und passe den Inhalt entsprechend an. In diesem Fall wissen wir nicht wer die Stelle schlussendlich ausgeschrieben hat.
        
        WICHTIG: Verwende die detaillierten Informationen aus der Stellenbeschreibung, um ein personalisiertes und spezifisches Motivationsschreiben zu erstellen. Gehe auf konkrete Anforderungen und Verantwortlichkeiten ein und zeige, wie der Bewerber diese erfüllen kann.
        
        Gib das Motivationsschreiben als JSON-Objekt mit folgender Struktur zurück:
        
        ```json
        {{
          "candidate_name": "Vollständiger Name des Bewerbers",
          "candidate_address": "Straße und Hausnummer",
          "candidate_city": "PLZ und Ort",
          "candidate_email": "E-Mail-Adresse",
          "candidate_phone": "Telefonnummer",
          "company_name": "Name des Unternehmens",
          "company_department": "Abteilung (falls bekannt, sonst 'Personalabteilung')",
          "company_address": "Adresse des Unternehmens (falls bekannt)",
          "date": "Ort, den [aktuelles Datum]",
          "subject": "Bewerbung als [Stellentitel]",
          "greeting": "Anrede (z.B. 'Sehr geehrte Damen und Herren')",
          "introduction": "Einleitungsabsatz",
          "body_paragraphs": [
            "Erster Hauptabsatz",
            "Zweiter Hauptabsatz",
            "Dritter Hauptabsatz (falls nötig)"
          ],
          "closing": "Schlussabsatz",
          "signature": "Grußformel (z.B. 'Mit freundlichen Grüßen')",
          "full_name": "Vollständiger Name des Bewerbers"
        }}
        ```
        
        Stelle sicher, dass alle Felder korrekt befüllt sind und das JSON-Format gültig ist.
        """.format(
            cv_summary,
            job_details.get('Job Title', 'N/A'),
            job_details.get('Company Name', 'N/A'),
            job_details.get('Location', 'N/A'),
            job_details.get('Job Description', 'N/A'),
            job_details.get('Required Skills', 'N/A'),
            job_details.get('Responsibilities', 'Keine spezifischen Verantwortlichkeiten aufgeführt.'),
            job_details.get('Company Information', 'Keine spezifischen Unternehmensinformationen verfügbar.')
        )
        
        # Generate the motivation letter using GPT-4o
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": "Du bist ein professioneller Bewerbungsberater, der Motivationsschreiben für Stellenbewerbungen erstellt. Gib deine Antwort als valides JSON-Objekt zurück."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500,
            response_format={"type": "json_object"}  # Ensure JSON response
        )
        
        # Extract the generated motivation letter as JSON
        motivation_letter_json_str = response.choices[0].message.content
        
        try:
            # Parse the JSON response
            motivation_letter_json = json.loads(motivation_letter_json_str)
            logger.info("Successfully parsed motivation letter JSON")
            
            # Convert JSON to HTML for backward compatibility
            html_content = json_to_html(motivation_letter_json)
            
            # Save the motivation letter (both JSON and HTML)
            # Sanitize job title and company name to avoid path issues
            job_title = job_details.get('Job Title', 'job')
            company_name = job_details.get('Company Name', 'company')
            
            # Replace problematic characters and limit length
            job_title = ''.join(c if c.isalnum() or c in [' ', '_', '-'] else '_' for c in job_title)
            company_name = ''.join(c if c.isalnum() or c in [' ', '_', '-'] else '_' for c in company_name)
            
            # Limit length to avoid excessively long filenames
            job_title = job_title.replace(' ', '_')[:30]
            company_name = company_name.replace(' ', '_')[:30]
            
            # Create the motivation letters directory if it doesn't exist
            motivation_letters_dir = Path('motivation_letters')
            motivation_letters_dir.mkdir(exist_ok=True)
            
            # Save the HTML version - use job title as the primary identifier
            html_filename = f"motivation_letter_{job_title}.html"
            html_file_path = motivation_letters_dir / html_filename
            
            logger.info(f"Saving HTML motivation letter to file: {html_file_path}")
            with open(html_file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Save the JSON version - use job title as the primary identifier
            json_filename = f"motivation_letter_{job_title}.json"
            json_file_path = motivation_letters_dir / json_filename
            
            logger.info(f"Saving JSON motivation letter to file: {json_file_path}")
            with open(json_file_path, 'w', encoding='utf-8') as f:
                json.dump(motivation_letter_json, f, ensure_ascii=False, indent=2)
            
            return {
                'motivation_letter_json': motivation_letter_json,
                'motivation_letter_html': html_content,
                'html_file_path': str(html_file_path),
                'json_file_path': str(json_file_path)
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON response: {str(e)}")
            logger.error(f"Raw response: {motivation_letter_json_str}")
            
            # Fallback: treat the response as HTML directly
            logger.warning("Falling back to treating response as HTML")
            
            # Sanitize job title and company name to avoid path issues
            job_title = job_details.get('Job Title', 'job')
            company_name = job_details.get('Company Name', 'company')
            
            # Replace problematic characters and limit length
            job_title = ''.join(c if c.isalnum() or c in [' ', '_', '-'] else '_' for c in job_title)
            company_name = ''.join(c if c.isalnum() or c in [' ', '_', '-'] else '_' for c in company_name)
            
            # Limit length to avoid excessively long filenames
            job_title = job_title.replace(' ', '_')[:30]
            company_name = company_name.replace(' ', '_')[:30]
            
            # Create the motivation letters directory if it doesn't exist
            motivation_letters_dir = Path('motivation_letters')
            motivation_letters_dir.mkdir(exist_ok=True)
            
            # Save the motivation letter to a file - use job title as the primary identifier
            filename = f"motivation_letter_{job_title}.html"
            motivation_letter_file = motivation_letters_dir / filename
            
            logger.info(f"Saving motivation letter to file: {motivation_letter_file}")
            with open(motivation_letter_file, 'w', encoding='utf-8') as f:
                f.write(motivation_letter_json_str)
            
            return {
                'motivation_letter': motivation_letter_json_str,
                'file_path': str(motivation_letter_file)
            }
    except Exception as e:
        logger.error(f"Error generating motivation letter: {str(e)}")
        return None

def main(cv_filename, job_url):
    """Main function to generate a motivation letter"""
    logger.info(f"Starting motivation letter generation for CV: {cv_filename} and job URL: {job_url}")
    
    # Load the CV summary
    cv_summary = load_cv_summary(cv_filename)
    if not cv_summary:
        logger.error("Failed to load CV summary")
        return None
    
    logger.info("Successfully loaded CV summary")
    
    # Get the job details
    job_details = get_job_details(job_url)
    if not job_details:
        logger.error("Failed to get job details")
        return None
    
    logger.info("Successfully got job details")
    
    # Generate the motivation letter
    result = generate_motivation_letter(cv_summary, job_details)
    if not result:
        logger.error("Failed to generate motivation letter")
        return None
    
    # Check which format we have (JSON or HTML)
    if 'json_file_path' in result:
        logger.info(f"Successfully generated motivation letter: {result['json_file_path']}")
    else:
        logger.info(f"Successfully generated motivation letter: {result['file_path']}")
    return result

if __name__ == "__main__":
    # Example usage
    cv_filename = "Lebenslauf"
    job_url = "https://www.ostjob.ch/jobs/detail/12345"
    result = main(cv_filename, job_url)
    
    if result:
        if 'json_file_path' in result:
            print(f"Motivation letter generated successfully: {result['json_file_path']}")
        else:
            print(f"Motivation letter generated successfully: {result['file_path']}")
    else:
        print("Failed to generate motivation letter")

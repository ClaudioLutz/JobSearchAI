import os
import json
import logging
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify, session
from werkzeug.utils import secure_filename
import urllib.parse

# Add the current directory to the Python path to find modules
import sys
sys.path.append('.')

# Import from existing modules
from process_cv.cv_processor import extract_cv_text, summarize_cv
from job_matcher import match_jobs_with_cv, generate_report, load_latest_job_data
from motivation_letter_generator import main as generate_motivation_letter
from word_template_generator import json_to_docx, create_word_document_from_json_file

# Helper function to get job details for a URL
def get_job_details_for_url(job_url):
    """Get job details for a URL from the latest job data file"""
    job_details = {}
    try:
        # Extract the job ID from the URL
        job_id = job_url.split('/')[-1]
        logger.info(f"Extracted job ID: {job_id}")
        
        # Find the job data file
        job_data_dir = Path('job-data-acquisition/job-data-acquisition/data')
        logger.info(f"Job data directory: {job_data_dir}")
        
        if job_data_dir.exists():
            # Get the latest job data file
            job_data_files = list(job_data_dir.glob('job_data_*.json'))
            logger.info(f"Found {len(job_data_files)} job data files")
            
            if job_data_files:
                latest_job_data_file = max(job_data_files, key=os.path.getctime)
                logger.info(f"Latest job data file: {latest_job_data_file}")
                
                # Load the job data
                with open(latest_job_data_file, 'r', encoding='utf-8') as f:
                    job_data = json.load(f)
                
                # Process the job data based on its structure
                job_listings = []
                
                # Check if the data has a nested structure
                if isinstance(job_data, list):
                    if len(job_data) > 0:
                        if isinstance(job_data[0], list):
                            # It's an array of arrays - flatten it
                            for job_array in job_data:
                                job_listings.extend(job_array)
                            logger.info(f"Found array of arrays structure with {len(job_listings)} total job listings")
                        elif isinstance(job_data[0], dict) and 'content' in job_data[0]:
                            # It's the old structure with a 'content' property
                            job_listings = job_data[0]['content']
                            logger.info(f"Found old structure with {len(job_listings)} job listings in 'content' array")
                        else:
                            # Assume it's a flat array of job listings
                            job_listings = job_data
                            logger.info(f"Using flat job data structure with {len(job_listings)} job listings")
                
                logger.info(f"Processed job data with {len(job_listings)} total job listings")
                
                # Find the job with the matching ID
                for i, job in enumerate(job_listings):
                    # Extract the job ID from the Application URL
                    job_application_url = job.get('Application URL', '')
                    logger.info(f"Job {i+1} Application URL: {job_application_url}")
                    
                    if job_id in job_application_url:
                        logger.info(f"Found matching job: {job.get('Job Title', 'N/A')} at {job.get('Company Name', 'N/A')}")
                        job_details = job
                        break
                
                # If no exact match found, use the first job as a fallback
                if not job_details and job_listings:
                    logger.info("No exact match found, using first job as fallback")
                    job_details = job_listings[0]
    except Exception as e:
        logger.error(f'Error getting job details: {str(e)}')
        import traceback
        logger.error(traceback.format_exc())
    
    return job_details

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("dashboard.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("dashboard")

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)  # For flash messages

# Progress tracking
operation_progress = {}
operation_status = {}

# Configure upload folder
UPLOAD_FOLDER = 'process_cv/cv-data/input'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def start_operation(operation_type):
    """Start tracking a new operation"""
    operation_id = str(uuid.uuid4())
    operation_progress[operation_id] = 0
    operation_status[operation_id] = {
        'type': operation_type,
        'status': 'starting',
        'message': f'Starting {operation_type}...',
        'start_time': datetime.now().isoformat()
    }
    return operation_id

def update_operation_progress(operation_id, progress, status=None, message=None):
    """Update the progress of an operation"""
    if operation_id in operation_progress:
        operation_progress[operation_id] = progress
        
        if status or message:
            if operation_id in operation_status:
                if status:
                    operation_status[operation_id]['status'] = status
                if message:
                    operation_status[operation_id]['message'] = message
                operation_status[operation_id]['updated_time'] = datetime.now().isoformat()
    
    logger.info(f"Operation {operation_id}: {progress}% complete - {message}")

def complete_operation(operation_id, status='completed', message='Operation completed'):
    """Mark an operation as completed"""
    if operation_id in operation_progress:
        operation_progress[operation_id] = 100
        
        if operation_id in operation_status:
            operation_status[operation_id]['status'] = status
            operation_status[operation_id]['message'] = message
            operation_status[operation_id]['completed_time'] = datetime.now().isoformat()
    
    logger.info(f"Operation {operation_id} {status}: {message}")

@app.route('/operation_status/<operation_id>')
def get_operation_status(operation_id):
    """Get the status of an operation"""
    if operation_id in operation_progress and operation_id in operation_status:
        return jsonify({
            'progress': operation_progress[operation_id],
            'status': operation_status[operation_id]
        })
    else:
        return jsonify({'error': 'Operation not found'}), 404

@app.route('/')
def index():
    """Render the main dashboard page"""
    # Get list of available CVs
    cv_dir = Path('process_cv/cv-data')
    cv_files = list(cv_dir.glob('**/*.pdf')) + list(cv_dir.glob('**/*.docx'))
    cv_files = [str(f.relative_to(cv_dir)) for f in cv_files]
    
    # Get list of available job data files
    job_data_dir = Path('job-data-acquisition/job-data-acquisition/data')
    if job_data_dir.exists():
        job_data_files = list(job_data_dir.glob('job_data_*.json'))
        job_data_files = [f.name for f in job_data_files]
    else:
        job_data_files = []
    
    # Get list of available job match reports
    report_dir = Path('job_matches')
    if report_dir.exists():
        report_files = list(report_dir.glob('job_matches_*.md'))
        report_files = [f.name for f in report_files]
    else:
        report_files = []
    
    return render_template('index.html', 
                          cv_files=cv_files, 
                          job_data_files=job_data_files,
                          report_files=report_files)

@app.route('/upload_cv', methods=['POST'])
def upload_cv():
    """Handle CV upload"""
    if 'cv_file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    
    file = request.files['cv_file']
    
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        flash(f'CV uploaded successfully: {filename}')
        
        # Process the CV
        try:
            cv_text = extract_cv_text(file_path)
            cv_summary = summarize_cv(cv_text)
            
            # Save the processed CV summary
            processed_dir = 'process_cv/cv-data/processed'
            os.makedirs(processed_dir, exist_ok=True)
            
            # Create summary filename without any nested path
            summary_filename = os.path.splitext(os.path.basename(filename))[0] + '_summary.txt'
            summary_path = os.path.join(processed_dir, summary_filename)
            
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(cv_summary)
                
            flash(f'CV processed successfully. Summary saved to: {summary_path}')
        except Exception as e:
            flash(f'Error processing CV: {str(e)}')
            logger.error(f'Error processing CV: {str(e)}')
    else:
        flash('Invalid file type. Only PDF files are allowed.')
    
    return redirect(url_for('index'))

@app.route('/run_job_matcher', methods=['POST'])
def run_job_matcher():
    """Run the job matcher with the selected CV"""
    cv_path = request.form.get('cv_path')
    min_score = int(request.form.get('min_score', 3))
    max_jobs = int(request.form.get('max_jobs', 50))
    max_results = int(request.form.get('max_results', 10))
    
    if not cv_path:
        flash('No CV selected')
        return redirect(url_for('index'))
    
    # Construct the full path to the CV
    full_cv_path = os.path.join('process_cv/cv-data', cv_path)
    
    try:
        # Start tracking the operation
        operation_id = start_operation('job_matching')
        
        # Define a function to run the job matcher in a background thread
        def run_job_matcher_task():
            try:
                # Update status
                update_operation_progress(operation_id, 10, 'processing', 'Loading job data...')
                
                # Match jobs with CV - pass both max_jobs and max_results
                matches = match_jobs_with_cv(full_cv_path, min_score=min_score, max_jobs=max_jobs, max_results=max_results)
                
                if not matches:
                    update_operation_progress(operation_id, 100, 'completed', 'No job matches found')
                    return
                
                # Update status
                update_operation_progress(operation_id, 80, 'processing', 'Adding CV path to matches and generating report...')
                
                # Add cv_path to each match dictionary before saving
                for match in matches:
                    match['cv_path'] = full_cv_path # Store the full path used for matching

                # Generate report (which now includes cv_path in the saved JSON)
                report_file = generate_report(matches)
                
                # Complete the operation
                complete_operation(operation_id, 'completed', f'Job matching completed. Results saved to: {report_file}')
            except Exception as e:
                logger.error(f'Error in job matcher task: {str(e)}')
                complete_operation(operation_id, 'failed', f'Error running job matcher: {str(e)}')
        
        # Start the background thread
        thread = threading.Thread(target=run_job_matcher_task)
        thread.daemon = True
        thread.start()
        
        # Return immediately with the operation ID
        flash(f'Job matcher started. Please wait while the results are being processed. (operation_id={operation_id})')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'Error running job matcher: {str(e)}')
        logger.error(f'Error running job matcher: {str(e)}')
        return redirect(url_for('index'))

@app.route('/run_job_scraper', methods=['POST'])
def run_job_scraper():
    """Run the job data acquisition component"""
    try:
        # Get max_pages parameter from the form
        max_pages = int(request.form.get('max_pages', 50))
        
        # Start tracking the operation
        operation_id = start_operation('job_scraping')
        
        # Define a function to run the job scraper in a background thread
        def run_job_scraper_task():
            try:
                # Update status
                update_operation_progress(operation_id, 10, 'processing', 'Updating settings...')
                
                # Update the settings.json file with the max_pages parameter
                settings_path = os.path.join(os.path.dirname(__file__), 'job-data-acquisition', 'settings.json')
                
                # Read the current settings
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                # Update the max_pages parameter
                settings['scraper']['max_pages'] = max_pages
                
                # Write the updated settings back to the file
                with open(settings_path, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, indent=4, ensure_ascii=False)
                
                # Update status
                update_operation_progress(operation_id, 20, 'processing', 'Starting job scraper...')
                
                # Import the job scraper module using importlib for more robust importing
                import importlib.util
                
                # Get the absolute path to the app.py file
                app_path = os.path.join(os.path.dirname(__file__), 'job-data-acquisition', 'app.py')
                
                # Load the module
                spec = importlib.util.spec_from_file_location("app_module", app_path)
                app_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(app_module)
                
                # Get the run_scraper function
                run_scraper = app_module.run_scraper
                
                # Update status
                update_operation_progress(operation_id, 30, 'processing', 'Scraping job listings...')
                
                # Run the scraper
                output_file = run_scraper()
                
                if output_file is None:
                    complete_operation(operation_id, 'failed', 'Job data acquisition failed. Check the logs for details.')
                else:
                    complete_operation(operation_id, 'completed', f'Job data acquisition completed. Data saved to: {output_file}')
            except Exception as e:
                logger.error(f'Error in job scraper task: {str(e)}')
                complete_operation(operation_id, 'failed', f'Error running job scraper: {str(e)}')
        
        # Start the background thread
        thread = threading.Thread(target=run_job_scraper_task)
        thread.daemon = True
        thread.start()
        
        # Return immediately with the operation ID
        flash(f'Job scraper started. Please wait while the job listings are being scraped. (operation_id={operation_id})')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'Error running job scraper: {str(e)}')
        logger.error(f'Error running job scraper: {str(e)}')
        return redirect(url_for('index'))

@app.route('/view_results/<report_file>')
def view_results(report_file):
    """View job match results"""
    # Get the JSON file path
    json_file = report_file.replace('.md', '.json')
    json_path = os.path.join('job_matches', json_file)
    
    try:
        # Load the job matches from the JSON file
        with open(json_path, 'r', encoding='utf-8') as f:
            matches = json.load(f)

        # Extract CV base name from the 'cv_path' stored within the matches data
        cv_filename = None
        if matches and isinstance(matches, list) and len(matches) > 0 and 'cv_path' in matches[0]:
            try:
                # Extract the filename stem (name without extension) from the stored path
                cv_full_path = matches[0]['cv_path']
                cv_filename = Path(cv_full_path).stem
                logger.info(f"Extracted CV filename '{cv_filename}' from matches[0]['cv_path']: {cv_full_path}")
            except Exception as path_e:
                logger.error(f"Error extracting filename from cv_path '{matches[0].get('cv_path')}': {path_e}")
        else:
            logger.warning(f"Could not find 'cv_path' in the first match of {json_path} to determine CV filename.")

        # Fix application URLs - extract path and create proper ostjob.ch URL
        for match in matches:
            if match.get('application_url') and match['application_url'] != 'N/A':
                url = match['application_url']
                if url.startswith("http://127.0.0.1:5000/") and url.count('/') >= 3:
                    # Extract path from http://127.0.0.1:5000/path
                    path = url.split('/', 3)[3]
                    match['application_url'] = f"https://www.ostjob.ch/{path}"
                elif url.startswith("127.0.0.1:5000/") and url.count('/') >= 1:
                    # Extract path from 127.0.0.1:5000/path
                    path = url.split('/', 1)[1]
                    match['application_url'] = f"https://www.ostjob.ch/{path}"
            
            # Check if a motivation letter already exists for this job
            if 'job_title' in match:
                job_title = match['job_title']
                # Sanitize job title to match the filename format
                sanitized_job_title = ''.join(c if c.isalnum() or c in [' ', '_', '-'] else '_' for c in job_title)
                sanitized_job_title = sanitized_job_title.replace(' ', '_')[:30]
                
                # Check for existing HTML and JSON files
                html_path = os.path.join('motivation_letters', f"motivation_letter_{sanitized_job_title}.html")
                json_path = os.path.join('motivation_letters', f"motivation_letter_{sanitized_job_title}.json")
                docx_path = os.path.join('motivation_letters', f"motivation_letter_{sanitized_job_title}.docx")
                
                # Add flags to the match data
                match['has_motivation_letter'] = os.path.exists(html_path) and os.path.exists(json_path)
                match['motivation_letter_html_path'] = html_path if match['has_motivation_letter'] else None
                match['motivation_letter_docx_path'] = docx_path if os.path.exists(docx_path) else None
        
        return render_template('results.html', matches=matches, report_file=report_file, cv_filename=cv_filename)
    except Exception as e:
        flash(f'Error loading results: {str(e)}')
        logger.error(f'Error loading results: {str(e)}')
        return redirect(url_for('index'))

@app.route('/download_report/<report_file>')
def download_report(report_file):
    """Download a job match report"""
    report_path = os.path.join('job_matches', report_file)
    
    try:
        return send_file(report_path, as_attachment=True)
    except Exception as e:
        flash(f'Error downloading report: {str(e)}')
        logger.error(f'Error downloading report: {str(e)}')
        return redirect(url_for('index'))

@app.route('/generate_motivation_letter', methods=['POST'])
def generate_motivation_letter_route():
    """Generate a motivation letter for a job"""
    try:
        # Get the CV filename and job URL from the form
        cv_filename = request.form.get('cv_filename')
        job_url = request.form.get('job_url')
        report_file = request.form.get('report_file')
        
        logger.info(f"Generating motivation letter for CV: {cv_filename} and job URL: {job_url}")
        
        if not cv_filename or not job_url:
            logger.error(f"Missing CV filename or job URL: cv_filename={cv_filename}, job_url={job_url}")
            flash('Missing CV filename or job URL')
            return redirect(url_for('index'))
        
        # Check if the CV summary file exists
        summary_path = os.path.join('process_cv/cv-data/processed', f"{cv_filename}_summary.txt")
        if not os.path.exists(summary_path):
            logger.error(f"CV summary file not found: {summary_path}")
            flash(f'CV summary file not found: {summary_path}')
            return redirect(url_for('view_results', report_file=report_file))
        
        # Get job details to check if a motivation letter already exists
        job_details = get_job_details_for_url(job_url)
        if job_details and 'Job Title' in job_details:
            job_title = job_details['Job Title']
            
            # Sanitize job title to match the filename format
            sanitized_job_title = ''.join(c if c.isalnum() or c in [' ', '_', '-'] else '_' for c in job_title)
            sanitized_job_title = sanitized_job_title.replace(' ', '_')[:30]
            
            # Check for existing HTML and DOCX files
            html_path = os.path.join('motivation_letters', f"motivation_letter_{sanitized_job_title}.html")
            json_path = os.path.join('motivation_letters', f"motivation_letter_{sanitized_job_title}.json")
            docx_path = os.path.join('motivation_letters', f"motivation_letter_{sanitized_job_title}.docx")
            
            if os.path.exists(html_path) and os.path.exists(json_path):
                logger.info(f"Motivation letter already exists for job title: {job_title}")
                
                # Create an operation ID for the existing letter
                operation_id = start_operation('motivation_letter_retrieval')
                
                # Complete the operation immediately
                complete_operation(operation_id, 'completed', 'Existing motivation letter retrieved')
                
                # Read the HTML content
                with open(html_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                # Store the result in the operation status
                operation_status[operation_id]['result'] = {
                    'has_json': True,
                    'motivation_letter_content': html_content,
                    'html_file_path': html_path,
                    'docx_file_path': docx_path if os.path.exists(docx_path) else None,
                    'job_details': job_details,
                    'report_file': report_file
                }
                
                # Redirect to view the existing letter
                flash(f'Existing motivation letter found for job title: {job_title}')
                return redirect(url_for('view_motivation_letter', operation_id=operation_id))
        
        # Start tracking the operation
        operation_id = start_operation('motivation_letter_generation')
        
        # Define a function to run the motivation letter generator in a background thread
        def generate_motivation_letter_task():
            try:
                # Update status
                update_operation_progress(operation_id, 10, 'processing', 'Extracting job details...')
                
                # Generate the motivation letter
                logger.info(f"Calling generate_motivation_letter with cv_filename={cv_filename}, job_url={job_url}")
                result = generate_motivation_letter(cv_filename, job_url)
                
                if not result:
                    logger.error("Failed to generate motivation letter, result is None")
                    complete_operation(operation_id, 'failed', 'Failed to generate motivation letter')
                    return
                
                # Update status
                update_operation_progress(operation_id, 70, 'processing', 'Formatting motivation letter...')
                
                logger.info(f"Successfully generated motivation letter")
                
                # Check if we have JSON data (new format) or HTML (old format)
                has_json = 'motivation_letter_json' in result and 'json_file_path' in result
                
                if has_json:
                    logger.info(f"Generated JSON motivation letter: {result['json_file_path']}")
                    
                    # Update status
                    update_operation_progress(operation_id, 80, 'processing', 'Creating Word document...')
                    
                    # Generate Word document from JSON
                    docx_path = json_to_docx(result['motivation_letter_json'])
                    logger.info(f"Generated Word document: {docx_path}")
                    
                    # Store the docx path in the result
                    result['docx_file_path'] = docx_path
                else:
                    logger.info(f"Generated HTML motivation letter: {result['file_path']}")
                
                # Update status
                update_operation_progress(operation_id, 90, 'processing', 'Getting job details...')
                
                # Get the job details
                job_details = {}
                try:
                    # Extract the job ID from the URL
                    job_id = job_url.split('/')[-1]
                    logger.info(f"Extracted job ID: {job_id}")
                    
                    # Find the job data file
                    job_data_dir = Path('job-data-acquisition/job-data-acquisition/data')
                    logger.info(f"Job data directory: {job_data_dir}")
                    
                    if job_data_dir.exists():
                        # Get the latest job data file
                        job_data_files = list(job_data_dir.glob('job_data_*.json'))
                        logger.info(f"Found {len(job_data_files)} job data files")
                        
                        if job_data_files:
                            latest_job_data_file = max(job_data_files, key=os.path.getctime)
                            logger.info(f"Latest job data file: {latest_job_data_file}")
                            
                            # Load the job data
                            with open(latest_job_data_file, 'r', encoding='utf-8') as f:
                                job_data = json.load(f)
                            
                            # Process the job data based on its structure
                            job_listings = []
                            
                            # Check if the data has a nested structure
                            if isinstance(job_data, list):
                                if len(job_data) > 0:
                                    if isinstance(job_data[0], list):
                                        # It's an array of arrays - flatten it
                                        for job_array in job_data:
                                            job_listings.extend(job_array)
                                        logger.info(f"Found array of arrays structure with {len(job_listings)} total job listings")
                                    elif isinstance(job_data[0], dict) and 'content' in job_data[0]:
                                        # It's the old structure with a 'content' property
                                        job_listings = job_data[0]['content']
                                        logger.info(f"Found old structure with {len(job_listings)} job listings in 'content' array")
                                    else:
                                        # Assume it's a flat array of job listings
                                        job_listings = job_data
                                        logger.info(f"Using flat job data structure with {len(job_listings)} job listings")
                            
                            logger.info(f"Processed job data with {len(job_listings)} total job listings")
                            
                            # Find the job with the matching ID
                            for i, job in enumerate(job_listings):
                                # Extract the job ID from the Application URL
                                job_application_url = job.get('Application URL', '')
                                logger.info(f"Job {i+1} Application URL: {job_application_url}")
                                
                                if job_id in job_application_url:
                                    logger.info(f"Found matching job: {job.get('Job Title', 'N/A')} at {job.get('Company Name', 'N/A')}")
                                    job_details = job
                                    break
                            
                            # If no exact match found, use the first job as a fallback
                            if not job_details and job_listings:
                                logger.info("No exact match found, using first job as fallback")
                                job_details = job_listings[0]
                except Exception as e:
                    logger.error(f'Error getting job details: {str(e)}')
                    import traceback
                    logger.error(traceback.format_exc())
                
                # Complete the operation
                complete_operation(operation_id, 'completed', 'Motivation letter generated successfully')
                
                # Store the result in the operation status for retrieval
                operation_status[operation_id]['result'] = {
                    'has_json': has_json,
                    'motivation_letter_content': result['motivation_letter_html'] if has_json else result['motivation_letter'],
                    'html_file_path': result['html_file_path'] if has_json else result['file_path'],
                    'docx_file_path': result['docx_file_path'] if has_json else None,
                    'job_details': job_details,
                    'report_file': report_file
                }
            except Exception as e:
                logger.error(f'Error in motivation letter generation task: {str(e)}')
                import traceback
                logger.error(traceback.format_exc())
                complete_operation(operation_id, 'failed', f'Error generating motivation letter: {str(e)}')
        
        # Start the background thread
        thread = threading.Thread(target=generate_motivation_letter_task)
        thread.daemon = True
        thread.start()
        
        # Return immediately with the operation ID
        flash(f'Motivation letter generation started. Please wait while the letter is being created. (operation_id={operation_id})')
        return redirect(url_for('view_results', report_file=report_file))
    except Exception as e:
        flash(f'Error generating motivation letter: {str(e)}')
        logger.error(f'Error generating motivation letter: {str(e)}')
        import traceback
        logger.error(traceback.format_exc())
        return redirect(url_for('index'))

@app.route('/download_motivation_letter')
def download_motivation_letter():
    """Download a generated motivation letter (HTML version)"""
    file_path = request.args.get('file_path')
    
    if not file_path:
        flash('No file path provided')
        return redirect(url_for('index'))
    
    try:
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        flash(f'Error downloading motivation letter: {str(e)}')
        logger.error(f'Error downloading motivation letter: {str(e)}')
        return redirect(url_for('index'))

@app.route('/download_motivation_letter_docx')
def download_motivation_letter_docx():
    """Download a generated motivation letter (Word document version)"""
    file_path = request.args.get('file_path')
    
    if not file_path:
        flash('No file path provided')
        return redirect(url_for('index'))
    
    try:
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        flash(f'Error downloading Word document: {str(e)}')
        logger.error(f'Error downloading Word document: {str(e)}')
        return redirect(url_for('index'))

@app.route('/download_docx_from_json')
def download_docx_from_json():
    """Download a Word document version of a motivation letter from its JSON file"""
    json_file_path = request.args.get('json_file_path')
    
    if not json_file_path:
        flash('No JSON file path provided')
        return redirect(url_for('index'))
    
    try:
        # Check if a corresponding .docx file already exists
        docx_file_path = json_file_path.replace('.json', '.docx')
        
        if not os.path.exists(docx_file_path):
            # If the .docx file doesn't exist, generate it from the JSON
            logger.info(f"Generating Word document from JSON file: {json_file_path}")
            docx_file_path = create_word_document_from_json_file(json_file_path)
            
            if not docx_file_path:
                flash('Failed to generate Word document')
                return redirect(url_for('index'))
        
        # Return the .docx file for download
        return send_file(docx_file_path, as_attachment=True)
    except Exception as e:
        flash(f'Error downloading Word document: {str(e)}')
        logger.error(f'Error downloading Word document: {str(e)}')
        import traceback
        logger.error(traceback.format_exc())
        return redirect(url_for('index'))

@app.route('/view_motivation_letter/<operation_id>')
def view_motivation_letter(operation_id):
    """View a generated motivation letter"""
    try:
        # Special case for existing motivation letters
        if operation_id == 'existing':
            # Get parameters from the request
            file_path = request.args.get('file_path')
            report_file = request.args.get('report_file')
            
            if not file_path or not os.path.exists(file_path):
                flash('Motivation letter file not found')
                return redirect(url_for('index'))
            
            # Read the HTML content
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Check for corresponding docx file
            docx_path = file_path.replace('.html', '.docx')
            has_docx = os.path.exists(docx_path)
            
            # Get job details from the filename
            job_title = os.path.basename(file_path).replace('motivation_letter_', '').replace('.html', '')
            
            # Create a simple job details dictionary
            job_details = {
                'Job Title': job_title.replace('_', ' '),
                'Application URL': '#'
            }
            
            # Render the motivation letter template
            return render_template('motivation_letter.html',
                                  motivation_letter=html_content,
                                  file_path=file_path,
                                  has_docx=has_docx,
                                  docx_file_path=docx_path if has_docx else None,
                                  job_details=job_details,
                                  report_file=report_file)
        
        # Regular case for newly generated motivation letters
        if operation_id not in operation_status or 'result' not in operation_status[operation_id]:
            flash('Motivation letter not found')
            return redirect(url_for('index'))
        
        # Get the result from the operation status
        result = operation_status[operation_id]['result']
        
        # Render the motivation letter template with the result data
        return render_template('motivation_letter.html',
                              motivation_letter=result['motivation_letter_content'],
                              file_path=result['html_file_path'],
                              has_docx='docx_file_path' in result and result['docx_file_path'] is not None,
                              docx_file_path=result.get('docx_file_path'),
                              job_details=result['job_details'],
                              report_file=result['report_file'])
    except Exception as e:
        flash(f'Error viewing motivation letter: {str(e)}')
        logger.error(f'Error viewing motivation letter: {str(e)}')
        import traceback
        logger.error(traceback.format_exc())
        return redirect(url_for('index'))

@app.route('/delete_job_data/<job_data_file>')
def delete_job_data(job_data_file):
    """Delete a job data file"""
    try:
        # Construct the full path to the job data file
        job_data_path = os.path.join('job-data-acquisition/job-data-acquisition/data', job_data_file)
        
        # Check if the file exists
        if not os.path.exists(job_data_path):
            flash(f'Job data file not found: {job_data_file}')
            return redirect(url_for('index'))
        
        # Delete the file
        os.remove(job_data_path)
        flash(f'Job data file deleted: {job_data_file}')
    except Exception as e:
        flash(f'Error deleting job data file: {str(e)}')
        logger.error(f'Error deleting job data file: {str(e)}')
    
    return redirect(url_for('index'))

@app.route('/delete_report/<report_file>')
def delete_report(report_file):
    """Delete a job match report file"""
    try:
        # Construct the full path to the report file
        report_path = os.path.join('job_matches', report_file)
        
        # Check if the file exists
        if not os.path.exists(report_path):
            flash(f'Report file not found: {report_file}')
            return redirect(url_for('index'))
        
        # Delete the markdown file
        os.remove(report_path)
        
        # Also delete the corresponding JSON file if it exists
        json_file = report_file.replace('.md', '.json')
        json_path = os.path.join('job_matches', json_file)
        if os.path.exists(json_path):
            os.remove(json_path)
            
        flash(f'Report file deleted: {report_file}')
    except Exception as e:
        flash(f'Error deleting report file: {str(e)}')
        logger.error(f'Error deleting report file: {str(e)}')
    
    return redirect(url_for('index'))

@app.route('/run_combined_process', methods=['POST'])
def run_combined_process():
    """Run both job data acquisition and job matcher in one go"""
    try:
        # Get parameters from the form
        cv_path = request.form.get('cv_path')
        max_pages = int(request.form.get('max_pages', 50))
        min_score = int(request.form.get('min_score', 3))
        max_jobs = int(request.form.get('max_jobs', 50))
        max_results = int(request.form.get('max_results', 10))
        
        if not cv_path:
            flash('No CV selected')
            return redirect(url_for('index'))
        
        # Construct the full path to the CV
        full_cv_path = os.path.join('process_cv/cv-data', cv_path)
        
        # Start tracking the operation
        operation_id = start_operation('combined_process')
        
        # Define a function to run the combined process in a background thread
        def run_combined_process_task():
            try:
                # Update status
                update_operation_progress(operation_id, 5, 'processing', 'Updating settings...')
                
                # Step 1: Update the settings.json file with the max_pages parameter
                settings_path = os.path.join(os.path.dirname(__file__), 'job-data-acquisition', 'settings.json')
                
                # Read the current settings
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                # Update the max_pages parameter
                settings['scraper']['max_pages'] = max_pages
                
                # Write the updated settings back to the file
                with open(settings_path, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, indent=4, ensure_ascii=False)
                
                # Update status
                update_operation_progress(operation_id, 10, 'processing', 'Starting job scraper...')
                
                # Step 2: Run the job scraper
                import importlib.util
                app_path = os.path.join(os.path.dirname(__file__), 'job-data-acquisition', 'app.py')
                spec = importlib.util.spec_from_file_location("app_module", app_path)
                app_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(app_module)
                
                # Run the scraper
                output_file = app_module.run_scraper()
                
                if output_file is None:
                    complete_operation(operation_id, 'failed', 'Job data acquisition failed. Check the logs for details.')
                    return
                
                # Update status
                update_operation_progress(operation_id, 60, 'processing', 'Job data acquisition completed. Starting job matcher...')
                
                # Step 3: Run the job matcher with the newly acquired data
                matches = match_jobs_with_cv(full_cv_path, min_score=min_score, max_jobs=max_jobs, max_results=max_results)
                
                if not matches:
                    complete_operation(operation_id, 'completed', 'No job matches found')
                    return
                
                # Update status
                update_operation_progress(operation_id, 90, 'processing', 'Generating report...')
                
                # Step 4: Generate report
                report_file = generate_report(matches)
                
                # Complete the operation
                complete_operation(operation_id, 'completed', f'Combined process completed. Results saved to: {report_file}')
                
                # Store the report file in the operation status for retrieval
                operation_status[operation_id]['report_file'] = os.path.basename(report_file)
            except Exception as e:
                logger.error(f'Error in combined process task: {str(e)}')
                import traceback
                logger.error(traceback.format_exc())
                complete_operation(operation_id, 'failed', f'Error running combined process: {str(e)}')
        
        # Start the background thread
        thread = threading.Thread(target=run_combined_process_task)
        thread.daemon = True
        thread.start()
        
        # Return immediately with the operation ID
        flash(f'Combined process started. Please wait while the job listings are being scraped and matched. (operation_id={operation_id})')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'Error running combined process: {str(e)}')
        logger.error(f'Error running combined process: {str(e)}')
        import traceback
        logger.error(traceback.format_exc())
        return redirect(url_for('index'))

@app.route('/delete_cv/<cv_file>')
def delete_cv(cv_file):
    """Delete a CV file"""
    try:
        # Determine if the CV is in the input directory or directly in cv-data
        cv_path_input = os.path.join('process_cv/cv-data/input', cv_file)
        cv_path_direct = os.path.join('process_cv/cv-data', cv_file)
        
        cv_path = None
        if os.path.exists(cv_path_input):
            cv_path = cv_path_input
        elif os.path.exists(cv_path_direct):
            cv_path = cv_path_direct
        
        if not cv_path:
            flash(f'CV file not found: {cv_file}')
            return redirect(url_for('index'))
        
        # Delete the CV file
        os.remove(cv_path)
        
        # Also delete the corresponding summary file if it exists
        base_filename = os.path.basename(cv_file)
        summary_filename = os.path.splitext(base_filename)[0] + '_summary.txt'
        summary_path = os.path.join('process_cv/cv-data/processed', summary_filename)
        
        if os.path.exists(summary_path):
            os.remove(summary_path)
            
        flash(f'CV file deleted: {cv_file}')
    except Exception as e:
        flash(f'Error deleting CV file: {str(e)}')
        logger.error(f'Error deleting CV file: {str(e)}')
    
    return redirect(url_for('index'))

@app.route('/view_cv_summary/<cv_file>')
def view_cv_summary(cv_file):
    """View a CV summary"""
    # Get the summary file path - ensure we're using just the basename
    base_filename = os.path.basename(cv_file)
    summary_filename = os.path.splitext(base_filename)[0] + '_summary.txt'
    summary_path = os.path.join('process_cv/cv-data/processed', summary_filename)
    
    try:
        # Check if the summary file exists
        if not os.path.exists(summary_path):
            # Process the CV to generate a summary
            # Determine if the CV is in the input directory or directly in cv-data
            cv_path_input = os.path.join('process_cv/cv-data/input', cv_file)
            cv_path_direct = os.path.join('process_cv/cv-data', cv_file)
            
            if os.path.exists(cv_path_input):
                cv_path = cv_path_input
            elif os.path.exists(cv_path_direct):
                cv_path = cv_path_direct
            else:
                return jsonify({'error': f'CV file not found: {cv_file}'})
                
            cv_text = extract_cv_text(cv_path)
            cv_summary = summarize_cv(cv_text)
            
            # Save the processed CV summary
            processed_dir = 'process_cv/cv-data/processed'
            os.makedirs(processed_dir, exist_ok=True)
            
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(cv_summary)
        
        # Load the CV summary
        with open(summary_path, 'r', encoding='utf-8') as f:
            summary = f.read()
        
        return jsonify({'summary': summary})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/delete_files', methods=['POST'])
def delete_files():
    """Handle bulk deletion of files"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Invalid request format'}), 400

    file_type = data.get('file_type')
    filenames = data.get('filenames')

    if not file_type or not filenames or not isinstance(filenames, list):
        return jsonify({'success': False, 'message': 'Missing file_type or filenames'}), 400

    deleted_count = 0
    failed_count = 0
    failed_files = []
    base_dir = ''

    try:
        if file_type == 'job_data':
            base_dir = Path('job-data-acquisition/job-data-acquisition/data')
            for filename in filenames:
                file_path = base_dir / secure_filename(filename)
                try:
                    if file_path.is_file():
                        os.remove(file_path)
                        deleted_count += 1
                        logger.info(f"Deleted job data file: {file_path}")
                    else:
                        raise FileNotFoundError(f"File not found: {file_path}")
                except Exception as e:
                    logger.error(f"Error deleting job data file {filename}: {str(e)}")
                    failed_count += 1
                    failed_files.append(filename)

        elif file_type == 'report':
            base_dir = Path('job_matches')
            for filename in filenames:
                # Delete MD file
                md_path = base_dir / secure_filename(filename)
                json_path = base_dir / secure_filename(filename.replace('.md', '.json'))
                deleted_md = False
                deleted_json = False
                try:
                    if md_path.is_file():
                        os.remove(md_path)
                        deleted_md = True
                        logger.info(f"Deleted report file: {md_path}")
                    # Delete corresponding JSON file
                    if json_path.is_file():
                        os.remove(json_path)
                        deleted_json = True
                        logger.info(f"Deleted corresponding JSON report file: {json_path}")

                    if deleted_md or deleted_json: # Count as one deletion if either file was removed
                         deleted_count += 1
                    elif not md_path.is_file() and not json_path.is_file():
                         # If neither file existed, maybe log it but don't count as failure?
                         logger.warning(f"Report files already deleted or never existed: {filename}")
                         # Optionally count as success if goal is just absence: deleted_count += 1
                    else:
                         # This case shouldn't happen if is_file checks passed, but as safety
                         raise FileNotFoundError(f"Report files not found: {filename}")

                except Exception as e:
                    logger.error(f"Error deleting report file {filename}: {str(e)}")
                    failed_count += 1
                    failed_files.append(filename)

        elif file_type == 'cv':
            processed_dir = Path('process_cv/cv-data/processed')
            input_dir = Path('process_cv/cv-data/input')
            direct_dir = Path('process_cv/cv-data')

            for filename in filenames:
                # Filename might contain subdirs like 'input/cv.pdf' or just 'cv.pdf'
                secure_name = secure_filename(filename) # Basic sanitization
                relative_path = Path(filename) # Keep original structure for path finding

                cv_path_input = input_dir / relative_path
                cv_path_direct = direct_dir / relative_path

                cv_path_to_delete = None
                if cv_path_input.is_file():
                    cv_path_to_delete = cv_path_input
                elif cv_path_direct.is_file():
                     # Check it's not the input or processed dir itself
                    if relative_path.name != 'input' and relative_path.name != 'processed':
                        cv_path_to_delete = cv_path_direct

                deleted_cv = False
                deleted_summary = False
                try:
                    if cv_path_to_delete:
                        os.remove(cv_path_to_delete)
                        deleted_cv = True
                        logger.info(f"Deleted CV file: {cv_path_to_delete}")

                        # Delete corresponding summary file
                        base_filename = cv_path_to_delete.stem # Name without extension
                        summary_filename = f"{base_filename}_summary.txt"
                        summary_path = processed_dir / summary_filename
                        if summary_path.is_file():
                            os.remove(summary_path)
                            deleted_summary = True
                            logger.info(f"Deleted corresponding summary file: {summary_path}")

                        deleted_count += 1
                    else:
                         logger.warning(f"CV file not found for deletion: {filename}")
                         # Decide if not found is a failure or just skipped
                         # failed_count += 1
                         # failed_files.append(filename)

                except Exception as e:
                    logger.error(f"Error deleting CV file {filename}: {str(e)}")
                    failed_count += 1
                    failed_files.append(filename)
        else:
            return jsonify({'success': False, 'message': f'Invalid file_type: {file_type}'}), 400

        return jsonify({
            'success': failed_count == 0,
            'message': f'Deleted {deleted_count} files. Failed to delete {failed_count} files.',
            'deleted_count': deleted_count,
            'failed_count': failed_count,
            'failed_files': failed_files
        })

    except Exception as e:
        logger.error(f"Error during bulk delete for type {file_type}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': f'An unexpected error occurred: {str(e)}'}), 500

@app.route('/view_job_data/<filename>')
def view_job_data(filename):
    """Display the contents of a specific job data JSON file."""
    try:
        # Secure the filename and construct the path
        secure_name = secure_filename(filename)
        file_path = Path('job-data-acquisition/job-data-acquisition/data') / secure_name

        if not file_path.is_file():
            flash(f'Job data file not found: {secure_name}')
            logger.error(f"Job data file not found: {file_path}")
            return redirect(url_for('index'))

        # Load the job data
        with open(file_path, 'r', encoding='utf-8') as f:
            job_data = json.load(f)

        # Process the job data based on its structure to get a flat list
        job_listings = []
        if isinstance(job_data, list):
            if len(job_data) > 0:
                if isinstance(job_data[0], list):
                    # Flatten array of arrays
                    for job_array in job_data:
                        job_listings.extend(job_array)
                    logger.info(f"Loaded array of arrays structure with {len(job_listings)} jobs from {secure_name}")
                elif isinstance(job_data[0], dict) and 'content' in job_data[0]:
                    # Old structure with 'content' property
                    job_listings = job_data[0]['content']
                    logger.info(f"Loaded old structure with {len(job_listings)} jobs from {secure_name}")
                else:
                    # Assume flat array of job listings
                    job_listings = job_data
                    logger.info(f"Loaded flat job data structure with {len(job_listings)} jobs from {secure_name}")
        else:
             logger.warning(f"Unexpected job data structure in {secure_name}: {type(job_data)}")

        # Render the new template
        return render_template('job_data_view.html', jobs=job_listings, filename=secure_name)

    except FileNotFoundError:
        flash(f'Job data file not found: {filename}')
        logger.error(f"FileNotFoundError for job data file: {filename}")
        return redirect(url_for('index'))
    except json.JSONDecodeError:
        flash(f'Error decoding JSON from file: {filename}')
        logger.error(f"JSONDecodeError for job data file: {filename}")
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'An error occurred while viewing job data: {str(e)}')
        logger.error(f'Error in view_job_data for {filename}: {str(e)}')
        import traceback
        logger.error(traceback.format_exc())
        return redirect(url_for('index'))

@app.route('/generate_multiple_letters', methods=['POST'])
def generate_multiple_letters():
    """Generate motivation letters for multiple selected jobs"""
    data = request.get_json()
    if not data:
        logger.error("Invalid request format for /generate_multiple_letters")
        return jsonify({'error': 'Invalid request format'}), 400

    job_urls = data.get('job_urls')
    cv_base_name = data.get('cv_filename') # Get CV filename directly from request

    if not job_urls or not isinstance(job_urls, list) or not cv_base_name:
        logger.error(f"Missing job_urls or cv_filename in request: {data}")
        return jsonify({'error': 'Missing job_urls or cv_filename'}), 400

    logger.info(f"Received request to generate letters for CV: {cv_base_name}")

    # Check if the corresponding CV summary exists (as generate_motivation_letter needs it)
    summary_path = Path('process_cv/cv-data/processed') / f"{cv_base_name}_summary.txt"
    if not summary_path.exists():
        logger.error(f"Required CV summary file not found: {summary_path}")
        return jsonify({'error': f'Required CV summary file not found for {cv_base_name}'}), 400

    success_count = 0
    errors = [] # Store failed job_urls

    for job_url in job_urls:
        # Skip invalid or placeholder URLs
        if not job_url or job_url == 'N/A' or not job_url.startswith('http'):
            logger.warning(f"Skipping invalid job URL: {job_url}")
            errors.append(job_url) # Count invalid URL as an error
            continue

        try:
            logger.info(f"Generating letter for CV '{cv_base_name}' and URL '{job_url}'")
            # Call the main function from motivation_letter_generator
            # It handles saving files and returns a result dict (or None on failure)
            result = generate_motivation_letter(cv_base_name, job_url)

            if result:
                logger.info(f"Successfully generated letter for URL: {job_url}")
                success_count += 1
                # Generate DOCX if JSON was produced
                if 'motivation_letter_json' in result and 'json_file_path' in result:
                     try:
                         docx_path = json_to_docx(result['motivation_letter_json'], output_path=result['json_file_path'].replace('.json', '.docx'))
                         if docx_path:
                             logger.info(f"Generated Word document: {docx_path} for URL: {job_url}")
                         else:
                             logger.warning(f"Failed to generate Word document (json_to_docx returned None) for URL: {job_url}")
                     except Exception as docx_e:
                         logger.error(f"Exception generating Word document for URL {job_url}: {str(docx_e)}")
                         # Don't add to errors list here, as the main letter generation succeeded
            else:
                # generate_motivation_letter returned None, indicating failure
                logger.error(f"Failed to generate letter (generate_motivation_letter returned None) for URL: {job_url}")
                errors.append(job_url)
        except Exception as e:
            logger.error(f"Exception generating letter for URL {job_url}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            errors.append(job_url)

    logger.info(f"Multiple letter generation complete. Success: {success_count}, Failures: {len(errors)}")
    return jsonify({
        'success_count': success_count,
        'errors': errors # List of URLs that failed
    })


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)

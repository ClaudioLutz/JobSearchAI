import os
import json
import logging
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from werkzeug.utils import secure_filename

# Add the current directory to the Python path to find modules
import sys
sys.path.append('.')

# Import from existing modules
from process_cv.cv_processor import extract_cv_text, summarize_cv
from job_matcher import match_jobs_with_cv, generate_report, load_latest_job_data

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

# Configure upload folder
UPLOAD_FOLDER = 'process_cv/cv-data/input'
ALLOWED_EXTENSIONS = {'pdf', 'docx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
            
            summary_filename = os.path.splitext(filename)[0] + '_summary.txt'
            summary_path = os.path.join(processed_dir, summary_filename)
            
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write(cv_summary)
                
            flash(f'CV processed successfully. Summary saved to: {summary_path}')
        except Exception as e:
            flash(f'Error processing CV: {str(e)}')
            logger.error(f'Error processing CV: {str(e)}')
    else:
        flash('Invalid file type. Only PDF and DOCX files are allowed.')
    
    return redirect(url_for('index'))

@app.route('/run_job_matcher', methods=['POST'])
def run_job_matcher():
    """Run the job matcher with the selected CV"""
    cv_path = request.form.get('cv_path')
    min_score = int(request.form.get('min_score', 3))
    max_results = int(request.form.get('max_results', 10))
    
    if not cv_path:
        flash('No CV selected')
        return redirect(url_for('index'))
    
    # Construct the full path to the CV
    full_cv_path = os.path.join('process_cv/cv-data', cv_path)
    
    try:
        # Match jobs with CV
        matches = match_jobs_with_cv(full_cv_path, min_score=min_score, max_results=max_results)
        
        if not matches:
            flash('No job matches found')
            return redirect(url_for('index'))
        
        # Generate report
        report_file = generate_report(matches)
        
        flash(f'Job matching completed. Results saved to: {report_file}')
        
        # Redirect to results page
        return redirect(url_for('view_results', report_file=os.path.basename(report_file)))
    except Exception as e:
        flash(f'Error running job matcher: {str(e)}')
        logger.error(f'Error running job matcher: {str(e)}')
        return redirect(url_for('index'))

@app.route('/run_job_scraper', methods=['POST'])
def run_job_scraper():
    """Run the job data acquisition component"""
    try:
        # Import the job scraper module
        sys.path.append('job-data-acquisition')
        from app import run_scraper
        
        # Run the scraper
        output_file = run_scraper()
        
        flash(f'Job data acquisition completed. Data saved to: {output_file}')
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
        
        return render_template('results.html', matches=matches, report_file=report_file)
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

@app.route('/view_cv_summary/<cv_file>')
def view_cv_summary(cv_file):
    """View a CV summary"""
    # Get the summary file path
    summary_filename = os.path.splitext(cv_file)[0] + '_summary.txt'
    summary_path = os.path.join('process_cv/cv-data/processed', summary_filename)
    
    try:
        # Check if the summary file exists
        if not os.path.exists(summary_path):
            # Process the CV to generate a summary
            cv_path = os.path.join('process_cv/cv-data', cv_file)
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

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)

import os
import json
import threading
import urllib.parse
import importlib.util
from pathlib import Path
from datetime import datetime
from flask import (
    Blueprint, request, redirect, url_for, flash, render_template,
    send_file, jsonify, current_app
)
from flask_login import login_required
from werkzeug.utils import secure_filename

# Add project root to path to find modules
import sys
sys.path.append('.')

# Import necessary functions from other modules
from job_matcher import match_jobs_with_cv, generate_report
from utils.decorators import admin_required

# Set up logging using centralized configuration
from utils.logging_config import get_logger
logger = get_logger("dashboard.job_matching")

job_matching_bp = Blueprint('job_matching', __name__, url_prefix='/job_matching')

# Placeholder for get_job_details_for_url if it's moved/shared
# This function is complex and might be better in a dedicated 'utils' or 'helpers' module
# For now, assume it might be attached to current_app or imported from its final location.
def get_job_details_for_url(job_url):
    """Placeholder: Get job details for a URL from the latest job data file"""
    # This function needs access to the job data directory and logic from the original dashboard.
    # It should ideally be refactored into a shared utility.
    # For now, we'll try accessing it via current_app if attached there, or raise NotImplementedError.
    if hasattr(current_app, 'get_job_details_for_url'):
        return current_app.get_job_details_for_url(job_url)
    else:
        # Fallback or raise error - depends on where the function ends up
        logger.warning("get_job_details_for_url not found on current_app, using basic implementation.")
        # Basic implementation attempt (might fail depending on context)
        job_details = {}
        try:
            job_id = job_url.split('/')[-1]
            # Use getattr for safer access to current_app properties in fallback
            root_path = getattr(current_app, 'root_path', '.')
            job_data_dir = Path(root_path) / 'job-data-acquisition/job-data-acquisition/data'
            if job_data_dir.exists():
                job_data_files = list(job_data_dir.glob('job_data_*.json'))
                if job_data_files:
                    latest_job_data_file = max(job_data_files, key=os.path.getctime)
                    with open(latest_job_data_file, 'r', encoding='utf-8') as f:
                        job_data = json.load(f)
                    job_listings = []
                    if isinstance(job_data, list):
                         if len(job_data) > 0:
                            if isinstance(job_data[0], list):
                                for job_array in job_data: job_listings.extend(job_array)
                            elif isinstance(job_data[0], dict) and 'content' in job_data[0]:
                                job_listings = job_data[0]['content']
                            else: job_listings = job_data
                    for job in job_listings:
                        job_application_url = job.get('Application URL', '')
                        if job_id in job_application_url:
                            job_details = job
                            break
                    if not job_details and job_listings: job_details = job_listings[0]
        except Exception as e:
            logger.error(f'Error in fallback get_job_details_for_url: {str(e)}')
        return job_details
        # raise NotImplementedError("get_job_details_for_url needs to be provided or refactored.")


@job_matching_bp.route('/run_matcher', methods=['POST'])
@login_required
@admin_required
def run_job_matcher():
    """Run the job matcher with the selected CV
    
    DEPRECATED: This route is deprecated as of Story 4.1.
    Please use the Run Combined Process workflow instead.
    This route is maintained for backward compatibility only.
    """
    # Log deprecation warning
    logger.warning("DEPRECATED: /job_matching/run_matcher route accessed. Please use /job_matching/run_combined_process instead.")
    flash('Note: This endpoint is deprecated. Please use "Run Combined Process" for the complete workflow.', 'warning')
    
    cv_path_rel = request.form.get('cv_path') # This is the relative path from the form
    max_jobs = int(request.form.get('max_jobs', 50))

    if not cv_path_rel:
        flash('No CV selected')
        return redirect(url_for('index'))

    # Construct the full path to the CV relative to the app root
    full_cv_path = os.path.join(current_app.root_path, 'process_cv/cv-data', cv_path_rel)

    if not os.path.exists(full_cv_path):
         flash(f'CV file not found at expected location: {full_cv_path}')
         logger.error(f"CV file not found for matching: {full_cv_path} (relative path was {cv_path_rel})")
         return redirect(url_for('index'))

    try:
        # Access operation tracking functions
        start_operation = current_app.extensions['start_operation']
        update_operation_progress = current_app.extensions['update_operation_progress']
        complete_operation = current_app.extensions['complete_operation']
        app_instance = current_app._get_current_object() # Get app instance for context

        # Start tracking the operation
        operation_id = start_operation('job_matching')

        # Define a function to run the job matcher in a background thread
        def run_job_matcher_task(app, op_id, cv_full_path_task, cv_path_rel_task, max_jobs_task):
             with app.app_context(): # Establish app context for the thread
                try:
                    # Update status
                    update_operation_progress(op_id, 10, 'processing', 'Loading job data...')

                    # Match jobs with CV - ALL matches saved to database
                    matches = match_jobs_with_cv(cv_full_path_task, max_jobs=max_jobs_task)

                    if not matches:
                        update_operation_progress(op_id, 100, 'completed', 'No job matches found')
                        return

                    # Update status
                    update_operation_progress(op_id, 80, 'processing', 'Adding CV path to matches and generating report...')

                    # Add cv_path (relative path is fine here for identification) to each match dictionary before saving
                    for match in matches:
                        match['cv_path'] = cv_path_rel_task # Store the relative path used for matching identification

                    # Generate report (which now includes cv_path in the saved JSON)
                    report_file_path = generate_report(matches) # Returns full path
                    report_filename = os.path.basename(report_file_path)

                    # Complete the operation
                    complete_operation(op_id, 'completed', f'Job matching completed. Results saved to: {report_filename}')
                except Exception as e:
                    logger.error(f'Error in job matcher task: {str(e)}', exc_info=True)
                    complete_operation(op_id, 'failed', f'Error running job matcher: {str(e)}')

        # Start the background thread, passing app instance and args
        thread_args = (app_instance, operation_id, full_cv_path, cv_path_rel, max_jobs)
        thread = threading.Thread(target=run_job_matcher_task, args=thread_args)
        thread.daemon = True
        thread.start()

        # Return immediately with the operation ID
        flash(f'Job matcher started. Please wait while the results are being processed. (operation_id={operation_id})')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'Error running job matcher: {str(e)}')
        logger.error(f'Error running job matcher: {str(e)}', exc_info=True)
        return redirect(url_for('index'))

@job_matching_bp.route('/run_combined_process', methods=['POST'])
@login_required
@admin_required
def run_combined_process():
    """Run both job data acquisition and job matcher in one go"""
    try:
        # Get parameters from the form
        cv_path_rel = request.form.get('cv_path')
        search_term = request.form.get('search_term')
        max_pages = int(request.form.get('max_pages', 50))
        max_jobs = int(request.form.get('max_jobs', 50))

        if not cv_path_rel:
            flash('No CV selected')
            return redirect(url_for('index'))
        
        if not search_term:
            flash('Search term is required')
            return redirect(url_for('index'))

        # Construct the full path to the CV
        full_cv_path = os.path.join(current_app.root_path, 'process_cv/cv-data', cv_path_rel)

        if not os.path.exists(full_cv_path):
             flash(f'CV file not found at expected location: {full_cv_path}')
             logger.error(f"CV file not found for combined process: {full_cv_path} (relative path was {cv_path_rel})")
             return redirect(url_for('index'))

        # Access operation tracking functions
        start_operation = current_app.extensions['start_operation']
        update_operation_progress = current_app.extensions['update_operation_progress']
        complete_operation = current_app.extensions['complete_operation']
        # operation_status = current_app.extensions['operation_status'] # Access via app.extensions inside task
        app_instance = current_app._get_current_object() # Get app instance for context

        # Start tracking the operation
        operation_id = start_operation('combined_process')

        # Define a function to run the combined process in a background thread
        # Pass necessary variables and app instance
        def run_combined_process_task(app, op_id, cv_full_path_task, cv_path_rel_task, search_term_task, max_pages_task, max_jobs_task):
            with app.app_context(): # Establish app context for the thread
                try:
                    # Access operation status via app extensions now that context exists
                    operation_status_ctx = app.extensions['operation_status']

                    # Update status (use op_id passed to function)
                    update_operation_progress(op_id, 5, 'processing', 'Updating settings...')

                    # Step 1: Update the settings.json file with the search_term and max_pages parameters
                    settings_path = os.path.join(app.root_path, 'job-data-acquisition', 'settings.json') # Use app.root_path
                    try:
                        with open(settings_path, 'r', encoding='utf-8') as f: settings = json.load(f)
                        
                        # Update max_pages
                        settings['scraper']['max_pages'] = max_pages_task # Use passed variable
                        
                        # Update search terms - make selected term the first/primary term
                        if 'search_terms' not in settings:
                            settings['search_terms'] = []
                        
                        # Remove the selected term from its current position (if it exists)
                        search_terms_list = settings['search_terms']
                        if search_term_task in search_terms_list:
                            search_terms_list.remove(search_term_task)
                        
                        # Insert the selected term at the beginning (primary position)
                        search_terms_list.insert(0, search_term_task)
                        settings['search_terms'] = search_terms_list
                        
                        with open(settings_path, 'w', encoding='utf-8') as f: json.dump(settings, f, indent=4, ensure_ascii=False)
                        logger.info(f"Updated settings with search term '{search_term_task}' as primary term")
                    except Exception as settings_e:
                        logger.error(f"Error updating settings for combined run: {settings_e}")
                        complete_operation(op_id, 'failed', f'Error updating scraper settings: {settings_e}')
                        return

                    # Update status
                    update_operation_progress(op_id, 10, 'processing', 'Starting job scraper with deduplication...')

                    # Step 2: Run the job scraper WITH DEDUPLICATION
                    new_jobs = None
                    try:
                        app_path = os.path.join(app.root_path, 'job-data-acquisition', 'app.py') # Use app.root_path
                        if not os.path.exists(app_path):
                             raise FileNotFoundError(f"Scraper app.py not found at {app_path}")
                        spec = importlib.util.spec_from_file_location("app_module", app_path)
                        app_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(app_module)
                        
                        # Get deduplicated scraper function
                        run_scraper_dedup = getattr(app_module, 'run_scraper_with_deduplication', None)
                        
                        if not run_scraper_dedup:
                            raise ModuleNotFoundError(
                                "run_scraper_with_deduplication not found in job-data-acquisition/app.py. "
                                "This function is required for database-backed deduplication."
                            )
                        
                        # Call with explicit parameters (solves search term and deduplication issues)
                        logger.info(f"Running scraper with deduplication for term: {search_term_task}")
                        new_jobs = run_scraper_dedup(
                            search_term=search_term_task,  # ✅ Explicit parameter
                            cv_path=cv_full_path_task,     # ✅ For CV key generation
                            max_pages=max_pages_task       # ✅ Configurable limit
                        )
                        
                    except Exception as scraper_e:
                         logger.error(f"Error running scraper in combined process: {scraper_e}", exc_info=True)
                         complete_operation(op_id, 'failed', f'Job data acquisition failed: {scraper_e}')
                         return

                    if new_jobs is None:
                        complete_operation(op_id, 'failed', 'Job data acquisition failed (no new jobs returned). Check logs.')
                        return
                    
                    if len(new_jobs) == 0:
                        complete_operation(op_id, 'completed', 'No new jobs found (all duplicates or no results)')
                        return
                    
                    logger.info(f"Found {len(new_jobs)} new jobs after deduplication")

                    # Update status
                    update_operation_progress(op_id, 60, 'processing', f'Evaluating and matching {len(new_jobs)} new jobs...')
                    
                    # Evaluate new jobs with CV and save matches to database
                    from job_matcher import evaluate_and_save_matches
                    
                    try:
                        matched_count = evaluate_and_save_matches(cv_full_path_task, new_jobs, search_term_task)
                        logger.info(f"Successfully evaluated and saved {matched_count}/{len(new_jobs)} new jobs")
                        
                    except Exception as match_e:
                        logger.error(f"Error in job matching: {match_e}", exc_info=True)
                        complete_operation(op_id, 'failed', f'Failed to match jobs: {match_e}')
                        return

                    # Update status
                    update_operation_progress(op_id, 80, 'processing', 'Reading all matches from database...')

                    # Step 3: Read all matches from database (including newly evaluated ones)
                    from utils.db_utils import JobMatchDatabase
                    from utils.cv_utils import generate_cv_key
                    
                    try:
                        # Generate CV key for querying
                        cv_key = generate_cv_key(cv_full_path_task)
                        
                        db = JobMatchDatabase()
                        db.connect()
                        
                        # Get ALL jobs from database for this CV and search term (both new and existing)
                        # This query returns all jobs, not just the ones from this scrape
                        cursor = db.conn.cursor()
                        cursor.execute("""
                            SELECT job_url, job_title, company_name, location, overall_match,
                                   skills_match, experience_match, education_fit,
                                   career_trajectory_alignment, preference_match,
                                   potential_satisfaction, location_compatibility, reasoning,
                                   scraped_data
                            FROM job_matches
                            WHERE cv_key = ? AND search_term = ?
                            ORDER BY overall_match DESC
                        """, (cv_key, search_term_task))
                        
                        rows = cursor.fetchall()
                        db.close()
                        
                        if not rows:
                            complete_operation(op_id, 'completed', f'No jobs found in database for CV key {cv_key[:8]}... and search term {search_term_task}')
                            return
                        
                        logger.info(f"Retrieved {len(rows)} total job matches from database")
                        
                        # Convert database rows to match format for report generation
                        matches = []
                        for row in rows:
                            # Parse scraped_data JSON if it exists
                            scraped_data = {}
                            try:
                                if row[13]:  # scraped_data column
                                    scraped_data = json.loads(row[13])
                            except (json.JSONDecodeError, TypeError):
                                logger.warning(f"Failed to parse scraped_data for {row[1]}")
                            
                            match = {
                                'application_url': row[0],
                                'job_title': row[1],
                                'company_name': row[2],
                                'location': row[3],
                                'overall_match': row[4],
                                'skills_match': row[5],
                                'experience_match': row[6],
                                'education_fit': row[7],
                                'career_trajectory_alignment': row[8],
                                'preference_match': row[9],
                                'potential_satisfaction': row[10],
                                'location_compatibility': row[11],
                                'reasoning': row[12],
                                'job_description': scraped_data.get('Job Description', 'N/A'),
                                'cv_path': cv_path_rel_task
                            }
                            matches.append(match)
                        
                    except Exception as db_read_e:
                        logger.error(f"Error reading from database: {db_read_e}", exc_info=True)
                        complete_operation(op_id, 'failed', f'Failed to read jobs from database: {db_read_e}')
                        return

                    # Update status
                    update_operation_progress(op_id, 90, 'processing', 'Generating backward-compatible file report...')

                    # Step 4: Generate report (BACKWARD COMPATIBILITY - for file-based workflows)
                    report_file_path = generate_report(matches)
                    report_filename = os.path.basename(report_file_path)

                    # Complete the operation
                    complete_operation(op_id, 'completed', 
                        f'Combined process completed. {len(matches)} matches available in database. File report: {report_filename}')

                    # Store the report file in the operation status for retrieval (if needed elsewhere)
                    if op_id in operation_status_ctx:
                        operation_status_ctx[op_id]['report_file'] = report_filename

                except Exception as e:
                    logger.error(f'Error in combined process task: {str(e)}', exc_info=True)
                    complete_operation(op_id, 'failed', f'Error running combined process: {str(e)}')

        # Start the background thread, passing necessary arguments including app instance
        thread_args = (app_instance, operation_id, full_cv_path, cv_path_rel, search_term, max_pages, max_jobs)
        thread = threading.Thread(target=run_combined_process_task, args=thread_args)
        thread.daemon = True
        thread.start()

        # Return immediately with the operation ID
        flash(f'Combined process started. Please wait. (operation_id={operation_id})')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'Error running combined process: {str(e)}')
        logger.error(f'Error running combined process: {str(e)}', exc_info=True)
        return redirect(url_for('index'))


@job_matching_bp.route('/view_results/<report_file>')
@login_required
def view_results(report_file):
    """View job match results"""
    # Secure the report filename
    secure_report_file = secure_filename(report_file)
    report_dir = Path(current_app.root_path) / 'job_matches'
    json_file = secure_report_file.replace('.md', '.json')
    json_path = report_dir / json_file

    try:
        # Get list of available CV summary base names
        processed_cv_dir = Path(current_app.root_path) / 'process_cv/cv-data/processed'
        available_cvs = []
        if processed_cv_dir.exists():
            available_cvs = sorted(
                p.stem.replace('_summary', '')
                for p in processed_cv_dir.glob('*_summary.txt')
            )
        logger.info(f"Available CVs for dropdown: {available_cvs}")

        # Load the job matches from the JSON file
        if not json_path.is_file():
            flash(f"Report JSON file not found: {json_file}")
            logger.error(f"Report JSON file not found: {json_path}")
            return redirect(url_for('index'))

        with open(json_path, 'r', encoding='utf-8') as f:
            matches = json.load(f)

        # Determine associated CV filename from the 'cv_path' stored in matches
        associated_cv_filename = None
        if matches and isinstance(matches, list) and matches[0] and 'cv_path' in matches[0]:
            try:
                # Extract the base name from the stored relative path
                potential = Path(matches[0]['cv_path']).stem
                if potential in available_cvs:
                    associated_cv_filename = potential
                    logger.info(f"Associated CV '{potential}' for report {json_file}")
                else:
                    logger.warning(f"CV base name '{potential}' from report {json_file} not found in available summaries {available_cvs}")
            except Exception as path_e:
                logger.error(f"Error extracting cv_path base name from report {json_file}: {path_e}")

        if not associated_cv_filename:
            logger.warning(f"Could not determine associated CV for report {json_file}")

        # --- Check for generated files for each match ---
        letters_dir = Path(current_app.root_path) / 'motivation_letters'
        existing_scraped = list(letters_dir.glob('*_scraped_data.json'))

        # Get all motivation letter HTML, JSON, and DOCX files for direct checking
        all_html_files = list(letters_dir.glob('motivation_letter_*.html'))
        all_json_files = list(letters_dir.glob('motivation_letter_*.json'))
        all_docx_files = list(letters_dir.glob('motivation_letter_*.docx'))

        logger.info(f"Checking for generated files: {len(existing_scraped)} scraped, {len(all_html_files)} HTML, {len(all_json_files)} JSON, {len(all_docx_files)} DOCX")

        for match in matches:
            # Normalize match_app_url (assuming 'application_url' is the key)
            match_app_url = match.get('application_url')
            if match_app_url and match_app_url != 'N/A':
                if match_app_url.startswith('/'):
                    # Assuming base URL for relative paths if needed
                    base_url = "https://www.ostjob.ch/" # Consider making this configurable
                    match_app_url = urllib.parse.urljoin(base_url, match_app_url.lstrip('/'))
            else:
                match_app_url = None

            # Initialize flags
            match.update({
                'has_motivation_letter': False,
                'motivation_letter_html_path': None, # Store relative path for URL generation
                'motivation_letter_json_path': None, # Store relative path
                'motivation_letter_docx_path': None, # Store relative path
                'has_email_text': False, # NEW: Flag for email text existence
                'has_scraped_data': False,
                'scraped_data_filename': None, # Store filename for URL generation
            })

            if not match_app_url:
                continue

            # --- URL Matching Logic (Primary Method) ---
            # Import URLNormalizer for centralized URL handling
            from utils.url_utils import URLNormalizer
            
            # Define sanitize_filename helper here or move to a shared utils module
            def sanitize_filename(name, length=30):
                # Allow alphanumeric, space, underscore, hyphen. Replace others with underscore.
                sanitized = ''.join(c if c.isalnum() or c in [' ', '_', '-'] else '_' for c in name)
                # Replace spaces with underscores
                sanitized = sanitized.replace(' ', '_')
                # Limit length
                return sanitized[:length]

            # Clean and normalize match URL using URLNormalizer
            match_app_url = URLNormalizer.clean_malformed_url(match_app_url)
            norm_match_url = URLNormalizer.normalize_for_comparison(match_app_url)
            found_files_by_url = False

            for scraped_path in existing_scraped:
                try:
                    with open(scraped_path, 'r', encoding='utf-8') as f_scraped:
                        actual = json.load(f_scraped)
                    stored_url = actual.get('Application URL')
                    if stored_url and stored_url != 'N/A':
                        # Clean and normalize stored URL
                        stored_url = URLNormalizer.clean_malformed_url(stored_url)
                        stored_url = URLNormalizer.to_full_url(stored_url)
                        norm_stored_url = URLNormalizer.normalize_for_comparison(stored_url)
                        logger.debug(f"Comparing normalized URLs: Match='{norm_match_url}', Stored='{norm_stored_url}' (from {scraped_path.name})")

                        # More robust comparison: check equality or if one contains the other (handles slight variations)
                        if norm_match_url == norm_stored_url or \
                           (norm_match_url and norm_stored_url and norm_match_url in norm_stored_url) or \
                           (norm_match_url and norm_stored_url and norm_stored_url in norm_match_url):

                            logger.info(f"Matched normalized URLs for scraped file {scraped_path.name}")
                            match['has_scraped_data'] = True
                            match['scraped_data_filename'] = scraped_path.name

                            # Now check for corresponding motivation letter files based on the scraped data's job title
                            title_from_scraped = actual.get('Job Title', 'job') # Use title from the matched scraped file
                            sanitized_scraped_title = sanitize_filename(title_from_scraped)

                            html_file = letters_dir / f"motivation_letter_{sanitized_scraped_title}.html"
                            json_file_check = letters_dir / f"motivation_letter_{sanitized_scraped_title}.json"
                            docx_file = letters_dir / f"motivation_letter_{sanitized_scraped_title}.docx"

                            has_letter = html_file.is_file() and json_file_check.is_file()
                            has_docx = docx_file.is_file()

                            if has_letter:
                                match['has_motivation_letter'] = True
                                match['motivation_letter_html_path'] = str(html_file.relative_to(current_app.root_path))
                                match['motivation_letter_json_path'] = str(json_file_check.relative_to(current_app.root_path)) # Store JSON path
                                # Check for email text in the found JSON
                                try:
                                    with open(json_file_check, 'r', encoding='utf-8') as f_json:
                                        letter_data = json.load(f_json)
                                    if letter_data.get('email_text'):
                                        match['has_email_text'] = True
                                except Exception as e_json_load:
                                    logger.warning(f"Could not load or check email_text in {json_file_check}: {e_json_load}")
                            if has_docx:
                                match['motivation_letter_docx_path'] = str(docx_file.relative_to(current_app.root_path))

                            found_files_by_url = True
                            break # Found match for this job URL, move to next match in outer loop
                except Exception as e_load:
                    logger.error(f"Error processing scraped file {scraped_path}: {e_load}")
                    continue # Skip this scraped file

            # Log if files weren't found by URL match
            if not found_files_by_url:
                logger.warning(f"No generated files could be associated with URL {match_app_url} (Report Job Title: {match.get('job_title')}) via URL matching.")

        # Render the results template
        return render_template(
            'results.html',
            matches=matches,
            report_file=secure_report_file, # Pass the secured filename
            available_cvs=available_cvs,
            associated_cv_filename=associated_cv_filename
        )

    except json.JSONDecodeError as json_err:
        flash(f'Error reading report file {json_file}: Invalid JSON.')
        logger.error(f'Error decoding JSON from {json_path}: {json_err}')
        return redirect(url_for('index'))
    except FileNotFoundError:
         flash(f'Report file not found: {json_file}')
         logger.error(f"Report file not found: {json_path}")
         return redirect(url_for('index'))
    except Exception as e:
        flash(f'Error loading results: {e}')
        logger.error(f'Error loading results for {secure_report_file}: {e}', exc_info=True)
        return redirect(url_for('index'))


@job_matching_bp.route('/download_report/<report_file>')
@login_required
def download_report(report_file):
    """Download a job match report (Markdown file)"""
    secure_report_file = secure_filename(report_file)
    report_path = Path(current_app.root_path) / 'job_matches' / secure_report_file

    try:
        if not report_path.is_file():
             flash(f'Report file not found: {secure_report_file}')
             logger.error(f"Report file not found for download: {report_path}")
             return redirect(url_for('index')) # Or maybe back to results?

        return send_file(str(report_path), as_attachment=True)
    except Exception as e:
        flash(f'Error downloading report: {str(e)}')
        logger.error(f'Error downloading report {secure_report_file}: {str(e)}', exc_info=True)
        # Redirect intelligently, maybe back to the results page if possible
        # For now, redirecting to index
        return redirect(url_for('index'))

@job_matching_bp.route('/delete_report/<report_file>')
@login_required
def delete_report(report_file):
    """Delete a job match report file (MD and JSON)"""
    try:
        secure_report_file = secure_filename(report_file)
        report_dir = Path(current_app.root_path) / 'job_matches'
        report_path_md = report_dir / secure_report_file

        # Construct JSON filename
        json_file = secure_report_file.replace('.md', '.json')
        report_path_json = report_dir / json_file

        deleted_md = False
        deleted_json = False

        # Check and delete the markdown file
        if report_path_md.is_file():
            os.remove(report_path_md)
            logger.info(f"Deleted report file: {report_path_md}")
            deleted_md = True
        else:
             logger.warning(f"Report MD file not found for deletion: {report_path_md}")


        # Check and delete the corresponding JSON file
        if report_path_json.is_file():
            os.remove(report_path_json)
            logger.info(f"Deleted corresponding JSON report file: {report_path_json}")
            deleted_json = True
        else:
             logger.warning(f"Report JSON file not found for deletion: {report_path_json}")

        if deleted_md or deleted_json:
             flash(f'Report files deleted: {secure_report_file}')
        else:
             flash(f'Report files not found: {secure_report_file}')

    except Exception as e:
        flash(f'Error deleting report file: {str(e)}')
        logger.error(f'Error deleting report file {report_file}: {str(e)}', exc_info=True)

    # Redirect back to the main dashboard after deletion
    return redirect(url_for('index'))


@job_matching_bp.route('/view_all_matches', methods=['GET'])
@login_required
def view_all_matches():
    """
    View all job matches with filtering and pagination
    
    Query parameters:
        - search_term: Filter by search term
        - cv_key: Filter by CV version
        - min_score: Minimum match score (0-10)
        - location: Filter by location (partial match)
        - date_from: Filter by match date (from)
        - date_to: Filter by match date (to)
        - sort_by: Sort field and direction
        - page: Page number (default 1)
        - per_page: Results per page (default 50)
    """
    import math
    from utils.db_utils import JobMatchDatabase
    
    # Extract filter parameters
    filters = {
        'search_term': request.args.get('search_term', ''),
        'cv_key': request.args.get('cv_key', ''),
        'min_score': request.args.get('min_score', 0, type=int),
        'location': request.args.get('location', ''),
        'date_from': request.args.get('date_from', ''),
        'date_to': request.args.get('date_to', ''),
        'sort_by': request.args.get('sort_by', 'overall_match DESC')
    }
    
    # Pagination
    page = max(1, request.args.get('page', 1, type=int))
    per_page = request.args.get('per_page', 50, type=int)
    offset = (page - 1) * per_page
    
    # Query database
    db = JobMatchDatabase()
    try:
        db.connect()
        
        # Build WHERE clause
        where_clauses = []
        params = []
        
        if filters['search_term']:
            where_clauses.append("search_term = ?")
            params.append(filters['search_term'])
        
        if filters['cv_key']:
            where_clauses.append("cv_key = ?")
            params.append(filters['cv_key'])
        
        if filters['min_score'] > 0:
            where_clauses.append("overall_match >= ?")
            params.append(filters['min_score'])
        
        if filters['location']:
            where_clauses.append("location LIKE ?")
            params.append(f"%{filters['location']}%")
        
        if filters['date_from']:
            where_clauses.append("DATE(matched_at) >= ?")
            params.append(filters['date_from'])
        
        if filters['date_to']:
            where_clauses.append("DATE(matched_at) <= ?")
            params.append(filters['date_to'])
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        # Validate sort_by to prevent SQL injection
        valid_sorts = [
            'overall_match DESC', 'overall_match ASC',
            'matched_at DESC', 'matched_at ASC',
            'company_name ASC', 'job_title ASC'
        ]
        if filters['sort_by'] not in valid_sorts:
            filters['sort_by'] = 'overall_match DESC'
        
        # Count total results
        count_sql = f"SELECT COUNT(*) FROM job_matches WHERE {where_sql}"
        assert db.conn is not None, "Database connection not established"
        cursor = db.conn.cursor()
        cursor.execute(count_sql, params)
        total_count = cursor.fetchone()[0]
        
        # Get paginated results with application status
        query_sql = f"""
            SELECT 
                jm.id,
                jm.job_url,
                jm.job_title,
                jm.company_name,
                jm.location,
                jm.overall_match,
                jm.search_term,
                jm.matched_at,
                jm.cv_key,
                COALESCE(app.status, 'MATCHED') as status,
                app.updated_at,
                CASE 
                    WHEN app.status = 'PREPARING' 
                        AND julianday('now') - julianday(app.updated_at) > 7 
                    THEN 1 
                    ELSE 0 
                END as is_stale
            FROM job_matches jm
            LEFT JOIN applications app ON jm.id = app.job_match_id
            WHERE {where_sql}
            ORDER BY {filters['sort_by']}
            LIMIT ? OFFSET ?
        """
        cursor.execute(query_sql, params + [per_page, offset])
        
        results = []
        for row in cursor.fetchall():
            score = row[5]
            result_dict = {
                'id': row[0],  # Include job_match_id for frontend API calls
                'job_url': row[1],
                'job_title': row[2],
                'company_name': row[3],
                'location': row[4],
                'overall_match': score,
                'score_class': get_score_class(score),
                'search_term': row[6],
                'matched_at': row[7],
                'cv_key': row[8],
                'status': row[9],  # Application status
                'status_updated_at': row[10],  # Last status update timestamp
                'is_stale': bool(row[11])  # Stale indicator (7+ days in PREPARING)
            }
            
            # Add file existence checks
            file_checks = check_for_generated_files(result_dict['job_url'])
            result_dict.update(file_checks)
            
            results.append(result_dict)
        
        # Get available filter options
        cursor.execute("SELECT DISTINCT search_term FROM job_matches ORDER BY search_term")
        available_search_terms = [row[0] for row in cursor.fetchall()]
        
        cursor.execute("""
            SELECT cv_key, file_name, upload_date 
            FROM cv_versions 
            ORDER BY upload_date DESC
        """)
        available_cvs = [
            {'cv_key': row[0], 'file_name': row[1], 'upload_date': row[2]}
            for row in cursor.fetchall()
        ]
        
        # Calculate pagination
        total_pages = math.ceil(total_count / per_page) if total_count > 0 else 1
        page = min(page, total_pages)  # Ensure page doesn't exceed total_pages
        
        return render_template(
            'all_matches.html',
            results=results,
            total_count=total_count,
            current_page=page,
            total_pages=total_pages,
            per_page=per_page,
            filters=filters,
            available_search_terms=available_search_terms,
            available_cvs=available_cvs
        )
    
    except Exception as e:
        logger.error(f"Error in view_all_matches: {e}", exc_info=True)
        flash(f'Error loading job matches: {str(e)}')
        return redirect(url_for('index'))
    
    finally:
        db.close()


def check_for_generated_files(job_url):
    """
    Check if generated files exist for given job URL in NEW checkpoint architecture
    Post Epic-2: Files are now in applications/{folder}/ structure
    
    Args:
        job_url: The job posting URL to check
        
    Returns:
        dict: File existence flags (has_motivation_letter, has_docx, has_scraped_data, has_email_text)
    """
    from pathlib import Path
    from utils.url_utils import URLNormalizer
    import urllib.parse
    
    # NEW: Check applications directory (checkpoint architecture from Epic 2)
    applications_dir = Path(current_app.root_path) / 'applications'
    
    # Clean and normalize URL
    job_url = URLNormalizer.clean_malformed_url(job_url)
    
    # Handle relative URLs
    if job_url.startswith('/'):
        base_url = "https://www.ostjob.ch/"
        job_url = urllib.parse.urljoin(base_url, job_url.lstrip('/'))
    
    norm_job_url = URLNormalizer.normalize_for_comparison(job_url)
    
    # Initialize flags
    result = {
        'has_motivation_letter': False,
        'has_docx': False,
        'has_scraped_data': False,
        'has_email_text': False,
        'motivation_letter_html_path': None,
        'motivation_letter_json_path': None,
        'motivation_letter_docx_path': None,
        'scraped_data_filename': None
    }
    
    # Check all application folders for matching job URL
    if not applications_dir.exists():
        logger.warning(f"Applications directory not found: {applications_dir}")
        return result
    
    for app_folder in applications_dir.iterdir():
        if not app_folder.is_dir():
            continue
        
        # Check job-details.json in each folder
        job_details_path = app_folder / 'job-details.json'
        if not job_details_path.is_file():
            continue
        
        try:
            with open(job_details_path, 'r', encoding='utf-8') as f:
                job_data = json.load(f)
            
            stored_url = job_data.get('Application URL')
            if not stored_url or stored_url == 'N/A':
                continue
            
            # Clean and normalize stored URL
            stored_url = URLNormalizer.clean_malformed_url(stored_url)
            stored_url = URLNormalizer.to_full_url(stored_url)
            norm_stored_url = URLNormalizer.normalize_for_comparison(stored_url)
            
            # Compare normalized URLs
            if norm_job_url == norm_stored_url or \
               (norm_job_url and norm_stored_url and norm_job_url in norm_stored_url) or \
               (norm_job_url and norm_stored_url and norm_stored_url in norm_job_url):
                
                logger.info(f"✅ Found matching application folder: {app_folder.name}")
                result['has_scraped_data'] = True
                result['scraped_data_filename'] = str(job_details_path.relative_to(current_app.root_path))
                
                # Check for letter files in checkpoint structure
                html_file = app_folder / 'bewerbungsschreiben.html'
                json_file = app_folder / 'application-data.json'
                docx_file = app_folder / 'bewerbungsschreiben.docx'
                email_file = app_folder / 'email-text.txt'
                
                if html_file.is_file():
                    result['has_motivation_letter'] = True
                    result['motivation_letter_html_path'] = str(html_file.relative_to(current_app.root_path))
                    logger.info(f"Found HTML: {html_file.name}")
                
                if json_file.is_file():
                    result['motivation_letter_json_path'] = str(json_file.relative_to(current_app.root_path))
                    # Check for email text in JSON
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f_json:
                            letter_data = json.load(f_json)
                        if letter_data.get('email_text') or email_file.is_file():
                            result['has_email_text'] = True
                            logger.info("Found email text")
                    except Exception as e:
                        logger.warning(f"Could not check email_text in {json_file}: {e}")
                
                if docx_file.is_file():
                    result['has_docx'] = True
                    result['motivation_letter_docx_path'] = str(docx_file.relative_to(current_app.root_path))
                    logger.info(f"Found DOCX: {docx_file.name}")
                
                break  # Found match, stop searching
                
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Error reading {job_details_path}: {e}")
            continue
    
    if not result['has_scraped_data']:
        logger.debug(f"No application folder found for URL: {norm_job_url}")
    
    return result


def sanitize_filename(name, length=30):
    """Sanitize filename by removing invalid characters"""
    sanitized = ''.join(c if c.isalnum() or c in [' ', '_', '-'] else '_' for c in name)
    sanitized = sanitized.replace(' ', '_')
    return sanitized[:length]


def get_score_class(score):
    """Return CSS class based on score"""
    if score >= 8:
        return 'high'
    elif score >= 6:
        return 'medium'
    else:
        return 'low'


@job_matching_bp.route('/api/job-reasoning', methods=['GET'])
@login_required
def api_job_reasoning():
    """API endpoint to get job reasoning from database"""
    from utils.db_utils import JobMatchDatabase
    
    job_url = request.args.get('url')
    if not job_url:
        return jsonify({'success': False, 'error': 'Job URL is required'}), 400
    
    db = JobMatchDatabase()
    try:
        db.connect()
        assert db.conn is not None, "Database connection not established"
        cursor = db.conn.cursor()
        
        # Query for the job match
        cursor.execute("""
            SELECT job_title, company_name, reasoning 
            FROM job_matches 
            WHERE job_url = ?
            LIMIT 1
        """, (job_url,))
        
        row = cursor.fetchone()
        if row:
            return jsonify({
                'success': True,
                'job_title': row[0],
                'company_name': row[1],
                'reasoning': row[2] or 'No reasoning available'
            })
        else:
            return jsonify({'success': False, 'error': 'Job match not found'}), 404
            
    except Exception as e:
        logger.error(f"Error fetching job reasoning: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
    
    finally:
        db.close()


@job_matching_bp.route('/api/job-matches', methods=['GET'])
@login_required
def api_job_matches():
    """API endpoint for filtered job matches"""
    from dashboard import query_job_matches
    
    # Parse query parameters
    filters = {
        'search_term': request.args.get('search_term'),
        'min_score': request.args.get('min_score', type=int),
        'date_from': request.args.get('date_from'),
        'date_to': request.args.get('date_to'),
        'location': request.args.get('location')
    }
    
    # Remove None values
    filters = {k: v for k, v in filters.items() if v is not None}
    
    sort_by = request.args.get('sort_by', 'overall_match')
    page = request.args.get('page', 1, type=int)
    per_page = 50
    offset = (page - 1) * per_page
    
    try:
        matches = query_job_matches(
            filters=filters,
            sort_by=sort_by,
            sort_order='DESC',
            limit=per_page,
            offset=offset
        )
        
        return jsonify({
            'success': True,
            'matches': matches,
            'page': page,
            'per_page': per_page,
            'total': len(matches)
        })
        
    except Exception as e:
        logger.error(f"Error querying matches: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@job_matching_bp.route('/kanban')
@login_required
def kanban_board():
    """Display Kanban board view of job applications."""
    from utils.cv_utils import get_cv_versions
    from utils.db_utils import JobMatchDatabase
    
    # Get CV versions for filter
    cv_versions = get_cv_versions()
    
    # FALLBACK: If no CV versions registered, get cv_keys directly from job_matches
    if not cv_versions:
        logger.warning("No CV versions found in cv_versions table, using cv_keys from job_matches")
        db = JobMatchDatabase()
        db.connect()
        cursor = db.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT cv_key 
            FROM job_matches 
            WHERE cv_key IS NOT NULL 
            ORDER BY cv_key
        """)
        cv_keys = cursor.fetchall()
        db.close()
        
        # Convert to same format as get_cv_versions: [(cv_key, display_name, date)]
        cv_versions = [(row[0], f"CV {row[0][:8]}...", None) for row in cv_keys]
        logger.info(f"Found {len(cv_versions)} distinct cv_keys in job_matches")
    
    # Get selected CV from query param or session
    selected_cv = request.args.get('cv_key')
    
    if not selected_cv and cv_versions:
        selected_cv = cv_versions[0][0]  # Default to first CV
    
    # Fetch all jobs with status
    db = JobMatchDatabase()
    db.connect()
    
    query = '''
        SELECT 
            jm.id,
            jm.job_url,
            jm.job_title,
            jm.company_name,
            jm.overall_match,
            COALESCE(app.status, 'MATCHED') as status,
            app.updated_at,
            CASE 
                WHEN app.status = 'PREPARING' 
                    AND julianday('now') - julianday(app.updated_at) > 7 
                THEN 1 
                ELSE 0 
            END as is_stale
        FROM job_matches jm
        LEFT JOIN applications app ON jm.id = app.job_match_id
        WHERE jm.cv_key = ?
        ORDER BY jm.matched_at DESC
    '''
    
    cursor = db.conn.cursor()
    cursor.execute(query, (selected_cv,))
    results = cursor.fetchall()
    db.close()
    
    # Group jobs by status
    pipeline = {
        'MATCHED': [],
        'INTERESTED': [],
        'PREPARING': [],
        'APPLIED': [],
        'INTERVIEW': [],
        'OFFER': [],
        'REJECTED': [],
        'ARCHIVED': []
    }
    
    for row in results:
        job = {
            'id': row[0],
            'url': row[1],
            'title': row[2],
            'company': row[3],
            'match_score': row[4],
            'status': row[5],
            'updated_at': row[6],
            'is_stale': bool(row[7])
        }
        pipeline[row[5]].append(job)
    
    return render_template(
        'kanban.html',
        pipeline=pipeline,
        cv_versions=cv_versions,
        selected_cv=selected_cv,
        show_archived=request.args.get('show_archived', 'false') == 'true'
    )

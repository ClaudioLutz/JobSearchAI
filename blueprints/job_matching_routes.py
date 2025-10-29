import os
import json
import logging
import threading
import urllib.parse
import importlib.util
from pathlib import Path
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
# Assuming get_job_details_for_url might be needed and moved to a utils module or kept in main app
# from dashboard import get_job_details_for_url # Example
from utils.decorators import admin_required

job_matching_bp = Blueprint('job_matching', __name__, url_prefix='/job_matching')

logger = logging.getLogger("dashboard.job_matching") # Use a child logger

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
    """Run the job matcher with the selected CV"""
    cv_path_rel = request.form.get('cv_path') # This is the relative path from the form
    min_score = int(request.form.get('min_score', 3))
    max_jobs = int(request.form.get('max_jobs', 50))
    max_results = int(request.form.get('max_results', 10))

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
        def run_job_matcher_task(app, op_id, cv_full_path_task, cv_path_rel_task, min_score_task, max_jobs_task, max_results_task):
             with app.app_context(): # Establish app context for the thread
                try:
                    # Update status
                    update_operation_progress(op_id, 10, 'processing', 'Loading job data...')

                    # Match jobs with CV - pass both max_jobs and max_results
                    matches = match_jobs_with_cv(cv_full_path_task, min_score=min_score_task, max_jobs=max_jobs_task, max_results=max_results_task)

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
        thread_args = (app_instance, operation_id, full_cv_path, cv_path_rel, min_score, max_jobs, max_results)
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
        max_pages = int(request.form.get('max_pages', 50))
        min_score = int(request.form.get('min_score', 3))
        max_jobs = int(request.form.get('max_jobs', 50))
        max_results = int(request.form.get('max_results', 10))

        if not cv_path_rel:
            flash('No CV selected')
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
        def run_combined_process_task(app, op_id, cv_full_path_task, cv_path_rel_task, max_pages_task, min_score_task, max_jobs_task, max_results_task):
            with app.app_context(): # Establish app context for the thread
                try:
                    # Access operation status via app extensions now that context exists
                    operation_status_ctx = app.extensions['operation_status']

                    # Update status (use op_id passed to function)
                    update_operation_progress(op_id, 5, 'processing', 'Updating settings...')

                    # Step 1: Update the settings.json file with the max_pages parameter
                    settings_path = os.path.join(app.root_path, 'job-data-acquisition', 'settings.json') # Use app.root_path
                    try:
                        with open(settings_path, 'r', encoding='utf-8') as f: settings = json.load(f)
                        settings['scraper']['max_pages'] = max_pages_task # Use passed variable
                        with open(settings_path, 'w', encoding='utf-8') as f: json.dump(settings, f, indent=4, ensure_ascii=False)
                    except Exception as settings_e:
                        logger.error(f"Error updating settings for combined run: {settings_e}")
                        complete_operation(op_id, 'failed', f'Error updating scraper settings: {settings_e}')
                        return

                    # Update status
                    update_operation_progress(op_id, 10, 'processing', 'Starting job scraper...')

                    # Step 2: Run the job scraper
                    output_file = None
                    try:
                        app_path = os.path.join(app.root_path, 'job-data-acquisition', 'app.py') # Use app.root_path
                        if not os.path.exists(app_path):
                             raise FileNotFoundError(f"Scraper app.py not found at {app_path}")
                        spec = importlib.util.spec_from_file_location("app_module", app_path)
                        app_module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(app_module)
                        run_scraper = getattr(app_module, 'run_scraper', None)
                        if run_scraper:
                            output_file = run_scraper() # run_scraper should return the output file path
                        else:
                             raise ModuleNotFoundError("run_scraper function not found in job-data-acquisition/app.py")
                    except Exception as scraper_e:
                         logger.error(f"Error running scraper in combined process: {scraper_e}", exc_info=True)
                         complete_operation(op_id, 'failed', f'Job data acquisition failed: {scraper_e}')
                         return

                    if output_file is None:
                        complete_operation(op_id, 'failed', 'Job data acquisition failed (no output file). Check logs.')
                        return

                    # Update status
                    update_operation_progress(op_id, 60, 'processing', 'Job data acquisition completed. Starting job matcher...')

                    # Step 3: Run the job matcher with the newly acquired data
                    matches = match_jobs_with_cv(cv_full_path_task, min_score=min_score_task, max_jobs=max_jobs_task, max_results=max_results_task) # Use passed variables

                    if not matches:
                        complete_operation(op_id, 'completed', 'No job matches found after scraping')
                        return

                    # Update status
                    update_operation_progress(op_id, 90, 'processing', 'Generating report...')

                    # Add relative cv_path for identification
                    for match in matches:
                        match['cv_path'] = cv_path_rel_task # Use passed variable

                    # Step 4: Generate report
                    report_file_path = generate_report(matches)
                    report_filename = os.path.basename(report_file_path)

                    # Complete the operation
                    complete_operation(op_id, 'completed', f'Combined process completed. Results saved to: {report_filename}')

                    # Store the report file in the operation status for retrieval (if needed elsewhere)
                    if op_id in operation_status_ctx:
                        operation_status_ctx[op_id]['report_file'] = report_filename

                except Exception as e:
                    logger.error(f'Error in combined process task: {str(e)}', exc_info=True)
                    complete_operation(op_id, 'failed', f'Error running combined process: {str(e)}')

        # Start the background thread, passing necessary arguments including app instance
        thread_args = (app_instance, operation_id, full_cv_path, cv_path_rel, max_pages, min_score, max_jobs, max_results)
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

"""
Application Queue Bridge Service
Transforms job matches and letters into queue applications.

Part of Story 1.4: Application Queue Integration Bridge
Architectural Pattern: Adapter/Transformer
"""

import json
import logging
import tempfile
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from models.application_context import ApplicationContext
from utils.url_utils import URLNormalizer
from utils.queue_validation import ApplicationValidator
from utils.email_quality import EmailQualityChecker


logger = logging.getLogger(__name__)


class QueueBridgeService:
    """
    Bridge service that aggregates data from multiple sources
    and transforms it into queue application format.
    
    Coordinates:
    - Data aggregation (match + letter + scraped)
    - Contact information extraction
    - Transformation to ApplicationContext
    - Validation
    - Queue file creation with atomic writes
    """
    
    def __init__(self, root_path: Optional[str] = None,
                 matches_dir: str = 'job_matches', 
                 letters_dir: str = 'motivation_letters',
                 queue_dir: str = 'job_matches/pending'):
        """
        Initialize bridge service.
        
        Args:
            root_path: Optional project root path. If provided, all other paths 
                      are treated as relative to this root.
            matches_dir: Directory containing match JSON files
            letters_dir: Directory containing letter files
            queue_dir: Directory for queue applications (pending)
        """
        if root_path:
            # When root_path is provided, treat all dirs as relative to it
            self.matches_dir = Path(root_path) / matches_dir
            self.letters_dir = Path(root_path) / letters_dir
            self.queue_dir = Path(root_path) / queue_dir
        else:
            # Use paths as-is (backward compatible)
            self.matches_dir = Path(matches_dir)
            self.letters_dir = Path(letters_dir)
            self.queue_dir = Path(queue_dir)
        self.url_normalizer = URLNormalizer()
        self.validator = ApplicationValidator()
        self.email_checker = EmailQualityChecker()
        
        # Ensure queue directory exists
        self.queue_dir.mkdir(parents=True, exist_ok=True)
    
    def aggregate_application_data(
        self,
        match_file: str,
        selected_indices: List[int]
    ) -> Tuple[List[ApplicationContext], List[Dict]]:
        """
        Aggregate data for selected matches from multiple sources.
        
        Args:
            match_file: Filename of match JSON (e.g., 'job_matches_20251016.json')
            selected_indices: List of match indices to process
            
        Returns:
            tuple: (list of ApplicationContext objects, list of errors)
        """
        contexts = []
        errors = []
        
        # Load match file
        match_path = self.matches_dir / match_file
        if not match_path.exists():
            errors.append({
                'type': 'file_not_found',
                'message': f'Match file not found: {match_file}',
                'file': match_file
            })
            return contexts, errors
        
        try:
            with open(match_path, 'r', encoding='utf-8') as f:
                matches = json.load(f)
        except Exception as e:
            errors.append({
                'type': 'json_parse_error',
                'message': f'Failed to parse match file: {str(e)}',
                'file': match_file
            })
            return contexts, errors
        
        # Process each selected match
        for idx in selected_indices:
            if idx >= len(matches):
                errors.append({
                    'type': 'invalid_index',
                    'message': f'Invalid match index: {idx}',
                    'index': idx
                })
                continue
            
            match = matches[idx]
            
            try:
                context = self._build_application_context(match, match_file)
                if context:
                    contexts.append(context)
                else:
                    errors.append({
                        'type': 'context_build_failed',
                        'message': 'Failed to build context',
                        'job_title': match.get('job_title', 'Unknown'),
                        'index': idx
                    })
            except Exception as e:
                errors.append({
                    'type': 'processing_error',
                    'message': str(e),
                    'job_title': match.get('job_title', 'Unknown'),
                    'index': idx
                })
                logger.error(f"Error processing match {idx}: {e}", exc_info=True)
        
        return contexts, errors
    
    def _build_application_context(
        self,
        match: dict,
        match_file: str
    ) -> Optional[ApplicationContext]:
        """
        Build ApplicationContext from match data and associated files.
        
        Args:
            match: Match dictionary
            match_file: Source match filename
            
        Returns:
            ApplicationContext or None if build fails
        """
        # Extract basic match data
        job_title = match.get('job_title', '')
        company_name = match.get('company_name', '')
        application_url = match.get('application_url', '')
        match_score = match.get('overall_match', 0)
        cv_path = match.get('cv_path', '')
        location = match.get('location')
        
        # Normalize URL to full URL if relative
        if application_url:
            application_url = self.url_normalizer.to_full_url(application_url)
        
        # Find corresponding letter file
        letter_data = self._find_letter_for_match(match, application_url)
        if not letter_data:
            logger.warning(f"No letter found for {job_title} at {company_name}")
            return None
        
        # Find scraped data for contact information
        scraped_data = self._find_scraped_data(application_url, job_title)
        contact_person, recipient_email = self._extract_contact_info(scraped_data)
        
        # Build ApplicationContext
        try:
            context = ApplicationContext(
                job_title=job_title,
                company_name=company_name,
                application_url=application_url,
                match_score=match_score,
                cv_path=cv_path,
                subject_line=letter_data.get('subject', f'Bewerbung als {job_title}'),
                letter_html=letter_data.get('letter_content', ''),
                location=location,
                letter_text=letter_data.get('letter_text'),
                email_text=letter_data.get('email_text'),
                contact_person=contact_person,
                recipient_email=recipient_email,
                job_description=scraped_data.get('Job Description') if scraped_data else None
            )
            
            # Validate context
            is_valid, validation_errors = context.validate()
            if not is_valid:
                logger.error(f"Context validation failed: {validation_errors}")
                return None
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to create ApplicationContext: {e}", exc_info=True)
            return None
    
    def _find_letter_for_match(
        self,
        match: dict,
        match_url: str
    ) -> Optional[dict]:
        """
        Find motivation letter file corresponding to match.
        
        Strategy:
        1. Look for letter with matching URL
        2. Look for letter with matching job title + company
        3. Load both JSON (for metadata) and HTML (for content)
        
        Args:
            match: Match dictionary
            match_url: Normalized match URL
            
        Returns:
            Letter data dict with 'letter_content' field or None
        """
        job_title = match.get('job_title', '')
        company_name = match.get('company_name', '')
        
        # Search in letters directory
        for letter_file in self.letters_dir.rglob('*.json'):
            try:
                with open(letter_file, 'r', encoding='utf-8') as f:
                    letter_data = json.load(f)
                
                # Check URL match
                letter_url = letter_data.get('application_url', '')
                if letter_url and match_url:
                    if self.url_normalizer.urls_match(letter_url, match_url):
                        # Load corresponding HTML file
                        html_file = letter_file.with_suffix('.html')
                        if html_file.exists():
                            with open(html_file, 'r', encoding='utf-8') as f_html:
                                letter_data['letter_content'] = f_html.read()
                        else:
                            logger.warning(f"HTML file not found for {letter_file.name}")
                            # Generate HTML from JSON structure if possible
                            letter_data['letter_content'] = self._generate_html_from_json(letter_data)
                        
                        return letter_data
                
                # Check job title + company match
                letter_title = letter_data.get('job_title', '')
                letter_company = letter_data.get('company_name', '')
                if (letter_title.lower() == job_title.lower() and
                    letter_company.lower() == company_name.lower()):
                    # Load corresponding HTML file
                    html_file = letter_file.with_suffix('.html')
                    if html_file.exists():
                        with open(html_file, 'r', encoding='utf-8') as f_html:
                            letter_data['letter_content'] = f_html.read()
                    else:
                        logger.warning(f"HTML file not found for {letter_file.name}")
                        letter_data['letter_content'] = self._generate_html_from_json(letter_data)
                    
                    return letter_data
                    
            except Exception as e:
                logger.debug(f"Could not read letter file {letter_file}: {e}")
                continue
        
        return None
    
    def _generate_html_from_json(self, letter_json: dict) -> str:
        """
        Generate simple HTML from letter JSON structure as fallback.
        
        Args:
            letter_json: Letter data dictionary
            
        Returns:
            HTML string
        """
        try:
            # Extract fields
            greeting = letter_json.get('greeting', '')
            introduction = letter_json.get('introduction', '')
            body_paragraphs = letter_json.get('body_paragraphs', [])
            closing = letter_json.get('closing', '')
            signature = letter_json.get('signature', '')
            full_name = letter_json.get('full_name', '')
            
            # Build simple HTML
            html_parts = []
            if greeting:
                html_parts.append(f"<p>{greeting},</p>")
            if introduction:
                html_parts.append(f"<p>{introduction}</p>")
            for paragraph in body_paragraphs:
                html_parts.append(f"<p>{paragraph}</p>")
            if closing:
                html_parts.append(f"<p>{closing}</p>")
            if signature or full_name:
                html_parts.append(f"<p>{signature},<br>{full_name}</p>")
            
            return '\n'.join(html_parts) if html_parts else '<p>Letter content not available</p>'
            
        except Exception as e:
            logger.error(f"Failed to generate HTML from JSON: {e}")
            return '<p>Letter content generation failed</p>'
    
    def _find_scraped_data(
        self,
        application_url: str,
        job_title: str
    ) -> Optional[dict]:
        """
        Find scraped job data file.
        
        Args:
            application_url: Job URL
            job_title: Job title for fallback matching
            
        Returns:
            Scraped data dict or None
        """
        # Look in job-data-acquisition/data directory
        scraped_dir = Path('job-data-acquisition/data')
        if not scraped_dir.exists():
            scraped_dir = Path('job-data-acquisitiondata')  # Alternative path
        
        if not scraped_dir.exists():
            logger.debug("Scraped data directory not found")
            return None
        
        # Search for JSON files
        for scraped_file in scraped_dir.rglob('*.json'):
            try:
                with open(scraped_file, 'r', encoding='utf-8') as f:
                    scraped_data = json.load(f)
                
                # Check URL match
                scraped_url = scraped_data.get('Application URL', '')
                if scraped_url and application_url:
                    if self.url_normalizer.urls_match(scraped_url, application_url):
                        return scraped_data
                
                # Fallback: Check job title match
                scraped_title = scraped_data.get('Job Title', '')
                if scraped_title.lower() == job_title.lower():
                    return scraped_data
                    
            except Exception as e:
                logger.debug(f"Could not read scraped file {scraped_file}: {e}")
                continue
        
        return None
    
    def _extract_contact_info(
        self,
        scraped_data: Optional[dict]
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract contact person and email from scraped data.
        
        Args:
            scraped_data: Scraped job data
            
        Returns:
            tuple: (contact_person, recipient_email)
        """
        if not scraped_data:
            return None, None
        
        contact_person = scraped_data.get('Contact Person')
        recipient_email = scraped_data.get('Email') or scraped_data.get('Contact Email')
        
        return contact_person, recipient_email
    
    def send_to_queue(self, match: dict) -> Optional[str]:
        """
        Send a single match to the queue.
        
        This is a convenience method that wraps the full transformation pipeline:
        1. Build ApplicationContext from match
        2. Find letter and scraped data
        3. Validate
        4. Save to queue
        
        Args:
            match: Match dictionary with job details
            
        Returns:
            Application ID if successful, None if failed
        """
        try:
            # Clean URL if present
            if 'application_url' in match and match['application_url']:
                match['application_url'] = URLNormalizer.clean_malformed_url(match['application_url'])
            
            # Build context
            context = self._build_application_context(match, 'direct')
            if not context:
                logger.error(f"Failed to build context for {match.get('job_title')}")
                return None
            
            # Transform to queue application
            queue_app = context.to_queue_application()
            
            # Validate
            is_valid, validation_errors = self.validator.validate_for_queue(queue_app)
            if not is_valid:
                logger.error(f"Validation failed for {context.job_title}: {validation_errors}")
                return None
            
            # Check email quality and log warnings
            if queue_app.get('recipient_email'):
                email_assessment = self.email_checker.assess_email(
                    queue_app['recipient_email']
                )
                if email_assessment['severity'] in ['warning', 'critical']:
                    logger.warning(
                        f"{context.job_title}: {email_assessment['recommendation']}"
                    )
            
            # Save to queue
            app_id = queue_app['id']
            queue_file = self.queue_dir / f"{app_id}.json"
            
            # Atomic write
            self._atomic_write_json(queue_file, queue_app)
            logger.info(f"Queued application: {app_id} for {context.job_title}")
            
            return app_id
            
        except Exception as e:
            logger.error(
                f"Failed to queue {match.get('job_title', 'Unknown')}: {e}",
                exc_info=True
            )
            return None
    
    def send_multiple_to_queue(
        self,
        contexts: List[ApplicationContext],
        dry_run: bool = False
    ) -> Dict:
        """
        Transform multiple contexts and save to queue directory.
        
        Args:
            contexts: List of ApplicationContext objects
            dry_run: If True, validate but don't save files
            
        Returns:
            dict: {
                'queued': int,
                'failed': int,
                'warnings': List[str],
                'errors': List[dict]
            }
        """
        result = {
            'queued': 0,
            'failed': 0,
            'warnings': [],
            'errors': []
        }
        
        for context in contexts:
            try:
                # Transform to queue application
                queue_app = context.to_queue_application()
                
                # Validate
                is_valid, validation_errors = self.validator.validate_for_queue(queue_app)
                if not is_valid:
                    result['failed'] += 1
                    result['errors'].append({
                        'job_title': context.job_title,
                        'type': 'validation_error',
                        'details': validation_errors
                    })
                    continue
                
                # Check email quality
                if queue_app.get('recipient_email'):
                    email_assessment = self.email_checker.assess_email(
                        queue_app['recipient_email']
                    )
                    if email_assessment['severity'] in ['warning', 'critical']:
                        result['warnings'].append(
                            f"{context.job_title}: {email_assessment['recommendation']}"
                        )
                
                # Save to queue (unless dry run)
                if not dry_run:
                    app_id = queue_app['id']
                    queue_file = self.queue_dir / f"{app_id}.json"
                    
                    # Atomic write
                    self._atomic_write_json(queue_file, queue_app)
                    logger.info(f"Queued application: {app_id} for {context.job_title}")
                
                result['queued'] += 1
                
            except Exception as e:
                result['failed'] += 1
                result['errors'].append({
                    'job_title': context.job_title,
                    'type': 'processing_error',
                    'message': str(e)
                })
                logger.error(f"Failed to queue {context.job_title}: {e}", exc_info=True)
        
        return result
    
    def _atomic_write_json(self, path: Path, data: dict):
        """
        Write JSON file atomically to prevent corruption.
        
        Args:
            path: Target file path
            data: Data to write
        """
        # Write to temp file first
        with tempfile.NamedTemporaryFile(
            mode='w',
            encoding='utf-8',
            dir=path.parent,
            delete=False,
            suffix='.tmp'
        ) as tmp:
            json.dump(data, tmp, indent=2, ensure_ascii=False)
            tmp.flush()
            os.fsync(tmp.fileno())
            temp_path = tmp.name
        
        # Atomic rename
        os.replace(temp_path, path)
    
    def check_duplicate(
        self,
        job_title: str,
        company_name: str
    ) -> Optional[str]:
        """
        Check if application already exists in queue.
        
        Args:
            job_title: Job title
            company_name: Company name
            
        Returns:
            Application ID if duplicate found, None otherwise
        """
        # Check pending queue
        for queue_file in self.queue_dir.glob('*.json'):
            try:
                with open(queue_file, 'r', encoding='utf-8') as f:
                    queue_app = json.load(f)
                
                if (queue_app.get('job_title', '').lower() == job_title.lower() and
                    queue_app.get('company_name', '').lower() == company_name.lower()):
                    return queue_app.get('id')
                    
            except Exception as e:
                logger.debug(f"Could not read queue file {queue_file}: {e}")
                continue
        
        return None

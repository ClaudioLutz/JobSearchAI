"""
Settings API Blueprint - Manages search terms configuration

Provides REST API endpoints for managing search terms in settings.json:
- GET /api/settings/search_terms - Retrieve current search terms
- POST /api/settings/search_terms - Add new search term
- PUT /api/settings/search_terms/<index> - Update existing search term
- DELETE /api/settings/search_terms/<index> - Remove search term

All modifications create timestamped backups to prevent data loss.
"""

from flask import Blueprint, jsonify, request
from pathlib import Path
import json
import re
from datetime import datetime
import shutil
import logging

bp = Blueprint('settings', __name__, url_prefix='/api/settings')
logger = logging.getLogger(__name__)

# Configuration
SETTINGS_FILE = Path('job-data-acquisition/settings.json')
BACKUP_DIR = Path('job-data-acquisition/backups')

# Validation constants
SEARCH_TERM_PATTERN = re.compile(r'^[A-Za-z0-9\-]+$')
MAX_TERM_LENGTH = 100


def validate_search_term(term: str) -> tuple:
    """
    Validate search term format.
    
    Rules:
    - Only alphanumeric characters and hyphens
    - Maximum 100 characters
    - Cannot start or end with hyphen
    - No consecutive hyphens
    
    Args:
        term: Search term to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not term:
        return False, "Search term cannot be empty"
    
    if len(term) > MAX_TERM_LENGTH:
        return False, f"Search term too long (max {MAX_TERM_LENGTH} characters)"
    
    if not SEARCH_TERM_PATTERN.match(term):
        return False, "Search term can only contain letters, numbers, and hyphens"
    
    if term.startswith('-') or term.endswith('-'):
        return False, "Search term cannot start or end with hyphen"
    
    if '--' in term:
        return False, "Search term cannot contain consecutive hyphens"
    
    return True, ""


def backup_settings():
    """
    Create timestamped backup of settings.json.
    
    Returns:
        Path: Path to created backup file
    """
    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = BACKUP_DIR / f'settings_backup_{timestamp}.json'
        shutil.copy2(SETTINGS_FILE, backup_path)
        logger.info(f"Created settings backup: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        raise


def read_settings() -> dict:
    """
    Read current settings.json file.
    
    Returns:
        dict: Settings data
    """
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to read settings: {e}")
        raise


def write_settings(settings: dict):
    """
    Write updated settings.json atomically.
    
    Uses temporary file and atomic rename to prevent corruption.
    
    Args:
        settings: Settings dictionary to write
    """
    try:
        # Write to temporary file first
        temp_file = SETTINGS_FILE.with_suffix('.tmp')
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        
        # Atomic rename
        temp_file.replace(SETTINGS_FILE)
        logger.info("Settings updated successfully")
    except Exception as e:
        logger.error(f"Failed to write settings: {e}")
        # Clean up temp file if it exists
        if temp_file.exists():
            temp_file.unlink()
        raise


@bp.route('/search_terms', methods=['GET'])
def get_search_terms():
    """
    Get list of current search terms.
    
    Returns:
        JSON response with search terms array and base URL
    """
    try:
        settings = read_settings()
        
        search_terms = settings.get('search_terms', [])
        base_url = settings.get('base_url', 'https://www.ostjob.ch/job/suche-{search_term}-seite-')
        
        return jsonify({
            'search_terms': search_terms,
            'base_url': base_url,
            'count': len(search_terms)
        })
    
    except Exception as e:
        logger.error(f"Error getting search terms: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/search_terms', methods=['POST'])
def add_search_term():
    """
    Add new search term to configuration.
    
    Request body:
        {"search_term": "IT-Manager-festanstellung-pensum-80-bis-100"}
    
    Returns:
        JSON response with success status and created term
    """
    try:
        data = request.get_json()
        new_term = data.get('search_term', '').strip()
        
        # Validate term
        is_valid, error_msg = validate_search_term(new_term)
        if not is_valid:
            return jsonify({'error': error_msg}), 400
        
        # Read current settings
        settings = read_settings()
        
        # Check for duplicates
        existing_terms = settings.get('search_terms', [])
        if new_term in existing_terms:
            return jsonify({'error': 'Search term already exists'}), 400
        
        # Create backup before modification
        backup_path = backup_settings()
        
        # Add new term
        if 'search_terms' not in settings:
            settings['search_terms'] = []
        settings['search_terms'].append(new_term)
        
        # Write atomically
        write_settings(settings)
        
        logger.info(f"Added search term: {new_term}")
        
        return jsonify({
            'success': True,
            'search_term': new_term,
            'backup': str(backup_path)
        })
    
    except Exception as e:
        logger.error(f"Error adding search term: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/search_terms/<int:index>', methods=['PUT'])
def update_search_term(index: int):
    """
    Update existing search term by index.
    
    Args:
        index: Zero-based index of term to update
    
    Request body:
        {"search_term": "New-Term-Value"}
    
    Returns:
        JSON response with success status
    """
    try:
        data = request.get_json()
        new_term = data.get('search_term', '').strip()
        
        # Validate term
        is_valid, error_msg = validate_search_term(new_term)
        if not is_valid:
            return jsonify({'error': error_msg}), 400
        
        # Read current settings
        settings = read_settings()
        search_terms = settings.get('search_terms', [])
        
        # Validate index
        if index < 0 or index >= len(search_terms):
            return jsonify({'error': 'Invalid index'}), 400
        
        # Check for duplicates (excluding current index)
        for i, term in enumerate(search_terms):
            if i != index and term == new_term:
                return jsonify({'error': 'Search term already exists'}), 400
        
        # Create backup before modification
        backup_path = backup_settings()
        
        # Update term
        old_term = search_terms[index]
        search_terms[index] = new_term
        settings['search_terms'] = search_terms
        
        # Write atomically
        write_settings(settings)
        
        logger.info(f"Updated search term at index {index}: {old_term} -> {new_term}")
        
        return jsonify({
            'success': True,
            'search_term': new_term,
            'old_term': old_term,
            'backup': str(backup_path)
        })
    
    except Exception as e:
        logger.error(f"Error updating search term: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/search_terms/<int:index>', methods=['DELETE'])
def delete_search_term(index: int):
    """
    Delete search term by index.
    
    Args:
        index: Zero-based index of term to delete
    
    Returns:
        JSON response with success status
    """
    try:
        # Read current settings
        settings = read_settings()
        search_terms = settings.get('search_terms', [])
        
        # Validate index
        if index < 0 or index >= len(search_terms):
            return jsonify({'error': 'Invalid index'}), 400
        
        # Create backup before modification
        backup_path = backup_settings()
        
        # Delete term
        deleted_term = search_terms[index]
        del search_terms[index]
        settings['search_terms'] = search_terms
        
        # Write atomically
        write_settings(settings)
        
        logger.info(f"Deleted search term at index {index}: {deleted_term}")
        
        return jsonify({
            'success': True,
            'deleted_term': deleted_term,
            'backup': str(backup_path)
        })
    
    except Exception as e:
        logger.error(f"Error deleting search term: {e}")
        return jsonify({'error': str(e)}), 500

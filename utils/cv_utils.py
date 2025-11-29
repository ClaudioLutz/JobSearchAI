"""
CV utilities for JobSearchAI unified database.

This module provides CV key generation and metadata management
for tracking CV versions in the database.

Part of Epic 2: SQLite Deduplication & Integration Implementation
Story 2.1: Database Foundation
"""

import hashlib
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import sqlite3

# Set up logging
logger = logging.getLogger("cv_utils")
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


def generate_cv_key(cv_path: str) -> str:
    """
    Generate a deterministic CV key based on file content.
    
    Uses SHA256 hash of CV file content, truncated to 16 characters.
    Same content always produces the same key.
    
    Args:
        cv_path: Path to CV file
        
    Returns:
        16-character hexadecimal string representing CV key
        
    Raises:
        FileNotFoundError: If CV file doesn't exist
        IOError: If file cannot be read
        
    Examples:
        >>> generate_cv_key("process_cv/cv-data/input/cv.docx")
        'a1b2c3d4e5f6g7h8'
    """
    cv_file = Path(cv_path)
    
    # Validate file exists
    if not cv_file.exists():
        raise FileNotFoundError(f"CV file not found: {cv_path}")
    
    if not cv_file.is_file():
        raise IOError(f"Path is not a file: {cv_path}")
    
    try:
        # Read file content in binary mode
        with open(cv_file, 'rb') as f:
            cv_bytes = f.read()
        
        # Generate SHA256 hash
        file_hash = hashlib.sha256(cv_bytes).hexdigest()
        
        # Return first 16 characters (sufficient for uniqueness)
        cv_key = file_hash[:16]
        
        logger.debug(f"Generated CV key {cv_key} for {cv_path}")
        return cv_key
        
    except IOError as e:
        logger.error(f"Failed to read CV file {cv_path}: {e}")
        raise


def get_or_create_cv_metadata(
    cv_path: str,
    db_conn: sqlite3.Connection,
    summary: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Get existing CV metadata or create new entry if doesn't exist.
    
    Args:
        cv_path: Path to CV file
        db_conn: SQLite database connection
        summary: Optional CV summary text
        metadata: Optional additional metadata as dictionary
        
    Returns:
        Dictionary containing CV metadata including cv_key
        
    Raises:
        FileNotFoundError: If CV file doesn't exist
        sqlite3.Error: If database operation fails
        
    Example:
        >>> conn = sqlite3.connect("instance/jobsearchai.db")
        >>> cv_data = get_or_create_cv_metadata("cv.docx", conn)
        >>> print(cv_data['cv_key'])
        'a1b2c3d4e5f6g7h8'
    """
    # Generate CV key from file content
    cv_key = generate_cv_key(cv_path)
    
    cv_file = Path(cv_path)
    
    # Check if CV already exists in database
    cursor = db_conn.cursor()
    cursor.execute("""
        SELECT * FROM cv_versions WHERE cv_key = ?
    """, (cv_key,))
    
    existing = cursor.fetchone()
    
    if existing:
        # Return existing metadata
        logger.debug(f"Found existing CV metadata for key {cv_key}")
        
        # Convert row to dictionary
        if hasattr(existing, 'keys'):
            result = dict(existing)
        else:
            # Fallback for non-Row objects
            result = {
                'cv_key': existing[0],
                'file_name': existing[1],
                'file_path': existing[2],
                'file_hash': existing[3],
                'upload_date': existing[4],
                'summary': existing[5],
                'metadata': existing[6]
            }
        
        # Parse JSON metadata if present
        if result.get('metadata'):
            try:
                result['metadata'] = json.loads(result['metadata'])
            except json.JSONDecodeError:
                pass
        
        return result
    
    # Create new CV metadata entry
    file_name = cv_file.name
    file_path = str(cv_file.absolute())
    
    # Generate full file hash for metadata storage
    with open(cv_file, 'rb') as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()
    
    # Convert metadata dict to JSON
    metadata_json = json.dumps(metadata) if metadata else None
    
    # Insert into database
    try:
        cursor.execute("""
            INSERT INTO cv_versions (
                cv_key, file_name, file_path, file_hash,
                summary, metadata
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            cv_key,
            file_name,
            file_path,
            file_hash,
            summary,
            metadata_json
        ))
        
        db_conn.commit()
        logger.info(f"Created new CV metadata for key {cv_key}")
        
        # Return the created metadata
        result = {
            'cv_key': cv_key,
            'file_name': file_name,
            'file_path': file_path,
            'file_hash': file_hash,
            'upload_date': datetime.now().isoformat(),
            'summary': summary,
            'metadata': metadata
        }
        
        return result
        
    except sqlite3.IntegrityError:
        # Race condition: another process created it
        logger.debug(f"CV metadata already exists (race condition): {cv_key}")
        # Fetch and return the existing entry
        cursor.execute("SELECT * FROM cv_versions WHERE cv_key = ?", (cv_key,))
        existing = cursor.fetchone()
        
        if hasattr(existing, 'keys'):
            result = dict(existing)
        else:
            result = {
                'cv_key': existing[0],
                'file_name': existing[1],
                'file_path': existing[2],
                'file_hash': existing[3],
                'upload_date': existing[4],
                'summary': existing[5],
                'metadata': existing[6]
            }
        
        if result.get('metadata'):
            try:
                result['metadata'] = json.loads(result['metadata'])
            except json.JSONDecodeError:
                pass
        
        return result
        
    except sqlite3.Error as e:
        logger.error(f"Failed to create CV metadata: {e}")
        raise


def validate_cv_file(cv_path: str) -> bool:
    """
    Validate that CV file exists and is readable.
    
    Args:
        cv_path: Path to CV file
        
    Returns:
        True if file is valid, False otherwise
    """
    try:
        cv_file = Path(cv_path)
        
        if not cv_file.exists():
            logger.warning(f"CV file does not exist: {cv_path}")
            return False
        
        if not cv_file.is_file():
            logger.warning(f"Path is not a file: {cv_path}")
            return False
        
        # Try to read file to ensure it's accessible
        with open(cv_file, 'rb') as f:
            f.read(1)  # Read just 1 byte to test
        
        return True
        
    except Exception as e:
        logger.error(f"CV file validation failed for {cv_path}: {e}")
        return False


def get_cv_versions(db_conn: Optional[sqlite3.Connection] = None) -> list:
    """
    Get list of all CV versions from database.
    
    Args:
        db_conn: Optional database connection. If not provided, creates a new connection.
        
    Returns:
        List of tuples (cv_key, file_name, upload_date)
        
    Example:
        >>> cvs = get_cv_versions()
        >>> for cv_key, name, date in cvs:
        ...     print(f"{name} ({cv_key[:8]}...) uploaded {date}")
    """
    close_conn = False
    
    try:
        # Create connection if not provided
        if db_conn is None:
            from utils.db_utils import JobMatchDatabase
            db = JobMatchDatabase()
            db.connect()
            db_conn = db.conn
            close_conn = True
        
        cursor = db_conn.cursor()
        cursor.execute("""
            SELECT cv_key, file_name, upload_date
            FROM cv_versions
            ORDER BY upload_date DESC
        """)
        
        results = cursor.fetchall()
        logger.debug(f"Retrieved {len(results)} CV versions")
        
        return results
        
    except sqlite3.Error as e:
        logger.error(f"Failed to retrieve CV versions: {e}")
        return []
        
    finally:
        if close_conn and db_conn:
            db_conn.close()

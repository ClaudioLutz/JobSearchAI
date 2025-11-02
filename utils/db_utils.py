"""
Database utilities for JobSearchAI unified SQLite database.

This module provides centralized database access for job matching data,
supporting deduplication, CV versioning, and efficient querying.

Part of Epic 2: SQLite Deduplication & Integration Implementation
Story 2.1: Database Foundation
"""

import sqlite3
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from contextlib import contextmanager

from utils.url_utils import URLNormalizer

# Set up logging
logger = logging.getLogger("db_utils")
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


class JobMatchDatabase:
    """
    Centralized database access for job matching operations.
    
    Provides:
    - Database connection management
    - Schema initialization
    - Deduplication checks
    - Insert operations
    - Query operations
    """
    
    # SQLite PRAGMA settings for optimal performance
    PRAGMA_SETTINGS = {
        'journal_mode': 'WAL',      # Write-Ahead Logging for better concurrency
        'synchronous': 'NORMAL',    # Balance between safety and performance
        'foreign_keys': 'ON',       # Enforce foreign key constraints
        'temp_store': 'MEMORY',     # Use memory for temp tables
    }
    
    def __init__(self, db_path: str = "instance/jobsearchai.db", timeout: float = 30.0):
        """
        Initialize database connection manager.
        
        Args:
            db_path: Path to SQLite database file
            timeout: Connection timeout in seconds
        """
        self.db_path = db_path
        self.timeout = timeout
        self.conn: Optional[sqlite3.Connection] = None
        self.url_normalizer = URLNormalizer()
        
        logger.info(f"JobMatchDatabase initialized with path: {db_path}")
    
    def connect(self) -> sqlite3.Connection:
        """
        Establish database connection with optimal settings.
        
        Returns:
            sqlite3.Connection: Database connection
            
        Raises:
            sqlite3.Error: If connection fails
        """
        if self.conn is not None:
            return self.conn
        
        try:
            # Ensure directory exists
            db_dir = Path(self.db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)
            
            # Create connection with timeout and multi-threading support
            self.conn = sqlite3.connect(
                self.db_path,
                timeout=self.timeout,
                check_same_thread=False  # Allow multi-threaded access
            )
            
            # Enable row factory for dict-like access
            self.conn.row_factory = sqlite3.Row
            
            # Apply PRAGMA settings
            for pragma, value in self.PRAGMA_SETTINGS.items():
                self.conn.execute(f"PRAGMA {pragma} = {value}")
            
            logger.info("Database connection established")
            return self.conn
            
        except sqlite3.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("Database connection closed")
    
    @contextmanager
    def transaction(self):
        """
        Context manager for database transactions.
        
        Usage:
            with db.transaction():
                db.insert_job_match(data)
        """
        if not self.conn:
            self.connect()
        
        conn = self.conn
        assert conn is not None, "Database connection not established"
        
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    
    def init_database(self):
        """
        Initialize database schema with all tables and indexes.
        
        Creates:
        - job_matches table
        - cv_versions table
        - scrape_history table
        - All required indexes
        """
        if not self.conn:
            self.connect()
        
        assert self.conn is not None, "Database connection not established"
        cursor = self.conn.cursor()
        
        try:
            # Create job_matches table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS job_matches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_url TEXT NOT NULL,
                    search_term TEXT NOT NULL,
                    cv_key TEXT NOT NULL,
                    job_title TEXT,
                    company_name TEXT,
                    location TEXT,
                    posting_date TEXT,
                    salary_range TEXT,
                    overall_match INTEGER NOT NULL,
                    skills_match INTEGER,
                    experience_match INTEGER,
                    education_fit INTEGER,
                    career_trajectory_alignment INTEGER,
                    preference_match INTEGER,
                    potential_satisfaction INTEGER,
                    location_compatibility TEXT,
                    reasoning TEXT,
                    scraped_data TEXT NOT NULL,
                    scraped_at TEXT NOT NULL,
                    matched_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(job_url, search_term, cv_key)
                )
            """)
            
            # Create cv_versions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cv_versions (
                    cv_key TEXT PRIMARY KEY,
                    file_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_hash TEXT NOT NULL,
                    upload_date TEXT DEFAULT CURRENT_TIMESTAMP,
                    summary TEXT,
                    metadata TEXT
                )
            """)
            
            # Create scrape_history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scrape_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    search_term TEXT NOT NULL,
                    page_number INTEGER NOT NULL,
                    jobs_found INTEGER NOT NULL,
                    new_jobs INTEGER NOT NULL,
                    duplicate_jobs INTEGER NOT NULL,
                    scraped_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    duration_seconds REAL
                )
            """)
            
            # Create indexes for query performance
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_search_term ON job_matches(search_term)",
                "CREATE INDEX IF NOT EXISTS idx_cv_key ON job_matches(cv_key)",
                "CREATE INDEX IF NOT EXISTS idx_overall_match ON job_matches(overall_match)",
                "CREATE INDEX IF NOT EXISTS idx_matched_at ON job_matches(matched_at)",
                "CREATE INDEX IF NOT EXISTS idx_location ON job_matches(location)",
                "CREATE INDEX IF NOT EXISTS idx_search_cv_match ON job_matches(search_term, cv_key, overall_match)",
            ]
            
            for index_sql in indexes:
                cursor.execute(index_sql)
            
            self.conn.commit()
            logger.info("Database schema initialized successfully")
            
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database schema: {e}")
            raise
    
    def job_exists(self, job_url: str, search_term: str, cv_key: str) -> bool:
        """
        Check if a job match already exists in database.
        
        Args:
            job_url: Job posting URL (will be normalized)
            search_term: Search term used to find the job
            cv_key: CV version key
            
        Returns:
            True if job exists, False otherwise
        """
        if not self.conn:
            self.connect()
        
        assert self.conn is not None, "Database connection not established"
        
        # Normalize URL for consistent comparison
        normalized_url = self.url_normalizer.to_full_url(job_url)
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM job_matches
            WHERE job_url = ? AND search_term = ? AND cv_key = ?
        """, (normalized_url, search_term, cv_key))
        
        count = cursor.fetchone()[0]
        return count > 0
    
    def insert_job_match(self, match_data: Dict[str, Any]) -> Optional[int]:
        """
        Insert a job match record into database.
        
        Args:
            match_data: Dictionary containing job match data
            
        Returns:
            Row ID of inserted record, or None if duplicate
            
        Raises:
            sqlite3.OperationalError: If database operation fails
        """
        if not self.conn:
            self.connect()
        
        assert self.conn is not None, "Database connection not established"
        
        # Normalize URL
        match_data['job_url'] = self.url_normalizer.to_full_url(match_data['job_url'])
        
        # Convert scraped_data to JSON if it's a dict
        if isinstance(match_data.get('scraped_data'), dict):
            match_data['scraped_data'] = json.dumps(match_data['scraped_data'])
        
        # Ensure timestamps are in ISO format
        if 'scraped_at' not in match_data:
            match_data['scraped_at'] = datetime.now().isoformat()
        
        cursor = self.conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO job_matches (
                    job_url, search_term, cv_key, job_title, company_name,
                    location, posting_date, salary_range, overall_match,
                    skills_match, experience_match, education_fit,
                    career_trajectory_alignment, preference_match,
                    potential_satisfaction, location_compatibility,
                    reasoning, scraped_data, scraped_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                match_data['job_url'],
                match_data['search_term'],
                match_data['cv_key'],
                match_data.get('job_title'),
                match_data.get('company_name'),
                match_data.get('location'),
                match_data.get('posting_date'),
                match_data.get('salary_range'),
                match_data['overall_match'],
                match_data.get('skills_match'),
                match_data.get('experience_match'),
                match_data.get('education_fit'),
                match_data.get('career_trajectory_alignment'),
                match_data.get('preference_match'),
                match_data.get('potential_satisfaction'),
                match_data.get('location_compatibility'),
                match_data.get('reasoning'),
                match_data['scraped_data'],
                match_data['scraped_at']
            ))
            
            self.conn.commit()
            logger.debug(f"Inserted job match: {match_data['job_url']}")
            return cursor.lastrowid
            
        except sqlite3.IntegrityError:
            # Duplicate entry (expected during deduplication)
            logger.debug(f"Duplicate entry: {match_data['job_url']}")
            return None
            
        except sqlite3.OperationalError as e:
            logger.error(f"Database operational error: {e}")
            raise
    
    def insert_scrape_history(self, history_data: Dict[str, Any]) -> int:
        """
        Insert scrape history record.
        
        Args:
            history_data: Dictionary containing scrape history data
            
        Returns:
            Row ID of inserted record
        """
        if not self.conn:
            self.connect()
        
        assert self.conn is not None, "Database connection not established"
        
        if 'scraped_at' not in history_data:
            history_data['scraped_at'] = datetime.now().isoformat()
        
        cursor = self.conn.cursor()
        
        cursor.execute("""
            INSERT INTO scrape_history (
                search_term, page_number, jobs_found, new_jobs,
                duplicate_jobs, scraped_at, duration_seconds
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            history_data['search_term'],
            history_data['page_number'],
            history_data['jobs_found'],
            history_data['new_jobs'],
            history_data['duplicate_jobs'],
            history_data['scraped_at'],
            history_data.get('duration_seconds')
        ))
        
        self.conn.commit()
        row_id = cursor.lastrowid
        assert row_id is not None, "Failed to get inserted row ID"
        return row_id
    
    def query_matches(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Query job matches with optional filters.
        
        Args:
            filters: Optional dictionary with filter criteria:
                - search_term: Filter by search term
                - cv_key: Filter by CV version
                - min_score: Minimum overall match score
                - date_range: Tuple of (start_date, end_date) in ISO format
                - location: Filter by location (partial match)
                - limit: Maximum number of results
                - offset: Number of results to skip
                
        Returns:
            List of job match dictionaries
        """
        if not self.conn:
            self.connect()
        
        assert self.conn is not None, "Database connection not established"
        
        filters = filters or {}
        
        # Build query
        query = "SELECT * FROM job_matches WHERE 1=1"
        params = []
        
        if filters.get('search_term'):
            query += " AND search_term = ?"
            params.append(filters['search_term'])
        
        if filters.get('cv_key'):
            query += " AND cv_key = ?"
            params.append(filters['cv_key'])
        
        if filters.get('min_score'):
            query += " AND overall_match >= ?"
            params.append(filters['min_score'])
        
        if filters.get('date_range'):
            start_date, end_date = filters['date_range']
            query += " AND matched_at BETWEEN ? AND ?"
            params.extend([start_date, end_date])
        
        if filters.get('location'):
            query += " AND location LIKE ?"
            params.append(f"%{filters['location']}%")
        
        # Order by match score and date
        query += " ORDER BY overall_match DESC, matched_at DESC"
        
        # Add pagination
        if filters.get('limit'):
            query += " LIMIT ?"
            params.append(filters['limit'])
            
            if filters.get('offset'):
                query += " OFFSET ?"
                params.append(filters['offset'])
        
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        
        # Convert rows to dictionaries
        results = []
        for row in cursor.fetchall():
            result = dict(row)
            # Parse JSON fields
            if result.get('scraped_data'):
                try:
                    result['scraped_data'] = json.loads(result['scraped_data'])
                except json.JSONDecodeError:
                    pass
            results.append(result)
        
        return results
    
    def get_job_by_url(self, job_url: str, cv_key: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific job match by URL and CV key.
        
        Args:
            job_url: Job posting URL
            cv_key: CV version key
            
        Returns:
            Job match dictionary or None if not found
        """
        if not self.conn:
            self.connect()
        
        assert self.conn is not None, "Database connection not established"
        
        # Normalize URL
        normalized_url = self.url_normalizer.to_full_url(job_url)
        
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM job_matches
            WHERE job_url = ? AND cv_key = ?
            LIMIT 1
        """, (normalized_url, cv_key))
        
        row = cursor.fetchone()
        if row:
            result = dict(row)
            # Parse JSON fields
            if result.get('scraped_data'):
                try:
                    result['scraped_data'] = json.loads(result['scraped_data'])
                except json.JSONDecodeError:
                    pass
            return result
        
        return None

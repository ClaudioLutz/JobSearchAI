import sqlite3
import logging
import os
from contextlib import contextmanager
from pathlib import Path
from config import config # Import the config OBJECT

# Constants
DATABASE_FILENAME = "jobsearchai.db"

# Logger setup (consider moving to a central logging config if needed)
logger = logging.getLogger(__name__)
# Basic logging config for this module if not configured elsewhere
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def get_database_path() -> Path:
    """Gets the absolute path to the SQLite database file."""
    # Use the get_path METHOD of the config OBJECT
    data_root = config.get_path('data_root') # Get user's data directory from config object
    if not data_root:
        # Fallback or raise error if data_root isn't configured
        logger.error("Data root directory is not configured. Cannot determine database path.")
        # Consider a more robust fallback, maybe user's home dir? For now, raise.
        raise ValueError("Data root directory not configured.")
    return Path(data_root) / DATABASE_FILENAME

def initialize_database():
    """Initializes the database by creating it and the necessary tables if they don't exist."""
    db_path = get_database_path()
    try:
        # Ensure the directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initializing database at: {db_path}")

        # Connect (creates the file if it doesn't exist)
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()

            # Create CVS table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS CVS (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_filename TEXT NOT NULL,
                original_filepath TEXT UNIQUE NOT NULL,
                summary_filepath TEXT UNIQUE,
                html_filepath TEXT UNIQUE,
                processing_timestamp TEXT,
                upload_timestamp TEXT NOT NULL
            );
            """)
            logger.info("Checked/Created CVS table.")

            # Create JOB_DATA_BATCHES table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS JOB_DATA_BATCHES (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_timestamp TEXT NOT NULL,
                source_urls TEXT,
                data_filepath TEXT UNIQUE NOT NULL,
                settings_used TEXT
            );
            """)
            logger.info("Checked/Created JOB_DATA_BATCHES table.")

            # Create JOB_MATCH_REPORTS table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS JOB_MATCH_REPORTS (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_timestamp TEXT NOT NULL,
                report_filepath_json TEXT UNIQUE NOT NULL,
                report_filepath_md TEXT UNIQUE NOT NULL,
                cv_id INTEGER,
                job_data_batch_id INTEGER,
                parameters_used TEXT,
                match_count INTEGER,
                FOREIGN KEY (cv_id) REFERENCES CVS (id) ON DELETE SET NULL,
                FOREIGN KEY (job_data_batch_id) REFERENCES JOB_DATA_BATCHES (id) ON DELETE SET NULL
            );
            """)
            logger.info("Checked/Created JOB_MATCH_REPORTS table.")

            # Create MOTIVATION_LETTERS table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS MOTIVATION_LETTERS (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                generation_timestamp TEXT NOT NULL,
                job_title TEXT,
                company_name TEXT,
                job_url TEXT,
                cv_id INTEGER,
                job_match_report_id INTEGER,
                letter_filepath_json TEXT UNIQUE NOT NULL,
                letter_filepath_html TEXT UNIQUE,
                letter_filepath_docx TEXT UNIQUE,
                scraped_data_filepath TEXT UNIQUE,
                FOREIGN KEY (cv_id) REFERENCES CVS (id) ON DELETE SET NULL,
                FOREIGN KEY (job_match_report_id) REFERENCES JOB_MATCH_REPORTS (id) ON DELETE SET NULL
            );
            """)
            logger.info("Checked/Created MOTIVATION_LETTERS table.")

            conn.commit()
            logger.info("Database initialization complete.")

    except sqlite3.Error as e:
        logger.error(f"Database error during initialization: {e}", exc_info=True)
        raise # Re-raise after logging
    except Exception as e:
        logger.error(f"An unexpected error occurred during database initialization: {e}", exc_info=True)
        raise # Re-raise after logging


def get_db_connection() -> sqlite3.Connection:
    """Establishes and returns a connection to the SQLite database."""
    db_path = get_database_path()
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row # Return rows as dictionary-like objects
        # Enable foreign key support (important!)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error to {db_path}: {e}", exc_info=True)
        raise

@contextmanager
def database_connection():
    """Provides a database connection context manager."""
    conn = None # Initialize conn to None
    try:
        conn = get_db_connection()
        logger.debug("Database connection acquired.")
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Database operation error: {e}", exc_info=True)
        if conn:
            conn.rollback()
            logger.warning("Database transaction rolled back due to error.")
        raise # Re-raise the exception
    except Exception as e:
        logger.error(f"An unexpected error occurred during database operation: {e}", exc_info=True)
        if conn:
            conn.rollback()
            logger.warning("Database transaction rolled back due to unexpected error.")
        raise # Re-raise the exception
    else:
        if conn:
            try:
                conn.commit()
                logger.debug("Database transaction committed.")
            except sqlite3.Error as e:
                logger.error(f"Database commit error: {e}", exc_info=True)
                conn.rollback() # Rollback if commit fails
                raise
    finally:
        if conn:
            conn.close()
            logger.debug("Database connection closed.")

# Example usage (for testing purposes, can be removed later)
if __name__ == "__main__":
    print(f"Database path: {get_database_path()}")
    initialize_database()
    print("Database initialized (or already exists).")

    # Test connection and insert/query (optional)
    try:
        with database_connection() as conn:
            cursor = conn.cursor()
            # Example: Insert dummy CV data (replace with actual logic later)
            # cursor.execute("INSERT INTO CVS (original_filename, original_filepath, summary_filepath, upload_timestamp) VALUES (?, ?, ?, datetime('now'))",
            #                ('test.pdf', 'cv/input/test.pdf', 'cv/processed/test_summary.txt'))
            # print("Dummy CV inserted (if table was empty).")

            # Example: Query CVs
            cursor.execute("SELECT * FROM CVS")
            rows = cursor.fetchall()
            print(f"\nCVs in database ({len(rows)}):")
            for row in rows:
                print(dict(row)) # Print as dictionary

    except Exception as e:
        print(f"Error during test operations: {e}")

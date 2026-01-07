from utils.db_utils import JobMatchDatabase
from models.application_status import ApplicationStatus

# Set up logging using centralized configuration
from utils.logging_config import get_logger
logger = get_logger("application_service")

def get_application_status(job_match_id):
    """
    Get the status of an application by job_match_id.
    Returns 'MATCHED' if no application record exists.
    """
    db = JobMatchDatabase()
    try:
        return db.get_application_status(job_match_id)
    except Exception as e:
        logger.error(f"Error getting application status: {e}")
        return ApplicationStatus.MATCHED.value
    finally:
        db.close()

def update_application_status(job_match_id, new_status, notes=None):
    """
    Update or create an application status.
    Returns True on success, False on failure.
    Automatically updates updated_at timestamp.
    """
    db = JobMatchDatabase()
    try:
        return db.update_application_status(job_match_id, new_status, notes)
    except Exception as e:
        logger.error(f"Error updating application status: {e}")
        return False
    finally:
        db.close()

def add_application_note(job_match_id, note):
    """Add or append a note to an application."""
    db = JobMatchDatabase()
    try:
        return db.add_application_note(job_match_id, note)
    except Exception as e:
        logger.error(f"Error adding application note: {e}")
        return False
    finally:
        db.close()

def get_application_by_job_match_id(job_match_id):
    """Get full application record."""
    db = JobMatchDatabase()
    try:
        return db.get_application_by_job_match_id(job_match_id)
    except Exception as e:
        logger.error(f"Error getting application: {e}")
        return None
    finally:
        db.close()

def get_application_pipeline_stats(cv_key=None):
    """
    Get count of jobs in each status stage.
    If cv_key is provided, filter by that CV.
    
    Returns:
        dict: Status counts including TOTAL_ACTIVE, TOTAL_CLOSED, TOTAL_ALL
    """
    db = JobMatchDatabase()
    try:
        db.connect()
        cursor = db.conn.cursor()
        
        # Query with LEFT JOIN to include jobs without application records
        query = '''
            SELECT 
                COALESCE(app.status, 'MATCHED') as status,
                COUNT(*) as count
            FROM job_matches jm
            LEFT JOIN applications app ON jm.id = app.job_match_id
        '''
        
        params = []
        if cv_key:
            query += ' WHERE jm.cv_key = ?'
            params.append(cv_key)
        
        query += ' GROUP BY COALESCE(app.status, "MATCHED")'
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # Initialize stats dictionary with all possible statuses
        stats = {
            'MATCHED': 0,
            'INTERESTED': 0,
            'PREPARING': 0,
            'APPLIED': 0,
            'INTERVIEW': 0,
            'OFFER': 0,
            'REJECTED': 0,
            'ARCHIVED': 0
        }
        
        # Populate with actual counts
        for row in results:
            status, count = row
            if status in stats:
                stats[status] = count
        
        # Calculate totals
        stats['TOTAL_ACTIVE'] = (
            stats['MATCHED'] + 
            stats['INTERESTED'] + 
            stats['PREPARING'] + 
            stats['APPLIED'] + 
            stats['INTERVIEW'] + 
            stats['OFFER']
        )
        stats['TOTAL_CLOSED'] = stats['REJECTED'] + stats['ARCHIVED']
        stats['TOTAL_ALL'] = stats['TOTAL_ACTIVE'] + stats['TOTAL_CLOSED']
        
        logger.info(f"Pipeline stats for cv_key={cv_key}: {stats['TOTAL_ALL']} total jobs")
        return stats
        
    except Exception as e:
        logger.error(f"Error getting pipeline stats: {e}")
        return {
            'MATCHED': 0, 'INTERESTED': 0, 'PREPARING': 0,
            'APPLIED': 0, 'INTERVIEW': 0, 'OFFER': 0,
            'REJECTED': 0, 'ARCHIVED': 0,
            'TOTAL_ACTIVE': 0, 'TOTAL_CLOSED': 0, 'TOTAL_ALL': 0
        }
    finally:
        db.close()

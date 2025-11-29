from enum import Enum

class ApplicationStatus(Enum):
    MATCHED = "MATCHED"
    INTERESTED = "INTERESTED"
    PREPARING = "PREPARING"
    APPLIED = "APPLIED"
    INTERVIEW = "INTERVIEW"
    OFFER = "OFFER"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"
    
    @classmethod
    def is_valid(cls, status_str):
        """Validate if a status string is valid."""
        return status_str in [s.value for s in cls]
    
    @classmethod
    def get_all_values(cls):
        """Return list of all valid status values."""
        return [s.value for s in cls]

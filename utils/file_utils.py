"""
File operation utilities for JobsearchAI.

This module provides functions for common file operations used across the application,
leveraging the centralized configuration for consistent path resolution.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, cast

# Import the configuration module
from config import config

# Set up logging
logger = logging.getLogger(__name__)

def get_latest_file(
    directory: Union[str, Path], 
    pattern: str
) -> Optional[Path]:
    """
    Get the most recent file matching a pattern in a directory.
    
    Args:
        directory: Directory path (string or Path) or path name from config
        pattern: Glob pattern to match files
        
    Returns:
        Path to the most recent file, or None if no matching files found
    
    Example:
        latest_job_data = get_latest_file("job_data", "job_data_*.json")
    """
    # Resolve directory path
    if isinstance(directory, str):
        # Check if it's a named path in config
        config_path = config.get_path(directory)
        if config_path:
            dir_path = config_path
        else:
            # Use as a literal path
            dir_path = Path(directory)
    else:
        dir_path = directory
    
    # Check if directory exists
    if not dir_path.exists():
        logger.warning(f"Directory does not exist: {dir_path}")
        return None
    
    # Find matching files
    matching_files = list(dir_path.glob(pattern))
    if not matching_files:
        logger.info(f"No files matching '{pattern}' found in {dir_path}")
        return None
    
    # Return the most recent file
    return max(matching_files, key=lambda x: x.stat().st_mtime)

def load_json_file(
    file_path: Union[str, Path],
    default: Any = None,
    encoding: str = 'utf-8'
) -> Any:
    """
    Load data from a JSON file with error handling.
    
    Args:
        file_path: Path to the JSON file
        default: Value to return if loading fails
        encoding: File encoding
        
    Returns:
        Loaded JSON data, or default value if loading fails
    
    Example:
        settings = load_json_file("settings.json", default={})
    """
    # Convert to Path if string
    if isinstance(file_path, str):
        # Check if it's a named path in config
        config_path = config.get_path(file_path)
        if config_path and config_path.is_file():
            path = config_path
        else:
            # Use as a literal path
            path = Path(file_path)
    else:
        path = file_path
    
    # Check if file exists
    if not path.exists():
        logger.warning(f"File does not exist: {path}")
        return default
    
    # Load JSON
    try:
        with open(path, 'r', encoding=encoding) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in {path}: {e}")
        return default
    except Exception as e:
        logger.error(f"Error loading JSON from {path}: {e}")
        return default

def save_json_file(
    data: Any,
    file_path: Union[str, Path],
    encoding: str = 'utf-8',
    indent: int = 2,
    ensure_ascii: bool = False
) -> bool:
    """
    Save data to a JSON file with error handling.
    
    Args:
        data: Data to save
        file_path: Path to the JSON file
        encoding: File encoding
        indent: JSON indentation level
        ensure_ascii: Whether to escape non-ASCII characters
        
    Returns:
        True if saving succeeded, False otherwise
    
    Example:
        success = save_json_file(data, "output/results.json")
    """
    # Convert to Path if string
    if isinstance(file_path, str):
        # Check if it's a named path in config
        config_path = config.get_path(file_path)
        if config_path:
            path = config_path
        else:
            # Use as a literal path
            path = Path(file_path)
    else:
        path = file_path
    
    # Create parent directories if they don't exist
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save JSON
    try:
        with open(path, 'w', encoding=encoding) as f:
            json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
        logger.info(f"Saved JSON data to {path}")
        return True
    except Exception as e:
        logger.error(f"Error saving JSON to {path}: {e}")
        return False

def flatten_nested_job_data(job_data: Any) -> List[Dict[str, Any]]:
    """
    Flatten nested job data structures into a simple list of job listings.
    
    This handles various nested structures found in the job data files:
    - Array of arrays (flattened)
    - Dictionary with "content" key
    - List of dictionaries with "content" keys
    - Flat array of job listings
    
    Args:
        job_data: Job data in various formats
        
    Returns:
        Flattened list of job listings
    
    Example:
        job_listings = flatten_nested_job_data(raw_job_data)
    """
    if job_data is None:
        return []
    
    job_listings = []
    
    try:
        # Handle array of arrays structure
        if isinstance(job_data, list) and len(job_data) > 0 and isinstance(job_data[0], list):
            # Flatten the array of arrays
            for job_array in job_data:
                if isinstance(job_array, list):
                    job_listings.extend(job_array)
                else:
                    job_listings.append(job_array)
        
        # Handle dictionary with "content" key
        elif isinstance(job_data, dict) and "content" in job_data:
            content = job_data["content"]
            if isinstance(content, list):
                job_listings.extend(content)
            else:
                job_listings.append(content)
        
        # Handle list of dictionaries with "content" keys
        elif isinstance(job_data, list):
            for item in job_data:
                if isinstance(item, dict) and "content" in item:
                    content = item["content"]
                    if isinstance(content, list):
                        job_listings.extend(content)
                    else:
                        job_listings.append(content)
                else:
                    # Assume item is a job listing
                    job_listings.append(item)
        
        # Default: assume job_data is already a flat list or single item
        else:
            if isinstance(job_data, list):
                job_listings = job_data
            else:
                job_listings = [job_data]
        
        # Filter out any non-dictionary items
        job_listings = [job for job in job_listings if isinstance(job, dict)]
        
        logger.info(f"Flattened job data containing {len(job_listings)} listings")
        return job_listings
    
    except Exception as e:
        logger.error(f"Error flattening job data: {e}")
        return []

def create_timestamped_filename(
    base_name: str,
    extension: str,
    timestamp_format: str = "%Y%m%d_%H%M%S"
) -> str:
    """
    Create a filename with a timestamp.
    
    Args:
        base_name: Base filename
        extension: File extension (without dot)
        timestamp_format: Format for the timestamp
        
    Returns:
        Timestamped filename
    
    Example:
        filename = create_timestamped_filename("job_matches", "json")
        # Returns: "job_matches_20250427_095200.json"
    """
    timestamp = datetime.now().strftime(timestamp_format)
    return f"{base_name}_{timestamp}.{extension}"

def ensure_output_directory(output_dir: Union[str, Path]) -> Path:
    """
    Ensure an output directory exists.
    
    Args:
        output_dir: Directory path or config path name
        
    Returns:
        Path object for the directory
    
    Example:
        output_path = ensure_output_directory("job_matches")
    """
    # Resolve directory path
    if isinstance(output_dir, str):
        # Check if it's a named path in config
        config_path = config.get_path(output_dir)
        if config_path:
            dir_path = config_path
        else:
            # Use as a literal path
            dir_path = Path(output_dir)
    else:
        dir_path = output_dir
    
    # Create directory if it doesn't exist
    dir_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Ensured output directory exists: {dir_path}")
    
    return dir_path

def load_text_file(
    file_path: Union[str, Path],
    default: Optional[str] = None,
    encoding: str = 'utf-8'
) -> Optional[str]:
    """
    Load text from a file with error handling.
    
    Args:
        file_path: Path to the text file
        default: Value to return if loading fails
        encoding: File encoding
        
    Returns:
        File content as string, or default if loading fails
    
    Example:
        cv_summary = load_text_file("process_cv/cv-data/processed/Lebenslauf_summary.txt")
    """
    # Convert to Path if string
    if isinstance(file_path, str):
        # Check if it's a named path in config
        config_path = config.get_path(file_path)
        if config_path and config_path.is_file():
            path = config_path
        else:
            # Use as a literal path
            path = Path(file_path)
    else:
        path = file_path
    
    # Check if file exists
    if not path.exists():
        logger.warning(f"File does not exist: {path}")
        return default
    
    # Load text
    try:
        with open(path, 'r', encoding=encoding) as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error loading text from {path}: {e}")
        return default

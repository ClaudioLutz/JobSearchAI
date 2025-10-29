"""
JobsearchAI Centralized Configuration Module

This module provides centralized access to all configuration settings across the application
while maintaining backward compatibility with existing configuration approaches.

IMPORTANT: This module does NOT change any existing configuration files or values - it simply
provides a unified interface for accessing them.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from dotenv import load_dotenv

# Set up logging
logger = logging.getLogger("config")
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

class ConfigManager:
    """
    Centralized configuration management for JobsearchAI.
    
    This class provides access to all configuration settings while preserving
    the existing configuration structure and values.
    """
    _instance = None
    
    def __new__(cls):
        """Singleton pattern implementation"""
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the configuration manager (only once)"""
        if self._initialized:
            return
        
        # Initialize base paths
        self.PROJECT_ROOT = Path(os.getcwd()).resolve()
        
        # Load environment variables
        self._load_environment()
        
        # Initialize path mappings
        self._setup_paths()
        
        # Load settings from job-data-acquisition/settings.json
        self._load_settings()
        
        # Set default values
        self._setup_defaults()
        
        # Validate critical configurations
        self._validate_config()
        
        # Log initialization complete
        logger.info(f"Configuration manager initialized. Project root: {self.PROJECT_ROOT}")
        self._initialized = True
    
    def _load_environment(self):
        """Load environment variables from .env files (without changing how they're loaded)"""
        self.ENV = {}
        
        # We're not changing how env vars are loaded in existing components,
        # just providing a cache and centralized access
        
        # env_path is typically loaded from process_cv/.env
        env_path = self.PROJECT_ROOT / "process_cv" / ".env"
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)
            logger.info(f"Loaded environment variables from {env_path}")
        
        # Cache commonly used environment variables
        self.ENV["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
        
        # Database environment variables
        self.ENV["DATABASE_URL"] = os.getenv("DATABASE_URL")
        self.ENV["DB_NAME"] = os.getenv("DB_NAME", "jobsearchai")
        self.ENV["DB_USER"] = os.getenv("DB_USER", "jobsearchai_user")
        self.ENV["DB_PASSWORD"] = os.getenv("DB_PASSWORD")
        self.ENV["DB_HOST"] = os.getenv("DB_HOST", "localhost")
        self.ENV["DB_PORT"] = os.getenv("DB_PORT", "5432")
        self.ENV["SECRET_KEY"] = os.getenv("SECRET_KEY")
        
        # Log warning if critical variables are missing
        if not self.ENV["OPENAI_API_KEY"]:
            logger.warning("OPENAI_API_KEY environment variable not found")
        if not self.ENV["SECRET_KEY"]:
            logger.warning("SECRET_KEY environment variable not found")
        if not self.ENV["DATABASE_URL"] and not self.ENV["DB_PASSWORD"]:
            logger.warning("Database credentials not found in environment variables")
    
    def _setup_paths(self):
        """Set up path mappings to all important directories and files"""
        self.PATHS = {}
        
        # Main directories
        self.PATHS.update({
            "project_root": self.PROJECT_ROOT,
            "process_cv": self.PROJECT_ROOT / "process_cv",
            "job_data_acquisition": self.PROJECT_ROOT / "job-data-acquisition",
            "job_matches": self.PROJECT_ROOT / "job_matches",
            "motivation_letters": self.PROJECT_ROOT / "motivation_letters",
            "applications": self.PROJECT_ROOT / "applications",
            "templates": self.PROJECT_ROOT / "templates",
            "static": self.PROJECT_ROOT / "static",
            "blueprints": self.PROJECT_ROOT / "blueprints",
            "logs": self.PROJECT_ROOT / "logs",
        })
        
        # Subdirectories and files
        self.PATHS.update({
            # CV processing
            "cv_data": self.PATHS["process_cv"] / "cv-data",
            "cv_data_input": self.PATHS["process_cv"] / "cv-data" / "input",
            "cv_data_processed": self.PATHS["process_cv"] / "cv-data" / "processed",
            "cv_data_html": self.PATHS["process_cv"] / "cv-data" / "html",
            
            # Job data
            "job_data": self.PATHS["job_data_acquisition"] / "data",
            
            # Templates and settings
            "env_file": self.PATHS["process_cv"] / ".env",
            "settings_json": self.PATHS["job_data_acquisition"] / "settings.json",
            "letter_template": self.PATHS["motivation_letters"] / "template" / "motivation_letter_template.docx",
        })
        
        # Log warnings for critical paths that don't exist
        for name, path in self.PATHS.items():
            if not path.exists() and name not in ["cv_data_input", "cv_data_processed", "cv_data_html"]:
                logger.warning(f"Path does not exist: {name} ({path})")
    
    def _load_settings(self):
        """Load settings from settings.json (without changing the file)"""
        self.SETTINGS = {}
        
        settings_path = self.PATHS.get("settings_json")
        if settings_path and settings_path.exists():
            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    self.SETTINGS = json.load(f)
                logger.info(f"Loaded settings from {settings_path}")
            except Exception as e:
                logger.error(f"Error loading settings from {settings_path}: {e}")
    
    def _setup_defaults(self):
        """Set up default values for parameters (matching current implementation)"""
        self.DEFAULTS = {
            # Job matcher defaults (from job_matcher.py)
            "job_matcher": {
                "min_score": 6,
                "cli_min_score": 3,  # When run from CLI
                "max_jobs": 500,
                "max_results": 500
            },
            
            # OpenAI API defaults (from various files)
            "openai": {
                "model": "gpt-4.1",
                "temperature": 0.1,
                "max_tokens": 1600
            },
            
            # ScrapeGraphAI defaults (from settings.json if available)
            "scraper": {
                "max_pages": self.SETTINGS.get("scraper", {}).get("max_pages", 50),
                "headless": self.SETTINGS.get("scraper", {}).get("headless", True),
                "verbose": self.SETTINGS.get("scraper", {}).get("verbose", False)
            }
        }
    
    def _validate_config(self):
        """Validate critical configuration elements and log warnings"""
        # Check for critical environment variables
        if not self.ENV.get("OPENAI_API_KEY"):
            logger.warning("OPENAI_API_KEY not set - some functionality will be unavailable")
        
        # Check if critical paths exist
        critical_paths = ["cv_data", "job_data", "job_matches", "motivation_letters"]
        for path_name in critical_paths:
            path = self.PATHS.get(path_name)
            if not path or not path.exists():
                logger.warning(f"Critical path does not exist: {path_name} ({path})")
    
    # Public accessor methods
    
    def get_path(self, path_name: str) -> Optional[Path]:
        """Get a path by name"""
        path = self.PATHS.get(path_name)
        if not path:
            logger.warning(f"Requested path not found: {path_name}")
        return path
    
    def get_env(self, var_name: str, default: Optional[str] = None) -> Optional[str]:
        """Get an environment variable (with optional default)"""
        # First check our cache
        value = self.ENV.get(var_name)
        if value is not None:
            return value
        
        # Fall back to checking the environment directly
        value = os.getenv(var_name, default)
        
        # Update our cache
        self.ENV[var_name] = value
        
        return value
    
    def get_setting(self, section: str, setting: str, default: Any = None) -> Any:
        """Get a setting from settings.json"""
        return self.SETTINGS.get(section, {}).get(setting, default)
    
    def get_default(self, section: str, param: str, default: Any = None) -> Any:
        """Get a default parameter value"""
        return self.DEFAULTS.get(section, {}).get(param, default)
    
    def get_latest_file(self, dir_path: Union[str, Path], pattern: str) -> Optional[Path]:
        """Get the latest file matching a pattern in a directory"""
        if isinstance(dir_path, str):
            dir_path = self.get_path(dir_path) or Path(dir_path)
        
        if not dir_path.exists():
            logger.warning(f"Directory does not exist: {dir_path}")
            return None
        
        matching_files = list(dir_path.glob(pattern))
        if not matching_files:
            logger.warning(f"No files matching '{pattern}' found in {dir_path}")
            return None
        
        # Sort by modification time (newest first)
        return max(matching_files, key=lambda x: x.stat().st_mtime)
    
    def ensure_dir(self, path_name: str) -> Path:
        """Ensure a directory exists and return its path"""
        path = self.get_path(path_name)
        if path:
            path.mkdir(parents=True, exist_ok=True)
        return path

# Global config instance
config = ConfigManager()

# Convenience functions to match styles used in different modules
def get_openai_api_key() -> Optional[str]:
    """Get the OpenAI API key"""
    return config.get_env("OPENAI_API_KEY")

def get_project_root() -> Path:
    """Get the project root directory"""
    return config.get_path("project_root")

def get_latest_job_data_file() -> Optional[Path]:
    """Get the latest job data file"""
    return config.get_latest_file("job_data", "job_data_*.json")

def get_cv_data_processed_dir() -> Path:
    """Get the CV data processed directory"""
    return config.get_path("cv_data_processed")

def get_job_matcher_defaults() -> Dict[str, Any]:
    """Get the job matcher default parameters"""
    return {
        "min_score": config.get_default("job_matcher", "min_score"),
        "max_jobs": config.get_default("job_matcher", "max_jobs"),
        "max_results": config.get_default("job_matcher", "max_results")
    }

def get_openai_defaults() -> Dict[str, Any]:
    """Get the OpenAI API default parameters"""
    return {
        "model": config.get_default("openai", "model"),
        "temperature": config.get_default("openai", "temperature"),
        "max_tokens": config.get_default("openai", "max_tokens")
    }

def get_database_url() -> Optional[str]:
    """Get the database URL for SQLAlchemy"""
    # First try full DATABASE_URL if provided
    database_url = config.get_env("DATABASE_URL")
    if database_url:
        return database_url
    
    # Otherwise construct from individual components
    db_user = config.get_env("DB_USER")
    db_password = config.get_env("DB_PASSWORD")
    db_host = config.get_env("DB_HOST")
    db_port = config.get_env("DB_PORT")
    db_name = config.get_env("DB_NAME")
    
    if all([db_user, db_password, db_host, db_name]):
        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    return None

def get_secret_key() -> Optional[str]:
    """Get the Flask secret key"""
    return config.get_env("SECRET_KEY")

def get_database_config() -> Dict[str, Any]:
    """Get complete database configuration for Flask"""
    return {
        "SQLALCHEMY_DATABASE_URI": get_database_url(),
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SQLALCHEMY_ECHO": False  # Set to True for debugging
    }

# Main function to be called if this module is run directly
if __name__ == "__main__":
    # Simple test to verify configuration loading
    print(f"Project root: {config.get_path('project_root')}")
    print(f"OpenAI API key: {'Set' if config.get_env('OPENAI_API_KEY') else 'Not set'}")
    print(f"Latest job data file: {get_latest_job_data_file()}")
    print(f"Job matcher defaults: {get_job_matcher_defaults()}")

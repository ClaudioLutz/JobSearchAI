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
import sys
import keyring
import appdirs
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

        # Define user config and data directories
        self.APP_NAME = "JobsearchAI"
        self.USER_CONFIG_DIR = Path(appdirs.user_config_dir(self.APP_NAME))
        self.USER_CONFIG_FILE = self.USER_CONFIG_DIR / "settings.json"
        self.USER_DATA_DIR = Path(appdirs.user_data_dir(self.APP_NAME))

        # Ensure user directories exist
        self.USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"User Config Dir: {self.USER_CONFIG_DIR}")
        logger.info(f"User Data Dir: {self.USER_DATA_DIR}")

        # Load user settings first (needed for custom data dir)
        self._load_user_settings()

        # Determine project root (different for dev vs packaged app, uses user settings)
        self.PROJECT_ROOT = self._determine_project_root()

        # Load environment variables (primarily for dev, API keys handled separately)
        self._load_environment() # Keep for potential non-API env vars

        # Initialize path mappings (uses PROJECT_ROOT)
        self._setup_paths()
        
        # Load settings from job-data-acquisition/settings.json
        self._load_settings()
        
        # Set default values
        self._setup_defaults()
        
        # Validate critical configurations
        self._validate_config()
        
        # Log initialization complete
        logger.info(f"Configuration manager initialized. Project root: {self.PROJECT_ROOT}, User settings loaded: {'Yes' if hasattr(self, 'USER_SETTINGS') else 'No'}")
        self._initialized = True

    def _determine_project_root(self) -> Path:
        """Determine the effective root directory for data storage."""
        # If running as a packaged app (e.g., PyInstaller)
        if getattr(sys, 'frozen', False):
            # Use the user data directory for packaged apps
            logger.info("Running in packaged mode. Using user data directory for data.")
            # Use custom data dir if set by user
            custom_data_dir = self.USER_SETTINGS.get('custom_data_dir')
            if custom_data_dir:
                 logger.info(f"Using custom data directory: {custom_data_dir}")
                 return Path(custom_data_dir)
            return self.USER_DATA_DIR
        else:
            # Use the current working directory for development
            logger.info("Running in development mode. Using CWD for data.")
            return Path(os.getcwd()).resolve()

    def _load_user_settings(self):
        """Load user-specific settings from the user config directory."""
        self.USER_SETTINGS = {}
        if self.USER_CONFIG_FILE.exists():
            try:
                with open(self.USER_CONFIG_FILE, "r", encoding="utf-8") as f:
                    self.USER_SETTINGS = json.load(f)
                logger.info(f"Loaded user settings from {self.USER_CONFIG_FILE}")
            except json.JSONDecodeError:
                logger.error(f"Error decoding JSON from {self.USER_CONFIG_FILE}. Using empty settings.")
            except Exception as e:
                logger.error(f"Error loading user settings from {self.USER_CONFIG_FILE}: {e}")
        else:
            logger.info(f"User settings file not found at {self.USER_CONFIG_FILE}. Will create on save.")

    def save_user_settings(self):
        """Save current user settings to the config file."""
        try:
            self.USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(self.USER_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.USER_SETTINGS, f, indent=2, sort_keys=True)
            logger.info(f"Saved user settings to {self.USER_CONFIG_FILE}")
            return True
        except Exception as e:
            logger.error(f"Error saving user settings to {self.USER_CONFIG_FILE}: {e}")
            return False

    def _load_environment(self):
        """Load environment variables from .env files (primarily for dev)."""
        self.ENV = {}
        # Determine potential .env locations based on CWD (dev environment)
        cwd_root = Path(os.getcwd()).resolve()
        env_path_root = cwd_root / ".env"
        env_path_cv = cwd_root / "process_cv" / ".env" # Legacy location

        # Load .env from project root (if exists, for dev)
        if env_path_root.exists():
             load_dotenv(dotenv_path=env_path_root)
             logger.info(f"Loaded environment variables from {env_path_root}")

        # Load .env from process_cv (legacy, for dev, potentially overrides root)
        if env_path_cv.exists():
            load_dotenv(dotenv_path=env_path_cv, override=True)
            logger.info(f"Loaded environment variables from {env_path_cv}")

        # Cache relevant environment variables (EXCLUDING API keys, handled by get_api_key)
        # Example: self.ENV["SOME_OTHER_VAR"] = os.getenv("SOME_OTHER_VAR")
        # No need to cache OPENAI_API_KEY here anymore.
    def _setup_paths(self):
        """Set up path mappings, differentiating data and code paths."""
        self.PATHS = {}
        # Use self.PROJECT_ROOT (determined by _determine_project_root) for DATA paths
        data_root = self.PROJECT_ROOT

        # Determine the root directory for CODE assets (templates, static)
        if getattr(sys, 'frozen', False):
            # Packaged app: assets are relative to sys._MEIPASS
            code_root = Path(sys._MEIPASS)
            logger.info(f"Packaged mode detected. Code root (sys._MEIPASS): {code_root}")
        else:
            # Development mode: assets are relative to the script's CWD
            code_root = Path(os.getcwd()).resolve()
            logger.info(f"Development mode detected. Code root (CWD): {code_root}")

        # --- Data Paths (relative to data_root) ---
        self.PATHS.update({
            "data_root": data_root, # Effective root for user data storage
            "process_cv": data_root / "process_cv",
            "job_data_acquisition": data_root / "job-data-acquisition",
            "job_matches": data_root / "job_matches",
            "motivation_letters": data_root / "motivation_letters",
            "logs": data_root / "logs",
            # CV processing subdirs
            "cv_data": data_root / "process_cv" / "cv-data",
            "cv_data_input": data_root / "process_cv" / "cv-data" / "input",
            "cv_data_processed": data_root / "process_cv" / "cv-data" / "processed",
            "cv_data_html": data_root / "process_cv" / "cv-data" / "html",
            # Job data subdir
            "job_data": data_root / "job-data-acquisition" / "data",
        })

        # --- Code/Asset Paths (relative to code_root) ---
        self.PATHS.update({
            "code_root": code_root, # Root where code/assets reside
            "templates": code_root / "templates",
            "static": code_root / "static",
            "blueprints": code_root / "blueprints", # Might not be needed directly if using Flask discovery
            "utils": code_root / "utils", # Might not be needed directly
            # Original scraper settings file (part of the code bundle)
            "settings_json": code_root / "job-data-acquisition" / "settings.json",
            # Letter template file (part of the code bundle)
            "letter_template_dir": code_root / "motivation_letters" / "template",
            "letter_template": code_root / "motivation_letters" / "template" / "motivation_letter_template.docx",
        })

        # --- User Configuration Paths ---
        self.PATHS.update({
            "user_config_dir": self.USER_CONFIG_DIR,
            "user_config_file": self.USER_CONFIG_FILE,
        })

        # --- Ensure essential DATA directories exist ---
        data_dirs_to_ensure = [
            "process_cv", "job_data_acquisition", "job_matches",
            "motivation_letters", "logs", "cv_data", "cv_data_input",
            "cv_data_processed", "cv_data_html", "job_data",
            "letter_template_dir" # Ensure template dir exists within data for potential user overrides? No, keep template with code.
        ]
        # Ensure the base data directories exist
        for dir_key in data_dirs_to_ensure:
             path = self.PATHS.get(dir_key)
             if path:
                 try:
                     path.mkdir(parents=True, exist_ok=True)
                 except OSError as e:
                     logger.error(f"Failed to create directory {path}: {e}")
             else:
                 logger.error(f"Path key '{dir_key}' not found in PATHS dictionary during directory creation.")


        # Log warnings for critical CODE/ASSET paths that don't exist
        # These should generally exist in both dev and packaged mode
        code_asset_paths_to_check = ["templates", "static", "letter_template"]
        for name in code_asset_paths_to_check:
             path = self.PATHS.get(name)
             # Check if it's a file or directory as appropriate
             exists = path.is_file() if name == "letter_template" else path.is_dir()
             if not path or not exists:
                 logger.warning(f"Required code/asset path does not exist or is not the correct type: {name} ({path})")
    
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
        # Check for required API keys using the new method
        if not self.has_required_api_keys():
            logger.warning("OpenAI API key is not configured. Please configure it via the setup wizard or configuration UI.")

        # Check if critical data paths exist (should have been created, but double-check)
        critical_data_paths = ["cv_data", "job_data", "job_matches", "motivation_letters"] # Define the list here
        for path_name in critical_data_paths: # Iterate over the defined list
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

    # --- API Key Management ---

    def get_api_key(self, service="openai") -> Optional[str]:
        """Get API key securely, checking keyring first, then user settings."""
        key_name = f"{service.upper()}_API_KEY" # e.g., OPENAI_API_KEY
        # 1. Check keyring
        try:
            key = keyring.get_password(self.APP_NAME, key_name)
            if key:
                logger.debug(f"Retrieved {service} API key from keyring.")
                return key
        except Exception as e:
            # Log keyring errors but don't stop the process
            logger.warning(f"Could not access keyring for {service} API key: {e}")

        # 2. Check user settings file (less secure fallback)
        key = self.USER_SETTINGS.get("api_keys", {}).get(key_name)
        if key:
            logger.debug(f"Retrieved {service} API key from user settings file.")
            return key

        logger.warning(f"{service} API key not found in keyring or user settings.")
        return None

    def set_api_key(self, service: str, key: str) -> bool:
        """Store API key securely, preferring keyring."""
        key_name = f"{service.upper()}_API_KEY"
        # 1. Try storing in keyring
        try:
            keyring.set_password(self.APP_NAME, key_name, key)
            logger.info(f"Stored {service} API key in system keyring.")
            # Optionally remove from settings file if it was there before
            if "api_keys" in self.USER_SETTINGS and key_name in self.USER_SETTINGS["api_keys"]:
                del self.USER_SETTINGS["api_keys"][key_name]
                if not self.USER_SETTINGS["api_keys"]: # Remove empty dict
                    del self.USER_SETTINGS["api_keys"]
                self.save_user_settings()
            return True
        except Exception as e:
            logger.warning(f"Could not store {service} API key in keyring: {e}. Falling back to user settings file.")

            # 2. Fallback to storing in user settings file
            if "api_keys" not in self.USER_SETTINGS:
                self.USER_SETTINGS["api_keys"] = {}
            self.USER_SETTINGS["api_keys"][key_name] = key
            return self.save_user_settings()

    def has_required_api_keys(self) -> bool:
        """Check if all required API keys (currently just OpenAI) are configured."""
        return bool(self.get_api_key("openai"))

    # --- First Run Check ---

    def is_first_run(self) -> bool:
        """Check if the application appears to be running for the first time."""
        # Crude check: Does the user config file exist AND contain the setup_complete flag?
        return not (self.USER_CONFIG_FILE.exists() and self.USER_SETTINGS.get("setup_complete", False))


# Global config instance
config = ConfigManager()

# Convenience functions to match styles used in different modules
def get_openai_api_key() -> Optional[str]:
    """Get the OpenAI API key using the secure method."""
    return config.get_api_key("openai")

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

# Main function to be called if this module is run directly
if __name__ == "__main__":
    # Simple test to verify configuration loading
    print(f"Project root: {config.get_path('project_root')}")
    print(f"OpenAI API key: {'Set' if config.get_env('OPENAI_API_KEY') else 'Not set'}")
    print(f"Latest job data file: {get_latest_job_data_file()}")
    print(f"Job matcher defaults: {get_job_matcher_defaults()}")

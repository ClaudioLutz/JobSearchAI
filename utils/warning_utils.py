"""
Utility functions for handling deprecation warnings, particularly for pkg_resources.

This module provides functions to suppress specific warnings that are common in
third-party libraries, especially the pkg_resources deprecation warning from docxcompose.
"""
import warnings
import functools

def suppress_pkg_resources_warning():
    """
    Suppress the pkg_resources deprecation warning.
    
    This is particularly useful for libraries like docxcompose that haven't
    been updated to use the newer importlib APIs yet.
    """
    warnings.filterwarnings(
        "ignore", 
        message="pkg_resources is deprecated as an API.*",
        category=UserWarning,
        module=".*"
    )

def suppress_docxcompose_warnings():
    """
    Suppress warnings specifically from docxcompose and related libraries.
    """
    # Suppress pkg_resources warning from docxcompose
    warnings.filterwarnings(
        "ignore",
        message="pkg_resources is deprecated as an API.*",
        category=UserWarning
    )
    
    # Suppress any other docxcompose related warnings
    warnings.filterwarnings(
        "ignore",
        category=UserWarning,
        module="docxcompose.*"
    )

def with_suppressed_warnings(warning_types=None):
    """
    Decorator to suppress specific warnings for a function.
    
    Args:
        warning_types (list): List of warning types to suppress.
                            Defaults to ['pkg_resources', 'docxcompose']
    
    Usage:
        @with_suppressed_warnings(['pkg_resources'])
        def my_function():
            # Function code that might trigger pkg_resources warnings
            pass
    """
    if warning_types is None:
        warning_types = ['pkg_resources', 'docxcompose']
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with warnings.catch_warnings():
                if 'pkg_resources' in warning_types:
                    suppress_pkg_resources_warning()
                if 'docxcompose' in warning_types:
                    suppress_docxcompose_warnings()
                
                return func(*args, **kwargs)
        return wrapper
    return decorator

# Context manager for temporary warning suppression
class SuppressWarnings:
    """
    Context manager for temporarily suppressing specific warnings.
    
    Usage:
        with SuppressWarnings(['pkg_resources']):
            # Code that might trigger pkg_resources warnings
            from docxtpl import DocxTemplate
    """
    
    def __init__(self, warning_types=None):
        if warning_types is None:
            warning_types = ['pkg_resources', 'docxcompose']
        self.warning_types = warning_types
        self._warnings_manager = None
    
    def __enter__(self):
        # Use the standard warnings.catch_warnings context manager
        self._warnings_manager = warnings.catch_warnings()
        self._warnings_manager.__enter__()
        
        if 'pkg_resources' in self.warning_types:
            suppress_pkg_resources_warning()
        if 'docxcompose' in self.warning_types:
            suppress_docxcompose_warnings()
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Let the warnings context manager handle restoration
        if self._warnings_manager:
            return self._warnings_manager.__exit__(exc_type, exc_val, exc_tb)

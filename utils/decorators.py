"""
Decorators for common patterns in JobsearchAI.

This module provides decorators for error handling, logging, and other common patterns
that can be applied consistently across the application.
"""

import functools
import logging
import time
import traceback
from typing import Any, Callable, Dict, Optional, TypeVar, Union, cast

# Type variable for functions
F = TypeVar('F', bound=Callable[..., Any])

def handle_exceptions(
    default_return: Any = None,
    log_level: int = logging.ERROR,
    logger: Optional[logging.Logger] = None
) -> Callable[[F], F]:
    """
    Decorator to handle exceptions in a consistent way.
    
    Args:
        default_return: Value to return if an exception occurs
        log_level: Logging level for exceptions
        logger: Logger to use. If None, uses the logger from the module where the decorated function is defined
    
    Returns:
        Decorated function
    
    Example:
        @handle_exceptions(default_return=[])
        def get_data():
            # Function that might raise an exception
            return some_operation()
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            nonlocal logger
            
            # Use the module's logger if none is provided
            if logger is None:
                logger = logging.getLogger(func.__module__)
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Get the full traceback
                tb = traceback.format_exc()
                
                # Log the exception
                logger.log(
                    log_level,
                    f"Error in {func.__name__}: {str(e)}\n{tb}"
                )
                
                # Return the default value
                return default_return
        
        return cast(F, wrapper)
    
    return decorator

def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
    logger: Optional[logging.Logger] = None
) -> Callable[[F], F]:
    """
    Decorator to retry a function on failure.
    
    Args:
        max_attempts: Maximum number of attempts
        delay: Initial delay between retries (in seconds)
        backoff_factor: Factor to increase delay by after each retry
        exceptions: Tuple of exceptions to catch and retry on
        logger: Logger to use. If None, uses the logger from the module where the decorated function is defined
    
    Returns:
        Decorated function
    
    Example:
        @retry(max_attempts=3, delay=1.0, exceptions=(ConnectionError, TimeoutError))
        def api_call():
            # Function that might fail temporarily
            return make_request()
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            nonlocal logger
            
            # Use the module's logger if none is provided
            if logger is None:
                logger = logging.getLogger(func.__module__)
            
            attempts = 0
            current_delay = delay
            
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempts += 1
                    
                    if attempts >= max_attempts:
                        logger.error(
                            f"Failed after {attempts} attempts. Error in {func.__name__}: {str(e)}"
                        )
                        raise
                    
                    # Log retry attempt
                    logger.warning(
                        f"Retry {attempts}/{max_attempts} for {func.__name__} after error: {str(e)}"
                        f" Retrying in {current_delay:.2f}s..."
                    )
                    
                    # Wait before retrying
                    time.sleep(current_delay)
                    
                    # Increase delay for next attempt
                    current_delay *= backoff_factor
        
        return cast(F, wrapper)
    
    return decorator

def log_execution_time(
    logger: Optional[logging.Logger] = None,
    level: int = logging.INFO
) -> Callable[[F], F]:
    """
    Decorator to log the execution time of a function.
    
    Args:
        logger: Logger to use. If None, uses the logger from the module where the decorated function is defined
        level: Logging level
    
    Returns:
        Decorated function
    
    Example:
        @log_execution_time()
        def slow_function():
            # Function that might take a long time
            return some_operation()
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            nonlocal logger
            
            # Use the module's logger if none is provided
            if logger is None:
                logger = logging.getLogger(func.__module__)
            
            # Record start time
            start_time = time.time()
            
            # Call the function
            result = func(*args, **kwargs)
            
            # Calculate and log execution time
            execution_time = time.time() - start_time
            logger.log(
                level,
                f"{func.__name__} executed in {execution_time:.2f}s"
            )
            
            return result
        
        return cast(F, wrapper)
    
    return decorator

def cache_result(max_size: int = 128, ttl: Optional[float] = None) -> Callable[[F], F]:
    """
    Simple in-memory cache decorator.
    
    Args:
        max_size: Maximum number of items to cache
        ttl: Time-to-live in seconds. If None, cache entries never expire
    
    Returns:
        Decorated function
    
    Example:
        @cache_result(max_size=100, ttl=3600)  # Cache up to 100 items for 1 hour
        def get_data(id):
            # Function that might be expensive and called frequently with the same args
            return fetch_data_from_api(id)
    """
    def decorator(func: F) -> F:
        # Cache storage: {args_hash: (result, timestamp)}
        cache: Dict[str, tuple] = {}
        # Track order of access for LRU eviction: {args_hash: access_time}
        access_times: Dict[str, float] = {}
        
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Create a cache key from the function arguments
            key_parts = [func.__name__]
            key_parts.extend([str(arg) for arg in args])
            key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
            key = ":".join(key_parts)
            
            # Get current time
            current_time = time.time()
            
            # Check if result is in cache and not expired
            if key in cache:
                result, timestamp = cache[key]
                
                # Check if entry is expired
                if ttl is not None and current_time - timestamp > ttl:
                    # Remove expired entry
                    del cache[key]
                    del access_times[key]
                else:
                    # Update access time
                    access_times[key] = current_time
                    return result
            
            # Call the function
            result = func(*args, **kwargs)
            
            # Store result in cache
            cache[key] = (result, current_time)
            access_times[key] = current_time
            
            # Evict oldest entry if cache is full
            if len(cache) > max_size:
                oldest_key = min(access_times.items(), key=lambda x: x[1])[0]
                del cache[oldest_key]
                del access_times[oldest_key]
            
            return result
        
        return cast(F, wrapper)
    
    return decorator

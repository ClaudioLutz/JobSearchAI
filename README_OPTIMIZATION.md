# JobsearchAI Code Optimization

This document describes the optimizations made to the JobsearchAI codebase to improve configuration management, error handling, and code reusability.

## Overview

The optimization introduces several new modules:

1. **Centralized Configuration**: `config.py` provides a single source of truth for all configuration settings.  
2. **Utility Modules**: A collection of utility modules in the `utils/` package that provide reusable functionality:  
   - `utils/decorators.py`: Decorators for error handling, retries, caching, and execution timing.  
   - `utils/file_utils.py`: Functions for common file operations with improved error handling.  
   - `utils/api_utils.py`: Wrappers for OpenAI API operations with retries and caching.

## Key Benefits

- **No Breaking Changes**: The optimization maintains full compatibility with existing code.  
- **Improved Error Handling**: Consistent error-handling patterns across all modules.  
- **Reduced Code Duplication**: Common functionality is now centralized and reusable.  
- **Better API Usage**: API calls are now cached, retried, and have better error handling.  
- **Centralized Configuration**: All configuration is now managed from a single module.  
- **Type Hints**: All new code includes type hints for better IDE support and code quality.

## Using the New Modules

### Configuration (`config.py`)

```python
# Import the configuration module
from config import config, get_openai_api_key, get_job_matcher_defaults

# Get a path from config
cv_data_dir = config.get_path("cv_data")

# Get an environment variable
api_key = get_openai_api_key()

# Get default parameters
job_matcher_params = get_job_matcher_defaults()

# Ensure a directory exists
logs_dir = config.ensure_dir("logs")
```

### Decorators (`utils/decorators.py`)

```python
from utils.decorators import (
    handle_exceptions,
    retry,
    log_execution_time,
    cache_result,
)

# Handle exceptions with a default return value
@handle_exceptions(default_return=[])
def get_data():
    # Function that might raise an exception
    return some_risky_operation()

# Retry on failure with exponential backoff
@retry(max_attempts=3, delay=1.0, backoff_factor=2.0)
def make_api_call():
    # Function that might fail temporarily
    return api_request()

# Log execution time
@log_execution_time()
def slow_function():
    # Function that might take a long time
    return expensive_operation()

# Cache results to avoid repeated expensive operations
@cache_result(max_size=100, ttl=3600)  # Cache up to 100 items for 1 hour
def get_data_by_id(id):
    # Function that might be called frequently with the same arguments
    return fetch_data_from_api(id)
```

### File Operations (`utils/file_utils.py`)

```python
from utils.file_utils import (
    get_latest_file,
    load_json_file,
    save_json_file,
    flatten_nested_job_data,
    create_timestamped_filename,
    ensure_output_directory,
    load_text_file,
)

# Get the most recent file matching a pattern
latest_job_data = get_latest_file("job_data", "job_data_*.json")

# Load a JSON file with error handling
data = load_json_file(latest_job_data, default=[])

# Flatten nested job data structures
job_listings = flatten_nested_job_data(data)

# Create a timestamped filename
filename = create_timestamped_filename("job_matches", "json")

# Ensure an output directory exists
output_dir = ensure_output_directory("job_matches")

# Save data to a JSON file
save_json_file(job_listings, output_dir / filename)

# Load text from a file
cv_summary = load_text_file(
    "process_cv/cv-data/processed/Lebenslauf_summary.txt"
)
```

### API Operations (`utils/api_utils.py`)

```python
from utils.api_utils import (
    openai_client,
    summarize_cv,
    generate_json_from_prompt,
)

# Generate chat completion
response = openai_client.generate_chat_completion(
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Tell me a joke."},
    ]
)

# Generate structured JSON output
job_details = openai_client.generate_structured_output(
    prompt="Extract job details from this text: ...",
    system_prompt="You are an expert at extracting structured job data.",
)

# Summarize text
summary = openai_client.summarize_text(
    text="Long document to summarize...",
    prompt_template="Provide a concise summary of this document:\n\n{text}",
)

# Generate JSON from a prompt (shorthand)
data = generate_json_from_prompt(
    prompt="Extract job details from this text: ...",
    system_prompt="You are an expert at extracting structured job data.",
)

# Summarize CV (shorthand)
cv_summary = summarize_cv(cv_text)
```

## Implementation Progress

### Completed Optimizations:

1. **job_matcher.py**: ✅ Fully optimized
   - Centralized configuration
   - File utility integration
   - OpenAI API wrapper integration
   - Error handling decorators
   - Fixed f-string issues with JSON templates

2. **job_details_utils.py**: ✅ Fully optimized
   - Centralized configuration 
   - File utility integration
   - OpenAI API wrapper integration
   - Error handling decorators
   - Improved performance tracking with execution time logging

### Pending Optimizations:

1. **letter_generation_utils.py**: Next priority

### Important Considerations for Future Work:

- When using JSON response formats with OpenAI, ensure the prompt includes the word "json"
- When including JSON examples in f-strings, use double curly braces to escape them: `{{` and `}}`
- The `ensure_output_directory` function was renamed to `ensure_output_dir` in job_matcher.py to avoid recursion issues
- Use `@handle_exceptions` on functions that might fail and need graceful fallback
- Use `@log_execution_time` on expensive operations to track performance

## Testing

Two test scripts are provided to verify the optimizations:

- `test_config.py` – tests the centralized-configuration module.  
- `test_optimized_code.py` – shows how to use all the new modules together to improve the job-matcher functionality.  

Run these tests to ensure the optimizations work correctly in your environment:

```bash
python test_config.py
python test_optimized_code.py
```

## Next Steps

To continue the integration process:

1. Optimize `job_details_utils.py` following the same pattern as job_matcher.py
2. Optimize `letter_generation_utils.py` to leverage the new utilities
3. Test each component after optimization
4. Document any challenges or special considerations in this README

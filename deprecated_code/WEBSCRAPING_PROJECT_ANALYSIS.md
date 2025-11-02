# JobSearchAI Playwright Web Scraping Project - Complete Analysis

## Overview

This document provides a comprehensive analysis of the JobSearchAI web scraping project, documenting all technical details, architectural decisions, and potential causes for the deployment vs local environment discrepancies observed in the web scraping functionality.

## Key Issue Summary

**Problem**: Web scraping works locally but fails in deployed Google Cloud Run environment, resulting in:
- Local environment: Successfully extracts 20+ job listings
- Cloud environment: Extracts 0 job listings ("Flattened job data containing 0 listings")

## Project Architecture

### 1. Core Components

#### 1.1 Web Scraping Engine
- **Framework**: ScrapeGraphAI with SmartScraperGraph
- **Browser Engine**: Playwright with Chromium
- **Target Website**: ostjob.ch (Swiss job portal)
- **Language**: Python 3.10

#### 1.2 Main Files
- `job-data-acquisition/app.py` - Standalone Flask scraping service
- `graph_scraper_utils.py` - Original scraping utilities
- `optimized_graph_scraper_utils.py` - Enhanced version with quality monitoring
- `job-data-acquisition/settings.json` - Scraper configuration
- `dashboard.py` - Main Flask application coordinating scraping

### 2. Configuration Analysis

#### 2.1 Settings.json Configuration
```json
{
    "scraper": {
        "llm": {
            "model": "openai/gpt-4.1-mini",
            "api_key": "${OPENAI_API_KEY}",
            "temperature": 0.1
        },
        "headless": false,
        "verbose": true,
        "output_format": "json",
        "max_pages": 2,
        "wait_time": 3,
        "browser_config": {
            "args": [
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-extensions",
                "--disable-plugins",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-features=TranslateUI",
                "--disable-blink-features=AutomationControlled"
            ],
            "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "viewport": {
                "width": 1920,
                "height": 1080
            }
        },
        "timeout": 30000,
        "load_wait": "networkidle"
    }
}
```

**Critical Issues Identified**:
1. **Headless Mode**: Set to `false` in settings but deployment requires `true`
2. **Environment Variables**: Uses `${OPENAI_API_KEY}` substitution pattern
3. **Browser Args**: Configured for Linux environment but may need additional Docker-specific flags

#### 2.2 Environment Variable Handling
- **Pattern**: `${VAR_NAME}` substitution in configuration
- **Implementation**: Custom regex-based substitution in both utilities
- **Risk**: API key availability difference between local and cloud environments

### 3. Docker Configuration Analysis

#### 3.1 Main Application Dockerfile
```dockerfile
FROM python:3.10-slim
# Installs system dependencies for Playwright
# Uses: playwright install chromium
# No Xvfb setup (relies on headless mode)
```

#### 3.2 Job-Data-Acquisition Dockerfile
```dockerfile
FROM python:3.10-slim
# Installs Xvfb for virtual display
# Uses: Xvfb :99 -screen 0 1920x1080x24
# Command: Xvfb in background + Python app
```

**Critical Differences**:
- Separate Dockerfile for scraping service includes Xvfb
- Main Dockerfile doesn't include virtual display setup
- Different browser installation approaches

### 4. Browser Configuration Analysis

#### 4.1 Optimized Configuration (optimized_graph_scraper_utils.py)
```python
"browser_config": {
    "args": [
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-extensions",
        "--disable-plugins",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
        "--disable-features=TranslateUI",
        "--disable-ipc-flooding-protection"
    ],
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "viewport": {"width": 1920, "height": 1080}
},
"headless": True,  # Forced to True in optimized version
"wait_time": 5     # Increased from 3 to 5 seconds
```

#### 4.2 Configuration Inconsistencies
- **Settings.json**: `headless: false`, `wait_time: 3`
- **Optimized utils**: `headless: True`, `wait_time: 5`
- **User Agent**: Linux-based in settings, Windows-based in optimized
- **Browser Args**: Different sets between configurations

### 5. Scraping Workflow Analysis

#### 5.1 Data Flow
1. **Trigger**: User clicks "Run Combined Process" in dashboard
2. **Settings Update**: Updates `max_pages` in settings.json
3. **Background Thread**: Spawns thread for scraping task
4. **Import Execution**: Dynamically imports and executes `job-data-acquisition/app.py`
5. **Scraping**: Iterates through pages (1 to max_pages)
6. **Data Processing**: Saves results to `job-data-acquisition/data/`
7. **Job Matching**: Processes scraped data with CV

#### 5.2 Critical Code Paths

**Dashboard Integration** (blueprints/job_matching_routes.py):
```python
# Dynamic import of scraper
app_path = os.path.join(app.root_path, 'job-data-acquisition', 'app.py')
spec = importlib.util.spec_from_file_location("app_module", app_path)
app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)
run_scraper = getattr(app_module, 'run_scraper', None)
output_file = run_scraper()
```

**Scraper Loop** (job-data-acquisition/app.py):
```python
for url in target_urls:
    for page in range(1, max_pages + 1):
        scraper = configure_scraper(url, page)
        results = scraper.run()
        all_results.append(results)
```

### 6. Environment Differences

#### 6.1 Local Environment Characteristics
- **Platform**: Windows 11 with MINGW64
- **Display**: Available for non-headless operation
- **Browser**: Full Chrome/Chromium with GUI capabilities
- **File System**: Windows paths with backslashes
- **Networking**: Direct internet access

#### 6.2 Cloud Environment Characteristics  
- **Platform**: Google Cloud Run (Linux containers)
- **Display**: No display server (requires headless mode)
- **Browser**: Chromium in container without GUI
- **File System**: Unix paths with forward slashes
- **Networking**: May have different IP ranges/restrictions

#### 6.3 Log Evidence Analysis

**Local Success Pattern**:
```
2025-09-10 20:15:34,591 - job_scraper - INFO - Scraping completed. Results saved to: job-data-acquisition/data/job_data_20250910_201534.json
2025-09-10 20:15:56,435 - utils.file_utils - INFO - Flattened job data containing 20 listings
```

**Cloud Failure Pattern**:
```
2025-09-10 18:05:11 2025-09-10 18:05:11,523 - job_matcher - INFO - Loading job data from /app/job-data-acquisition/data/job_data_20250910_180446.json
2025-09-10 18:05:11 2025-09-10 18:05:11,523 - utils.file_utils - INFO - Flattened job data containing 0 listings
```

### 7. Potential Root Causes

#### 7.1 Browser Configuration Issues
1. **Headless Mode Mismatch**: Settings.json uses `headless: false` but cloud requires `true`
2. **Missing Docker Browser Args**: May need additional flags for containerized Chrome
3. **Display Configuration**: Xvfb setup might not be properly configured
4. **Font Dependencies**: Missing fonts could affect rendering

#### 7.2 Network and Security Issues
1. **Bot Detection**: Target website may detect automated browsing differently in cloud
2. **IP Blocking**: Cloud provider IPs might be blocked
3. **User Agent Mismatch**: Inconsistent user agents between environments
4. **Request Rate Limiting**: Different timing behavior in cloud

#### 7.3 System Dependencies
1. **Missing Libraries**: Container might lack required system libraries
2. **Permissions**: File system permissions in container
3. **Memory Constraints**: Cloud Run memory limits affecting browser
4. **Timeout Issues**: Network timeouts different in cloud environment

#### 7.4 Configuration Management
1. **Environment Variables**: OPENAI_API_KEY availability in cloud
2. **Path Resolution**: Different file system paths between Windows/Linux
3. **Dynamic Imports**: Module loading issues in containerized environment

### 8. Quality Monitoring Features

#### 8.1 Optimized Scraper Features
- **Quality Scoring**: Calculates completeness scores for extracted data
- **Fallback Mechanism**: Can switch from headless to non-headless if quality poor
- **Monitoring**: Tracks extraction statistics and success rates
- **Validation**: Checks for meaningful content in job descriptions

#### 8.2 Quality Thresholds
```python
# Quality assessment criteria
critical_fields = ['Job Title', 'Company Name']
content_fields = ['Job Description', 'Required Skills', 'Responsibilities']
minimum_quality_score = 30
```

### 9. Data Processing Pipeline

#### 9.1 Data Structure
- **Input**: HTML from ostjob.ch pages
- **Processing**: ScrapeGraphAI with GPT-4.1-mini
- **Output**: JSON arrays of job objects
- **Storage**: Timestamped files in job-data-acquisition/data/

#### 9.2 Data Flattening Logic
```python
# Handles various nested structures:
# - Array of arrays: [[job1, job2], [job3, job4]]
# - Array of objects with content: [{"content": [job1, job2]}]
# - Flat arrays: [job1, job2, job3]
```

### 10. Recommendations for Fixes

#### 10.1 Immediate Actions
1. **Force Headless Mode**: Override settings.json with `headless: true` for cloud deployment
2. **Standardize Browser Config**: Use optimized configuration consistently
3. **Add Cloud-Specific Args**: Include additional Chrome flags for containerized environments
4. **Environment Detection**: Detect cloud vs local and adjust configuration accordingly

#### 10.2 Configuration Improvements
```python
# Recommended cloud browser args
CLOUD_BROWSER_ARGS = [
    "--headless",
    "--no-sandbox", 
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--remote-debugging-port=9222",
    "--disable-extensions",
    "--disable-plugins",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    "--disable-features=TranslateUI,VizDisplayCompositor",
    "--disable-blink-features=AutomationControlled",
    "--disable-ipc-flooding-protection",
    "--memory-pressure-off",
    "--max_old_space_size=4096"
]
```

#### 10.3 Monitoring Improvements
1. **Enhanced Logging**: Add detailed browser console logs
2. **Screenshot Capture**: Take screenshots on failure for debugging
3. **Network Monitoring**: Log network requests and responses
4. **Resource Usage**: Monitor memory and CPU usage during scraping

#### 10.4 Fallback Strategies
1. **Multiple User Agents**: Rotate through different user agents
2. **Request Delays**: Add random delays between requests
3. **Retry Logic**: Implement exponential backoff for failed requests
4. **Alternative Scraping**: Backup scraping method without AI

### 11. Testing Strategy

#### 11.1 Local Testing
```bash
# Test headless mode locally
export DISPLAY=:99
Xvfb :99 -screen 0 1920x1080x24 &
python job-data-acquisition/app.py
```

#### 11.2 Container Testing
```bash
# Test in Docker environment
docker build -t jobsearch-scraper .
docker run -e OPENAI_API_KEY=$OPENAI_API_KEY jobsearch-scraper
```

#### 11.3 Cloud Testing
```bash
# Deploy with debug logging
gcloud run deploy --set-env-vars DEBUG=true,PLAYWRIGHT_DEBUG=1
```

### 12. File Structure Summary

```
JobSearchAI/
├── job-data-acquisition/
│   ├── app.py                 # Standalone scraping service
│   ├── settings.json          # Scraper configuration
│   ├── Dockerfile            # Scraper container config
│   └── data/                 # Scraped data storage
├── graph_scraper_utils.py    # Original scraping utilities
├── optimized_graph_scraper_utils.py  # Enhanced scraping
├── dashboard.py              # Main Flask application
├── job_matcher.py           # CV matching logic
├── Dockerfile               # Main app container config
└── blueprints/
    └── job_matching_routes.py  # Job matching routes
```

### 13. Critical Environment Variables

```bash
OPENAI_API_KEY=sk-proj-...    # Required for AI processing
PORT=8080                     # Cloud Run port
DISPLAY=:99                   # Virtual display for headless
PLAYWRIGHT_BROWSERS_PATH=/app # Browser installation path
```

### 14. Conclusion

The web scraping failure in the deployed environment appears to be primarily caused by:

1. **Browser Configuration Mismatch**: Local uses non-headless mode while cloud requires headless
2. **System Dependencies**: Missing or misconfigured virtual display setup
3. **Environment-Specific Settings**: Different network conditions and security constraints

The most likely fix involves ensuring consistent headless configuration across all components and adding cloud-specific browser arguments to handle the containerized environment properly.

---

**Last Updated**: 2025-09-10  
**Analysis Based on**: Complete codebase review and log analysis

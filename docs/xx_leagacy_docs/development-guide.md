# JobSearchAI Development Guide

**Project:** JobSearchAI  
**Type:** Flask Web Application  
**Last Updated:** 2025-10-15

## Quick Start

### Prerequisites

- **Python:** 3.8 or higher
- **pip:** Python package manager
- **Git:** Version control
- **OpenAI API Key:** Required for AI features

### Initial Setup

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd JobSearchAI
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Playwright Browsers** (for web scraping)
   ```bash
   playwright install
   ```

4. **Configure Environment Variables**
   
   Create/update `process_cv/.env`:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   SECRET_KEY=your_secret_key_here
   ```

5. **Initialize Database**
   ```bash
   python init_db.py
   ```

6. **Run the Application**
   ```bash
   python dashboard.py
   ```

7. **Access the Dashboard**
   - Open browser to: `http://localhost:5000`
   - Register a new account
   - Start using the system!

## Development Environment

### Recommended Tools

- **IDE:** Visual Studio Code, PyCharm, or similar
- **Python Version Manager:** pyenv or conda
- **Virtual Environment:** venv or virtualenv (recommended)
- **Database Client:** DBeaver, pgAdmin (for PostgreSQL)

### Virtual Environment Setup

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Environment Variables

#### Root `.env` (optional)
```env
FLASK_ENV=development
SECRET_KEY=your-secret-key-for-sessions
DATABASE_URL=postgresql://user:password@localhost/jobsearchai  # Optional
```

#### `process_cv/.env` (required)
```env
OPENAI_API_KEY=sk-...your-key...
SECRET_KEY=your-secret-key
```

## Running the Application

### Standard Development Server

```bash
python dashboard.py
```

**Default Settings:**
- Host: `localhost` (127.0.0.1)
- Port: `5000`
- Debug Mode: Enabled in development
- Auto-reload: Yes

### Custom Configuration

```bash
# Run on different port
FLASK_RUN_PORT=8000 python dashboard.py

# Run with specific host (for network access)
FLASK_RUN_HOST=0.0.0.0 python dashboard.py
```

### Running Individual Components

#### CV Processor (Standalone)
```bash
cd process_cv
python cv_processor.py <path-to-cv.pdf>
```

#### Job Scraper (Standalone)
```bash
cd job-data-acquisition
python app.py
```

#### Job Matcher (Standalone)
```bash
python job_matcher.py
```

## Database Management

### Initialize Database

```bash
# Create tables
python init_db.py

# Create admin user
python init_db.py --create-admin

# Test database connection
python init_db.py --test-connection
```

### Database Migrations

Using Flask-Migrate (Alembic):

```bash
# Initialize migrations (first time only)
flask db init

# Create migration after model changes
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade

# Rollback last migration
flask db downgrade
```

### Reset Database

```bash
# SQLite (development)
rm instance/jobsearchai.db
python init_db.py

# PostgreSQL (production)
# Drop and recreate database manually, then:
python init_db.py
```

### Admin Password Reset

```bash
python reset_admin_password.py
```

## Project Structure

### Adding New Features

#### 1. New Blueprint (Route Group)

```python
# blueprints/my_new_routes.py
from flask import Blueprint, render_template, request
from flask_login import login_required

my_blueprint = Blueprint('my_feature', __name__)

@my_blueprint.route('/my-feature')
@login_required
def my_feature():
    return render_template('my_feature.html')
```

Register in `dashboard.py`:
```python
from blueprints.my_new_routes import my_blueprint
app.register_blueprint(my_blueprint)
```

#### 2. New Database Model

```python
# models/my_model.py
from models import db
from datetime import datetime

class MyModel(db.Model):
    __tablename__ = 'my_table'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<MyModel {self.name}>'
```

Create migration:
```bash
flask db migrate -m "Add MyModel table"
flask db upgrade
```

#### 3. New Template

```html
<!-- templates/my_feature.html -->
<!DOCTYPE html>
<html>
<head>
    <title>My Feature - JobSearchAI</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/styles.css') }}">
</head>
<body>
    <div class="container">
        <h1>My Feature</h1>
        <!-- Feature content -->
    </div>
</body>
</html>
```

#### 4. New Utility Function

```python
# utils/my_utils.py
from utils.decorators import handle_errors, retry_on_failure

@handle_errors
@retry_on_failure(max_retries=3)
def my_utility_function(param):
    """
    Description of what this function does.
    
    Args:
        param: Description of parameter
        
    Returns:
        Description of return value
    """
    # Implementation
    return result
```

## Code Style & Standards

### Python Style Guide

- Follow **PEP 8** style guide
- Use **type hints** where appropriate
- Write **docstrings** for functions and classes
- Keep functions **focused and small** (<50 lines ideal)

### Example:

```python
from typing import Dict, List, Optional
from utils.decorators import handle_errors

@handle_errors
def process_job_data(job_id: str, options: Optional[Dict] = None) -> Dict:
    """
    Process job data with optional configuration.
    
    Args:
        job_id: Unique identifier for the job
        options: Optional processing configuration
        
    Returns:
        Dict containing processed job information
        
    Raises:
        ValueError: If job_id is invalid
        ProcessingError: If processing fails
    """
    if not job_id:
        raise ValueError("job_id cannot be empty")
        
    # Processing logic here
    result = {
        'id': job_id,
        'status': 'processed',
        'data': processed_data
    }
    
    return result
```

### Import Organization

```python
# Standard library imports
import os
import json
from datetime import datetime
from typing import Dict, List

# Third-party imports
from flask import Flask, render_template
from flask_login import login_required
import openai

# Local application imports
from config import Config
from models import db, User
from utils.decorators import handle_errors
```

## Testing

### Manual Testing

Currently, the project uses manual testing via the web dashboard.

**Testing Checklist:**
- [ ] Authentication (register, login, logout)
- [ ] CV upload and processing
- [ ] Job scraping
- [ ] Job matching
- [ ] Motivation letter generation
- [ ] Document download
- [ ] Error handling
- [ ] Session management

### Adding Automated Tests (Future)

Recommended setup with pytest:

```bash
# Install pytest
pip install pytest pytest-flask pytest-cov

# Run tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html
```

Example test structure:
```
tests/
├── __init__.py
├── conftest.py           # Pytest configuration
├── test_auth.py          # Authentication tests
├── test_cv_processor.py  # CV processing tests
├── test_job_matcher.py   # Matching tests
└── test_api.py           # API endpoint tests
```

## Logging

### Log Files

- `dashboard.log` - Main application log
- `logs/cv_processor.log` - CV processing log
- `logs/job_matcher.log` - Job matching log
- `job-data-acquisition/logs/` - Scraper logs

### Viewing Logs

```bash
# Tail main log
tail -f dashboard.log

# View last 100 lines
tail -n 100 dashboard.log

# Search logs
grep "ERROR" dashboard.log
```

### Adding Logging to Code

```python
import logging

logger = logging.getLogger(__name__)

def my_function():
    logger.info("Starting function execution")
    try:
        # Code here
        logger.debug("Debug information")
        result = do_something()
        logger.info("Function completed successfully")
        return result
    except Exception as e:
        logger.error(f"Error in my_function: {str(e)}", exc_info=True)
        raise
```

## Common Development Tasks

### Update Dependencies

```bash
# Update specific package
pip install --upgrade package-name

# Update all packages (use with caution)
pip list --outdated
pip install --upgrade package-name

# Freeze current versions
pip freeze > requirements.txt
```

### Clear Caches

```bash
# Python bytecode
find . -type d -name "__pycache__" -exec rm -r {} +
find . -type f -name "*.pyc" -delete

# Flask cache (if using)
rm -rf flask_session/

# Browser cache (testing)
# Use browser's developer tools or incognito mode
```

### Debugging

#### Python Debugger (pdb)

```python
import pdb

def problematic_function():
    x = get_some_value()
    pdb.set_trace()  # Debugger will pause here
    result = process(x)
    return result
```

#### Flask Debug Mode

In `dashboard.py`:
```python
if __name__ == '__main__':
    app.run(debug=True)  # Enables debug mode
```

**Debug Features:**
- Interactive debugger in browser
- Auto-reload on code changes
- Detailed error pages

#### VS Code Debugging

`.vscode/launch.json`:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Flask",
            "type": "python",
            "request": "launch",
            "module": "flask",
            "env": {
                "FLASK_APP": "dashboard.py",
                "FLASK_ENV": "development"
            },
            "args": [
                "run",
                "--no-debugger"
            ],
            "jinja": true
        }
    ]
}
```

## Performance Optimization

### API Caching

Use decorators from `utils/decorators.py`:

```python
from utils.decorators import cached_result

@cached_result(ttl_seconds=3600)
def expensive_ai_call(text):
    # This result will be cached for 1 hour
    return openai_api_call(text)
```

### Database Query Optimization

```python
# Use eager loading for relationships
users = User.query.options(
    db.joinedload(User.cv_data)
).all()

# Use pagination for large result sets
page = request.args.get('page', 1, type=int)
per_page = 20
users = User.query.paginate(
    page=page,
    per_page=per_page,
    error_out=False
)
```

### File Handling

```python
from utils.file_utils import safe_file_operation

# Use utilities for consistent error handling
@safe_file_operation
def process_large_file(filepath):
    with open(filepath, 'r') as f:
        for line in f:  # Process line by line
            process_line(line)
```

## Troubleshooting

### Common Issues

#### 1. OpenAI API Errors

**Problem:** "RateLimitError" or "APIError"

**Solution:**
- Check API key validity
- Verify API quota/credits
- Implement retry logic (already in `utils/api_utils.py`)
- Add delays between requests

#### 2. Playwright Installation Issues

**Problem:** "Executable doesn't exist" error

**Solution:**
```bash
playwright install chromium
# or
python -m playwright install
```

#### 3. Database Connection Errors

**Problem:** "OperationalError: unable to open database file"

**Solution:**
- Ensure `instance/` directory exists
- Check file permissions
- Verify DATABASE_URL if using PostgreSQL
- Initialize database: `python init_db.py`

#### 4. Port Already in Use

**Problem:** "Address already in use"

**Solution:**
```bash
# Find process using port 5000
# Windows:
netstat -ano | findstr :5000
taskkill /PID <process_id> /F

# macOS/Linux:
lsof -ti:5000 | xargs kill -9

# Or use different port:
FLASK_RUN_PORT=8000 python dashboard.py
```

#### 5. Import Errors

**Problem:** "ModuleNotFoundError"

**Solution:**
- Verify virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`
- Check PYTHONPATH if needed
- Verify file structure matches imports

## Best Practices

### Security

- ✅ Never commit `.env` files or API keys
- ✅ Use environment variables for sensitive data
- ✅ Keep dependencies updated
- ✅ Validate all user input
- ✅ Use CSRF protection (Flask-WTF)
- ✅ Hash passwords (never store plain text)
- ✅ Use HTTPS in production

### Code Quality

- ✅ Write descriptive variable and function names
- ✅ Add comments for complex logic
- ✅ Keep functions focused (single responsibility)
- ✅ Use type hints
- ✅ Handle errors gracefully
- ✅ Log important events
- ✅ Write documentation

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/my-new-feature

# Make changes and commit
git add .
git commit -m "Add: Brief description of changes"

# Push to remote
git push origin feature/my-new-feature

# Create pull request for review
```

### Commit Message Convention

```
Type: Brief description (50 chars or less)

More detailed explanation if needed (wrapped at 72 chars).
Explain what and why, not how.

Types: Add, Fix, Update, Remove, Refactor, Docs, Style, Test
```

## Useful Commands Reference

```bash
# Development
python dashboard.py                    # Run main application
python init_db.py                      # Initialize database
python init_db.py --create-admin       # Create admin user

# Database
flask db migrate -m "description"      # Create migration
flask db upgrade                       # Apply migrations
flask db downgrade                     # Rollback migration

# Dependencies
pip install -r requirements.txt        # Install dependencies
pip freeze > requirements.txt          # Save current versions
pip list --outdated                    # Check for updates

# Playwright
playwright install                     # Install browsers
playwright install chromium            # Install specific browser

# Logs
tail -f dashboard.log                  # Follow main log
grep "ERROR" dashboard.log             # Search errors

# Cleanup
find . -name "__pycache__" -exec rm -r {} +   # Remove cache
```

## Additional Resources

### External Documentation

- [Flask Documentation](https://flask.palletsprojects.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Flask-Login Documentation](https://flask-login.readthedocs.io/)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Playwright Documentation](https://playwright.dev/python/)

### Internal Documentation

- [Authentication System](../Documentation/Authentication_System.md)
- [CV Processor](../Documentation/CV_Processor.md)
- [Job Matcher](../Documentation/Job_Matcher.md)
- [System Overview](../Documentation/System.md)

## Getting Help

### In-Project Documentation

Check the `Documentation/` folder for detailed component documentation.

### Logs

Check log files in `logs/` directory for error details.

### Debug Mode

Run with debug mode enabled for detailed error pages.

## Next Steps

1. **Explore the Dashboard:** Register and explore all features
2. **Review Documentation:** Read component docs in `Documentation/`
3. **Try the API:** Test CV processing, job scraping, matching
4. **Customize:** Modify templates, add features, enhance functionality
5. **Contribute:** Follow git workflow for new features

---

**Happy Coding! 🚀**

For questions or issues, refer to the comprehensive documentation in the `Documentation/` folder or check the logs for debugging information.

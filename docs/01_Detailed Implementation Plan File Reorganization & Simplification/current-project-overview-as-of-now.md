# JobSearchAI Project Overview

**Project Name:** JobSearchAI  
**Type:** Flask Web Application (Monolith)  
**Purpose:** AI-Powered Job Matching & Application System  
**Status:** Active Development (Local Deployment)  
**Last Updated:** 2025-10-15

## Executive Summary

JobSearchAI is an intelligent job search automation system that combines AI-powered CV analysis, automated web scraping, semantic job matching, and personalized application letter generation. Built as a Flask monolith for single-user local deployment, it streamlines the entire job search process from discovery to application.

## Key Features

### 🔐 Multi-User Authentication
- Secure user registration and login
- Password hashing with Werkzeug
- Session management with Flask-Login
- CSRF protection on all forms

### 📄 CV Processing
- PDF text extraction with PyMuPDF
- AI-powered CV summarization (OpenAI GPT-4)
- Structured data extraction
- HTML CV views

### 🌐 Automated Job Scraping
- ScrapeGraphAI + Playwright integration
- Configurable job site scraping (OstJob.ch)
- Intelligent data extraction
- JSON storage for processed results

### 🎯 Intelligent Job Matching
- Semantic matching using OpenAI embeddings
- Configurable scoring parameters
- Multi-criteria evaluation
- Detailed match reports

### ✉️ Motivation Letter Generation
- AI-powered personalized letters
- Multiple output formats (HTML, DOCX, JSON)
- Email text generation
- Template-based Word documents

### 🎨 Web Dashboard
- Dark theme UI
- Tabbed interface
- Real-time progress tracking
- File management
- Bulk operations support

## Technology Stack Summary

| Category | Technologies |
|----------|-------------|
| **Backend** | Python 3.8+, Flask 3.1.0 |
| **Database** | SQLite / PostgreSQL, SQLAlchemy |
| **Authentication** | Flask-Login, Flask-WTF, WTForms |
| **AI/ML** | OpenAI API (GPT-4), LangChain, EasyOCR |
| **Web Scraping** | ScrapeGraphAI, Playwright, BeautifulSoup |
| **Document Processing** | PyMuPDF, docxtpl, Pillow |
| **Frontend** | HTML5, CSS3, JavaScript, Jinja2 |

## Architecture

**Pattern:** Monolithic Flask Application  
**Structure:** Blueprint-based modular routes  
**Deployment:** Local development server  
**Database:** SQLite (default) or PostgreSQL

### Components

```
┌─────────────────────────────────────┐
│         Web Dashboard               │
│      (Flask + Jinja2 UI)            │
└─────────────┬───────────────────────┘
              │
    ┌─────────┴─────────┐
    │   Flask Blueprints │
    │  - Auth Routes     │
    │  - CV Routes       │
    │  - Job Routes      │
    │  - Matching Routes │
    │  - Letter Routes   │
    └─────────┬─────────┘
              │
    ┌─────────┴──────────────────────┐
    │                                 │
┌───▼──────┐  ┌────────┐  ┌─────────▼──┐
│ Database │  │ OpenAI │  │   File      │
│ (SQLite) │  │   API  │  │  Storage    │
└──────────┘  └────────┘  └────────────┘
```

## Project Structure

```
JobSearchAI/
├── dashboard.py              # Main application entry point
├── config.py                 # Centralized configuration
├── blueprints/               # Flask route modules
├── models/                   # Database models
├── templates/                # Jinja2 HTML templates
├── static/                   # CSS, JS, images
├── utils/                    # Reusable utilities
├── process_cv/               # CV processing pipeline
├── job-data-acquisition/     # Web scraping component
├── motivation_letters/       # Generated letters
├── Documentation/            # Comprehensive docs
└── docs/                     # Generated documentation
```

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt
playwright install

# 2. Configure environment
# Create process_cv/.env with OPENAI_API_KEY

# 3. Initialize database
python init_db.py

# 4. Run application
python dashboard.py

# 5. Access dashboard
# Open http://localhost:5000
```

## Use Cases

### Primary Workflow

1. **User registers/logs in** to the system
2. **Uploads CV** (PDF format)
3. **System processes CV** using AI (extracts, summarizes)
4. **User triggers job scraping** (configurable parameters)
5. **System scrapes job listings** from configured sites
6. **User initiates job matching** (selects CV + parameters)
7. **AI matches jobs** to CV using semantic analysis
8. **System generates match reports** with scores
9. **User selects matched jobs** for applications
10. **AI generates personalized letters** for each job
11. **User downloads** generated documents (DOCX, HTML)

### Alternative Workflows

- **Manual job input:** Enter job details directly
- **Bulk letter generation:** Generate multiple letters at once
- **CV management:** Upload and manage multiple CVs
- **Job data export:** Export scraped data for analysis

## Key Capabilities

### AI-Powered Intelligence

- **CV Summarization:** Extracts career trajectory, skills, preferences
- **Semantic Matching:** Understanding beyond keyword matching
- **Personalized Letters:** Context-aware, tailored content
- **OCR Support:** Processes image-based CVs

### Automation

- **Web Scraping:** Automated job data acquisition
- **Batch Processing:** Handle multiple CVs and jobs
- **Document Generation:** Automated letter creation
- **Quality Management:** Built-in validation and error handling

### User Experience

- **Intuitive Dashboard:** Clean, organized interface
- **Progress Tracking:** Real-time operation status
- **File Management:** Easy access to generated documents
- **Dark Theme:** Eye-friendly interface

## System Requirements

### Hardware
- **Processor:** Modern multi-core CPU
- **RAM:** 4GB minimum, 8GB recommended
- **Storage:** 2GB free space
- **Internet:** Required for OpenAI API and scraping

### Software
- **OS:** Windows, macOS, or Linux
- **Python:** 3.8 or higher
- **Browser:** Modern browser for dashboard access
- **Database:** SQLite (included) or PostgreSQL (optional)

### API Requirements
- **OpenAI API Key:** Required for AI features
- **API Credits:** Usage-based pricing applies

## Performance Characteristics

### Scalability
- **Current:** Single-user, local deployment
- **Concurrent Users:** 1 (designed for personal use)
- **Data Volume:** Suitable for personal job search needs

### Processing Times
- **CV Processing:** 5-15 seconds per CV
- **Job Scraping:** 2-5 minutes per session
- **Job Matching:** 10-30 seconds per match
- **Letter Generation:** 5-10 seconds per letter

### Bottlenecks
- OpenAI API rate limits
- Web scraping speed (Playwright overhead)
- Document generation (complex layouts)

## Security & Privacy

### Implemented Security
- ✅ Password hashing (Werkzeug)
- ✅ CSRF protection (Flask-WTF)
- ✅ Session management (Flask-Login)
- ✅ SQL injection prevention (SQLAlchemy ORM)
- ✅ Environment variable protection

### Privacy Considerations
- **Local Data:** All data stored locally
- **API Usage:** CV/job data sent to OpenAI API
- **No Cloud Storage:** No third-party data storage
- **Single User:** Designed for personal use

## Development Status

### Current Version
- **Status:** Active development
- **Stability:** Functional for personal use
- **Testing:** Manual testing via dashboard
- **Documentation:** Comprehensive

### Active Features
- ✅ Authentication system
- ✅ CV processing
- ✅ Job scraping
- ✅ Job matching
- ✅ Letter generation
- ✅ Web dashboard
- ✅ File management

### Known Limitations
- No automated test suite
- Single-user deployment only
- Limited to localhost
- No real-time notifications
- No export/import functionality

### Deprecated Features
- ❌ Docker deployment
- ❌ Google Cloud Run deployment
- ❌ CI/CD pipelines

## Future Enhancements

### Planned Features
1. Automated test suite (pytest)
2. Background job processing (Celery/RQ)
3. API rate limiting and caching
4. Export/import functionality
5. Advanced analytics dashboard
6. Multi-CV comparison
7. Job search scheduling

### Potential Improvements
- Performance optimization
- Enhanced error handling
- Additional AI models support
- More job site integrations
- Mobile responsive design
- Email integration
- Calendar integration

## Documentation

### Available Documentation

| Document | Purpose |
|----------|---------|
| [README.md](../README.md) | Project introduction & quick start |
| [Technology Stack](./technology-stack.md) | Comprehensive tech analysis |
| [Source Tree Analysis](./source-tree-analysis.md) | Directory structure & organization |
| [Development Guide](./development-guide.md) | Setup, development, troubleshooting |
| [Documentation/](../Documentation/) | Component-specific detailed docs |

### Component Documentation

- **[Authentication System](../Documentation/Authentication_System.md)** - Security implementation
- **[CV Processor](../Documentation/CV_Processor.md)** - CV processing pipeline
- **[Job Data Acquisition](../Documentation/Job_Data_Acquisition.md)** - Web scraping system
- **[Job Matcher](../Documentation/Job_Matcher.md)** - Matching algorithm
- **[Motivation Letter Generator](../Documentation/Motivation_Letter_Generator.md)** - Letter generation
- **[Dashboard](../Documentation/Dashboard.md)** - UI features & usage
- **[System Overview](../Documentation/System.md)** - Architecture overview

## Support & Maintenance

### Getting Help
1. Check existing documentation in `Documentation/`
2. Review logs in `logs/` directory
3. Enable Flask debug mode for detailed errors
4. Consult development guide for troubleshooting

### Maintenance Tasks
- **Regular:** Update dependencies, review logs
- **Periodic:** Clean old files, optimize database
- **As Needed:** Update OpenAI API usage, adjust scraping

## License & Attribution

### Dependencies
All dependencies are listed in `requirements.txt` with their respective licenses.

### External Services
- **OpenAI API:** Subject to OpenAI terms of service
- **ScrapeGraphAI:** Open source web scraping library
- **Playwright:** Browser automation framework

## Contact & Contributions

### For Users
- Review `Documentation/` for detailed usage instructions
- Check `README.md` for quick start guide
- Consult `development-guide.md` for setup help

### For Developers
- Follow code style guide in development documentation
- Maintain existing documentation structure
- Add tests for new features (when test suite is added)
- Update relevant documentation for changes

## Summary

JobSearchAI is a comprehensive, AI-powered job search automation system that:

- **Simplifies** the job search process through automation
- **Intelligently matches** candidates to opportunities using AI
- **Generates** personalized application materials
- **Provides** an intuitive interface for managing the workflow
- **Maintains** security and privacy through local deployment
- **Enables** efficient job search for individual users

Built with modern technologies and best practices, it demonstrates practical AI integration while maintaining simplicity and usability for personal use.

---

**For detailed information on any aspect of the system, refer to the comprehensive documentation in the `Documentation/` folder or the generated documentation in this `docs/` folder.**

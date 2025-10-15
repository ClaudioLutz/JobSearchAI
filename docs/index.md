# JobSearchAI - Documentation Index

**Project:** JobSearchAI  
**Type:** Flask Web Application (Monolith)  
**Purpose:** AI-Powered Job Matching & Application System  
**Documentation Generated:** 2025-10-15  
**Scan Level:** Deep

---

## 🎯 Quick Navigation

| For... | Start Here |
|--------|------------|
| **New Users** | [Project Overview](#project-overview) → [Quick Start](#quick-start) |
| **Developers** | [Development Guide](./development-guide.md) → [Source Tree](./source-tree-analysis.md) |
| **Architects** | [Technology Stack](./technology-stack.md) → [Architecture](#architecture) |
| **Troubleshooting** | [Development Guide - Troubleshooting](./development-guide.md#troubleshooting) |

---

## 📋 Project Overview

### Quick Reference

| Property | Value |
|----------|-------|
| **Project Type** | Web Application |
| **Architecture** | Flask Monolith |
| **Language** | Python 3.8+ |
| **Framework** | Flask 3.1.0 |
| **Deployment** | Local Development Server |
| **Database** | SQLite (default) / PostgreSQL |
| **Entry Point** | `dashboard.py` |
| **Default URL** | http://localhost:5000 |

### Key Features

- 🔐 **Multi-User Authentication** - Secure login with Flask-Login
- 📄 **CV Processing** - AI-powered CV analysis with OpenAI
- 🌐 **Job Scraping** - Automated data acquisition with ScrapeGraphAI
- 🎯 **Intelligent Matching** - Semantic job-CV matching
- ✉️ **Letter Generation** - Personalized motivation letters
- 🎨 **Web Dashboard** - Dark theme, intuitive interface

[→ Full Project Overview](./project-overview.md)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip package manager
- OpenAI API key

### Setup Steps

```bash
# 1. Install dependencies
pip install -r requirements.txt
playwright install

# 2. Configure environment variables
# Create process_cv/.env with:
# OPENAI_API_KEY=your_key_here
# SECRET_KEY=your_secret_key

# 3. Initialize database
python init_db.py

# 4. Run application
python dashboard.py

# 5. Open browser
# Navigate to http://localhost:5000
```

[→ Detailed Setup Guide](./development-guide.md#initial-setup)

---

## 📚 Generated Documentation

### Core Documentation

| Document | Description | Best For |
|----------|-------------|----------|
| **[Project Overview](./project-overview.md)** | Executive summary, features, architecture | Understanding the big picture |
| **[Technology Stack](./technology-stack.md)** | Comprehensive tech analysis, dependencies | Technology decisions, migrations |
| **[Source Tree Analysis](./source-tree-analysis.md)** | Directory structure, file organization | Navigation, understanding codebase |
| **[Development Guide](./development-guide.md)** | Setup, development, troubleshooting | Day-to-day development |

### Technical Documentation

#### Technology Stack
- **Backend:** Python 3.8+, Flask 3.1.0, SQLAlchemy
- **Authentication:** Flask-Login, Flask-WTF, Werkzeug
- **AI/ML:** OpenAI API (GPT-4), LangChain, EasyOCR
- **Scraping:** ScrapeGraphAI 1.46.0, Playwright 1.51.0
- **Documents:** PyMuPDF, docxtpl, Pillow
- **Frontend:** HTML5/CSS3, JavaScript, Jinja2

[→ Complete Technology Stack](./technology-stack.md)

#### Architecture Pattern

**Type:** Monolithic Flask Application  
**Pattern:** Blueprint-based modular organization  
**Deployment:** Local development server

```
Flask Dashboard (dashboard.py)
    ↓
Flask Blueprints (auth, cv, jobs, matching, letters)
    ↓
Database (SQLite) + OpenAI API + File Storage
```

[→ Detailed Architecture](./source-tree-analysis.md#data-flow-architecture)

---

## 📖 Existing Documentation

### Component Documentation

Located in `../Documentation/` - comprehensive, well-maintained docs:

| Component | Documentation | Purpose |
|-----------|--------------|---------|
| **Authentication** | [Authentication_System.md](../Documentation/Authentication_System.md) | Security implementation details |
| **CV Processing** | [CV_Processor.md](../Documentation/CV_Processor.md) | CV parsing and AI summarization |
| **Job Scraping** | [Job_Data_Acquisition.md](../Documentation/Job_Data_Acquisition.md) | Web scraping system |
| **Job Matching** | [Job_Matcher.md](../Documentation/Job_Matcher.md) | Semantic matching algorithm |
| **Letter Generation** | [Motivation_Letter_Generator.md](../Documentation/Motivation_Letter_Generator.md) | AI letter generation |
| **Word Templates** | [Word_Template_Generator.md](../Documentation/Word_Template_Generator.md) | DOCX file generation |
| **Dashboard** | [Dashboard.md](../Documentation/Dashboard.md) | Web interface features |
| **System Overview** | [System.md](../Documentation/System.md) | High-level architecture |

### Additional Resources

- **[README.md](../README.md)** - Project introduction & quick start
- **[Documentation README](../Documentation/README.md)** - Documentation index
- **[Technical Decisions Template](../Documentation/technical-decisions-template.md)** - Decision documentation format
- **[Trafilatura Migration Analysis](../Documentation/Trafilatura_Migration_Analysis.md)** - Migration insights

---

## 🔧 Development Resources

### Essential Commands

```bash
# Application
python dashboard.py                    # Run main application
python init_db.py                      # Initialize database
python init_db.py --create-admin       # Create admin user

# Database Migrations
flask db migrate -m "description"      # Create migration
flask db upgrade                       # Apply migrations

# Dependencies
pip install -r requirements.txt        # Install packages
playwright install                     # Install browsers

# Individual Components
python process_cv/cv_processor.py      # Run CV processor
python job-data-acquisition/app.py     # Run job scraper
python job_matcher.py                  # Run job matcher
```

[→ Full Command Reference](./development-guide.md#useful-commands-reference)

### Project Structure

```
JobSearchAI/
├── dashboard.py              # 🚀 Main entry point
├── config.py                 # ⚙️ Configuration
├── blueprints/               # 🔵 Flask routes
│   ├── auth_routes.py       # 🔐 Authentication
│   ├── cv_routes.py         # 📄 CV management
│   ├── job_data_routes.py   # 🌐 Job scraping
│   ├── job_matching_routes.py # 🎯 Matching
│   └── motivation_letter_routes.py # ✉️ Letters
├── models/                   # 🗄️ Database models
├── templates/                # 🎨 UI templates
├── static/                   # 🎨 CSS, JS assets
├── utils/                    # 🛠️ Utilities
├── process_cv/               # 📄 CV processing
├── job-data-acquisition/     # 🌐 Web scraping
├── Documentation/            # 📚 Component docs
└── docs/                     # 📊 Generated docs (this folder)
```

[→ Detailed Source Tree](./source-tree-analysis.md)

### Development Workflow

1. **Setup Environment** - Install dependencies, configure API keys
2. **Initialize Database** - Create tables and admin user
3. **Run Application** - Start Flask development server
4. **Make Changes** - Edit code, add features
5. **Test Manually** - Use web dashboard to test
6. **Check Logs** - Review logs for errors
7. **Commit Changes** - Follow git workflow

[→ Complete Development Guide](./development-guide.md)

---

## 🏗️ Architecture Insights

### Blueprint Organization

| Blueprint | Routes | Purpose |
|-----------|--------|---------|
| `auth_routes` | `/login`, `/register`, `/logout` | User authentication |
| `cv_routes` | `/cv/*` | CV upload and processing |
| `job_data_routes` | `/jobs/*` | Job scraping control |
| `job_matching_routes` | `/match/*` | Job matching execution |
| `motivation_letter_routes` | `/letter/*` | Letter generation |

### Data Flow

1. **User authenticates** → Flask-Login session
2. **Uploads CV** → PyMuPDF extraction → OpenAI summarization
3. **Triggers scraping** → Playwright → ScrapeGraphAI → JSON storage
4. **Initiates matching** → OpenAI embeddings → Semantic comparison
5. **Generates letters** → AI composition → Word document generation
6. **Downloads results** → DOCX, HTML, JSON formats

[→ Detailed Integration Points](./source-tree-analysis.md#integration-points)

### Database Schema

**Active Tables:**
- `users` - User accounts and authentication
- `cv_data` - Processed CV information
- `job_matches` - AI-generated job matches
- `motivation_letters` - Generated letter templates

**Technology:** SQLite (development) or PostgreSQL (production)

[→ Technology Stack Details](./technology-stack.md#database--orm)

---

## 🔍 File Locations

### Configuration

| File | Purpose | Location |
|------|---------|----------|
| `config.py` | Central configuration | Root |
| `.env` | Root environment vars | Root |
| `process_cv/.env` | CV processor config | `process_cv/` |
| `job-data-acquisition/settings.json` | Scraper config | `job-data-acquisition/` |

### Data Storage

| Type | Location | Format |
|------|----------|--------|
| **Database** | `instance/jobsearchai.db` | SQLite |
| **Uploaded CVs** | `process_cv/cv-data/input/` | PDF |
| **CV Summaries** | `process_cv/cv-data/processed/` | JSON |
| **Scraped Jobs** | `job-data-acquisition/data/` | JSON |
| **Job Matches** | `job_matches/` | MD, JSON |
| **Letters** | `motivation_letters/` | DOCX, HTML, JSON |

### Logs

| Log File | Purpose | Location |
|----------|---------|----------|
| `dashboard.log` | Main application | Root |
| `cv_processor.log` | CV processing | `logs/` |
| `job_matcher.log` | Job matching | `logs/` |
| Scraper logs | Web scraping | `job-data-acquisition/logs/` |

---

## ⚙️ Configuration

### Required Environment Variables

```env
# process_cv/.env
OPENAI_API_KEY=sk-...your-key...
SECRET_KEY=your-secret-key-here
```

### Optional Configuration

```env
# Root .env (optional)
FLASK_ENV=development
DATABASE_URL=postgresql://user:pass@localhost/jobsearchai
FLASK_RUN_PORT=5000
FLASK_RUN_HOST=localhost
```

[→ Environment Setup](./development-guide.md#environment-variables)

---

## 🚨 Important Notes

### Active vs. Deprecated

**✅ Active (Current Use):**
- Local localhost deployment
- Flask development server
- SQLite database (default)
- Manual testing via dashboard
- All blueprint routes
- All AI processing features

**❌ Deprecated (No Longer Used):**
- Docker deployment files
- Google Cloud Run configuration
- CI/CD pipeline files
- Various deployment scripts

[→ Deprecated Files List](./source-tree-analysis.md#deprecatedunused-files)

### Deployment Status

**Current:** Local development server only  
**Original Plan:** Google Cloud Run deployment (abandoned)  
**Reason:** Personal use, single-user, simpler local setup

---

## 📊 Performance & Scalability

### Current Characteristics

| Metric | Value |
|--------|-------|
| **Users** | Single user (local) |
| **CV Processing** | 5-15 seconds per CV |
| **Job Scraping** | 2-5 minutes per session |
| **Job Matching** | 10-30 seconds per match |
| **Letter Generation** | 5-10 seconds per letter |

### Bottlenecks

1. OpenAI API rate limits and latency
2. Playwright browser automation overhead
3. PDF extraction for complex documents
4. Document generation for complex layouts

[→ Performance Details](./project-overview.md#performance-characteristics)

---

## 🔒 Security & Privacy

### Implemented Security

- ✅ Password hashing (Werkzeug)
- ✅ CSRF protection (Flask-WTF)
- ✅ Session management (Flask-Login)
- ✅ SQL injection prevention (SQLAlchemy ORM)
- ✅ Environment variable protection

### Privacy Model

- **Local Data Storage** - All data stored on local machine
- **API Usage** - CV/job data sent to OpenAI API for processing
- **No Cloud Storage** - No third-party data storage
- **Single User** - Designed for personal use

[→ Security Details](./project-overview.md#security--privacy)

---

## 🛠️ Troubleshooting

### Common Issues

1. **OpenAI API Errors** → Check API key, verify credits
2. **Playwright Issues** → Run `playwright install`
3. **Database Errors** → Ensure `instance/` exists, run `init_db.py`
4. **Port in Use** → Change port or kill process
5. **Import Errors** → Reinstall dependencies

[→ Detailed Troubleshooting](./development-guide.md#troubleshooting)

### Getting Help

1. Check existing documentation in `Documentation/`
2. Review logs in `logs/` directory
3. Enable Flask debug mode
4. Consult development guide

---

## 📈 Future Enhancements

### Planned Features

- Automated test suite (pytest)
- Background job processing (Celery/RQ)
- API rate limiting and caching
- Export/import functionality
- Advanced analytics dashboard
- Multi-CV comparison
- Job search scheduling

[→ Full Enhancement List](./project-overview.md#future-enhancements)

---

## 📝 Documentation Updates

### Maintaining Documentation

When making changes:

1. **Update relevant component docs** in `Documentation/`
2. **Regenerate this documentation** if architecture changes
3. **Update README.md** for user-facing changes
4. **Log technical decisions** using the template

### Regenerating Documentation

```bash
# If using BMad Method:
@analyst *document-project

# Or manually update docs/ folder as needed
```

---

## 🎓 Learning Resources

### External Documentation

- [Flask Documentation](https://flask.palletsprojects.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Flask-Login Documentation](https://flask-login.readthedocs.io/)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Playwright Documentation](https://playwright.dev/python/)

### Internal Resources

- Comprehensive component docs in `Documentation/`
- Technology stack analysis in this folder
- Development guide with examples
- Source code comments and docstrings

---

## 📞 Support

### For Users
- Review `Documentation/` for detailed usage
- Check `README.md` for quick start
- Consult development guide for setup

### For Developers
- Follow development guide
- Maintain existing documentation structure
- Add tests when test suite is implemented
- Update documentation for changes

---

## 📦 Summary

**JobSearchAI** is a comprehensive AI-powered job search automation system that:

- ✨ **Simplifies** job search through intelligent automation
- 🎯 **Matches** candidates to opportunities using AI
- ✉️ **Generates** personalized application materials
- 🎨 **Provides** an intuitive web interface
- 🔒 **Maintains** security through local deployment
- 🚀 **Enables** efficient job search for individuals

**Documentation Structure:**

```
docs/                              # Generated documentation (this folder)
├── index.md                       # This file - master index
├── project-overview.md            # Executive summary
├── technology-stack.md            # Tech analysis
├── source-tree-analysis.md        # Directory structure
├── development-guide.md           # Dev setup & workflow
├── bmm-workflow-status.md         # Workflow tracking
└── project-scan-report.json       # Scan metadata

Documentation/                     # Component documentation
├── README.md                      # Documentation index
├── System.md                      # Architecture overview
├── Authentication_System.md       # Auth details
├── CV_Processor.md                # CV processing
├── Job_Data_Acquisition.md        # Scraping
├── Job_Matcher.md                 # Matching algorithm
├── Motivation_Letter_Generator.md # Letter generation
├── Dashboard.md                   # UI features
└── [additional docs]              # Migration analyses, etc.
```

---

**🎯 Ready to get started?**

1. [Set up your environment](./development-guide.md#initial-setup)
2. [Run the application](./development-guide.md#running-the-application)
3. [Explore the dashboard](http://localhost:5000)
4. [Read component docs](../Documentation/README.md) for details

---

*Documentation generated on 2025-10-15 using BMad Method document-project workflow with Deep Scan*

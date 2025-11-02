# JobSearchAI Technology Stack

**Project:** JobSearchAI  
**Type:** Flask Web Application (Monolith)  
**Deployment:** Local Development Server  
**Last Updated:** 2025-10-15

## Executive Summary

JobSearchAI is built as a Python Flask monolithic web application designed for single-user local deployment. The system leverages AI (OpenAI GPT-4) for intelligent job matching, CV processing, and motivation letter generation, combined with web scraping capabilities for automated job data acquisition.

## Core Technologies

### Backend Framework
| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.8+ | Primary programming language |
| **Flask** | 3.1.0 | Web framework and application server |
| **Werkzeug** | 3.1.3 | WSGI utility library (Flask dependency) |

### Database & ORM
| Technology | Version | Purpose |
|------------|---------|---------|
| **SQLAlchemy** | via Flask-SQLAlchemy 3.1.1 | ORM for database operations |
| **PostgreSQL** | - | Primary database (via psycopg2-binary 2.9.9) |
| **SQLite** | - | Alternative/development database |
| **Flask-Migrate** | 4.0.5 | Database migration management (Alembic wrapper) |

### Authentication & Security
| Technology | Version | Purpose |
|------------|---------|---------|
| **Flask-Login** | 0.6.3 | User session management |
| **Werkzeug Security** | 3.1.3 | Password hashing and security utilities |
| **Flask-WTF** | 1.2.1 | Form validation and CSRF protection |
| **WTForms** | 3.1.2 | Form validation library |

### AI & Machine Learning
| Technology | Version | Purpose |
|------------|---------|---------|
| **OpenAI** | 1.74.0 | GPT-4/GPT-3.5 API for CV processing, job matching, letter generation |
| **LangChain OpenAI** | 0.3.12 | LangChain integration for OpenAI models |
| **EasyOCR** | 1.7.1 | Optical character recognition for image-based CVs |

### Web Scraping & Automation
| Technology | Version | Purpose |
|------------|---------|---------|
| **ScrapeGraphAI** | 1.46.0 | AI-powered web scraping framework |
| **Playwright** | 1.51.0 | Browser automation for dynamic content scraping |
| **BeautifulSoup4** | 4.13.3 | HTML parsing and manipulation |
| **Requests** | 2.32.3 | HTTP client for web requests |

### Document Processing
| Technology | Version | Purpose |
|------------|---------|---------|
| **PyMuPDF** | 1.25.5 | PDF text extraction and processing |
| **docxtpl** | 0.19.0 | Word document template generation |
| **Pillow** | 10.4.0 | Image processing (supporting OCR) |

### Supporting Libraries
| Technology | Version | Purpose |
|------------|---------|---------|
| **python-dotenv** | 1.1.0 | Environment variable management |
| **certifi** | 2025.1.31 | SSL certificate validation |
| **NumPy** | 1.26.4 | Numerical computing (EasyOCR dependency) |
| **pathlib** | 1.0.1 | File path operations |

## Architecture Pattern

**Pattern:** Flask Monolith with Blueprint Architecture  
**Style:** MVC-inspired with service layer  
**Deployment:** Local development server (originally planned for Google Cloud Run)

### Key Architectural Decisions

1. **Monolithic Design**: All functionality in single deployable unit for simplicity
2. **Blueprint Organization**: Modular routes organization (auth, CV, jobs, matching, letters)
3. **Centralized Configuration**: Single `config.py` for all settings
4. **Utility Layer**: Reusable decorators and helpers in `utils/` package
5. **Local-First**: Optimized for single-user localhost deployment

## Frontend Technologies

| Technology | Purpose |
|------------|---------|
| **HTML5/CSS3** | UI markup and styling |
| **JavaScript** | Client-side interactivity |
| **Jinja2** | Server-side template engine (Flask default) |

### UI Characteristics
- Server-rendered pages with Jinja2 templates
- Dark theme interface
- Tabbed navigation
- Responsive design patterns
- Form-heavy interface for data input

## Development Tools

### Code Quality
- **Type Hints**: Used throughout codebase for IDE support
- **Decorators**: Custom error handling, retries, caching, timing
- **Logging**: Comprehensive logging to files and console

### Deprecated/Unused Technologies

The following were part of the original cloud deployment plan but are **no longer active**:

| Technology | Status | Original Purpose |
|------------|--------|------------------|
| **Docker** | Deprecated | Container packaging |
| **Google Cloud Run** | Deprecated | Cloud deployment platform |
| **Cloud Build** | Deprecated | CI/CD pipeline |
| **Various deployment scripts** | Deprecated | Deployment automation |

## Database Schema

### Active Tables
- **users**: User accounts with authentication
- **cv_data**: Processed CV information
- **job_matches**: AI-generated job matches
- **motivation_letters**: Generated letter templates

### Key Relationships
- Users → CV Data (one-to-many)
- Users → Job Matches (one-to-many)
- Users → Motivation Letters (one-to-many)

## API Integrations

### External APIs
1. **OpenAI API**
   - Model: GPT-4o-mini / GPT-3.5-turbo
   - Purpose: CV summarization, semantic job matching, letter generation
   - Authentication: API key in environment variables

2. **Job Sites (via Scraping)**
   - Primary Target: OstJob.ch
   - Method: ScrapeGraphAI + Playwright
   - Data: Job listings, company details, requirements

## File Storage

### Local File System Organization
```
├── instance/              # SQLite database files
├── process_cv/
│   └── cv-data/
│       ├── input/        # Uploaded CVs (PDF)
│       ├── processed/    # CV summaries (JSON)
│       └── html/         # CV HTML views
├── job-data-acquisition/
│   └── data/             # Scraped job data (JSON)
├── motivation_letters/   # Generated letters (DOCX, HTML, JSON)
├── job_matches/          # Match reports (MD, JSON)
└── logs/                 # Application logs
```

## Environment Configuration

### Required Environment Variables
- `OPENAI_API_KEY`: OpenAI API authentication
- `SECRET_KEY`: Flask session encryption
- `DATABASE_URL`: PostgreSQL connection (optional, defaults to SQLite)
- `FLASK_ENV`: Environment mode (development/production)

### Configuration Files
- `config.py`: Centralized application configuration
- `process_cv/.env`: CV processor environment variables
- `job-data-acquisition/settings.json`: Scraper configuration

## Performance Characteristics

### Scalability
- **Current**: Single-user, localhost deployment
- **Database**: SQLite (development) or PostgreSQL (production-ready)
- **Concurrency**: Limited by Flask development server
- **AI Processing**: Rate-limited by OpenAI API quotas

### Bottlenecks
1. **Web Scraping**: Playwright browser automation (resource intensive)
2. **AI Processing**: OpenAI API latency (2-10 seconds per request)
3. **Document Generation**: PDF extraction and Word generation
4. **OCR**: EasyOCR processing for image-based CVs

## Security Considerations

### Implemented
- Password hashing with Werkzeug
- CSRF protection on all forms
- Flask-Login session management
- SQL injection prevention via SQLAlchemy ORM
- Environment variable protection

### Considerations for Production
- HTTPS/TLS termination needed
- Rate limiting for API endpoints
- Input validation and sanitization
- API key rotation
- Database connection pooling

## Testing & Quality

### Current State
- No automated test suite present
- Manual testing via web dashboard
- Logging for debugging and monitoring

### Quality Tools
- Custom error handling decorators
- Retry logic for API calls
- Caching mechanisms for repeated operations
- Execution timing for performance monitoring

## Future Considerations

### Potential Enhancements
1. Automated testing suite (pytest)
2. API rate limiting and caching
3. Background job processing (Celery/RQ)
4. Multi-user support with role-based access
5. Real-time notifications
6. Export/import functionality
7. Advanced analytics dashboard

### Migration Path (if needed)
- Current architecture supports transition to cloud deployment
- Docker configuration exists but deprecated (can be revived)
- Database migrations already configured (Flask-Migrate)
- Blueprint structure enables microservices extraction if needed

## Summary

JobSearchAI is a well-structured Flask monolith leveraging modern AI capabilities for intelligent job matching. The technology stack is carefully selected for:

- **AI Integration**: OpenAI GPT models for intelligent processing
- **Automation**: ScrapeGraphAI + Playwright for reliable web scraping
- **Document Handling**: Comprehensive PDF and Word document processing
- **User Management**: Production-ready authentication and session management
- **Maintainability**: Clean code structure with utilities and blueprints
- **Local Development**: Optimized for single-user localhost deployment

The stack balances power (AI, scraping, document processing) with simplicity (monolithic design, local deployment) for effective job search automation.

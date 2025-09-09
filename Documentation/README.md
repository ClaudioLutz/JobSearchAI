# JobSearchAI Documentation

Welcome to the comprehensive documentation for JobSearchAI - an intelligent job application automation system with Spec-Driven Development capabilities.

## 📋 Documentation Structure

This documentation is organized into two complementary layers:

### 🏛️ Current State Documentation (Technical Reference)
Component-specific technical documentation describing the existing system architecture:

| Component | Purpose | Status | Key Technologies |
|-----------|---------|---------|------------------|
| [System Overview](System.md) | Complete system architecture and workflow | ✅ Production | Flask, OpenAI, SQLite |
| [Authentication System](Authentication_System.md) | User security and session management | ✅ Production | Flask-Login, SQLAlchemy |
| [CV Processor](CV_Processor.md) | PDF parsing and AI summarization | ✅ Production | PyMuPDF, OpenAI GPT-4 |
| [Job Data Acquisition](Job_Data_Acquisition.md) | Web scraping and data extraction | ✅ Production | ScrapeGraph AI, BeautifulSoup |
| [Job Matcher](Job_Matcher.md) | Semantic job-CV matching | ✅ Optimized | OpenAI GPT-4, ML algorithms |
| [Motivation Letter Generator](Motivation_Letter_Generator.md) | Personalized document generation | ✅ Production | OpenAI GPT-4, docxtpl |
| [Word Template Generator](Word_Template_Generator.md) | Document formatting and export | ✅ Production | python-docx, Jinja2 |
| [Dashboard Interface](Dashboard.md) | Web UI and user interaction | ✅ Production | Flask, Bootstrap 5, JavaScript |

### 🌱 Spec-Driven Development (Future State Planning)
Enhanced development capabilities for feature enhancement and modernization:

| Resource | Purpose | Location | Integration |
|----------|---------|----------|-------------|
| [Constitution](../memory/constitution.md) | Project principles and constraints | `memory/` | ✅ JobSearchAI-specific |
| [Spec Templates](../templates/) | Standardized specification formats | `templates/` | Available for features |
| [Development Scripts](../scripts/) | Automation and workflow tools | `scripts/` | Ready for enhancement |

## 🚀 Development Workflows

### Current System Maintenance
For bug fixes, minor improvements, and routine maintenance:
1. Reference the appropriate component documentation above
2. Follow existing Flask/Python patterns
3. Ensure compliance with [Constitution](../memory/constitution.md) principles

### Feature Enhancement & Modernization  
For new features, major improvements, and architectural changes:

#### Using Spec-Driven Development with GitHub Copilot:
```bash
# Step 1: Define Requirements
/specify [Describe enhancement within JobSearchAI context]

# Step 2: Technical Architecture  
/plan [Integration with existing Flask/SQLite stack]

# Step 3: Implementation Tasks
/tasks [Break down into actionable development tasks]
```

#### Example Enhancement Workflow:
```
/specify Enhance JobSearchAI's job matching algorithm to include sentiment analysis of job descriptions and provide personality-based compatibility scoring with uploaded CVs

/plan Integrate with existing Python/Flask stack, use scikit-learn for ML, maintain current SQLite database, add new matching endpoints to existing blueprints

/tasks Break down the sentiment analysis feature into implementable tasks for the current codebase structure
```

## 🔗 Cross-Reference Patterns

### Architecture Integration
- **Current State** (Documentation/) → **Future State** (specs/[NNN]-[feature-name]/)
- **Technical Reference** → **Implementation Specifications**
- **Component Docs** → **Feature Enhancement Plans**

### Development Guidelines
All development must comply with the [JobSearchAI Constitution](../memory/constitution.md):
- ✅ Data Privacy & Security (NON-NEGOTIABLE)
- ✅ Quality Standards (>80% matching accuracy)  
- ✅ Performance Requirements (<2s response times)
- ✅ Technology Stack Compatibility (Flask/SQLite)
- ✅ User Experience Consistency

## 🛠️ Quick Reference

### Essential Commands
```bash
# Start development server
python dashboard.py

# Initialize database
python init_db.py

# Run component tests
python -m pytest tests/

# Generate specifications (with Copilot)
/specify [enhancement description]
/plan [technical approach]
/tasks [implementation breakdown]
```

### Key Configuration Files
- `config.py` - Centralized configuration management
- `requirements.txt` - Python dependencies
- `.env` - Environment variables and API keys
- `job-data-acquisition/settings.json` - Scraper configuration

### Directory Structure
```
JobSearchAI/
├── Documentation/           # 📋 Current state technical docs
├── memory/                 # 🧠 Spec Kit principles & memory
├── scripts/                # 🔧 Development automation
├── templates/              # 📝 Spec Kit templates
├── blueprints/             # 🌐 Flask route organization
├── models/                 # 🗃️ Database models
├── process_cv/             # 📄 CV processing pipeline
├── job-data-acquisition/   # 🕸️ Web scraping system
└── utils/                  # 🛠️ Shared utilities
```

## 📊 System Health & Metrics

### Quality Metrics (Constitution Compliance)
- **Job Matching Accuracy**: Target >80% (see [Job Matcher](Job_Matcher.md))
- **Response Time**: Target <2s (monitored across all components)
- **Data Security**: Zero plain-text personal data (see [Authentication](Authentication_System.md))
- **Code Coverage**: Target >80% for new features
- **Documentation**: 100% coverage for new features

### Performance Monitoring
- CV Processing pipeline performance
- Job scraping success rates  
- User authentication metrics
- Database query optimization
- API response times

## 🎯 Immediate Enhancement Opportunities

Based on the current system analysis:

1. **Enhanced Job Matching**: ML-powered similarity scoring ([Job Matcher](Job_Matcher.md))
2. **CV Intelligence**: Extract skills, experience levels, preferences ([CV Processor](CV_Processor.md))  
3. **Personalized Recommendations**: User behavior-based suggestions
4. **Quality Metrics**: Track and improve matching accuracy
5. **Integration APIs**: Connect with external job boards ([Job Data Acquisition](Job_Data_Acquisition.md))

## 📞 Support & Resources

- **GitHub Repository**: [JobSearchAI Issues](https://github.com/ClaudioLutz/JobSearchAI/issues)
- **Spec Kit Documentation**: [github.com/github/spec-kit](https://github.com/github/spec-kit)
- **Development Guide**: See individual component documentation
- **Constitution**: [memory/constitution.md](../memory/constitution.md)

---

**Last Updated**: 2025-09-08 | **Documentation Version**: 2.0.0 | **System Status**: ✅ Production Ready with Spec-Driven Enhancement Capabilities

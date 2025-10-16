# Epic: MVP Email Automation Pipeline

**Epic ID:** email-automation
**Created:** 2025-10-15
**Status:** Ready for Implementation

---

## Epic Goal

Complete the JobSearchAI automation pipeline with three critical MVP features that enable end-to-end job application processing: (1) reliable email sending via Gmail SMTP, (2) comprehensive data validation preventing incomplete applications, and (3) user-friendly Application Queue UI for human-in-the-loop review and approval.

**User Value:** Transform job application workflow from 30-45 minutes of manual work per application to 2-3 minutes of focused review time, while maintaining professional quality and complete user control through validation and review gates.

---

## Epic Scope

### Included in MVP

**Backend Infrastructure:**
- Email sending module using Python smtplib with Gmail SMTP
- Data validation module with completeness scoring (0-100%)
- Flask blueprint for application queue routes
- File-based JSON storage for application states (pending/sent/failed)

**Frontend Interface:**
- Application Queue dashboard with card-based layout
- Status indicators (Ready/Needs Review/Sent)
- Application detail modal with tabbed interface
- Real-time validation feedback
- Confirmation dialogs for sends
- Batch send capability

**Quality Assurance:**
- Unit tests for email sender and validation modules
- Integration tests for complete user flow
- Error handling and user feedback mechanisms

### Explicitly Out of Scope (Post-MVP)

- Overnight batch automation/scheduling
- Follow-up tracking system
- Multi-platform job board support
- Headless Playwright mode optimization
- Advanced analytics and reporting
- Cloud deployment (local only for MVP)

---

## Success Criteria

1. **End-to-End Pipeline Works:**
   - User can manually trigger scrape → review → send workflow
   - All three modules (email, validation, queue) function reliably
   - Zero applications sent without explicit user approval

2. **Quality Gates Effective:**
   - Validation prevents sending incomplete applications (100% enforcement)
   - Email sending success rate >95% for properly configured Gmail
   - Clear error messages when issues occur

3. **User Experience Goals Met:**
   - Review 10+ applications in under 30 minutes
   - Obvious visual distinction between ready/needs-review applications
   - Single application review-to-send in under 2 minutes

4. **Technical Quality:**
   - Unit test coverage >80% for new modules
   - Integration test covers complete user journey
   - No regression in existing functionality

---

## Epic Dependencies

**External Dependencies:**
- Gmail account with app password authentication enabled
- `email-validator==2.1.0` Python library
- Existing Flask application infrastructure
- Bootstrap 5 (already in use)

**Internal Dependencies:**
- Existing job scraping functionality (Playwright)
- Existing AI matching and Bewerbung generation (OpenAI)
- Existing user authentication system

**Prerequisite Setup:**
- Gmail app password configured in `.env`
- Required directories created (`job_matches/pending`, `/sent`, `/failed`)
- Dependencies installed (`pip install email-validator==2.1.0`)

---

## Story Map

```
Epic: MVP Email Automation Pipeline
├── Story 1: Backend Infrastructure (Email + Validation) [5 points]
│   ├── Email sender module with Gmail SMTP
│   ├── Data validation module with scoring
│   └── Unit tests for both modules
├── Story 2: Application Queue UI [5 points]
│   ├── Flask routes and blueprint
│   ├── HTML templates (dashboard + modal)
│   ├── JavaScript interactions (AJAX, modals)
│   └── CSS styling for queue components
└── Story 3: Integration and Polish [3 points]
    ├── End-to-end integration testing
    ├── Error handling improvements
    ├── User feedback mechanisms
    └── Documentation updates
```

**Total Story Points:** 13
**Estimated Timeline:** 2 sprints (2 weeks at moderate pace, 1 week full-time)

---

## Story Summaries

### Story 1: Backend Infrastructure (Email + Validation)
**ID:** email-automation-1  
**Points:** 5  
**Estimate:** 5-7 hours

Implement core backend modules for email sending and data validation. Includes Python smtplib email sender with Gmail SMTP authentication, comprehensive validation module with completeness scoring, and unit tests ensuring reliability. This story provides the foundation for application sending with quality gates.

**Key Deliverables:**
- `utils/email_sender.py` - EmailSender class with Gmail SMTP
- `utils/validation.py` - ApplicationValidator class with scoring
- `tests/test_email_sender.py` - Unit tests for email functionality
- `tests/test_validation.py` - Unit tests for validation rules
- Gmail credentials configured in `.env`

### Story 2: Application Queue UI
**ID:** email-automation-2  
**Points:** 5  
**Estimate:** 6-8 hours

Build complete user interface for application review and approval. Includes Flask blueprint with routes, responsive HTML templates using Bootstrap 5, JavaScript interactions for modals and AJAX, and custom CSS for application cards and status indicators. Implements UX specification for efficient morning review workflow.

**Key Deliverables:**
- `blueprints/application_queue_routes.py` - Flask blueprint with routes
- `templates/application_queue.html` - Main queue dashboard
- `templates/application_detail.html` - Modal content
- `static/js/queue.js` - AJAX interactions
- `static/css/queue_styles.css` - Custom styling
- Navigation link added to main dashboard

### Story 3: Integration and Polish
**ID:** email-automation-3  
**Points:** 3  
**Estimate:** 2-4 hours

Complete end-to-end integration testing, refine error handling, and finalize user experience. Includes full pipeline test (scrape → review → send), responsive testing across devices, accessibility validation, error message improvements, and documentation updates.

**Key Deliverables:**
- Integration test suite covering complete user journey
- Error handling refinements based on testing
- Responsive behavior validated on mobile/tablet/desktop
- README.md updated with new features
- `.env.example` documented with email variables

---

## Implementation Sequence

**Recommended Order:**

1. **Story 1 First** (Backend Infrastructure)
   - Establishes foundation for email sending and validation
   - Can be tested independently with test scripts
   - No dependencies on other stories

2. **Story 2 Second** (Application Queue UI)
   - Builds on Story 1's email sender and validator
   - Integrates backend modules into user-facing interface
   - Requires Story 1 completion for send functionality

3. **Story 3 Third** (Integration and Polish)
   - Validates complete system integration
   - Depends on both Story 1 and Story 2
   - Catches any issues missed in individual stories

**Timeline Visualization:**

```
Week 1:
Mon-Wed: Story 1 (Backend Infrastructure)
Thu-Fri: Story 2 begins (Queue UI development)

Week 2:
Mon-Tue: Story 2 completion
Wed-Thu: Story 3 (Integration and Polish)
Fri: Buffer for fixes and deployment
```

---

## Risk Management

**High-Priority Risks:**

1. **Gmail SMTP Reliability**
   - Mitigation: Thorough testing with app password, error handling for auth failures
   - Fallback: Manual email as temporary workaround if issues arise

2. **Validation Completeness**
   - Mitigation: Comprehensive unit tests, real-world data testing
   - Fallback: Manual review remains ultimate quality gate

3. **UI Complexity Creep**
   - Mitigation: Strict adherence to UX spec, no feature additions mid-sprint
   - Fallback: Simplify to essential features if timeline pressured

---

## Related Documents

- **Tech Spec:** `docs/tech-spec.md` - Definitive technical implementation guide
- **UX Spec:** `docs/ux-specification.md` - Complete UI/UX design specification
- **Product Brief:** `docs/product-brief-JobSearchAI-2025-10-15.md` - Strategic context
- **Workflow Status:** `docs/bmm-workflow-status.md` - Current project status

---

## Epic Status Tracking

**Current Phase:** Ready for Implementation  
**Next Action:** Review and approve Story 1, then generate story context  
**Blockers:** None

---

_Generated by BMM (BMad Method) Level 1 planning workflow on 2025-10-15_

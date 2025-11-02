# Epic 4: Missing Features Part 2 - Brownfield Enhancement

## Epic Goal

Complete the UX vision established in Epic 3 by addressing five critical usability gaps that emerged after SQLite deduplication and initial UX improvements, delivering a polished, consistent user experience with full feature parity across all views.

## Epic Description

### Existing System Context

**Current relevant functionality:**
- Dashboard with three process panels: Job Data Acquisition, Run Job Matcher, Run Combined Process
- Active Search Terms widget for CRUD operations on search terms (Story 3.2)
- Unified All Job Matches view with filtering (Story 3.3)
- Two results views: results.html (single report) and all_matches.html (database query)
- SQLite database with deduplication, search term tracking, CV versioning (Epic 2)

**Technology stack:**
- Backend: Flask, SQLite, Python
- Frontend: Jinja2 templates, Bootstrap 5, JavaScript
- Job scraper: Separate Python service with settings.json configuration

**Integration points:**
- Dashboard templates (index.html) connect to job_matching_routes.py
- All Job Matches view queries database through view_all_matches route
- Run Combined Process integrates scraper with matcher
- Active Search Terms widget manages settings.json through settings API

### Enhancement Details

**What's being added/changed:**

Five critical UX improvements identified after Epic 2 and Epic 3 implementation:

1. **Remove Legacy Process Panels** - Delete redundant "Job Data Acquisition" and "Run Job Matcher" panels, keeping only "Run Combined Process" as the unified workflow
2. **Add Search Term Selection** - Enable users to select configured search terms when running the combined process (critical missing functionality)
3. **Standardize Action Menus** - Bring all_matches.html action menu to parity with results.html (8 actions vs 2 buttons)
4. **Standalone All Job Matches Page** - Replace iframe implementation with proper standalone page navigation
5. **Visual Progress Indicators** - Add table row highlighting for jobs with generated letters in All Job Matches view

**How it integrates:**
- Modifies existing templates (index.html, all_matches.html)
- Updates existing routes in job_matching_routes.py
- Extends JavaScript functionality in search_term_manager.js and all_matches.js
- Reuses existing backend logic for file existence checks
- No database schema changes required

**Success criteria:**
- Single, clear workflow for job processing (no redundant panels)
- Users can select from configured search terms (90%+ successful task completion)
- Consistent functionality across all views (full action parity)
- Professional navigation (no iframes, proper back button behavior)
- Immediate visual feedback on job processing status (color-coded rows)

## Stories

### Story 4.1: Remove Legacy Process Panels
**Priority:** HIGH | **Effort:** 0.5 days

Remove redundant "Job Data Acquisition" and "Run Job Matcher" panels from dashboard, keeping only "Run Combined Process" as the unified workflow. Simplifies UI and eliminates user confusion.

### Story 4.2: Add Search Term Selection to Run Combined Process
**Priority:** CRITICAL | **Effort:** 0.5-1 day

Add search term dropdown to Run Combined Process form, enabling users to select which configured search term to use for scraping. Completes the Active Search Terms feature implementation.

### Story 4.3: Standardize Action Menus Across Views
**Priority:** HIGH | **Effort:** 1-1.5 days

Bring All Job Matches view action menu to parity with Job Match Results view (8 actions vs current 2 buttons). Includes View Reasoning modal, Generate Letter variations, Download Word, View Scraped Data, View Email Text.

### Story 4.4: Make All Job Matches a Standalone Page
**Priority:** MEDIUM | **Effort:** 0.5-1 day

Remove iframe implementation and make All Job Matches a proper standalone page with breadcrumb navigation. Improves navigation flow, enables bookmarking, and fixes back button behavior.

### Story 4.5: Add Visual Indicator for Generated Letters
**Priority:** MEDIUM-HIGH | **Effort:** 0.5-1 day

Add visual highlighting (cyan/blue table rows) to All Job Matches view for jobs with generated motivation letters. Provides immediate progress tracking and matches results.html behavior.

## Compatibility Requirements

- [x] Existing APIs remain unchanged (routes kept for backward compatibility)
- [x] Database schema changes are backward compatible (no schema changes)
- [x] UI changes follow existing patterns (Bootstrap components, existing CSS)
- [x] Performance impact is minimal (reuses existing queries and logic)

## Risk Mitigation

**Primary Risk:** Removing legacy panels breaks user workflows or automation

**Mitigation:**
- Keep backend routes active with deprecation warnings
- Update user documentation before deployment
- Phased rollout: Story 4.2 (search term selection) before Story 4.1 (panel removal)
- Communication: Clear release notes explaining changes

**Rollback Plan:**
- Git revert to previous commit (templates only)
- Re-enable removed panels if critical issues arise
- Backend routes remain functional for API compatibility

## Definition of Done

- [x] All 5 stories completed with acceptance criteria met
- [x] Existing functionality verified through regression testing
- [x] Integration points working correctly (dashboard ↔ matcher ↔ scraper)
- [x] Documentation updated (user guide, screenshots)
- [x] No regression in existing features (Epic 2, Epic 3 functionality intact)
- [x] Search term selection works end-to-end
- [x] Action menus consistent across all views
- [x] Navigation flow professional (no iframe issues)
- [x] Visual indicators display correctly

## Implementation Sequence

### Sprint 1 - Critical Functionality & Cleanup
1. **Story 4.2** (CRITICAL) - Add search term selection (enables core feature)
2. **Story 4.1** (HIGH) - Remove legacy panels (depends on 4.2 being functional)

### Sprint 2 - Feature Parity & Polish
3. **Story 4.3** (HIGH) - Standardize action menus (feature parity)
4. **Story 4.5** (MEDIUM-HIGH) - Visual indicators (progress tracking)
5. **Story 4.4** (MEDIUM) - Standalone page (professional polish)

## Technical Dependencies

**Already Complete:**
- ✅ SQLite database with deduplication (Epic 2)
- ✅ Active Search Terms widget (Story 3.2)
- ✅ All Job Matches unified view (Story 3.3)
- ✅ Bootstrap 5, Jinja2 templates
- ✅ File existence checking logic in results.html

**Required New:**
- Search term parameter in run_combined_process route
- API endpoint for job reasoning modal
- JavaScript handlers for action menu
- Backend logic to check generated files for all_matches.html

## Related Documentation

- **Brainstorming Session:** `docs/02_3_System A and B Improvement Plan-implement-missing-features-part-2/brainstorming-session-results.md`
- **Previous Epic:** `docs/stories/epic-3-ux-improvements.md`
- **Architecture:** `docs/02_1_System A and B Improvement Plan/UNIFIED-ARCHITECTURE-DOCUMENT.md`

## Story Manager Handoff

Please develop detailed user stories for this brownfield epic. Key considerations:

**Technology Stack:**
- Backend: Flask (blueprints pattern), SQLite
- Frontend: Jinja2 templates, Bootstrap 5, JavaScript (no framework)
- Job Scraper: Python service with settings.json configuration

**Integration Points:**
- Dashboard templates → job_matching_routes.py
- Run Combined Process → scraper settings.json → matcher
- All Job Matches view → SQLite database queries
- JavaScript → Settings API for search term CRUD

**Existing Patterns to Follow:**
- Bootstrap 5 components (dropdowns, modals, form controls)
- Flask blueprints for routing
- Jinja2 template inheritance
- URL normalization utilities (utils/url_utils.py)
- File existence checking patterns from results.html

**Critical Compatibility Requirements:**
- Do not modify database schema
- Keep backend routes functional (mark deprecated if needed)
- Reuse existing URL normalization logic
- Match visual styling of results.html (table-info class for highlighting)
- Maintain backward compatibility for any automation

**Each Story Must Include:**
- Verification that existing Epic 2 and Epic 3 functionality remains intact
- Testing of integration points (scraper ↔ matcher ↔ database)
- Regression testing checklist
- User documentation updates

The epic should maintain system integrity while delivering a polished, consistent UX with full feature parity across all views and proper search term selection workflow.

---

**Epic Status:** Ready for Story Creation  
**Created:** November 2, 2025  
**Created By:** Product Manager (John)

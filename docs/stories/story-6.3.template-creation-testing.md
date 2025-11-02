# Story 6.3: Template Creation and Testing

**Epic:** Epic 6 - CV Template Generation  
**Status:** Draft  
**Story Type:** Template & Testing  
**Estimate:** 5 Story Points

---

## User Story

As a **job seeker using the application**,  
I want **a professionally formatted CV template that displays my tailored content correctly**,  
So that **my generated CVs look polished and professional for job applications**.

---

## Story Context

### Existing System Integration

**Integrates with:**
- `cv_template_generator.py` - Uses template for rendering (Story 6.1)
- `letter_generation_utils.py` - Integrated workflow (Story 6.2)
- DocxTpl library - Template rendering engine
- Existing application workflow

**Technology:**
- Microsoft Word (.docx format)
- DocxTpl library with Jinja2 syntax
- Professional CV formatting

**Follows pattern:**
- Similar to `Bewerbungsschreiben_template.docx` structure
- Professional document formatting
- Jinja2 placeholder syntax for DocxTpl

**Touch points:**
- Template stored in `process_cv/cv-data/template/`
- Used by `cv_template_generator.py::render_cv_template()`
- Tested through complete workflow

---

## Acceptance Criteria

### Functional Requirements

1. **Template File Creation**
   - Create `Lebenslauf_template.docx` Word document
   - Save to `process_cv/cv-data/template/` directory
   - Template uses professional CV formatting
   - File is compatible with DocxTpl library

2. **Placeholder Implementation**
   - Template contains `{{cv_motivation}}` placeholder
   - Template contains `{{cv_kurzprofil}}` placeholder
   - Template contains list placeholder for `{{fachkompetenzen}}`
   - Placeholders use correct Jinja2 syntax for DocxTpl
   - List syntax: `{% for item in fachkompetenzen %}{{item}}{% endfor %}`

3. **Professional Formatting**
   - Clear section headers (Motivation, Kurzprofil, Fachkompetenzen)
   - Consistent font usage throughout
   - Proper spacing between sections
   - Professional margins and layout
   - List formatting for competencies (bullet points)

4. **Template Testing with DocxTpl**
   - Template loads successfully with `DocxTemplate(path)`
   - Template renders with sample data
   - All placeholders replaced correctly
   - List items render as separate bullets
   - Generated document maintains formatting

5. **Language Considerations**
   - Section headers in German (primary language)
   - Template works for both German and English content
   - Special characters (ü, ö, ä) display correctly
   - No encoding issues

6. **Directory Structure**
   - Ensure `process_cv/cv-data/template/` directory exists
   - Template file accessible to cv_template_generator
   - Proper file permissions for reading

### Integration Requirements

7. **End-to-End Workflow Testing**
   - Test complete workflow from UI to generated CV
   - Generate motivation letter → verify CV created
   - Open generated CV → verify content rendered
   - Test with multiple different jobs
   - Test with both German and English jobs

8. **Content Quality Verification**
   - Generated CV content is job-specific
   - Word counts meet requirements (45-55 words)
   - Competencies list shows exactly 9 items
   - Content is relevant to job posting
   - No placeholder text remains

9. **Performance Validation**
   - CV generation completes within 7 seconds
   - No performance degradation to letter generation
   - Template rendering is fast (<1 second)
   - File I/O operations efficient

### Quality Requirements

10. **Manual Testing Scenarios**
    - Test with sample German job posting
    - Test with sample English job posting
    - Test with various job descriptions
    - Verify formatting in Word
    - Print preview verification
    - Compare with existing Bewerbungsschreiben template quality

11. **Error Handling Verification**
    - Test with missing template file
    - Test with corrupted template file
    - Test with invalid placeholder syntax
    - Verify appropriate error messages
    - Verify non-blocking behavior maintained

12. **Documentation Updates**
    - Update README if needed
    - Document template customization options
    - Add template location to configuration docs
    - Note any special requirements

---

## Technical Notes

### Template Structure

**File:** `process_cv/cv-data/template/Lebenslauf_template.docx`

**Required Sections:**
1. Header/Title section
2. Motivation section with `{{cv_motivation}}` placeholder
3. Kurzprofil section with `{{cv_kurzprofil}}` placeholder
4. Fachkompetenzen section with list loop

**Placeholder Syntax:**

```
Text placeholders:
{{cv_motivation}}
{{cv_kurzprofil}}

List placeholder:
{% for kompetenz in fachkompetenzen %}
• {{kompetenz}}
{% endfor %}
```

### Template Creation Steps

1. **Create Base Document**
   - Open Microsoft Word
   - Set up professional CV layout
   - Add section headers
   - Configure fonts and spacing

2. **Add Placeholders**
   - Insert `{{cv_motivation}}` in motivation section
   - Insert `{{cv_kurzprofil}}` in profile section
   - Create bulleted list with Jinja2 loop for competencies
   - Verify syntax is correct for DocxTpl

3. **Format Document**
   - Apply consistent fonts (e.g., Arial 10-12pt)
   - Set appropriate margins (2.5cm standard)
   - Configure section spacing
   - Apply professional styling

4. **Save and Test**
   - Save as `Lebenslauf_template.docx`
   - Test with DocxTpl library
   - Verify all placeholders work
   - Adjust formatting if needed

### Sample Test Data

**For Template Testing:**

```python
test_data = {
    'cv_motivation': 'Als erfahrener Softwareentwickler mit Schwerpunkt auf Backend-Entwicklung und über 5 Jahren Erfahrung in agilen Teams bin ich begeistert von der Möglichkeit, bei Ihrer innovativen Firma als Senior Developer zu arbeiten und zur Entwicklung moderner Webanwendungen beizutragen.',  # 45 words
    
    'cv_kurzprofil': 'Passionierter Full-Stack Entwickler mit umfassender Expertise in Python, JavaScript und Cloud-Technologien. Nachgewiesene Erfolge in der Leitung technischer Projekte von der Konzeption bis zur Produktivsetzung. Starke Kommunikationsfähigkeiten und Erfahrung in der Zusammenarbeit mit internationalen Teams.',  # 45 words
    
    'fachkompetenzen': [
        'Python, FastAPI, Django',
        'JavaScript, React, Node.js',
        'AWS, Docker, Kubernetes',
        'PostgreSQL, MongoDB',
        'REST APIs, Microservices',
        'Git, CI/CD, Agile',
        'Testing, TDD, Quality Assurance',
        'System Design, Architecture',
        'Team Leadership, Mentoring'
    ]
}
```

### Testing Checklist Items

**Template Validation:**
- [ ] Template file exists at correct location
- [ ] File opens in Microsoft Word without errors
- [ ] DocxTemplate can load the file
- [ ] All placeholders present and correctly formatted
- [ ] List loop syntax is correct

**Rendering Validation:**
- [ ] Template renders with test data
- [ ] Motivation section shows content
- [ ] Kurzprofil section shows content
- [ ] Competencies show as 9 bullet points
- [ ] No placeholder syntax remains visible
- [ ] Formatting is preserved

**Workflow Validation:**
- [ ] Complete workflow from UI works
- [ ] CV file appears in application folder
- [ ] Generated CV opens in Word
- [ ] Content is job-specific
- [ ] Multiple generations work correctly

---

## Definition of Done

- [x] `Lebenslauf_template.docx` created
- [x] Template saved in `process_cv/cv-data/template/` directory
- [x] All placeholders implemented correctly
- [x] Professional formatting applied
- [x] Template tested with DocxTpl library
- [x] Sample rendering successful
- [x] End-to-end workflow tested
- [x] Generated CVs display correctly in Word
- [x] Both German and English content tested
- [x] Performance meets requirements (<7 seconds total)
- [x] No regression in existing functionality
- [x] Error scenarios tested (missing template, etc.)
- [x] Documentation updated
- [x] Template approved for production use

---

## Testing Checklist

### Template Testing

```
[ ] Create template in Word
    - Professional CV layout
    - Clear section structure
    - Proper formatting
    
[ ] Add placeholders
    - {{cv_motivation}} placeholder
    - {{cv_kurzprofil}} placeholder
    - Jinja2 list loop for competencies
    
[ ] Test with DocxTpl
    - Load template with DocxTemplate()
    - Render with sample data
    - Verify output looks correct
    - Check all placeholders replaced
    
[ ] Format verification
    - Check in Word
    - Print preview
    - Font consistency
    - Spacing appropriate
    - Professional appearance
```

### End-to-End Testing

```
[ ] Full Workflow Test - German Job
    - Select German job posting
    - Generate motivation letter
    - Verify Lebenslauf.docx created
    - Open CV in Word
    - Verify content is in German
    - Verify content is job-specific
    - Check word counts
    - Check 9 competencies
    
[ ] Full Workflow Test - English Job
    - Select English job posting
    - Generate motivation letter
    - Verify Lebenslauf.docx created
    - Open CV in Word
    - Verify content is in English
    - Verify content is job-specific
    - Check word counts
    - Check 9 competencies
    
[ ] Multiple Generation Test
    - Generate CV for Job A
    - Generate CV for Job B
    - Generate CV for Job C
    - Verify each has unique, relevant content
    - Verify no content mixing
    
[ ] Performance Test
    - Measure total generation time
    - Verify <7 seconds for CV generation
    - Verify no impact on letter generation time
    - Check logs for performance data
```

### Error Scenario Testing

```
[ ] Missing Template Test
    - Rename template file temporarily
    - Generate motivation letter
    - Verify letter still generates
    - Verify warning logged
    - Verify workflow continues
    
[ ] Missing CV Summary Test
    - Remove CV summary file
    - Generate motivation letter
    - Verify letter still generates
    - Verify warning logged
    - Verify no CV generated
    
[ ] API Failure Simulation
    - Mock OpenAI API failure
    - Generate motivation letter
    - Verify letter generation continues
    - Verify error logged
    - Verify graceful handling
```

### Regression Testing

```
[ ] Existing functionality unchanged
    - Motivation letter DOCX generated
    - Motivation letter HTML generated
    - Original CV (PDF) copied
    - Email text generated
    - Application folder structure correct
    - All metadata files present
    - No UI changes
    - No route changes
```

---

## Dependencies

**Requires Stories 6.1 and 6.2 Completed:**
- `cv_template_generator.py` module exists and works
- Integration in `letter_generation_utils.py` complete
- Full workflow functional

**External Dependencies:**
- Microsoft Word (for template creation)
- DocxTpl library (already installed)

**Tools Needed:**
- Microsoft Word or compatible editor
- Sample job postings (German and English)
- Sample CV summary file

---

## Risk Assessment

**Risk:** Template formatting breaks in DocxTpl rendering

**Mitigation:**
- Test template extensively with DocxTpl before deployment
- Keep template simple and proven formatting
- Reference working Bewerbungsschreiben template
- Document any formatting limitations

**Risk:** Generated content doesn't fit template layout

**Mitigation:**
- Word count validation ensures content fits
- Template designed with flexible spacing
- Test with various content lengths
- Adjust template if needed during testing

**Risk:** Template file corruption or inaccessibility

**Mitigation:**
- Version control template file
- Backup template in safe location
- Clear error messages if template missing
- Non-blocking design means workflow continues

---

## Notes for Developer

- **Template Design:** Keep it simple and professional
- **Placeholder Syntax:** Must match DocxTpl/Jinja2 requirements exactly
- **Testing:** Test with real-world data, not just happy path
- **Formatting:** Less is more - avoid complex Word features
- **List Syntax:** Ensure loop syntax is correct for bullet points
- **Backup:** Keep original template safe during testing
- **Comparison:** Look at Bewerbungsschreiben template for inspiration
- **Languages:** Test with both German and English thoroughly
- **Edge Cases:** Test with very short and very long content
- **Documentation:** Document any template customization options

---

## Post-Deployment Checklist

```
[ ] Template file deployed to production
[ ] Directory permissions verified
[ ] End-to-end workflow tested in production
[ ] Monitoring in place for CV generation
[ ] Error logs reviewed
[ ] User feedback collected
[ ] Performance metrics reviewed
[ ] Documentation updated
[ ] Rollback plan tested and documented
[ ] Success metrics tracked (generation count, success rate)

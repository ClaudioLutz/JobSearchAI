# 5. Word Template Generator

**Purpose**: Convert motivation letter JSON data to professionally formatted Word documents using templates.

**Key Files**:
- `word_template_generator.py`: Main script for generating Word documents
- `motivation_letters/template/motivation_letter_template.docx`: Default path to the Word template with Jinja2-style variables.

**Technologies**:
- `docxtpl` library for template-based Word document generation (uses Jinja2 syntax).
- `python-docx` (as a dependency of `docxtpl`) for underlying Word document manipulation.
- JSON for structured data input.

**Process**:
1. Takes a structured JSON representation of a motivation letter (either as a dictionary or loaded from a file).
2. Loads a pre-designed Word template (`.docx`) containing Jinja2-style variables (e.g., `{{ variable_name }}`).
3. Creates a context dictionary mapping template variables to values from the input JSON.
4. Renders the template using `docxtpl`, replacing variables with the context data.
5. Saves the generated Word document. The default filename is based on the company name (`motivation_letters/motivation_letter_{company_name}.docx`) when called via `json_to_docx` without an explicit `output_path`. When called via `create_word_document_from_json_file`, the output filename mirrors the input JSON filename with a `.docx` extension.

**Features**:
- Template-based document generation for consistent formatting using `docxtpl`.
- Supports Jinja2-style variables, loops (`{% for ... %}`), and conditionals (`{% if ... %}`) within the Word template.
- Preserves formatting and styling from the Word template.
- Generates Word documents matching standard motivation letter structure based on input JSON.
- Automatic filename generation (defaulting to company name or based on input JSON filename).
- Designed to be easily integrated into workflows (e.g., called after motivation letter generation).
- Graceful error handling with informative error messages.
- Default values for missing fields to prevent template rendering issues.

**Functions**:
- `json_to_docx(motivation_letter_json, template_path='motivation_letters/template/motivation_letter_template.docx', output_path=None)`: 
  - Converts JSON to a Word document using a template
  - Creates output directory if it doesn't exist
  - Returns the path to the generated document or None if an error occurs
  - Uses company name (truncated to 30 chars) for default filename
- `create_word_document_from_json_file(json_file_path, template_path='motivation_letters/template/motivation_letter_template.docx')`:
  - Creates a Word document from a JSON file using a template
  - Output filename mirrors input JSON filename with .docx extension
  - Returns the path to the generated document or None if an error occurs

**Template Variables**:
The Word template includes the following variables with their mappings and defaults:
```
# Candidate Information
{{ candidate_name }}         # from JSON 'candidate_name' or ''
{{ candidate_address }}      # from JSON 'candidate_address' or ''
{{ candidate_city }}         # from JSON 'candidate_city' or ''
{{ candidate_email }}        # from JSON 'candidate_email' or ''
{{ candidate_phone }}        # from JSON 'candidate_phone' or ''

# Company Information
{{ company_name }}          # from JSON 'company_name' or ''
{{ company_department }}    # from JSON 'company_department' or ''
{{ company_street_number }} # from JSON 'company_street_number' or ''
{{ company_plz_city }}      # from JSON 'company_plz_city' or ''
{{ contact_person }}        # from JSON 'contact_person' or ''

# Letter Content
{{ date }}                  # from JSON 'date' or ''
{{ subject }}               # from JSON 'subject' or ''
{{ Salutation }}           # from JSON 'greeting' or 'Sehr geehrte Damen und Herren'
{{ introduction }}         # from JSON 'introduction' or ''

{% for paragraph in body_paragraphs %}
{{ paragraph }}            # from JSON 'body_paragraphs' list or []
{% endfor %}

{{ closing }}              # from JSON 'closing' or ''
{{ signature }}            # from JSON 'signature' or ''
{{ full_name }}            # from JSON 'full_name' or ''
```

**Output Format**:
- Word document (.docx) with a professionally formatted motivation letter
- The document includes:
  - Candidate's contact information
  - Company address and contact person
  - Date
  - Subject line
  - Formal greeting (with default if not provided)
  - Introduction paragraph
  - Main body paragraphs
  - Closing paragraph
  - Formal closing and signature

**Error Handling**:
- Missing JSON fields are replaced with empty strings to prevent template rendering errors
- Directory creation errors are caught and handled
- Template loading errors are caught and reported
- JSON parsing errors (for file-based creation) are caught and reported
- All errors return None and print an error message for debugging

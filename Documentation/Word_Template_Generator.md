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

**Functions**:
- `json_to_docx(motivation_letter_json, template_path='motivation_letters/template/motivation_letter_template.docx', output_path=None)`: Converts JSON to a Word document using a template
- `create_word_document_from_json_file(json_file_path, template_path='motivation_letters/template/motivation_letter_template.docx')`: Creates a Word document from a JSON file using a template

**Template Variables**:
The Word template includes the following variables:
```
{{ candidate_name }}
{{ candidate_address }}
{{ candidate_city }}
{{ candidate_email }}
{{ candidate_phone }}

{{ company_name }}
{{ company_department }}
{{ company_street_number }}
{{ company_plz_city }}

{{ date }}
{{ subject }}
{{ greeting }}
{{ introduction }}

{% for paragraph in body_paragraphs %}
{{ paragraph }}
{% endfor %}

{{ closing }}
{{ signature }}
{{ full_name }}
```

**Output Format**:
- Word document (.docx) with a professionally formatted motivation letter
- The document includes:
  - Candidate's contact information
  - Company address
  - Date
  - Subject line
  - Formal greeting
  - Introduction paragraph
  - Main body paragraphs
  - Closing paragraph
  - Formal closing and signature

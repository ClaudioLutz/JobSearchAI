# 5. Word Template Generator

**Purpose**: Convert motivation letter JSON data to professionally formatted Word documents using templates.

**Key Files**:
- `word_template_generator.py`: Main script for generating Word documents
- `motivation_letters/template/motivation_letter_template.docx`: Word template with Jinja2-style variables

**Technologies**:
- docxtpl for template-based Word document generation
- python-docx as the underlying library for Word document manipulation
- JSON for structured data input
- Jinja2-style template syntax for variable replacement
- Datetime for timestamp generation

**Process**:
1. Takes a structured JSON representation of a motivation letter
2. Loads a pre-designed Word template with Jinja2-style variables (e.g., `{{ variable_name }}`)
3. Replaces the variables with actual content from the JSON data
4. Saves the document to a file with a timestamp in the filename

**Features**:
- Template-based document generation for consistent formatting
- Support for Jinja2-style variables in Word templates
- Support for loops and conditionals in templates
- Professional document formatting with proper styling preserved from the template
- Structured layout matching standard motivation letter format
- Automatic filename generation based on job title and company
- Integration with the motivation letter generator
- Detailed logging for troubleshooting

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

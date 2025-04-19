# Word Template Update Documentation

## Overview

This document describes the update to the Word template generation process in the JobsearchAI system. The system has been updated to use the `docxtpl` library instead of the previous bookmark-based approach.

## Changes Made

### 1. Template Approach

**Previous Approach:**
- Used Word bookmarks to mark locations in the template where content should be inserted
- Required manual creation of bookmarks in the Word document
- Used direct XML manipulation to replace bookmark content

**New Approach:**
- Uses Jinja2-style variables (`{{ variable_name }}`) directly in the Word document
- Simplifies template creation and maintenance
- Uses the `docxtpl` library which is built on top of `python-docx` but adds template functionality

### 2. Code Changes

The `word_template_generator.py` file has been completely refactored:

- Removed bookmark-related functions (`replace_bookmark_text` and `insert_body_paragraphs_at_bookmark`)
- Simplified the `json_to_docx` function to use `DocxTemplate` from the `docxtpl` library
- Maintained the same function signatures for backward compatibility

### 3. Template Changes

The Word template has been updated:

- Replaced bookmarks with Jinja2-style variables (e.g., `{{ candidate_name }}`)
- For body paragraphs, the template now uses a loop: `{% for paragraph in body_paragraphs %}{{ paragraph }}{% endfor %}`

## Benefits of the New Approach

1. **Simpler Template Creation**: Non-technical users can create templates by simply typing placeholders
2. **Visual Feedback**: Placeholders are visible in the document, making it easier to see what will be replaced
3. **Less Complex Code**: No need for low-level XML manipulation
4. **More Maintainable**: The docxtpl library handles the complexities of Word document generation

## Required Variables in the Template

The following variables should be included in the Word template:

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

## Testing

A test script (`test_word_template.py`) has been created to verify the functionality of the new implementation. The test generates a sample motivation letter using the updated template and code.

## Future Considerations

- Consider adding support for additional template variables as needed
- Explore additional features of the `docxtpl` library, such as conditional sections and image insertion

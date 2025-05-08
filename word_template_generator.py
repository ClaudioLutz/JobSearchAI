import os
import json
from pathlib import Path
from docxtpl import DocxTemplate
from config import config # Import config

def json_to_docx(motivation_letter_json, template_path=None, output_path=None):
    """Generate a Word document from motivation letter JSON using docxtpl template."""
    try:
        # Use config for default template path
        if template_path is None:
            template_path = config.get_path('letter_template')
            if not template_path:
                print("Error: 'letter_template' path not found in config.")
                return None
        
        # Load the template
        doc = DocxTemplate(str(template_path)) # docxtpl expects string path
        
        # Create context dictionary for template rendering
        context = {
            'candidate_name': motivation_letter_json.get('candidate_name', ''),
            'candidate_address': motivation_letter_json.get('candidate_address', ''),
            'candidate_city': motivation_letter_json.get('candidate_city', ''),
            'candidate_email': motivation_letter_json.get('candidate_email', ''),
            'candidate_phone': motivation_letter_json.get('candidate_phone', ''),
            'company_name': motivation_letter_json.get('company_name', ''),
            'company_department': motivation_letter_json.get('company_department', ''),
            'company_street_number': motivation_letter_json.get('company_street_number', ''),
            'company_plz_city': motivation_letter_json.get('company_plz_city', ''),
            'contact_person': motivation_letter_json.get('contact_person', ''), # Added contact person
            'date': motivation_letter_json.get('date', ''),
            'subject': motivation_letter_json.get('subject', ''),
            'Salutation': motivation_letter_json.get('greeting', 'Sehr geehrte Damen und Herren'), # Map JSON 'greeting' to template 'Salutation'
            'introduction': motivation_letter_json.get('introduction', ''),
            'body_paragraphs': motivation_letter_json.get('body_paragraphs', []),
            'closing': motivation_letter_json.get('closing', ''),
            'signature': motivation_letter_json.get('signature', ''),
            'full_name': motivation_letter_json.get('full_name', '')
        }
        
        # Render the template with the context
        doc.render(context)
        
        # Determine output path
        if not output_path:
            letters_dir = config.get_path('motivation_letters')
            if not letters_dir:
                print("Error: 'motivation_letters' path not found in config.")
                return None
            job_title = motivation_letter_json.get('company_name', 'company').replace(' ', '_')[:30]
            # Ensure job_title is safe for a filename
            safe_job_title = "".join(c if c.isalnum() or c in ['_','-'] else '_' for c in job_title)
            output_path = letters_dir / f"motivation_letter_{safe_job_title}.docx"
        else:
            output_path = Path(output_path)
        
        # Ensure the directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save the document
        doc.save(str(output_path)) # docxtpl expects string path
        return str(output_path)
    except Exception as e:
        print(f"Error generating Word document: {e}")
        return None

def create_word_document_from_json_file(json_file_path, template_path=None):
    """Load JSON file and generate Word document using the template."""
    try:
        # Use config for default template path
        if template_path is None:
            template_path = config.get_path('letter_template')
            if not template_path:
                print("Error: 'letter_template' path not found in config for create_word_document_from_json_file.")
                return None
        
        with open(json_file_path, 'r', encoding='utf-8') as f:
            motivation_letter_json = json.load(f)
        
        # Determine output_path based on json_file_path, ensuring it's in the configured motivation_letters directory
        letters_dir = config.get_path('motivation_letters')
        if not letters_dir:
            print("Error: 'motivation_letters' path not found in config for output.")
            # Fallback to placing it next to the JSON, though not ideal
            output_filename = Path(json_file_path).stem + ".docx"
            output_path = Path(json_file_path).parent / output_filename
        else:
            output_filename = Path(json_file_path).stem + ".docx"
            output_path = letters_dir / output_filename

        return json_to_docx(motivation_letter_json, template_path=str(template_path), output_path=str(output_path)) # Pass paths as strings
    except Exception as e:
        print(f"Error creating Word document from JSON file: {e}")
        return None

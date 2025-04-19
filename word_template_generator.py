import os
import json
from pathlib import Path
from docxtpl import DocxTemplate

def json_to_docx(motivation_letter_json, template_path='motivation_letters/template/motivation_letter_template.docx', output_path=None):
    """Generate a Word document from motivation letter JSON using docxtpl template."""
    try:
        # Load the template
        doc = DocxTemplate(template_path)
        
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
            'date': motivation_letter_json.get('date', ''),
            'subject': motivation_letter_json.get('subject', ''),
            'greeting': motivation_letter_json.get('greeting', ''),
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
            job_title = motivation_letter_json.get('company_name', 'company').replace(' ', '_')[:30]
            output_path = Path('motivation_letters') / f"motivation_letter_{job_title}.docx"
        else:
            output_path = Path(output_path)
        
        # Ensure the directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save the document
        doc.save(str(output_path))
        return str(output_path)
    except Exception as e:
        print(f"Error generating Word document: {e}")
        return None

def create_word_document_from_json_file(json_file_path, template_path='motivation_letters/template/motivation_letter_template.docx'):
    """Load JSON file and generate Word document using the template."""
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            motivation_letter_json = json.load(f)
        output_path = json_file_path.replace('.json', '.docx')
        return json_to_docx(motivation_letter_json, template_path=template_path, output_path=output_path)
    except Exception as e:
        print(f"Error creating Word document from JSON file: {e}")
        return None

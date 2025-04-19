import json
from word_template_generator import json_to_docx

def test_template():
    """Test the word template generator with sample data."""
    # Sample motivation letter data
    sample_data = {
        "candidate_name": "Max Mustermann",
        "candidate_address": "Musterstrasse 123",
        "candidate_city": "8000 Zürich",
        "candidate_email": "max.mustermann@example.com",
        "candidate_phone": "+41 123 456 789",
        "company_name": "Example AG",
        "company_department": "Personalabteilung",
        "company_street_number": "Beispielstrasse 456",
        "company_plz_city": "8001 Zürich",
        "date": "Zürich, den 19.04.2025",
        "subject": "Bewerbung als Software Entwickler",
        "greeting": "Sehr geehrte Damen und Herren",
        "introduction": "Mit grossem Interesse habe ich Ihre Stellenausschreibung für die Position als Software Entwickler gelesen und bewerbe mich hiermit um diese Stelle.",
        "body_paragraphs": [
            "Während meiner mehrjährigen Tätigkeit als Entwickler konnte ich umfangreiche Erfahrungen in der Programmierung mit Python und JavaScript sammeln. Besonders meine Kenntnisse in der Webentwicklung mit modernen Frameworks wie React und Django würden perfekt zu den Anforderungen Ihrer ausgeschriebenen Stelle passen.",
            "Meine Stärken liegen in der strukturierten Arbeitsweise, der schnellen Auffassungsgabe für neue Technologien und der Fähigkeit, komplexe Probleme zu analysieren und effiziente Lösungen zu entwickeln. Zudem arbeite ich gerne im Team und bringe mich aktiv in Projekte ein."
        ],
        "closing": "Ich freue mich auf die Möglichkeit, mich persönlich bei Ihnen vorzustellen und meine Qualifikationen näher zu erläutern.",
        "signature": "Mit freundlichen Grüssen",
        "full_name": "Max Mustermann"
    }
    
    # Generate the Word document
    output_path = json_to_docx(sample_data, template_path='motivation_letters/template/motivation_letter_template.docx')
    
    if output_path:
        print(f"Test successful! Word document generated at: {output_path}")
    else:
        print("Test failed! Could not generate Word document.")

if __name__ == "__main__":
    test_template()

"""
Letter generation utilities for JobsearchAI.

This module provides functions for generating motivation letters and email texts
using the OpenAI API and converting the generated content to HTML format.
"""

import logging
import json
from pathlib import Path

# Import from centralized configuration
from config import config, get_openai_api_key, get_openai_defaults

# Import utilities
from utils.file_utils import (
    save_json_file, 
    ensure_output_directory,
    create_application_folder,
    create_metadata_file,
    copy_cv_to_folder,
    export_email_text,
    create_status_file
)
from utils.api_utils import openai_client, generate_json_from_prompt
from utils.decorators import handle_exceptions, log_execution_time

# Set up logger for this module
logger = logging.getLogger("letter_generation_utils")
# Configure logging basic setup if needed when run standalone
if not logger.hasHandlers():
     logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


@handle_exceptions(default_return="<p>Error generating HTML content</p>")
def json_to_html(motivation_letter_json):
    """Convert motivation letter JSON to HTML format"""
    candidate_name = motivation_letter_json.get('candidate_name', '')
    candidate_address = motivation_letter_json.get('candidate_address', '')
    candidate_city = motivation_letter_json.get('candidate_city', '')
    candidate_email = motivation_letter_json.get('candidate_email', '')
    candidate_phone = motivation_letter_json.get('candidate_phone', '')
    company_name = motivation_letter_json.get('company_name', '')
    company_department = motivation_letter_json.get('company_department', '')
    company_street_number = motivation_letter_json.get('company_street_number', '')
    company_plz_city = motivation_letter_json.get('company_plz_city', '')
    date = motivation_letter_json.get('date', '')
    subject = motivation_letter_json.get('subject', '')
    # Use the 'greeting' field directly from the JSON
    greeting = motivation_letter_json.get('greeting', 'Sehr geehrte Damen und Herren') # Fallback greeting
    introduction = motivation_letter_json.get('introduction', '')
    body_paragraphs = motivation_letter_json.get('body_paragraphs', [])
    closing = motivation_letter_json.get('closing', '')
    signature = motivation_letter_json.get('signature', '')
    full_name = motivation_letter_json.get('full_name', '')

    html_content = f"""<!DOCTYPE html>
<html lang="de">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Motivationsschreiben</title></head>
<body>
    <p>{candidate_name}<br>{candidate_address}<br>{candidate_city}<br>{candidate_email}<br>{candidate_phone}</p>
    <p>{company_name}<br>{company_department}<br>{company_street_number}<br>{company_plz_city}</p>
    <p>{date}</p>
    <h2>{subject}</h2>
    <p>{greeting},</p>
    <p>{introduction}</p>
"""
    for paragraph in body_paragraphs: html_content += f"    <p>{paragraph}</p>\n"
    html_content += f"""
    <p>{closing}</p>
    <p>{signature},<br>{full_name}</p>
</body></html>"""
    return html_content


@handle_exceptions(default_return=None)
@log_execution_time()
def generate_motivation_letter(cv_summary, job_details):
    """Generate a motivation letter using OpenAI API"""
    # Extract pre-determined salutation, default if not found
    extracted_salutation = job_details.get('Salutation', 'Sehr geehrte Damen und Herren')
    if not extracted_salutation or not isinstance(extracted_salutation, str) or len(extracted_salutation.strip()) == 0:
         extracted_salutation = 'Sehr geehrte Damen und Herren'
         logger.warning("Using default greeting as extracted 'Salutation' was empty or invalid.")
    else:
         logger.info(f"Using extracted salutation: '{extracted_salutation}'")

    # Updated prompt: Include Contact Person in input, request contact_person in output JSON.
    prompt = """
    Schreibe ein Motivationsschreiben aus den Informationen von der Webseite IN DER GLEICHEN SPRACHE WIE DIE INFORMATIONEN VON DER WEBSEITE! und dem Lebenslauf:
    
    IMPORTANT INSTRUCTION: Write the motivation letter in THE EXACT SAME LANGUAGE as the job description. If the job description is in English, write in English. If it's in German, write in German. MATCH THE LANGUAGE OF THE JOB POSTING EXACTLY!
    ## Lebenslauf des Bewerbers:\n{}\n
    ## Stellenangebot (von der Webseite):\nTitel: {}\nFirma: {}\nOrt: {}\nBeschreibung: \n{}\nErforderliche Fähigkeiten: \n{}\nVerantwortlichkeiten: \n{}\nUnternehmensinformationen: \n{}\nAnrede (Salutation): {}\nAnsprechpartner (Contact Person): {}\n
    Das Motivationsschreiben sollte:\n1. Professionell und überzeugend sein\n2. Die Qualifikationen und Erfahrungen des Bewerbers KONKRET mit den Anforderungen der Stelle verknüpfen\n3. Die Motivation des Bewerbers für die Stelle und das Unternehmen zum Ausdruck bringen\n4. Etwa eine halbe Seite lang sein (ca. 150-200 Wörter)\n5. In der gleichen Sprache wie die Jobbeschreibung verfasst sein\n6. Im formalen Bewerbungsstil mit Einleitung, Hauptteil, Schluss und Grußformel sein (OHNE die Anrede/greeting selbst zu generieren)\n7. SPEZIFISCH auf die Stellenanforderungen und Verantwortlichkeiten eingehen, die aus der Webseite extrahiert wurden\n8. Die Stärken des Bewerbers hervorheben, die besonders relevant für diese Position sind\n9. Auf die Unternehmenskultur und -werte eingehen, wenn diese Informationen verfügbar sind\n10. KONKRETE BEISPIELE aus dem Lebenslauf des Bewerbers verwenden, die zeigen, wie er/sie die Anforderungen erfüllt\n
    WICHTIG: Falls die Firma der ausgeschriebenen Stell die "Universal-Job AG" ist, behandle sie als Personalvermittler in deinem Schreiben und passe den Inhalt entsprechend an. In diesem Fall wissen wir nicht wer die Stelle schlussendlich ausgeschrieben hat.\n
    WICHTIG: Verwende die detaillierten Informationen aus der Stellenbeschreibung, um ein personalisiertes und spezifisches Motivationsschreiben zu erstellen. Gehe auf konkrete Anforderungen und Verantwortlichkeiten ein und zeige, wie der Bewerber diese erfüllen kann.\n
    WICHTIG: Der Motivations Text darf maximal 200-300 Wörter beinhalten.\n"ß" soll als "ss" geschrieben werden.\n
    ACHTE AUF DIE RECHTSCHREIBUNG UND GRAMMATIK DENN DAS IST EIN BEWERBUNGSSCHREIBEN!  \n

    WICHTIG: Die Sprache des Motivationsschreibens MUSS mit der Sprache der Jobbeschreibung übereinstimmen! \n

    Gib das Motivationsschreiben als JSON-Objekt mit folgender Struktur zurück (das 'greeting'-Feld wird später hinzugefügt):\n```json\n{{\n  "candidate_name": "Vollständiger Name des Bewerbers",\n  "candidate_address": "Straße und Hausnummer",\n  "candidate_city": "PLZ und Ort",\n  "candidate_email": "E-Mail-Adresse",\n  "candidate_phone": "Telefonnummer",\n  "company_name": "Name des Unternehmens",\n  "company_department": "Abteilung (falls bekannt, sonst 'Personalabteilung')",\n  "company_street_number": "Strasse und Hausnummerdes Unternehmens (falls bekannt)",\n  "company_plz_city": "Postleitzahl und Stadt (falls bekannt)",\n  "contact_person": "Name des Ansprechpartners (falls bekannt, sonst null)",\n  "date": "Ort, den [aktuelles Datum]",\n  "subject": "Bewerbung als [Stellentitel]",\n  "introduction": "Einleitungsabsatz",\n  "body_paragraphs": [\n    "Erster Hauptabsatz",\n    "Zweiter Hauptabsatz",\n    "Dritter Hauptabsatz (falls nötig)"\n  ],\n  "closing": "Schlussabsatz",\n  "signature": "Grussformel (z.B. 'Mit freundlichen Grüssen')",\n  "full_name": "Vollständiger Name des Bewerbers"\n}}\n```\nStelle sicher, dass alle Felder korrekt befüllt sind und das JSON-Format gültig ist. Das Feld 'greeting' wird NICHT von dir generiert.
    """.format(
        cv_summary,
        job_details.get('Job Title', 'N/A'),
        job_details.get('Company Name', 'N/A'),
        job_details.get('Location', 'N/A'),
        job_details.get('Job Description', 'N/A'),
        job_details.get('Required Skills', 'N/A'),
        job_details.get('Responsibilities', 'Keine spezifischen Verantwortlichkeiten aufgeführt.'),
        job_details.get('Company Information', 'Keine spezifischen Unternehmensinformationen verfügbar.'),
        extracted_salutation, # Include the extracted salutation in the input context
        job_details.get('Contact Person', 'N/A') # Include the contact person name in the input context
    )

    # Get OpenAI defaults
    openai_defaults = get_openai_defaults()
    
    # Use generate_json_from_prompt to get structured JSON result
    system_prompt = "You are a professional job application consultant who creates motivation letters. Always use the SAME LANGUAGE as the job description provided in the prompt. Adapt your writing style and language to match the job posting language perfectly."
    motivation_letter_json = generate_json_from_prompt(
        prompt=prompt,
        system_prompt=system_prompt,
        default={}
    )
    
    # If we didn't get a valid result
    if not motivation_letter_json:
        logger.error("Failed to generate motivation letter JSON from OpenAI")
        return None
    
    # Add the pre-extracted greeting back into the dictionary
    motivation_letter_json['greeting'] = extracted_salutation
    
    # Ensure contact_person is present, even if null
    if 'contact_person' not in motivation_letter_json:
        motivation_letter_json['contact_person'] = job_details.get('Contact Person')  # Get from original details if LLM missed it
    
    # Add application_url and job_title for queue bridge matching (Story 1.4)
    motivation_letter_json['application_url'] = job_details.get('Application URL', '')
    motivation_letter_json['job_title'] = job_details.get('Job Title', '')
    
    logger.info("Successfully parsed motivation letter JSON and added greeting, application_url, and job_title.")

    # Generate HTML from the JSON
    html_content = json_to_html(motivation_letter_json)

    # --- CHECKPOINT ARCHITECTURE FILE SAVING ---
    # Create checkpoint folder with structured naming
    app_folder = create_application_folder(job_details, base_dir='applications')
    logger.info(f"📁 Created checkpoint folder: {app_folder}")

    # Define file paths in checkpoint folder
    html_file_path = app_folder / 'bewerbungsschreiben.html'
    json_file_path = app_folder / 'application-data.json'
    scraped_data_path = app_folder / 'job-details.json'

    # Save HTML
    logger.info(f"Saving HTML motivation letter to: {html_file_path}")
    with open(html_file_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    # Save JSON (application data)
    logger.info(f"Saving JSON motivation letter to: {json_file_path}")
    save_json_file(motivation_letter_json, json_file_path, ensure_ascii=False, indent=2)

    # Save job details
    logger.info(f"Saving job details to: {scraped_data_path}")
    save_json_file(job_details, scraped_data_path, ensure_ascii=False, indent=2)

    # Create checkpoint infrastructure files
    create_metadata_file(app_folder, job_details)
    copy_cv_to_folder(app_folder)
    create_status_file(app_folder)

    # Generate DOCX file in checkpoint folder
    from word_template_generator import json_to_docx
    docx_file_path = app_folder / 'bewerbungsschreiben.docx'
    logger.info(f"Generating DOCX file: {docx_file_path}")
    docx_result = json_to_docx(motivation_letter_json, output_path=str(docx_file_path))
    if not docx_result:
        logger.warning("Failed to generate DOCX file")

    # Generate email text and save to checkpoint folder
    logger.info("Generating email text...")
    email_text = generate_email_text_only(cv_summary, job_details)
    if email_text:
        export_email_text(app_folder, email_text)
    else:
        logger.warning("Failed to generate email text")

    logger.info(f"🎯 Checkpoint package ready at: {app_folder}")
    # --- End CHECKPOINT ARCHITECTURE FILE SAVING ---

    # Return dictionary with results and paths
    return {
        'motivation_letter_json': motivation_letter_json,
        'motivation_letter_html': html_content,
        'html_file_path': str(html_file_path),
        'json_file_path': str(json_file_path),
        'scraped_data_path': str(scraped_data_path)
    }


@handle_exceptions(default_return=None)
@log_execution_time()
def generate_email_text_only(cv_summary, job_details):
    """Generate only the short email text using OpenAI API"""
    # Extract contact person if available for personalization
    contact_person = job_details.get('Contact Person', None)
    greeting = f"Sehr geehrte/r Herr/Frau {contact_person.split()[-1]}" if contact_person else "Sehr geehrte Damen und Herren"

    prompt = f"""
    Erstelle einen kurzen, kreativen E-Mail-Text (ca. 50-70 Wörter) basierend auf dem Lebenslauf und der Stellenbeschreibung. Dieser Text dient als Begleittext für eine E-Mail-Bewerbung, in der die Anhänge (Lebenslauf, Motivationsschreiben) gesendet werden.
    
    IMPORTANT INSTRUCTION: Write the email text in THE EXACT SAME LANGUAGE as the job description. If the job description is in English, write in English. If it's in German, write in German. MATCH THE LANGUAGE OF THE JOB POSTING EXACTLY!

    Der Text sollte:
    - Professionell, aber ansprechend und nicht zu generisch sein.
    - Kurz auf die beworbene Stelle ({job_details.get('Job Title', 'diese interessante Position')}) bei {job_details.get('Company Name', 'Ihrem Unternehmen')} eingehen.
    - Die Motivation oder eine Schlüsselqualifikation des Bewerbers andeuten.
    - Auf die angehängten Dokumente (Lebenslauf, Motivationsschreiben) hinweisen.
    - Mit einer passenden Grußformel enden.
    - In der gleichen Sprache wie die Jobbeschreibung verfasst sein.
    - "ß" soll als "ss" geschrieben werden.

    Lebenslauf-Zusammenfassung:
    {cv_summary}

    Stellenbeschreibung (Auszug):
    Titel: {job_details.get('Job Title', 'N/A')}
    Firma: {job_details.get('Company Name', 'N/A')}
    Beschreibung: {job_details.get('Job Description', 'N/A')[:200]}...
    Ansprechpartner: {contact_person if contact_person else 'Nicht angegeben'}

    Gib NUR den E-Mail-Text als JSON-Objekt mit folgender Struktur zurück:
    ```json
    {{
      "email_text": "Der generierte E-Mail-Text hier (ca. 50-70 Wörter)."
    }}
    ```
    Stelle sicher, dass das JSON-Format gültig ist und nur das Feld "email_text" enthält.
    """

    # Get OpenAI defaults with slight adjustment for creativity
    openai_defaults = get_openai_defaults()
    temperature = 0.8  # Slightly higher temperature for creativity
    
    # Use generate_json_from_prompt with a custom system message
    system_prompt = "You are an assistant who creates concise and creative email texts for job applications. Always use the SAME LANGUAGE as the job description provided in the prompt. Adapt your writing style and language to match the job posting language perfectly."
    email_json = generate_json_from_prompt(
        prompt=prompt,
        system_prompt=system_prompt, 
        default={"email_text": ""}
    )
    
    email_text = email_json.get('email_text')
    if email_text:
        logger.info("Successfully generated email text.")
        return email_text
    else:
        logger.error("Generated JSON did not contain 'email_text' field or was empty.")
        return None

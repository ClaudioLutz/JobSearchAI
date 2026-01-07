"""
Letter generation utilities for JobsearchAI.

This module provides functions for generating motivation letters and email texts
using the OpenAI API and converting the generated content to HTML format.
"""

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

# Set up logging using centralized configuration
from utils.logging_config import get_logger
logger = get_logger("letter_generation_utils")


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

    # Updated prompt: Optimized for GPT-5.1's advanced language capabilities
    prompt = """
    Erstelle ein professionelles Bewerbungsschreiben aus den folgenden Informationen. WICHTIG: Verwende die EXAKT GLEICHE SPRACHE wie die Stellenbeschreibung.
    
    CRITICAL: Write the motivation letter in THE EXACT SAME LANGUAGE as the job description. If the job description is in English, write in English. If in German, write in German. MATCH THE LANGUAGE PERFECTLY!
    
    ## Lebenslauf des Bewerbers:
    {}
    
    ## Stellenangebot:
    Titel: {}
    Firma: {}
    Ort: {}
    Beschreibung: {}
    Erforderliche Fähigkeiten: {}
    Verantwortlichkeiten: {}
    Unternehmensinformationen: {}
    Anrede (Salutation): {}
    Ansprechpartner (Contact Person): {}
    
    ## Anforderungen an das Bewerbungsschreiben:
    
    **Sprache & Rechtschreibung:**
    - Verwende perfekte Grammatik und korrekte Rechtschreibung in der Zielsprache
    - Bei deutschen Texten: Verwende korrekte Umlaute (ä, ö, ü) und ß gemäß aktueller deutscher Rechtschreibung
    - Bei Schweizer Unternehmen kannst du "ss" statt "ß" verwenden (aber Umlaute beibehalten)
    
    **Inhalt & Struktur:**
    1. Professionell und überzeugend
    2. Konkrete Verknüpfung der Bewerber-Qualifikationen mit den Stellenanforderungen
    3. Klare Motivation für die Position und das Unternehmen
    4. Umfang: 200-300 Wörter (prägnant und aussagekräftig)
    5. Formaler Bewerbungsstil: Einleitung, Hauptteil, Schluss (OHNE Anrede - diese wird separat hinzugefügt)
    6. Spezifisch auf Stellenanforderungen und Verantwortlichkeiten eingehen
    7. Relevante Stärken des Bewerbers hervorheben
    8. Unternehmenskultur und -werte berücksichtigen (falls verfügbar)
    9. Konkrete Beispiele aus dem Lebenslauf verwenden
    
    **Besondere Hinweise:**
    - Falls die Firma "Universal-Job AG" ist: Behandle sie als Personalvermittler, da der tatsächliche Arbeitgeber unbekannt ist
    - Verwende detaillierte Informationen aus der Stellenbeschreibung für maximale Personalisierung
    - Zeige konkret, wie der Bewerber die geforderten Anforderungen erfüllt
    
    ## JSON-Ausgabeformat:
    
    Gib das Bewerbungsschreiben als valides JSON-Objekt zurück (das 'greeting'-Feld wird separat hinzugefügt):
    
    ```json
    {{
      "candidate_name": "Vollständiger Name des Bewerbers",
      "candidate_address": "Straße und Hausnummer",
      "candidate_city": "PLZ und Ort",
      "candidate_email": "E-Mail-Adresse",
      "candidate_phone": "Telefonnummer",
      "company_name": "Name des Unternehmens",
      "company_department": "Abteilung (falls bekannt, sonst 'Personalabteilung')",
      "company_street_number": "Straße und Hausnummer des Unternehmens (falls bekannt)",
      "company_plz_city": "Postleitzahl und Stadt (falls bekannt)",
      "contact_person": "Name des Ansprechpartners (falls bekannt, sonst null)",
      "date": "Ort, den [aktuelles Datum]",
      "subject": "Bewerbung als [Stellentitel]",
      "introduction": "Einleitungsabsatz",
      "body_paragraphs": [
        "Erster Hauptabsatz",
        "Zweiter Hauptabsatz",
        "Dritter Hauptabsatz (falls nötig)"
      ],
      "closing": "Schlussabsatz",
      "signature": "Grußformel (z.B. 'Mit freundlichen Grüßen')",
      "full_name": "Vollständiger Name des Bewerbers"
    }}
    ```
    
    Stelle sicher, dass alle Felder korrekt ausgefüllt sind und das JSON-Format valide ist.
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
    
    # Use generate_json_from_prompt with enhanced system prompt for GPT-5.1
    system_prompt = """You are an expert job application consultant with native-level proficiency in German and English. 
    
    Your specialties:
    - Creating compelling, professional motivation letters
    - Perfect grammar and orthography in both German and English
    - Matching the exact language and tone of job descriptions
    - Using correct German special characters (ä, ö, ü, ß) when writing in German
    - Adapting writing style to match company culture and job requirements
    
    Always match the language of the job description exactly and use proper orthography."""
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

    # --- CV TEMPLATE GENERATION (Story 6.2) ---
    # Generate customized CV template DOCX
    from cv_template_generator import generate_cv_docx, get_cv_summary_path
    
    cv_docx_path = app_folder / 'Lebenslauf.docx'
    cv_template_path = 'process_cv/cv-data/template/Lebenslauf_template.docx'
    
    # Get CV summary path
    cv_summary_path = get_cv_summary_path()
    
    if cv_summary_path and cv_summary_path.exists():
        try:
            # Read CV summary
            with open(cv_summary_path, 'r', encoding='utf-8') as f:
                cv_summary_text = f.read()
            
            # Prepare job details dict for CV generation
            cv_job_details = {
                'company_name': job_details.get('Company Name', ''),
                'job_title': job_details.get('Job Title', ''),
                'job_description': job_details.get('Job Description', ''),
                'language': job_details.get('Language', 'de')
            }
            
            # Generate CV DOCX (non-blocking)
            logger.info("Generating CV template...")
            cv_result = generate_cv_docx(
                cv_summary=cv_summary_text,
                job_details=cv_job_details,
                template_path=cv_template_path,
                output_path=str(cv_docx_path)
            )
            
            if cv_result:
                logger.info(f"✓ CV template generated successfully: {cv_docx_path}")
            else:
                logger.warning(f"Failed to generate CV template at {cv_docx_path}")
                # Continue execution - non-blocking
                
        except Exception as e:
            logger.error(f"Error during CV template generation: {e}")
            # Continue execution - non-blocking
    else:
        logger.warning("CV summary not found, skipping CV template generation")
        # Continue execution
    # --- End CV TEMPLATE GENERATION ---

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
    Erstelle einen kurzen, professionellen E-Mail-Begleittext (50-70 Wörter) für eine Bewerbung per E-Mail.
    
    CRITICAL: Write the email text in THE EXACT SAME LANGUAGE as the job description. If the job description is in English, write in English. If in German, write in German. MATCH THE LANGUAGE PERFECTLY!

    ## Anforderungen an den E-Mail-Text:
    
    **Sprache & Stil:**
    - Verwende perfekte Grammatik und korrekte Rechtschreibung in der Zielsprache
    - Bei deutschen Texten: Verwende korrekte Umlaute (ä, ö, ü) und ß gemäß deutscher Rechtschreibung
    - Bei Schweizer Unternehmen kannst du "ss" statt "ß" verwenden (aber Umlaute beibehalten)
    - Professionell, aber ansprechend und nicht generisch
    
    **Inhalt:**
    - Bezug zur Position: {job_details.get('Job Title', 'diese interessante Position')} bei {job_details.get('Company Name', 'Ihrem Unternehmen')}
    - Kurze Andeutung einer Schlüsselqualifikation oder Motivation
    - Hinweis auf die angehängten Dokumente (Lebenslauf, Motivationsschreiben)
    - Passende Grußformel
    - Exakt in der Sprache der Jobbeschreibung verfasst

    ## Kontext:
    
    Lebenslauf-Zusammenfassung:
    {cv_summary}

    Stellenbeschreibung:
    - Titel: {job_details.get('Job Title', 'N/A')}
    - Firma: {job_details.get('Company Name', 'N/A')}
    - Beschreibung: {job_details.get('Job Description', 'N/A')[:200]}...
    - Ansprechpartner: {contact_person if contact_person else 'Nicht angegeben'}

    ## JSON-Ausgabe:
    
    Gib NUR den E-Mail-Text als JSON-Objekt zurück:
    ```json
    {{
      "email_text": "Der generierte E-Mail-Text hier (50-70 Wörter)"
    }}
    ```
    Stelle sicher, dass das JSON valide ist und nur das Feld "email_text" enthält.
    """

    # Get OpenAI defaults with slight adjustment for creativity
    openai_defaults = get_openai_defaults()
    temperature = 0.8  # Slightly higher temperature for creativity
    
    # Use generate_json_from_prompt with enhanced system prompt for GPT-5.1
    system_prompt = """You are an expert at crafting professional email texts for job applications with native-level proficiency in German and English.
    
    Your specialties:
    - Creating concise, engaging email texts
    - Perfect grammar and orthography in both German and English
    - Matching the exact language and tone of job descriptions
    - Using correct German special characters (ä, ö, ü, ß) when writing in German
    
    Always match the language of the job description exactly and use proper orthography."""
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

"""
Job Text Extractor - Extract structured job details from pasted text using Instructor.

This module provides LLM-based extraction of job posting details from raw text,
using Pydantic models for validation and Instructor for structured output.
"""

from typing import Optional, Dict, Any

import instructor
from pydantic import BaseModel, Field, field_validator, model_validator
from openai import OpenAI

from config import get_openai_api_key, get_openai_defaults

# Set up logging using centralized configuration
from utils.logging_config import get_logger
logger = get_logger("job_text_extractor")

# German extraction prompt matching existing style
EXTRACTION_SYSTEM_PROMPT = """Du bist ein Experte für die Extraktion strukturierter Daten aus Stellenanzeigen.
Extrahiere alle relevanten Felder aus dem bereitgestellten Text.
Antworte IN DER GLEICHEN SPRACHE wie die Stellenanzeige.
Wenn eine Kontaktperson gefunden wird, erstelle die passende Anrede (Herr/Frau + Nachname)."""


class JobPosting(BaseModel):
    """Structured job posting data extracted from raw text."""

    job_title: str = Field(
        ...,
        min_length=2,
        description="Der Stellentitel/Positionsname"
    )

    company_name: str = Field(
        ...,
        min_length=2,
        description="Der Name des einstellenden Unternehmens"
    )

    job_description: str = Field(
        ...,
        min_length=20,
        description="Umfassende Stellenbeschreibung mit Zusammenfassung der Rolle"
    )

    required_skills: str = Field(
        default="",
        description="Liste der erforderlichen Fähigkeiten und Qualifikationen"
    )

    responsibilities: str = Field(
        default="",
        description="Liste der wichtigsten Verantwortlichkeiten und Aufgaben"
    )

    company_info: Optional[str] = Field(
        default=None,
        description="Informationen über Unternehmenskultur, Benefits usw."
    )

    location: Optional[str] = Field(
        default=None,
        description="Arbeitsort/Standort"
    )

    salary_range: Optional[str] = Field(
        default=None,
        description="Gehaltsspanne falls erwähnt"
    )

    posting_date: Optional[str] = Field(
        default=None,
        description="Veröffentlichungsdatum falls erwähnt"
    )

    contact_person: Optional[str] = Field(
        default=None,
        description="Name der Kontaktperson"
    )

    contact_email: Optional[str] = Field(
        default=None,
        description="E-Mail-Adresse für Bewerbungen"
    )

    salutation: str = Field(
        default="Sehr geehrte Damen und Herren",
        description="Passende Anrede basierend auf Kontaktperson"
    )

    application_url: Optional[str] = Field(
        default=None,
        description="Ursprüngliche URL der Stellenanzeige"
    )

    @field_validator('job_title', 'company_name', mode='before')
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip whitespace from string fields."""
        if isinstance(v, str):
            return v.strip()
        return v

    @model_validator(mode='after')
    def generate_salutation_from_contact(self) -> 'JobPosting':
        """Generate appropriate salutation based on contact person after all fields are set."""
        # If salutation is already set properly (e.g., by LLM), keep it
        if self.salutation and self.salutation != "Sehr geehrte Damen und Herren":
            return self

        # If no contact person, use default salutation
        if not self.contact_person:
            return self

        contact = self.contact_person.strip()
        if not contact:
            return self

        # Common German female titles/names indicators
        female_indicators = ['Frau', 'frau', 'Fr.', 'fr.']
        male_indicators = ['Herr', 'herr', 'Hr.', 'hr.']

        # Check if title already indicates gender
        for indicator in female_indicators:
            if indicator in contact:
                # Extract last name
                parts = contact.replace(indicator, '').strip().split()
                last_name = parts[-1] if parts else contact
                object.__setattr__(self, 'salutation', f"Sehr geehrte Frau {last_name}")
                return self

        for indicator in male_indicators:
            if indicator in contact:
                parts = contact.replace(indicator, '').strip().split()
                last_name = parts[-1] if parts else contact
                object.__setattr__(self, 'salutation', f"Sehr geehrter Herr {last_name}")
                return self

        # Default: keep neutral salutation
        return self


def extract_job_from_text(
    raw_text: str,
    source_url: Optional[str] = None,
    model: Optional[str] = None
) -> Optional[JobPosting]:
    """
    Extract structured job details from raw pasted text using Instructor.

    Args:
        raw_text: The copied/pasted job posting text
        source_url: Optional URL where the job was found
        model: Optional model override (defaults to config)

    Returns:
        JobPosting: Validated, structured job data, or None if extraction fails
    """
    if not raw_text or len(raw_text.strip()) < 50:
        logger.warning("Text too short for extraction (minimum 50 characters)")
        return None

    # Get API key and model from config
    api_key = get_openai_api_key()
    if not api_key:
        logger.error("OpenAI API key not configured")
        return None

    defaults = get_openai_defaults()
    model = model or defaults.get("model", "gpt-4.1")

    logger.info(f"Extracting job details from text ({len(raw_text)} chars) using model: {model}")

    try:
        # Create Instructor client
        client = instructor.from_openai(OpenAI(api_key=api_key))

        # Extract structured data
        job = client.chat.completions.create(
            model=model,
            response_model=JobPosting,
            max_retries=2,
            messages=[
                {
                    "role": "system",
                    "content": EXTRACTION_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": f"Extrahiere die Stellendetails aus diesem Text:\n\n{raw_text}"
                }
            ]
        )

        # Add source URL if provided
        if source_url:
            job.application_url = source_url

        logger.info(f"Successfully extracted job: {job.job_title} at {job.company_name}")
        return job

    except Exception as e:
        logger.error(f"Failed to extract job details: {e}", exc_info=True)
        return None


def job_posting_to_dict(job: JobPosting) -> Dict[str, Any]:
    """
    Convert JobPosting model to dict format matching job_details_utils.py output.

    Args:
        job: JobPosting Pydantic model

    Returns:
        dict: Job details in standard format for compatibility
    """
    return {
        'Job Title': job.job_title,
        'Company Name': job.company_name,
        'Job Description': job.job_description,
        'Required Skills': job.required_skills or '',
        'Responsibilities': job.responsibilities or '',
        'Company Information': job.company_info or '',
        'Location': job.location or '',
        'Salary Range': job.salary_range or '',
        'Posting Date': job.posting_date or '',
        'Contact Person': job.contact_person or '',
        'Application Email': job.contact_email or '',
        'Salutation': job.salutation,
        'Application URL': job.application_url or ''
    }


def get_job_details_from_text(
    pasted_text: str,
    source_url: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Extract job details from pasted text and return as dict.

    This is the main entry point for the extraction, returning
    results in the same format as job_details_utils.py functions.

    Args:
        pasted_text: Raw text copied from job posting website
        source_url: Original URL of the job posting

    Returns:
        dict: Job details in standard format, or None if extraction fails
    """
    job = extract_job_from_text(pasted_text, source_url)

    if job is None:
        return None

    return job_posting_to_dict(job)


# For testing purposes
if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Test with sample text
    sample_text = """
    Software Engineer (m/w/d) - Backend Development

    Firma: TechCorp GmbH
    Standort: Zürich, Schweiz

    Über uns:
    TechCorp ist ein führendes Technologieunternehmen mit Fokus auf innovative Softwarelösungen.

    Ihre Aufgaben:
    - Entwicklung von Backend-Services mit Python und FastAPI
    - Datenbankdesign und -optimierung
    - API-Entwicklung und Integration
    - Code Reviews und technische Dokumentation

    Ihr Profil:
    - Abgeschlossenes Studium in Informatik oder vergleichbar
    - 3+ Jahre Erfahrung in Python-Entwicklung
    - Kenntnisse in SQL und NoSQL Datenbanken
    - Erfahrung mit Docker und Kubernetes

    Kontakt: Frau Müller
    E-Mail: jobs@techcorp.ch
    """

    result = get_job_details_from_text(sample_text, "https://example.com/job/123")
    if result:
        print("\n--- Extracted Job Details ---")
        for key, value in result.items():
            print(f"{key}: {value}")
    else:
        print("Extraction failed")

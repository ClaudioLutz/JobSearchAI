"""
CV Template Generator for JobsearchAI.

This module provides functions to generate customized CV (Lebenslauf) content using AI
and render it into Word document templates for job applications.

The module integrates with the existing motivation letter generation workflow,
following established patterns from word_template_generator.py and letter_generation_utils.py.
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, List, Any
from utils.warning_utils import SuppressWarnings

# Import docxtpl with suppressed pkg_resources warnings
with SuppressWarnings(['pkg_resources']):
    from docxtpl import DocxTemplate

# Import from centralized configuration and utilities
from config import get_openai_defaults
from utils.api_utils import generate_json_from_prompt

# Set up logger for this module
logger = logging.getLogger(__name__)

# Module constants
DEFAULT_TEMPLATE_PATH = 'process_cv/cv-data/template/Lebenslauf_template.docx'
DEFAULT_CV_SUMMARY_DIR = 'process_cv/cv-data/processed'
WORD_COUNT_MIN = 45
WORD_COUNT_MAX = 55
COMPETENCIES_COUNT = 9
MAX_RETRIES = 1


def get_cv_summary_path() -> Optional[Path]:
    """
    Find the most recent CV summary file in the processed directory.
    
    Returns:
        Path object to the most recent CV summary file, or None if not found
        
    Example:
        >>> cv_path = get_cv_summary_path()
        >>> if cv_path:
        ...     with open(cv_path, 'r', encoding='utf-8') as f:
        ...         cv_summary = f.read()
    """
    try:
        summary_dir = Path(DEFAULT_CV_SUMMARY_DIR)
        
        if not summary_dir.exists():
            logger.warning(f"CV summary directory does not exist: {summary_dir}")
            return None
        
        # Find all summary files
        summary_files = list(summary_dir.glob('*_summary.txt'))
        
        if not summary_files:
            logger.warning(f"No CV summary files found in {summary_dir}")
            return None
        
        # Get the most recently modified file
        most_recent = max(summary_files, key=lambda p: p.stat().st_mtime)
        logger.info(f"Found CV summary file: {most_recent}")
        return most_recent
        
    except Exception as e:
        logger.error(f"Error finding CV summary file: {e}")
        return None


def generate_cv_content(
    cv_summary: str,
    job_details: Dict[str, Any],
    retry_count: int = 0
) -> Optional[Dict[str, Any]]:
    """
    Generate job-specific CV content using OpenAI API.
    
    Args:
        cv_summary: Full text of the candidate's CV summary
        job_details: Dictionary containing job information (company_name, job_title, 
                     job_description, language)
        retry_count: Current retry attempt (used for recursion)
        
    Returns:
        Dictionary with keys: cv_motivation, cv_kurzprofil, fachkompetenzen
        or None if generation fails after retries
        
    Example:
        >>> content = generate_cv_content(cv_summary, {
        ...     'company_name': 'TechCorp',
        ...     'job_title': 'Senior Developer',
        ...     'job_description': 'We are looking for...',
        ...     'language': 'de'
        ... })
    """
    try:
        # Extract job details with fallbacks
        company_name = job_details.get('company_name', 'das Unternehmen')
        job_title = job_details.get('job_title', 'diese Position')
        job_description = job_details.get('job_description', 'N/A')
        language = job_details.get('language', 'de')
        
        # Determine language-specific instructions
        if language.lower() == 'en':
            lang_instruction = "Write all content in English."
            greeting_example = "Dear Hiring Manager"
        else:
            lang_instruction = "Schreibe alle Inhalte auf Deutsch. Verwende 'ss' statt 'ß'."
            greeting_example = "Sehr geehrte Damen und Herren"
        
        # Construct system prompt
        system_prompt = f"""You are an expert CV writer specialized in creating job-specific CV content.
Generate professional, targeted CV sections that highlight the candidate's relevant skills and experience 
for the specific position. {lang_instruction}"""
        
        # Construct user prompt
        user_prompt = f"""
Based on the candidate's CV summary and the job details below, generate three specific sections 
for a customized CV template:

## Candidate CV Summary:
{cv_summary}

## Target Job Details:
Company: {company_name}
Position: {job_title}
Job Description: {job_description}

## Required Output Sections:

1. **cv_motivation** (45-55 words): A compelling motivation statement explaining why the candidate 
   is interested in this specific role at this company. Should be personal, enthusiastic, and 
   show knowledge of the company/role.

2. **cv_kurzprofil** (45-55 words): A brief professional profile highlighting the candidate's 
   most relevant qualifications, experience, and strengths for THIS specific position. 
   Focus on what makes them a strong match.

3. **fachkompetenzen** (exactly 9 items): A list of the candidate's most relevant technical 
   and professional competencies for this role. Each item should be 2-5 words. 
   Examples: "Python, FastAPI, Django", "Cloud Architecture (AWS)", "Agile Team Leadership"

## Important Requirements:
- {lang_instruction}
- Word counts MUST be strictly within 45-55 words for cv_motivation and cv_kurzprofil
- fachkompetenzen MUST contain exactly 9 items
- Content must be specific to THIS job, not generic
- Use "ss" instead of "ß" in German text
- Maintain professional tone

Return the result as a JSON object with this exact structure:
{{
  "cv_motivation": "Your 45-55 word motivation text here",
  "cv_kurzprofil": "Your 45-55 word profile text here",
  "fachkompetenzen": [
    "Competency 1",
    "Competency 2",
    "Competency 3",
    "Competency 4",
    "Competency 5",
    "Competency 6",
    "Competency 7",
    "Competency 8",
    "Competency 9"
  ]
}}
"""
        
        # Generate content using OpenAI API
        logger.info(f"Generating CV content for {job_title} at {company_name} (language: {language})")
        content = generate_json_from_prompt(
            prompt=user_prompt,
            system_prompt=system_prompt,
            default=None
        )
        
        if not content:
            logger.error("Failed to generate CV content from OpenAI API")
            return None
        
        # Apply ß → ss replacement for German text
        if language.lower() == 'de':
            for key in ['cv_motivation', 'cv_kurzprofil']:
                if key in content and isinstance(content[key], str):
                    content[key] = content[key].replace('ß', 'ss')
            
            # Also replace in competencies list
            if 'fachkompetenzen' in content and isinstance(content['fachkompetenzen'], list):
                content['fachkompetenzen'] = [
                    item.replace('ß', 'ss') if isinstance(item, str) else item
                    for item in content['fachkompetenzen']
                ]
        
        # Validate the generated content
        is_valid, error_msg = validate_cv_content(content)
        
        if not is_valid:
            logger.warning(f"Generated CV content failed validation: {error_msg}")
            
            # Retry once if this is the first attempt
            if retry_count < MAX_RETRIES:
                logger.info(f"Retrying content generation (attempt {retry_count + 1}/{MAX_RETRIES + 1})")
                return generate_cv_content(cv_summary, job_details, retry_count + 1)
            else:
                logger.error("Max retries reached, content validation still failing")
                return None
        
        logger.info("Successfully generated and validated CV content")
        return content
        
    except Exception as e:
        logger.error(f"Error generating CV content: {e}", exc_info=True)
        return None


def validate_cv_content(content: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate that generated CV content meets all requirements.
    
    Args:
        content: Dictionary with cv_motivation, cv_kurzprofil, fachkompetenzen
        
    Returns:
        Tuple of (is_valid: bool, error_message: str)
        If valid, error_message is empty string
        
    Example:
        >>> is_valid, error = validate_cv_content(content)
        >>> if not is_valid:
        ...     print(f"Validation failed: {error}")
    """
    try:
        # Check for required fields
        required_fields = ['cv_motivation', 'cv_kurzprofil', 'fachkompetenzen']
        for field in required_fields:
            if field not in content:
                return False, f"Missing required field: {field}"
        
        # Validate cv_motivation word count
        cv_motivation = content.get('cv_motivation', '')
        if not isinstance(cv_motivation, str):
            return False, "cv_motivation must be a string"
        
        motivation_word_count = len(cv_motivation.split())
        if not (WORD_COUNT_MIN <= motivation_word_count <= WORD_COUNT_MAX):
            return False, f"cv_motivation word count {motivation_word_count} not in range {WORD_COUNT_MIN}-{WORD_COUNT_MAX}"
        
        # Validate cv_kurzprofil word count
        cv_kurzprofil = content.get('cv_kurzprofil', '')
        if not isinstance(cv_kurzprofil, str):
            return False, "cv_kurzprofil must be a string"
        
        kurzprofil_word_count = len(cv_kurzprofil.split())
        if not (WORD_COUNT_MIN <= kurzprofil_word_count <= WORD_COUNT_MAX):
            return False, f"cv_kurzprofil word count {kurzprofil_word_count} not in range {WORD_COUNT_MIN}-{WORD_COUNT_MAX}"
        
        # Validate fachkompetenzen count
        fachkompetenzen = content.get('fachkompetenzen', [])
        if not isinstance(fachkompetenzen, list):
            return False, "fachkompetenzen must be a list"
        
        if len(fachkompetenzen) != COMPETENCIES_COUNT:
            return False, f"fachkompetenzen count {len(fachkompetenzen)} != {COMPETENCIES_COUNT}"
        
        # Check that all competencies are non-empty strings
        for i, item in enumerate(fachkompetenzen):
            if not isinstance(item, str) or not item.strip():
                return False, f"fachkompetenzen item {i} is not a valid non-empty string"
        
        logger.info("CV content validation passed")
        return True, ""
        
    except Exception as e:
        logger.error(f"Error during CV content validation: {e}", exc_info=True)
        return False, f"Validation error: {str(e)}"


def render_cv_template(
    content: Dict[str, Any],
    template_path: str,
    output_path: str
) -> bool:
    """
    Render CV template with generated content and save to output path.
    
    Args:
        content: Dictionary with cv_motivation, cv_kurzprofil, fachkompetenzen
        template_path: Path to the .docx template file
        output_path: Path where the rendered document should be saved
        
    Returns:
        True if rendering and saving succeeded, False otherwise
        
    Example:
        >>> success = render_cv_template(
        ...     content=generated_content,
        ...     template_path='process_cv/cv-data/template/Lebenslauf_template.docx',
        ...     output_path='applications/company_job/Lebenslauf.docx'
        ... )
    """
    try:
        template_path_obj = Path(template_path)
        
        # Check if template exists
        if not template_path_obj.exists():
            logger.error(f"Template file not found: {template_path}")
            return False
        
        # Load the template
        logger.info(f"Loading template from: {template_path}")
        doc = DocxTemplate(template_path)
        
        # Prepare context for rendering
        context = {
            'cv_motivation': content.get('cv_motivation', ''),
            'cv_kurzprofil': content.get('cv_kurzprofil', ''),
            'fachkompetenzen': content.get('fachkompetenzen', [])
        }
        
        # Render the template
        logger.info("Rendering template with generated content")
        doc.render(context)
        
        # Ensure output directory exists
        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        # Save the rendered document
        logger.info(f"Saving rendered document to: {output_path}")
        doc.save(str(output_path))
        
        logger.info("Successfully rendered and saved CV template")
        return True
        
    except Exception as e:
        logger.error(f"Error rendering CV template: {e}", exc_info=True)
        return False


def generate_cv_docx(
    cv_summary: str,
    job_details: Dict[str, Any],
    template_path: str = DEFAULT_TEMPLATE_PATH,
    output_path: Optional[str] = None
) -> bool:
    """
    Main function to orchestrate complete CV generation workflow.
    
    This function:
    1. Generates CV content using OpenAI API
    2. Validates the generated content
    3. Renders the content into a Word template
    4. Saves the final document
    
    Args:
        cv_summary: Full text of the candidate's CV summary
        job_details: Dictionary with company_name, job_title, job_description, language
        template_path: Path to the CV template file (defaults to DEFAULT_TEMPLATE_PATH)
        output_path: Path where the rendered CV should be saved (required)
        
    Returns:
        True if complete workflow succeeded, False otherwise
        
    Example:
        >>> success = generate_cv_docx(
        ...     cv_summary=cv_text,
        ...     job_details={'company_name': 'TechCorp', 'job_title': 'Developer', ...},
        ...     output_path='applications/techcorp_developer/Lebenslauf.docx'
        ... )
    """
    try:
        if not output_path:
            logger.error("output_path is required for generate_cv_docx")
            return False
        
        logger.info("Starting CV generation workflow")
        
        # Step 1: Generate content
        content = generate_cv_content(cv_summary, job_details)
        if not content:
            logger.error("Failed to generate CV content")
            return False
        
        # Step 2: Content is already validated in generate_cv_content
        logger.info("CV content validated successfully")
        
        # Step 3: Render template
        success = render_cv_template(
            content=content,
            template_path=template_path,
            output_path=output_path
        )
        
        if not success:
            logger.error("Failed to render CV template")
            return False
        
        logger.info(f"CV generation workflow completed successfully: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error in CV generation workflow: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    """
    Simple test/example usage of the module.
    This section can be used for manual testing during development.
    """
    # Example test data
    test_job_details = {
        'company_name': 'TechCorp AG',
        'job_title': 'Senior Python Developer',
        'job_description': 'We are looking for an experienced Python developer with strong backend skills...',
        'language': 'de'
    }
    
    print("CV Template Generator Module")
    print("=" * 50)
    
    # Test 1: Find CV summary
    print("\n1. Finding CV summary file...")
    cv_path = get_cv_summary_path()
    if cv_path:
        print(f"   ✓ Found: {cv_path}")
        with open(cv_path, 'r', encoding='utf-8') as f:
            cv_summary = f.read()
        print(f"   ✓ Loaded CV summary ({len(cv_summary)} characters)")
    else:
        print("   ✗ No CV summary found")
        cv_summary = "Test CV summary text..."
    
    # Test 2: Validate template exists
    print("\n2. Checking template file...")
    template_path = Path(DEFAULT_TEMPLATE_PATH)
    if template_path.exists():
        print(f"   ✓ Template exists: {template_path}")
    else:
        print(f"   ✗ Template not found: {template_path}")
    
    print("\nModule loaded successfully!")
    print("Use generate_cv_docx() to generate CV documents.")

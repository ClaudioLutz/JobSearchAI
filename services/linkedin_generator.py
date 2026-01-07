"""
LinkedIn message generation service.

This module provides functions for generating LinkedIn connection requests and messages
using the OpenAI API.
"""

from typing import Dict, Optional, Any
from utils.api_utils import generate_json_from_prompt

# Set up logging using centralized configuration
from utils.logging_config import get_logger
logger = get_logger("linkedin_generator")

# Character limit constants
CONNECTION_REQUEST_MAX_CHARS = 300
PEER_NETWORKING_MAX_CHARS = 500
INMAIL_MAX_WORDS = 150
JOB_DESCRIPTION_SNIPPET_LENGTH = 500

def _normalize_sharp_s(text: str) -> str:
    """
    Replace German sharp s characters with their 'ss'/'SS' equivalents.
    Applied before length validations to ensure character limits are checked after normalization.
    """
    return text.replace("ß", "ss").replace("ẞ", "SS")

def generate_linkedin_messages(cv_summary: str, job_details: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """
    Generate LinkedIn messages (Connection Request, Peer Networking, InMail)
    based on CV summary and job details.
    
    This function uses the OpenAI API to generate three types of personalized LinkedIn
    messages tailored to the candidate's background and the target job. Messages are
    automatically generated in the same language as the job description.
    
    Args:
        cv_summary (str): Summary of the candidate's CV/resume
        job_details (Dict[str, Any]): Dictionary containing job information with keys:
            - 'Company Name' (str): Name of the company
            - 'Job Title' (str): Title of the position
            - 'Contact Person' (str, optional): Name of hiring manager/recruiter
            - 'Job Description' (str): Full job description text
    
    Returns:
        Optional[Dict[str, str]]: Dictionary with three message types, or None if generation fails:
            - 'connection_request_hiring_manager': Message for hiring manager (< 300 chars)
            - 'peer_networking': Message for potential colleagues (< 500 chars)
            - 'inmail_message': Longer pitch message (< 150 words)
    
    Example:
        >>> cv_summary = "Experienced Python Developer with 5 years in AI/ML..."
        >>> job_details = {
        ...     'Company Name': 'Tech Corp',
        ...     'Job Title': 'Senior Python Engineer',
        ...     'Contact Person': 'Jane Smith',
        ...     'Job Description': 'We are looking for a Python expert...'
        ... }
        >>> messages = generate_linkedin_messages(cv_summary, job_details)
        >>> if messages:
        ...     print(messages['connection_request_hiring_manager'])
    """
    
    if not cv_summary:
        logger.error("CV summary is required but was not provided")
        return None
    
    company_name = job_details.get('Company Name', 'the company')
    job_title = job_details.get('Job Title', 'the position')
    contact_person = job_details.get('Contact Person')
    job_description = job_details.get('Job Description', '')
    
    logger.info(f"Generating LinkedIn messages for {job_title} at {company_name}")
    
    # Limit job description to avoid token overflow
    job_description_snippet = job_description[:JOB_DESCRIPTION_SNIPPET_LENGTH]
    if len(job_description) > JOB_DESCRIPTION_SNIPPET_LENGTH:
        job_description_snippet += "..."
    
    # Determine language from job description (heuristic or passed explicitly)
    # The prompt will instruct the AI to detect and match language.
    
    prompt = f"""
    Generate 3 variations of LinkedIn messages based on the candidate's CV summary and the job details.
    
    IMPORTANT INSTRUCTION: Write the messages in THE EXACT SAME LANGUAGE as the job description. If the job description is in English, write in English. If it's in German, write in German. MATCH THE LANGUAGE OF THE JOB POSTING EXACTLY!

    ## Job Details:
    Company: {company_name}
    Job Title: {job_title}
    Contact Person: {contact_person if contact_person else "Not specified (Use generic placeholder if needed)"}
    Description: {job_description_snippet}
    
    ## Candidate CV Summary:
    {cv_summary}
    
    ## Required Output (JSON):
    Generate a JSON object with the following keys:
    1. "connection_request_hiring_manager": A connection request message for the hiring manager or recruiter. STRICTLY UNDER {CONNECTION_REQUEST_MAX_CHARS} CHARACTERS. Professional but engaging.
    2. "peer_networking": A message to a potential peer (future colleague) to ask about company culture. Casual but professional. Under {CONNECTION_REQUEST_MAX_CHARS} characters preferred but can be slightly longer if needed (max {PEER_NETWORKING_MAX_CHARS}).
    3. "inmail_message": A longer InMail message (direct message) pitching the candidate. Similar to a very short cover letter. Max {INMAIL_MAX_WORDS} words.

    ## Constraints:
    - "connection_request_hiring_manager" MUST be < {CONNECTION_REQUEST_MAX_CHARS} characters.
    - Use placeholders like [Name] if no specific contact person is provided.
    - Highlight specific skills from the CV that match the job.
    - "ß" should be written as "ss".
    
    Output JSON format:
    {{
        "connection_request_hiring_manager": "...",
        "peer_networking": "...",
        "inmail_message": "..."
    }}
    """
    
    system_prompt = "You are an expert networking coach helping a candidate craft high-impact LinkedIn messages. You strictly enforce character limits and match the language of the job description."
    
    try:
        messages_json = generate_json_from_prompt(
            prompt=prompt,
            system_prompt=system_prompt,
            default={}
        )
        
        if not messages_json:
            logger.error(f"Failed to generate LinkedIn messages JSON for {job_title} at {company_name}")
            return None
        
        # Validate that all required keys are present
        required_keys = ['connection_request_hiring_manager', 'peer_networking', 'inmail_message']
        missing_keys = [key for key in required_keys if key not in messages_json]
        if missing_keys:
            logger.error(f"Generated JSON missing required keys: {missing_keys}")
            return None
            
        # Normalize German sharp s -> 'ss'/'SS' as required
        for key in required_keys:
            val = messages_json.get(key, '')
            if isinstance(val, str) and ('ß' in val or 'ẞ' in val):
                messages_json[key] = _normalize_sharp_s(val)

        # Post-processing to ensure character limits
        # Connection request validation (CRITICAL - must be < 300 chars)
        connection_request = messages_json.get('connection_request_hiring_manager', '')
        if len(connection_request) > CONNECTION_REQUEST_MAX_CHARS:
            logger.warning(
                f"Generated connection request exceeded {CONNECTION_REQUEST_MAX_CHARS} chars "
                f"({len(connection_request)} chars). Truncating."
            )
            messages_json['connection_request_hiring_manager'] = connection_request[:297] + "..."
        
        # Peer networking validation
        peer_message = messages_json.get('peer_networking', '')
        if len(peer_message) > PEER_NETWORKING_MAX_CHARS:
            logger.warning(
                f"Generated peer networking message exceeded {PEER_NETWORKING_MAX_CHARS} chars "
                f"({len(peer_message)} chars). Truncating."
            )
            messages_json['peer_networking'] = peer_message[:497] + "..."
        
        # InMail validation (word count)
        inmail_message = messages_json.get('inmail_message', '')
        word_count = len(inmail_message.split())
        if word_count > INMAIL_MAX_WORDS:
            logger.warning(
                f"Generated InMail message exceeded {INMAIL_MAX_WORDS} words "
                f"({word_count} words). Truncating."
            )
            words = inmail_message.split()
            messages_json['inmail_message'] = ' '.join(words[:INMAIL_MAX_WORDS]) + "..."
        
        logger.info(
            f"Successfully generated LinkedIn messages for {job_title} at {company_name}. "
            f"Lengths: connection={len(messages_json['connection_request_hiring_manager'])}, "
            f"peer={len(messages_json['peer_networking'])}, "
            f"inmail={len(messages_json['inmail_message'].split())} words"
        )
            
        return messages_json
        
    except Exception as e:
        logger.error(
            f"Error generating LinkedIn messages for {job_title} at {company_name}: {e}",
            exc_info=True
        )
        return None

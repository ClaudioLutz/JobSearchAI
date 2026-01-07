#%%

from pathlib import Path
import fitz
import openai
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Set up logging using centralized configuration
from utils.logging_config import get_logger
logger = get_logger("cv_processor")

def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file."""
    logger.info(f"=== PDF TEXT EXTRACTION START ===")
    logger.info(f"PDF path: {pdf_path}")
    logger.info(f"File exists: {os.path.exists(pdf_path)}")
    
    if os.path.exists(pdf_path):
        logger.info(f"File size: {os.path.getsize(pdf_path)} bytes")
    
    text = ""
    try:
        with fitz.open(pdf_path) as pdf:
            logger.info(f"PDF opened successfully - {len(pdf)} pages")
            for page_num, page in enumerate(pdf):
                page_text = page.get_text()
                text += page_text
                logger.info(f"Page {page_num + 1}: {len(page_text)} characters")
        
        logger.info(f"Total extracted: {len(text)} characters")
        logger.info(f"Text preview: {text[:200]}...")
        logger.info("=== PDF TEXT EXTRACTION COMPLETE ===")
    except Exception as e:
        logger.error(f"Error extracting text from {pdf_path}: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        text = ""
    
    return text

# General extraction function
def extract_cv_text(file_path):
    """Extract text from a CV file (currently PDF only)."""
    if file_path.lower().endswith(".pdf"):
        return extract_text_from_pdf(file_path)
    logger.error(f"Unsupported file type: {file_path}")
    raise ValueError("Unsupported file type. Only PDF allowed.")

# Load environment variables from the .env file located next to this script
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path, override=False)  # Don't override system env vars

# Initialize the OpenAI client with detailed logging
api_key = os.getenv("OPENAI_API_KEY")
logger.info("=== CV PROCESSOR INITIALIZATION ===")
logger.info(f"Environment check - OPENAI_API_KEY present: {bool(api_key)}")
if api_key:
    logger.info(f"API key starts with: {api_key[:15]}...")
    logger.info(f"API key length: {len(api_key)}")
else:
    logger.error("CRITICAL: OPENAI_API_KEY not found in environment variables")
    # Show available environment variables for debugging
    env_vars = [k for k in os.environ.keys() if 'API' in k or 'KEY' in k]
    logger.error(f"Available env vars with API/KEY: {env_vars}")

try:
    if api_key:
        client = openai.OpenAI(api_key=api_key)
        logger.info("OpenAI client initialized successfully")
        # Test the client connection
        try:
            models = client.models.list()
            logger.info(f"API connection test successful - found {len(models.data)} models")
        except Exception as api_test_e:
            logger.error(f"API connection test failed: {api_test_e}")
    else:
        client = None
        logger.error("Cannot initialize OpenAI client - no API key")
except Exception as e:
    logger.error(f"Failed to initialize OpenAI client: {e}")
    client = None

logger.info("=== INITIALIZATION COMPLETE ===")

def summarize_cv(cv_text):
    """Summarize CV text using the OpenAI API."""
    logger.info("=== CV SUMMARIZATION START ===")
    logger.info(f"Client initialized: {bool(client)}")
    logger.info(f"CV text length: {len(cv_text) if cv_text else 0}")
    
    if not client:
        logger.error("OpenAI client not initialized. Cannot generate CV summary.")
        return "Error: OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
    
    if not cv_text or cv_text.strip() == "":
        logger.warning("Empty CV text provided for summarization.")
        return "Error: No text extracted from CV file."
    
    logger.info(f"CV text preview: {cv_text[:300]}...")
        
    prompt = f"""
   Extrahieren Sie strukturierte und prägnante Informationen aus diesem Lebenslauf:

     {cv_text}

   Die Informationen sollen einem Personalvermittler helfen den richtige offene Stelle für diese Person zu finden.

   Bitte achten Sie besonders auf folgende Aspekte:
   1. Karriereverlauf und -entwicklung: Wie hat sich die Karriere der Person entwickelt? Welche Richtung hat die Karriere genommen?
   2. Berufliche Präferenzen: Welche Art von Tätigkeiten, Branchen, Unternehmensgrößen oder Arbeitsumgebungen bevorzugt die Person basierend auf ihrem Lebenslauf?
   3. Karriereziele: Welche langfristigen Karriereziele lassen sich aus dem Lebenslauf ableiten?
   4. Zufriedenheitsindikatoren: Gibt es Hinweise darauf, in welchen früheren Positionen die Person besonders erfolgreich oder zufrieden war?
   5. Arbeitswerte und kulturelle Präferenzen: Welche Werte und kulturellen Aspekte scheinen für die Person wichtig zu sein?
    """

    logger.info(f"Prompt length: {len(prompt)}")
    logger.info("Making OpenAI API call...")

    try:
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": "Sie sind ein Assistent, der strukturierte Informationen aus Lebenslauftexten extrahiert."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=4000,
        )

        logger.info("OpenAI API call successful")
        logger.info(f"Response choices: {len(response.choices)}")
        
        summary = response.choices[0].message.content
        logger.info(f"Raw summary content: {bool(summary)}")
        if summary:
            summary = summary.strip()
            logger.info(f"Generated CV summary ({len(summary)} characters)")
            logger.info(f"Summary preview: {summary[:200]}...")
            logger.info("=== CV SUMMARIZATION COMPLETE ===")
            return summary
        else:
            logger.warning("OpenAI returned empty response")
            logger.info("=== CV SUMMARIZATION FAILED (EMPTY) ===")
            return "Error: Empty response from OpenAI API."
    except Exception as e:
        logger.error(f"Error summarizing CV: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception details: {str(e)}")
        logger.info("=== CV SUMMARIZATION FAILED (EXCEPTION) ===")
        return f"Error processing CV: {str(e)}"

if __name__ == "__main__":
    sample_cv = "cv-data/input/Lebenslauf_-_Lutz_Claudio.pdf"
    logger.info(f"Running test CV processing for {sample_cv}")
    text = extract_cv_text(sample_cv)
    summary = summarize_cv(text)
    print(summary)

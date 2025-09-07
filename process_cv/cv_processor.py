#%%

from pathlib import Path
import fitz
import openai
import os
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("cv_processor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("cv_processor")

def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file."""
    logger.info(f"Extracting text from PDF: {pdf_path}")
    text = ""
    try:
        with fitz.open(pdf_path) as pdf:
            for page in pdf:
                text += page.get_text()
        logger.info(f"Extracted {len(text)} characters from {pdf_path}")
    except Exception as e:
        logger.error(f"Error extracting text from {pdf_path}: {e}")
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
load_dotenv(dotenv_path=env_path, override=True)  # Force override system env vars

# Initialize the OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    logger.warning("OPENAI_API_KEY not set. OpenAI API calls may fail.")
else:
    logger.info(f"Using OpenAI API key starting with: {api_key[:10]}...")
client = openai.OpenAI(api_key=api_key)

def summarize_cv(cv_text):
    """Summarize CV text using the OpenAI API."""
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

        summary = response.choices[0].message.content.strip()
        logger.info(f"Generated CV summary ({len(summary)} characters)")
        return summary
    except Exception as e:
        logger.error(f"Error summarizing CV: {e}")
        return ""

if __name__ == "__main__":
    sample_cv = "cv-data/input/Lebenslauf_-_Lutz_Claudio.pdf"
    logger.info(f"Running test CV processing for {sample_cv}")
    text = extract_cv_text(sample_cv)
    summary = summarize_cv(text)
    print(summary)

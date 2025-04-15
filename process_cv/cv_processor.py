#%%

from pathlib import Path
import fitz
import docx
import openai
import os
from dotenv import load_dotenv

# PDF extraction function
def extract_text_from_pdf(pdf_path):
    text = ''
    with fitz.open(pdf_path) as pdf:
        for page in pdf:
            text += page.get_text()
    return text

# DOCX extraction function
def extract_text_from_docx(docx_path):
    doc = docx.Document(docx_path)
    return '\n'.join([para.text for para in doc.paragraphs])

# General extraction function
def extract_cv_text(file_path):
    if file_path.lower().endswith('.pdf'):
        return extract_text_from_pdf(file_path)
    elif file_path.lower().endswith('.docx'):
        return extract_text_from_docx(file_path)
    else:
        raise ValueError("Unsupported file type. Only PDF and DOCX allowed.")

env_path = Path("c:/Codes/JobsearchAI/process_cv/.env")
load_dotenv(dotenv_path=env_path)

# Initialize the OpenAI client
client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def summarize_cv(cv_text):
    prompt = f"""
   Extrahieren Sie strukturierte und prägnante Informationen aus diesem Lebenslauf:    
   
     {cv_text}
    
   Die Informationen sollen einem Personalvermittler helfen den richtige offene Stelle für diese Person zu finden.
    """

    response = client.chat.completions.create(
        model='gpt-4.1',
        messages=[
            {"role": "system", "content": "Sie sind ein Assistent, der strukturierte Informationen aus Lebenslauftexten extrahiert."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=800,
    )

    return response.choices[0].message.content.strip()

if __name__ == "__main__":
    cv_text = extract_cv_text('cv-data/Lebenslauf_Claudio Lutz.pdf')
    cv_summary = summarize_cv(cv_text)
    print(cv_summary)

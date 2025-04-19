from pathlib import Path
import fitz
import openai
import os
import json
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("cv_to_html_converter.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("cv_to_html_converter")

# Load environment variables
env_path = Path("c:/Codes/JobsearchAI/process_cv/.env")
load_dotenv(dotenv_path=env_path)

# Initialize the OpenAI client
client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def extract_pdf_structure(pdf_path):
    """
    Extract text and structural information from a PDF file
    """
    logger.info(f"Extracting structure from PDF: {pdf_path}")
    
    structure = {
        "pages": [],
        "metadata": {}
    }
    
    try:
        with fitz.open(pdf_path) as pdf:
            # Extract document metadata
            structure["metadata"] = {
                "title": pdf.metadata.get("title", ""),
                "author": pdf.metadata.get("author", ""),
                "subject": pdf.metadata.get("subject", ""),
                "keywords": pdf.metadata.get("keywords", ""),
                "creator": pdf.metadata.get("creator", ""),
                "producer": pdf.metadata.get("producer", ""),
                "page_count": len(pdf),
                "dimensions": {
                    "width": pdf[0].rect.width,
                    "height": pdf[0].rect.height
                }
            }
            
            # Process each page
            for page_num, page in enumerate(pdf):
                page_structure = {
                    "page_number": page_num + 1,
                    "dimensions": {
                        "width": page.rect.width,
                        "height": page.rect.height
                    },
                    "text_blocks": [],
                    "images": []
                }
                
                # Extract text blocks with position and font information
                blocks = page.get_text("dict")["blocks"]
                for block in blocks:
                    if block["type"] == 0:  # Text block
                        for line in block["lines"]:
                            for span in line["spans"]:
                                text_block = {
                                    "text": span["text"],
                                    "position": {
                                        "x0": span["bbox"][0],
                                        "y0": span["bbox"][1],
                                        "x1": span["bbox"][2],
                                        "y1": span["bbox"][3]
                                    },
                                    "font": span["font"],
                                    "font_size": span["size"],
                                    "color": span["color"],
                                    "is_bold": "bold" in span["font"].lower() or "heavy" in span["font"].lower(),
                                    "is_italic": "italic" in span["font"].lower() or "oblique" in span["font"].lower()
                                }
                                page_structure["text_blocks"].append(text_block)
                    
                    elif block["type"] == 1:  # Image block
                        image_block = {
                            "position": {
                                "x0": block["bbox"][0],
                                "y0": block["bbox"][1],
                                "x1": block["bbox"][2],
                                "y1": block["bbox"][3]
                            }
                        }
                        page_structure["images"].append(image_block)
                
                structure["pages"].append(page_structure)
        
        logger.info(f"Successfully extracted structure from PDF with {len(structure['pages'])} pages")
        return structure
    
    except Exception as e:
        logger.error(f"Error extracting PDF structure: {str(e)}")
        raise

def convert_cv_to_html(pdf_path):
    """
    Convert a CV PDF to HTML using GPT-4 to preserve layout and styling
    """
    logger.info(f"Converting CV to HTML: {pdf_path}")
    
    try:
        # Extract PDF structure
        pdf_structure = extract_pdf_structure(pdf_path)
        
        # Extract plain text for context
        plain_text = ""
        with fitz.open(pdf_path) as pdf:
            for page in pdf:
                plain_text += page.get_text()
        
        # Prepare the prompt for GPT-4
        prompt = f"""
        I need you to convert a CV/resume from PDF to HTML. I'll provide the PDF structure and content.
        
        Your task is to create a well-formatted HTML representation that:
        1. Preserves the original layout and visual hierarchy as much as possible
        2. Uses semantic HTML5 elements appropriately (header, section, etc.)
        3. Includes proper CSS styling to match the original appearance
        4. Is optimized for both screen viewing and printing on A4 paper
        5. Uses responsive design principles while maintaining the CV structure
        
        Here's the PDF structure information (position, fonts, etc.):
        {json.dumps(pdf_structure, indent=2)}
        
        And here's the plain text content for context:
        {plain_text}
        
        Please generate complete HTML with embedded CSS that:
        - Uses a clean, professional design
        - Preserves the original layout structure
        - Maintains the visual hierarchy (headings, sections, etc.)
        - Includes print-specific styles for A4 paper
        - Uses appropriate font sizes, spacing, and margins
        - Is well-structured and semantically correct
        
        Return ONLY the complete HTML code without any explanations or markdown formatting.
        """
        
        # Call GPT-4.1-mini to generate the HTML
        logger.info("Calling GPT-4.1-mini to generate HTML")
        response = client.chat.completions.create(
            model='gpt-4.1-mini',
            messages=[
                {"role": "system", "content": "You are an expert in converting PDF documents to HTML with perfect layout preservation."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=4000,
        )
        
        html_content = response.choices[0].message.content.strip()
        
        # Clean up the response if it contains markdown code blocks
        if html_content.startswith("```html"):
            html_content = html_content.replace("```html", "", 1)
            if html_content.endswith("```"):
                html_content = html_content[:-3]
            html_content = html_content.strip()
        
        # Ensure the HTML content is properly formatted
        # If it doesn't start with <!DOCTYPE html>, it might be just the body content
        if not html_content.lower().startswith("<!doctype html>") and not html_content.lower().startswith("<html"):
            # Wrap the content in basic HTML structure
            html_content = f"""
            <style>
                /* Base styles for CV */
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    margin: 0;
                    padding: 0;
                }}
                
                /* Add any additional base styles here */
            </style>
            <div class="cv-document">
                {html_content}
            </div>
            """
        
        logger.info("Successfully generated HTML content")
        return html_content
    
    except Exception as e:
        logger.error(f"Error converting CV to HTML: {str(e)}")
        raise

def save_cv_html(html_content, output_path):
    """
    Save the generated HTML content to a file
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"HTML content saved to: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Error saving HTML content: {str(e)}")
        raise

def convert_pdf_to_html(pdf_path, output_dir=None):
    """
    Main function to convert a PDF CV to HTML
    """
    try:
        # Create output directory if it doesn't exist
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(pdf_path), "html")
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate output filename
        pdf_filename = os.path.basename(pdf_path)
        html_filename = os.path.splitext(pdf_filename)[0] + ".html"
        output_path = os.path.join(output_dir, html_filename)
        
        # Convert CV to HTML
        html_content = convert_cv_to_html(pdf_path)
        
        # Save HTML content
        saved_path = save_cv_html(html_content, output_path)
        
        return {
            "success": True,
            "html_path": saved_path,
            "html_content": html_content
        }
    
    except Exception as e:
        logger.error(f"Error in convert_pdf_to_html: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    # Test the converter with a sample CV
    sample_cv_path = 'cv-data/Lebenslauf_Claudio Lutz.pdf'
    result = convert_pdf_to_html(sample_cv_path)
    
    if result["success"]:
        print(f"CV successfully converted to HTML: {result['html_path']}")
    else:
        print(f"Error converting CV to HTML: {result['error']}")

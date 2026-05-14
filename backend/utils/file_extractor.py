"""
Utility functions for extracting text from files (PDF, images)
"""
import os
from PIL import Image
import io

def extract_text_from_pdf(file_path):
    """
    Extract text from PDF file
    Returns extracted text as string
    """
    try:
        # Try using PyPDF2 first
        try:
            import PyPDF2
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text.strip()
        except ImportError:
            # Fallback to pdfplumber if PyPDF2 not available
            try:
                import pdfplumber
                text = ""
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                return text.strip()
            except ImportError:
                return "PDF extraction requires PyPDF2 or pdfplumber library. Please install: pip install PyPDF2"
    except Exception as e:
        return f"Error extracting PDF text: {str(e)}"

def extract_text_from_image(file_path):
    """
    Extract text from image using OCR
    Returns extracted text as string
    """
    try:
        # Try using pytesseract for OCR
        try:
            import pytesseract
            from PIL import Image
            
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
            return text.strip()
        except ImportError:
            return "Image OCR requires pytesseract library and Tesseract OCR. Please install: pip install pytesseract"
        except Exception as e:
            return f"Error extracting image text: {str(e)}"
    except Exception as e:
        return f"Error processing image: {str(e)}"

def extract_text_from_docx(file_path):
    """
    Extract text from DOCX file
    Returns extracted text as string
    """
    try:
        try:
            from docx import Document
            doc = Document(file_path)
            text = []
            for paragraph in doc.paragraphs:
                text.append(paragraph.text)
            return '\n'.join(text).strip()
        except ImportError:
            return "DOCX extraction requires python-docx library. Please install: pip install python-docx"
    except Exception as e:
        return f"Error extracting DOCX text: {str(e)}"

def extract_text_from_file(file_path, file_extension):
    """
    Extract text from file based on extension
    Returns extracted text as string
    """
    ext = file_extension.lower()
    
    if ext == 'pdf':
        return extract_text_from_pdf(file_path)
    elif ext in ['jpg', 'jpeg', 'png']:
        return extract_text_from_image(file_path)
    elif ext in ['docx', 'doc']:
        return extract_text_from_docx(file_path)
    elif ext == 'txt':
        # Plain text file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            return f"Error reading text file: {str(e)}"
    else:
        return f"Unsupported file type: {ext}. Supported types: PDF, DOCX, TXT, JPG, PNG"


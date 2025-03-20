from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import io
import re
import json
import tempfile
import shutil
from dotenv import load_dotenv
import google.generativeai as genai
import fitz  # PyMuPDF
import docx
from PIL import Image
from typing import Optional, List, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel
import uvicorn
import requests
import json
from fastapi import FastAPI, HTTPException

# Load environment variables
load_dotenv()

# Google API configuration
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable is not set")

# PostgreSQL configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# Configure Gemini model
genai.configure(api_key=GOOGLE_API_KEY)

# Model configuration
GENERATION_CONFIG = {
    "temperature": 0.2,
    "top_p": 0.8,
    "top_k": 40,
    "max_output_tokens": 2048,
}

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config=GENERATION_CONFIG
)

class DocumentProcessor:
    def process_document(self, file_path):
        """Process a document file and extract job description information"""
        # Determine file type
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension == '.pdf':
            return self._process_pdf(file_path)
        elif file_extension in ['.docx', '.doc']:
            return self._process_word(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
    
    def _process_pdf(self, file_path):
        """Process PDF file"""
        # Open the PDF
        pdf_document = fitz.open(file_path)
        
        # Extract text from all pages
        full_text = ""
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            full_text += page.get_text()
        
        # Create an image of the first page for visual analysis
        first_page = pdf_document[0]
        pix = first_page.get_pixmap()
        img_bytes = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_bytes))
        
        # Use Gemini to extract information from both text and image
        return self._extract_with_gemini(full_text, img)
    
    def _process_word(self, file_path):
        """Process Word document"""
        if file_path.endswith('.docx'):
            # Extract text from Word document
            doc = docx.Document(file_path)
            full_text = "\n".join([para.text for para in doc.paragraphs])
            
            # Use Gemini to extract information
            return self._extract_with_gemini(full_text)
        else:
            # For .doc files - would need additional library
            raise NotImplementedError("DOC file processing not implemented")
    
    def _extract_with_gemini(self, text, image=None):
        """Extract job description information using Google Gemini 2.0"""
        # Create prompt for Gemini
        prompt = """
        Extract the following details from the job description document:
        
        1. Job title
        2. Company name
        3. Job location
        4. Full job description
        5. Required skills (technical and soft skills that are explicitly mentioned as required)
        6. Preferred/Good to have skills (skills that are mentioned as preferred, good to have, or a plus)
        7. Years of experience required
        8. Education requirements
        9. Job type (full-time, part-time, contract, etc.)
        10. Salary range (if mentioned)
        11. Benefits (if mentioned)
        12. Application URL (if mentioned)
        13. Contact email (if mentioned)
        14. Date posted (if mentioned)
        
        Format the response as a JSON object with these fields:
        {
            "title": "",
            "company": "",
            "location": "",
            "description": "",
            "required_skills": [],
            "preferred_skills": [],
            "experience_required": "",
            "education_required": "",
            "job_type": "",
            "salary_range": "",
            "benefits": [],
            "application_url": "",
            "contact_email": "",
            "date_posted": ""
        }
        
        If a field is missing from the document, return an empty string or empty array as appropriate.
        """
        
        try:
            # If we have both text and image
            if image:
                response = model.generate_content([prompt, text, image])
            else:
                response = model.generate_content([prompt, text])
            
            # Get the response text
            response_text = response.text
            
            # Extract JSON from response (handle potential extra text)
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > 0:
                json_str = response_text[json_start:json_end]
                try:
                    extracted_info = json.loads(json_str)
                    return extracted_info
                except json.JSONDecodeError:
                    # Try to clean up the JSON
                    cleaned_json = self._clean_json_string(json_str)
                    extracted_info = json.loads(cleaned_json)
                    return extracted_info
            else:
                # Fallback to basic extraction
                return self._extract_basic_info(text)
                
        except Exception as e:
            print(f"Error with Gemini extraction: {e}")
            # Fallback to basic extraction
            return self._extract_basic_info(text)
    
    def _clean_json_string(self, json_str):
        """Clean up common JSON formatting issues"""
        # Replace single quotes with double quotes
        json_str = json_str.replace("'", '"')
        
        # Fix trailing commas
        json_str = re.sub(r',\s*}', '}', json_str)
        json_str = re.sub(r',\s*]', ']', json_str)
        
        return json_str
    
    def _extract_basic_info(self, text):
        """Fallback method: Extract basic job information using regex patterns"""
        # Initialize job info dictionary
        job_info = {
            "title": "",
            "company": "",
            "location": "",
            "description": text[:1000] if len(text) > 1000 else text,  # Truncate long descriptions
            "required_skills": [],
            "preferred_skills": [],
            "experience_required": "",
            "education_required": "",
            "job_type": "",
            "salary_range": "",
            "benefits": [],
            "application_url": "",
            "contact_email": "",
            "date_posted": ""
        }
        
        # Extract job title (often at the beginning or in capitalized text)
        title_patterns = [
            r'^(.+?)\n',  # First line of the document
            r'job title[:\s]+(.+?)(?:\n|$)',  # Explicit job title
            r'position[:\s]+(.+?)(?:\n|$)',  # Position statement
        ]
        
        for pattern in title_patterns:
            title_match = re.search(pattern, text, re.IGNORECASE)
            if title_match:
                job_info["title"] = title_match.group(1).strip()
                break
        
        # Extract company name
        company_patterns = [
            r'(?:company|organization|employer)[:\s]+(.+?)(?:\n|$)',
            r'(?:at|with|for)\s+([A-Z][A-Za-z0-9\s&,.]+?)(?:\n|$)'
        ]
        
        for pattern in company_patterns:
            company_match = re.search(pattern, text, re.IGNORECASE)
            if company_match:
                job_info["company"] = company_match.group(1).strip()
                break
        
        # Extract location
        location_patterns = [
            r'(?:location|place|city)[:\s]+(.+?)(?:\n|$)',
            r'(?:in|at)\s+([A-Z][A-Za-z\s,]+(?:,\s*[A-Z]{2})?)(?:\n|$)'
        ]
        
        for pattern in location_patterns:
            location_match = re.search(pattern, text, re.IGNORECASE)
            if location_match:
                job_info["location"] = location_match.group(1).strip()
                break
        
        # Extract email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            job_info["contact_email"] = emails[0]
        
        # Extract URLs
        url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+|(?:apply|application)[^\n]*(?:at|@)\s*([^\s<>"]+)'
        urls = re.findall(url_pattern, text)
        if urls:
            job_info["application_url"] = urls[0]
        
        return job_info

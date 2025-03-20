# config.py
import os
from dotenv import load_dotenv
import google.generativeai as genai
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import HTTPException

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

MODEL = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config=GENERATION_CONFIG
)


def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")
# Initialize database tables

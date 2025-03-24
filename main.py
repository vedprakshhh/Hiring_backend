from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv
import google.generativeai as genai
import os
# Import routers
from routers import job_descriptions, job_skills, recruiters, stats, assignment, resume
from database import init_db, create_tables

# Load environment variables
load_dotenv()

# Configure Google Gemini API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable is not set")

# Configure Gemini model
genai.configure(api_key=GOOGLE_API_KEY)

# Create FastAPI app
app = FastAPI(title="Job Description Analyzer API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development only. Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(job_descriptions.router)
app.include_router(job_skills.router)
app.include_router(recruiters.router)
app.include_router(stats.router)
app.include_router(assignment.router)
app.include_router(resume.router)

@app.get("/")
async def root():
    return {"message": "Job Description Analyzer API is running"}

@app.get("/api/health")
async def health_check():
    """API health check endpoint"""
    # Check database connection
    try:
        from config import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "ok",
        "database": db_status,
        "version": "1.0.0"
    }

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    try:
        init_db()
        create_tables()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")

# Run the application
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
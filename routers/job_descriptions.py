# routers/job_descriptions.py
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from typing import List, Optional
import tempfile
import shutil
import os
from models import JobDescriptionCreate, JobDescriptionResponse
from database import get_db_connection
from utils.document_processor import DocumentProcessor

router = APIRouter(
    prefix="",
    tags=["job_descriptions"]
)

# Function to save job description to PostgreSQL
def save_job_description(job_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Insert job description
        cursor.execute("""
        INSERT INTO job_descriptions (
            title, company, location, description, experience_required,
            education_required, job_type, salary_range, application_url,
            contact_email, date_posted
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """, (
            job_data["title"],
            job_data["company"],
            job_data["location"],
            job_data["description"],
            job_data["experience_required"],
            job_data["education_required"],
            job_data["job_type"],
            job_data["salary_range"],
            job_data["application_url"],
            job_data["contact_email"],
            job_data["date_posted"]
        ))
        
        job_id = cursor.fetchone()["id"]
        
        # Insert required skills
        for skill in job_data["required_skills"]:
            cursor.execute("""
            INSERT INTO job_skills (job_id, skill, is_required)
            VALUES (%s, %s, %s)
            """, (job_id, skill, True))
        
        # Insert preferred skills
        for skill in job_data["preferred_skills"]:
            cursor.execute("""
            INSERT INTO job_skills (job_id, skill, is_required)
            VALUES (%s, %s, %s)
            """, (job_id, skill, False))
        
        # Insert benefits
        if job_data["benefits"]:
            for benefit in job_data["benefits"]:
                cursor.execute("""
                INSERT INTO job_benefits (job_id, benefit)
                VALUES (%s, %s)
                """, (job_id, benefit))
        
        conn.commit()
        return job_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()

@router.post("/api/job-descriptions/analyze", response_model=JobDescriptionResponse)
async def analyze_job_description(file: UploadFile = File(...)):
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            # Copy the uploaded file to the temporary file
            shutil.copyfileobj(file.file, temp_file)
            temp_file_path = temp_file.name
        
        # Process the document
        processor = DocumentProcessor()
        extracted_info = processor.process_document(temp_file_path)
        
        # Save to PostgreSQL
        job_id = save_job_description(extracted_info)
        
        # Clean up the temporary file
        os.unlink(temp_file_path)
        
        # Return the extracted information with the database ID
        response_data = {**extracted_info, "id": job_id}
        return response_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/job-descriptions/{job_id}", response_model=JobDescriptionResponse)
async def get_job_description(job_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get job description
        cursor.execute("""
        SELECT * FROM job_descriptions WHERE id = %s
        """, (job_id,))
        job = cursor.fetchone()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job description not found")
        
        # Get required skills
        cursor.execute("""
        SELECT skill FROM job_skills WHERE job_id = %s AND is_required = TRUE
        """, (job_id,))
        required_skills = [row["skill"] for row in cursor.fetchall()]
        
        # Get preferred skills
        cursor.execute("""
        SELECT skill FROM job_skills WHERE job_id = %s AND is_required = FALSE
        """, (job_id,))
        preferred_skills = [row["skill"] for row in cursor.fetchall()]
        
        # Get benefits
        cursor.execute("""
        SELECT benefit FROM job_benefits WHERE job_id = %s
        """, (job_id,))
        benefits = [row["benefit"] for row in cursor.fetchall()]
        
        # Combine data
        job_data = dict(job)
        job_data["required_skills"] = required_skills
        job_data["preferred_skills"] = preferred_skills
        job_data["benefits"] = benefits
        
        return job_data
    
    finally:
        cursor.close()
        conn.close()

@router.get("/api/job-descriptions", response_model=List[JobDescriptionResponse])
async def list_job_descriptions(skip: int = 0, limit: int = 100):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get all job descriptions with pagination
        cursor.execute("""
        SELECT * FROM job_descriptions ORDER BY id DESC LIMIT %s OFFSET %s
        """, (limit, skip))
        jobs = cursor.fetchall()
        
        # Get all skills
        cursor.execute("""
        SELECT job_id, skill, is_required FROM job_skills
        WHERE job_id IN (SELECT id FROM job_descriptions ORDER BY id DESC LIMIT %s OFFSET %s)
        """, (limit, skip))
        skills_rows = cursor.fetchall()
        
        # Get all benefits
        cursor.execute("""
        SELECT job_id, benefit FROM job_benefits
        WHERE job_id IN (SELECT id FROM job_descriptions ORDER BY id DESC LIMIT %s OFFSET %s)
        """, (limit, skip))
        benefit_rows = cursor.fetchall()
        
        # Organize skills and benefits by job_id
        skills_by_job = {}
        benefits_by_job = {}
        
        for row in skills_rows:
            job_id = row["job_id"]
            skill = row["skill"]
            is_required = row["is_required"]
            
            if job_id not in skills_by_job:
                skills_by_job[job_id] = {"required": [], "preferred": []}
            
            if is_required:
                skills_by_job[job_id]["required"].append(skill)
            else:
                skills_by_job[job_id]["preferred"].append(skill)
        
        for row in benefit_rows:
            job_id = row["job_id"]
            benefit = row["benefit"]
            
            if job_id not in benefits_by_job:
                benefits_by_job[job_id] = []
            
            benefits_by_job[job_id].append(benefit)
        
        # Combine data
        result = []
        for job in jobs:
            job_data = dict(job)
            job_id = job["id"]
            
            job_data["required_skills"] = skills_by_job.get(job_id, {"required": []})["required"]
            job_data["preferred_skills"] = skills_by_job.get(job_id, {"preferred": []})["preferred"]
            job_data["benefits"] = benefits_by_job.get(job_id, [])
            
            result.append(job_data)
        
        return result
    
    finally:
        cursor.close()
        conn.close()

@router.put("/api/job-descriptions/{job_id}", response_model=JobDescriptionResponse)
async def update_job_description(job_id: int, job_data: JobDescriptionCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Start transaction
        conn.autocommit = False
        
        # Check if job exists
        cursor.execute("SELECT id FROM job_descriptions WHERE id = %s", (job_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Job description not found")
        
        # Update job description
        cursor.execute("""
        UPDATE job_descriptions SET
            title = %s,
            company = %s,
            location = %s,
            description = %s,
            experience_required = %s,
            education_required = %s,
            job_type = %s,
            salary_range = %s,
            application_url = %s,
            contact_email = %s,
            date_posted = %s
        WHERE id = %s
        """, (
            job_data.title,
            job_data.company,
            job_data.location,
            job_data.description,
            job_data.experience_required,
            job_data.education_required,
            job_data.job_type,
            job_data.salary_range,
            job_data.application_url,
            job_data.contact_email,
            job_data.date_posted,
            job_id
        ))
        
        # Delete existing skills
        cursor.execute("DELETE FROM job_skills WHERE job_id = %s", (job_id,))
        
        # Insert new required skills
        for skill in job_data.required_skills:
            cursor.execute("""
            INSERT INTO job_skills (job_id, skill, is_required)
            VALUES (%s, %s, %s)
            """, (job_id, skill, True))
        
        # Insert new preferred skills
        for skill in job_data.preferred_skills:
            cursor.execute("""
            INSERT INTO job_skills (job_id, skill, is_required)
            VALUES (%s, %s, %s)
            """, (job_id, skill, False))
        
        # Delete existing benefits
        cursor.execute("DELETE FROM job_benefits WHERE job_id = %s", (job_id,))
        
        # Insert new benefits
        if job_data.benefits:
            for benefit in job_data.benefits:
                cursor.execute("""
                INSERT INTO job_benefits (job_id, benefit)
                VALUES (%s, %s)
                """, (job_id, benefit))
        
        # Commit transaction
        conn.commit()
        
        # Return updated job
        return {**job_data.dict(), "id": job_id}
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        conn.autocommit = True
        cursor.close()
        conn.close()

@router.post("/api/job-descriptions", response_model=JobDescriptionResponse)
async def create_job_description(job_data: JobDescriptionCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Insert job description
        cursor.execute("""
        INSERT INTO job_descriptions (
            title, company, location, description, experience_required,
            education_required, job_type, salary_range, application_url,
            contact_email, date_posted
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """, (
            job_data.title,
            job_data.company,
            job_data.location,
            job_data.description,
            job_data.experience_required,
            job_data.education_required,
            job_data.job_type,
            job_data.salary_range,
            job_data.application_url,
            job_data.contact_email,
            job_data.date_posted
        ))
        
        job_id = cursor.fetchone()["id"]
        
        # Insert required skills
        for skill in job_data.required_skills:
            cursor.execute("""
            INSERT INTO job_skills (job_id, skill, is_required)
            VALUES (%s, %s, %s)
            """, (job_id, skill, True))
        
        # Insert preferred skills
        for skill in job_data.preferred_skills:
            cursor.execute("""
            INSERT INTO job_skills (job_id, skill, is_required)
            VALUES (%s, %s, %s)
            """, (job_id, skill, False))
        
        # Insert benefits
        if job_data.benefits:
            for benefit in job_data.benefits:
                cursor.execute("""
                INSERT INTO job_benefits (job_id, benefit)
                VALUES (%s, %s)
                """, (job_id, benefit))
        
        conn.commit()
        
        # Return created job
        return {**job_data.dict(), "id": job_id}
    
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        cursor.close()
        conn.close()

@router.get("/api/job-descriptions/search", response_model=List[JobDescriptionResponse])
async def search_job_descriptions(
    query: Optional[str] = None,
    company: Optional[str] = None,
    location: Optional[str] = None,
    skill: Optional[str] = None,
    job_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Build query
        sql_query = """
        SELECT DISTINCT jd.* FROM job_descriptions jd
        """
        
        # Add join if searching by skill
        if skill:
            sql_query += " LEFT JOIN job_skills js ON jd.id = js.job_id"
        
        # Add WHERE clauses
        conditions = []
        params = []
        
        if query:
            conditions.append("(jd.title ILIKE %s OR jd.description ILIKE %s)")
            params.extend([f"%{query}%", f"%{query}%"])
        
        if company:
            conditions.append("jd.company ILIKE %s")
            params.append(f"%{company}%")
        
        if location:
            conditions.append("jd.location ILIKE %s")
            params.append(f"%{location}%")
        
        if skill:
            conditions.append("js.skill ILIKE %s")
            params.append(f"%{skill}%")
        
        if job_type:
            conditions.append("jd.job_type ILIKE %s")
            params.append(f"%{job_type}%")
        
        if conditions:
            sql_query += " WHERE " + " AND ".join(conditions)
        
        # Add pagination
        sql_query += " ORDER BY jd.id DESC LIMIT %s OFFSET %s"
        params.extend([limit, skip])
        
        # Execute query
        cursor.execute(sql_query, params)
        jobs = cursor.fetchall()
        job_ids = [job["id"] for job in jobs]
        
        if not job_ids:
            return []
        
        # Get all skills for found jobs
        cursor.execute("""
        SELECT job_id, skill, is_required FROM job_skills
        WHERE job_id = ANY(%s)
        """, (job_ids,))
        skills_rows = cursor.fetchall()
        
        # Get all benefits for found jobs
        cursor.execute("""
        SELECT job_id, benefit FROM job_benefits
        WHERE job_id = ANY(%s)
        """, (job_ids,))
        benefit_rows = cursor.fetchall()
        
        # Organize skills and benefits by job_id
        skills_by_job = {}
        benefits_by_job = {}
        
        for row in skills_rows:
            job_id = row["job_id"]
            skill = row["skill"]
            is_required = row["is_required"]
            
            if job_id not in skills_by_job:
                skills_by_job[job_id] = {"required": [], "preferred": []}
            
            if is_required:
                skills_by_job[job_id]["required"].append(skill)
            else:
                skills_by_job[job_id]["preferred"].append(skill)
        
        for row in benefit_rows:
            job_id = row["job_id"]
            benefit = row["benefit"]
            
            if job_id not in benefits_by_job:
                benefits_by_job[job_id] = []
            
            benefits_by_job[job_id].append(benefit)
        
        # Combine data
        result = []
        for job in jobs:
            job_data = dict(job)
            job_id = job["id"]
            
            job_data["required_skills"] = skills_by_job.get(job_id, {"required": []})["required"]
            job_data["preferred_skills"] = skills_by_job.get(job_id, {"preferred": []})["preferred"]
            job_data["benefits"] = benefits_by_job.get(job_id, [])
            
            result.append(job_data)
        
        return result
    
    finally:
        cursor.close()
        conn.close()
# routers/job_skills.py
from fastapi import APIRouter, HTTPException
from models import SkillRatingRequest
from database import get_db_connection

router = APIRouter(
    prefix="/api/job-skills",
    tags=["job_skills"]
)

@router.get("/ratings/{job_id}")
async def get_skill_ratings(job_id: int):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute(
            "SELECT * FROM job_skill_ratings WHERE job_id = %s",
            (job_id,)
        )
        
        ratings = cur.fetchall()
        
        # Format the response
        required_skills = {}
        preferred_skills = {}
        
        for rating in ratings:
            if rating['is_required']:
                required_skills[rating['skill_name']] = rating['rating']
            else:
                preferred_skills[rating['skill_name']] = rating['rating']
        
        return {
            "job_id": job_id,
            "required_skills": required_skills,
            "preferred_skills": preferred_skills
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving skill ratings: {str(e)}")
    finally:
        if conn:
            conn.close()

@router.post("/ratings")
async def save_skill_ratings(request: SkillRatingRequest):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Delete existing ratings for this job
        cur.execute(
            "DELETE FROM job_skill_ratings WHERE job_id = %s",
            (request.job_id,)
        )
        
        # Save required skills
        for skill, rating in request.required_skills.items():
            cur.execute(
                "INSERT INTO job_skill_ratings (job_id, skill_name, rating, is_required) VALUES (%s, %s, %s, %s)",
                (request.job_id, skill, rating, True)
            )
        
        # Save preferred skills
        for skill, rating in request.preferred_skills.items():
            cur.execute(
                "INSERT INTO job_skill_ratings (job_id, skill_name, rating, is_required) VALUES (%s, %s, %s, %s)",
                (request.job_id, skill, rating, False)
            )
        
        conn.commit()
        return {"message": "Skill ratings saved successfully"}
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error saving skill ratings: {str(e)}")
    finally:
        if conn:
            conn.close()

@router.get("")
async def get_all_skills():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get all unique skills
        cursor.execute("""
        SELECT DISTINCT skill, is_required FROM job_skills
        ORDER BY skill
        """)
        skills = cursor.fetchall()
        
        # Organize by required/preferred
        required_skills = []
        preferred_skills = []
        
        for skill in skills:
            if skill["is_required"]:
                required_skills.append(skill["skill"])
            else:
                preferred_skills.append(skill["skill"])
        
        return {
            "required_skills": list(set(required_skills)),
            "preferred_skills": list(set(preferred_skills)),
            "all_skills": list(set(required_skills + preferred_skills))
        }
    
    finally:
        cursor.close()
        conn.close()
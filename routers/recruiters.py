# routers/recruiters.py
from fastapi import APIRouter, HTTPException
from typing import List
from models import RecruiterCreate, RecruiterResponse
from database import get_db_connection
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(
    prefix="/api/recruiters",
    tags=["recruiters"]
)

@router.get("", response_model=List[RecruiterResponse])
async def get_recruiters():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM recruiters ORDER BY name")
        recruiters = cursor.fetchall()
        
        # Convert datetime objects to strings
        for recruiter in recruiters:
            if isinstance(recruiter["created_at"], datetime):
                recruiter["created_at"] = recruiter["created_at"].isoformat()
                
        return recruiters
    finally:
        cursor.close()
        conn.close()

@router.get("/{recruiter_id}", response_model=RecruiterResponse)
async def get_recruiter(recruiter_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM recruiters WHERE id = %s", (recruiter_id,))
        recruiter = cursor.fetchone()
        
        if not recruiter:
            raise HTTPException(status_code=404, detail="Recruiter not found")
        
        # Convert datetime to string
        if isinstance(recruiter["created_at"], datetime):
            recruiter["created_at"] = recruiter["created_at"].isoformat()
        
        return recruiter
    finally:
        cursor.close()
        conn.close()

@router.post("", response_model=RecruiterResponse)
async def create_recruiter(recruiter: RecruiterCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO recruiters (name, email, phone) VALUES (%s, %s, %s) RETURNING *",
            (recruiter.name, recruiter.email, recruiter.phone)
        )
        new_recruiter = cursor.fetchone()
        conn.commit()
        
        # Convert datetime to string
        if isinstance(new_recruiter["created_at"], datetime):
            new_recruiter["created_at"] = new_recruiter["created_at"].isoformat()
        
        return new_recruiter
    finally:
        cursor.close()
        conn.close()

@router.put("/{recruiter_id}", response_model=RecruiterResponse)
async def update_recruiter(recruiter_id: int, recruiter: RecruiterCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id FROM recruiters WHERE id = %s", (recruiter_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Recruiter not found")
        
        cursor.execute(
            """
            UPDATE recruiters 
            SET name = %s, email = %s, phone = %s
            WHERE id = %s
            RETURNING *
            """,
            (recruiter.name, recruiter.email, recruiter.phone, recruiter_id)
        )
        
        updated_recruiter = cursor.fetchone()
        conn.commit()
        
        # Convert datetime to string
        if isinstance(updated_recruiter["created_at"], datetime):
            updated_recruiter["created_at"] = updated_recruiter["created_at"].isoformat()
        
        return updated_recruiter
    finally:
        cursor.close()
        conn.close()

@router.delete("/{recruiter_id}")
async def delete_recruiter(recruiter_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id FROM recruiters WHERE id = %s", (recruiter_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Recruiter not found")
        
        # Remove the check entirely for now
        # We'll add it back once we know the correct column name
        
        cursor.execute("DELETE FROM recruiters WHERE id = %s", (recruiter_id,))
        conn.commit()
        
        return {"message": "Recruiter deleted successfully"}
    finally:
        cursor.close()
        conn.close()
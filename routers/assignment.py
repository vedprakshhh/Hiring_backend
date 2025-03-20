# routers/recruiters.py
from fastapi import APIRouter, HTTPException
from models import Assignment, AssignmentUpdate, AssignmentCreate
from database import get_db_connection
from pydantic import BaseModel
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException, Depends
from typing import List, Optional
from contextlib import contextmanager


router = APIRouter(
    prefix="",
)

@router.get("/api/job-recruiter-assignments", response_model=List[Assignment])
async def get_all_assignments():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM job_recruiter_view
                ORDER BY assigned_date DESC
            """)
            assignments = cur.fetchall()
            return assignments

@router.get("/api/job-recruiter-assignments/job/{job_id}", response_model=List[Assignment])
async def get_assignments_by_job(job_id: int):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM job_recruiter_view
                WHERE job_id = %s
            """, (job_id,))
            assignments = cur.fetchall()
            return assignments

@router.post("/api/job-recruiter-assignments", response_model=Assignment)
async def create_assignment(assignment: AssignmentCreate):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            try:
                # Check if assignment already exists
                cur.execute("""
                    SELECT id FROM job_recruiter_assignments 
                    WHERE job_id = %s
                """, (assignment.job_id,))
                existing = cur.fetchone()
                
                if existing:
                    # Update existing assignment
                    cur.execute("""
                        UPDATE job_recruiter_assignments 
                        SET recruiter_id = %s, assigned_date = CURRENT_TIMESTAMP 
                        WHERE job_id = %s 
                        RETURNING id, job_id, recruiter_id, assigned_date
                    """, (assignment.recruiter_id, assignment.job_id))
                    result = cur.fetchone()
                else:
                    # Create new assignment
                    cur.execute("""
                        INSERT INTO job_recruiter_assignments (job_id, recruiter_id) 
                        VALUES (%s, %s) 
                        RETURNING id, job_id, recruiter_id, assigned_date
                    """, (assignment.job_id, assignment.recruiter_id))
                    result = cur.fetchone()
                
                conn.commit()
                
                # Get full view data
                cur.execute("""
                    SELECT * FROM job_recruiter_view WHERE id = %s
                """, (result['id'],))
                return cur.fetchone()
                
            except psycopg2.errors.ForeignKeyViolation:
                conn.rollback()
                raise HTTPException(status_code=400, detail="Invalid job ID or recruiter ID")
            except psycopg2.errors.UniqueViolation:
                conn.rollback()
                raise HTTPException(status_code=400, detail="This job is already assigned to this recruiter")
            except Exception as e:
                conn.rollback()
                raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@router.put("/api/job-recruiter-assignments/{assignment_id}", response_model=Assignment)
async def update_assignment(assignment_id: int, assignment: AssignmentUpdate):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("""
                    UPDATE job_recruiter_assignments 
                    SET recruiter_id = %s, assigned_date = CURRENT_TIMESTAMP 
                    WHERE id = %s 
                    RETURNING id
                """, (assignment.recruiter_id, assignment_id))
                
                result = cur.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail="Assignment not found")
                
                conn.commit()
                
                # Get full view data
                cur.execute("""
                    SELECT * FROM job_recruiter_view WHERE id = %s
                """, (assignment_id,))
                return cur.fetchone()
                
            except psycopg2.errors.ForeignKeyViolation:
                conn.rollback()
                raise HTTPException(status_code=400, detail="Invalid recruiter ID")
            except Exception as e:
                conn.rollback()
                raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@router.delete("/api/job-recruiter-assignments/{assignment_id}")
async def delete_assignment(assignment_id: int):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM job_recruiter_assignments 
                WHERE id = %s 
                RETURNING id
            """, (assignment_id,))
            
            result = cur.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="Assignment not found")
            
            conn.commit()
            return {"message": "Assignment deleted successfully"}
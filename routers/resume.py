from fastapi import FastAPI, HTTPException, Depends, Body
from pydantic import BaseModel
from typing import Optional, List
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import os
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from typing import List
from database import get_db_connection
from pydantic import BaseModel
from datetime import datetime
from models import Employee

router = APIRouter(
    prefix="",
)

@router.get("/api/employees", response_model=List[Employee])
async def get_employees():
    """Get all employees from the database"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, name, phone_number, skills, role FROM employees")
        employees = cur.fetchall()
        cur.close()
        conn.close()
        return employees
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/api/employees/{employee_id}", response_model=Employee)
async def get_employee(employee_id: str):
    """Get a specific employee by ID"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, name, phone_number, skills, role FROM employees WHERE id = %s", (employee_id,))
        employee = cur.fetchone()
        cur.close()
        conn.close()
        
        if employee is None:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        return employee
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/api/feedback")
async def create_feedback(feedback_data: dict):
    """Save interview feedback"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Assuming you have a feedback table - adjust the SQL as needed
        cur.execute(
            """
            INSERT INTO feedback (job_id, employee_id, position, technical_skills, communication_skills, overall_rating)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                feedback_data.get("jobId"),
                feedback_data.get("employeeId"),
                feedback_data.get("position"),
                feedback_data.get("technicalSkills"),
                feedback_data.get("communicationSkills"),
                feedback_data.get("overallRating")
            )
        )
        
        cur.close()
        conn.close()
        return {"status": "success", "message": "Feedback saved successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
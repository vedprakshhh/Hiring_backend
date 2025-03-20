# models.py
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class JobDescriptionCreate(BaseModel):
    title: str
    company: str
    location: str
    description: str
    required_skills: List[str]
    preferred_skills: List[str]
    experience_required: str
    education_required: str
    job_type: str
    salary_range: Optional[str] = None
    benefits: Optional[List[str]] = None
    application_url: Optional[str] = None
    contact_email: Optional[str] = None
    date_posted: Optional[str] = None
    
class JobDescriptionResponse(JobDescriptionCreate):
    id: int

class SkillRatingRequest(BaseModel):
    job_id: int
    required_skills: Dict[str, int]
    preferred_skills: Dict[str, int]

class RecruiterCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None

class RecruiterResponse(RecruiterCreate):
    id: int
    created_at: Optional[str] = None

# Pydantic models for request/response validation
class AssignmentCreate(BaseModel):
    job_id: int
    recruiter_id: int

class AssignmentUpdate(BaseModel):
    recruiter_id: int

class Assignment(BaseModel):
    id: int
    job_id: int
    recruiter_id: int
    assigned_date: datetime
    job_title: Optional[str] = None
    recruiter_name: Optional[str] = None
    company: Optional[str] = None

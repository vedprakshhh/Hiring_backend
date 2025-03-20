from fastapi import APIRouter, HTTPException
from config import get_db_connection
from typing import Dict, List, Any

router = APIRouter(tags=["stats"])

@router.get("/stats")
async def get_job_stats():
    """
    Get statistics about job descriptions, skills, and other metrics
    
    Returns various statistics including:
    - Total counts (jobs, companies, locations)
    - Top required and preferred skills
    - Job type distribution
    - Recent job listings
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Count of job descriptions
        cursor.execute("SELECT COUNT(*) as job_count FROM job_descriptions")
        job_count = cursor.fetchone()["job_count"]
        
        # Count of companies
        cursor.execute("SELECT COUNT(DISTINCT company) as company_count FROM job_descriptions")
        company_count = cursor.fetchone()["company_count"]
        
        # Count of locations
        cursor.execute("SELECT COUNT(DISTINCT location) as location_count FROM job_descriptions")
        location_count = cursor.fetchone()["location_count"]
        
        # Top 10 required skills
        cursor.execute("""
        SELECT skill, COUNT(*) as count
        FROM job_skills
        WHERE is_required = TRUE
        GROUP BY skill
        ORDER BY count DESC
        LIMIT 10
        """)
        top_required_skills = [{"skill": row["skill"], "count": row["count"]} for row in cursor.fetchall()]
        
        # Top 10 preferred skills
        cursor.execute("""
        SELECT skill, COUNT(*) as count
        FROM job_skills
        WHERE is_required = FALSE
        GROUP BY skill
        ORDER BY count DESC
        LIMIT 10
        """)
        top_preferred_skills = [{"skill": row["skill"], "count": row["count"]} for row in cursor.fetchall()]
        
        # Job types distribution
        cursor.execute("""
        SELECT job_type, COUNT(*) as count
        FROM job_descriptions
        WHERE job_type != ''
        GROUP BY job_type
        ORDER BY count DESC
        """)
        job_types = [{"type": row["job_type"], "count": row["count"]} for row in cursor.fetchall()]
        
        # Recent additions
        cursor.execute("""
        SELECT id, title, company, location, created_at
        FROM job_descriptions
        ORDER BY created_at DESC
        LIMIT 5
        """)
        recent_jobs = [dict(row) for row in cursor.fetchall()]
        
        # Experience levels
        cursor.execute("""
        SELECT experience_required, COUNT(*) as count
        FROM job_descriptions
        WHERE experience_required != ''
        GROUP BY experience_required
        ORDER BY count DESC
        LIMIT 10
        """)
        experience_levels = [{"level": row["experience_required"], "count": row["count"]} for row in cursor.fetchall()]
        
        # Education requirements
        cursor.execute("""
        SELECT education_required, COUNT(*) as count
        FROM job_descriptions
        WHERE education_required != ''
        GROUP BY education_required
        ORDER BY count DESC
        LIMIT 10
        """)
        education_requirements = [{"education": row["education_required"], "count": row["count"]} for row in cursor.fetchall()]
        
        # Most active companies
        cursor.execute("""
        SELECT company, COUNT(*) as job_count
        FROM job_descriptions
        GROUP BY company
        ORDER BY job_count DESC
        LIMIT 10
        """)
        top_companies = [{"company": row["company"], "job_count": row["job_count"]} for row in cursor.fetchall()]
        
        # Popular locations
        cursor.execute("""
        SELECT location, COUNT(*) as job_count
        FROM job_descriptions
        GROUP BY location
        ORDER BY job_count DESC
        LIMIT 10
        """)
        top_locations = [{"location": row["location"], "job_count": row["job_count"]} for row in cursor.fetchall()]
        
        return {
            "summary": {
                "job_count": job_count,
                "company_count": company_count,
                "location_count": location_count
            },
            "top_required_skills": top_required_skills,
            "top_preferred_skills": top_preferred_skills,
            "job_types": job_types,
            "recent_jobs": recent_jobs,
            "experience_levels": experience_levels,
            "education_requirements": education_requirements,
            "top_companies": top_companies,
            "top_locations": top_locations
        }
    
    finally:
        cursor.close()
        conn.close()

@router.get("/job-types")
async def get_job_types():
    """Get list of all job types in the database with their counts"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
        SELECT DISTINCT job_type, COUNT(*) as job_count
        FROM job_descriptions
        WHERE job_type != ''
        GROUP BY job_type
        ORDER BY job_count DESC
        """)
        job_types = [{"type": row["job_type"], "job_count": row["job_count"]} for row in cursor.fetchall()]
        return job_types
    
    finally:
        cursor.close()
        conn.close()

@router.get("/skill-demand")
async def get_skill_demand():
    """Get trending skills and their growth over time"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get skill demand (using created_at from job_skills table)
        cursor.execute("""
        SELECT 
            skill,
            COUNT(*) as total_count,
            SUM(CASE WHEN is_required = TRUE THEN 1 ELSE 0 END) as required_count,
            SUM(CASE WHEN is_required = FALSE THEN 1 ELSE 0 END) as preferred_count,
            DATE_TRUNC('month', created_at) as month
        FROM job_skills
        GROUP BY skill, DATE_TRUNC('month', created_at)
        ORDER BY month DESC, total_count DESC
        LIMIT 100
        """)
        
        skills_demand = []
        for row in cursor.fetchall():
            skills_demand.append({
                "skill": row["skill"],
                "total_count": row["total_count"],
                "required_count": row["required_count"],
                "preferred_count": row["preferred_count"],
                "month": row["month"].strftime('%Y-%m') if row["month"] else None
            })
        
        # Get top trending skills (those with increasing demand)
        cursor.execute("""
        WITH monthly_counts AS (
            SELECT 
                skill,
                DATE_TRUNC('month', created_at) as month,
                COUNT(*) as count
            FROM job_skills
            GROUP BY skill, DATE_TRUNC('month', created_at)
        ),
        skill_growth AS (
            SELECT 
                skill,
                COALESCE(
                    (
                        SELECT AVG(count) 
                        FROM monthly_counts mc2 
                        WHERE mc2.skill = mc1.skill AND 
                              mc2.month >= (CURRENT_DATE - INTERVAL '1 month')::date
                    ), 0
                ) as recent_avg,
                COALESCE(
                    (
                        SELECT AVG(count) 
                        FROM monthly_counts mc2 
                        WHERE mc2.skill = mc1.skill AND 
                              mc2.month < (CURRENT_DATE - INTERVAL '1 month')::date AND
                              mc2.month >= (CURRENT_DATE - INTERVAL '3 months')::date
                    ), 0
                ) as previous_avg
            FROM monthly_counts mc1
            GROUP BY skill
        )
        SELECT 
            skill, 
            recent_avg,
            previous_avg,
            CASE 
                WHEN previous_avg = 0 THEN 100
                ELSE (recent_avg - previous_avg) / previous_avg * 100
            END as growth_percent
        FROM skill_growth
        WHERE recent_avg > 0
        ORDER BY growth_percent DESC
        LIMIT 20
        """)
        
        trending_skills = []
        for row in cursor.fetchall():
            trending_skills.append({
                "skill": row["skill"],
                "recent_avg": float(row["recent_avg"]),
                "previous_avg": float(row["previous_avg"]),
                "growth_percent": float(row["growth_percent"])
            })
            
        return {
            "skills_demand": skills_demand,
            "trending_skills": trending_skills
        }
    
    finally:
        cursor.close()
        conn.close()

@router.get("/salary-analysis")
async def get_salary_analysis():
    """Get salary statistics across different job types and experience levels"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Extract minimum and maximum salary from salary_range
        cursor.execute("""
        WITH salary_data AS (
            SELECT 
                id,
                job_type,
                experience_required,
                REGEXP_MATCH(salary_range, '\\$?(\\d+[,\\d]*)\\s*-\\s*\\$?(\\d+[,\\d]*)') as salary_parts
            FROM job_descriptions
            WHERE salary_range ~* '\\$?(\\d+[,\\d]*)\\s*-\\s*\\$?(\\d+[,\\d]*)'
        )
        SELECT 
            job_type,
            experience_required,
            ROUND(AVG(REPLACE(salary_parts[1], ',', '')::numeric)) as avg_min_salary,
            ROUND(AVG(REPLACE(salary_parts[2], ',', '')::numeric)) as avg_max_salary,
            COUNT(*) as job_count
        FROM salary_data
        GROUP BY job_type, experience_required
        HAVING COUNT(*) > 1
        ORDER BY avg_max_salary DESC
        """)
        
        salary_by_job_type = []
        for row in cursor.fetchall():
            salary_by_job_type.append({
                "job_type": row["job_type"],
                "experience_required": row["experience_required"],
                "avg_min_salary": float(row["avg_min_salary"]),
                "avg_max_salary": float(row["avg_max_salary"]),
                "job_count": row["job_count"]
            })
            
        return {
            "salary_by_job_type": salary_by_job_type
        }
    except Exception as e:
        return {
            "error": str(e),
            "message": "Could not analyze salary data - this may be due to inconsistent salary formats",
            "salary_by_job_type": []
        }
    finally:
        cursor.close()
        conn.close()

@router.get("/dashboard-summary")
async def get_dashboard_summary():
    """Get a summary of key metrics for the dashboard"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Job count
        cursor.execute("SELECT COUNT(*) as count FROM job_descriptions")
        job_count = cursor.fetchone()["count"]
        
        # Jobs added this month
        cursor.execute("""
        SELECT COUNT(*) as count 
        FROM job_descriptions 
        WHERE created_at >= DATE_TRUNC('month', CURRENT_DATE)
        """)
        jobs_this_month = cursor.fetchone()["count"]
        
        # Total companies
        cursor.execute("SELECT COUNT(DISTINCT company) as count FROM job_descriptions")
        company_count = cursor.fetchone()["count"]
        
        # Top skills
        cursor.execute("""
        SELECT skill, COUNT(*) as count 
        FROM job_skills 
        WHERE is_required = TRUE 
        GROUP BY skill 
        ORDER BY count DESC 
        LIMIT 5
        """)
        top_skills = [{"skill": row["skill"], "count": row["count"]} for row in cursor.fetchall()]
        
        # Latest jobs
        cursor.execute("""
        SELECT id, title, company, created_at 
        FROM job_descriptions 
        ORDER BY created_at DESC 
        LIMIT 3
        """)
        latest_jobs = [dict(row) for row in cursor.fetchall()]
        
        return {
            "job_count": job_count,
            "jobs_this_month": jobs_this_month,
            "company_count": company_count,
            "top_skills": top_skills,
            "latest_jobs": latest_jobs
        }
    
    finally:
        cursor.close()
        conn.close()
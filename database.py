# database.py
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import HTTPException
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

def get_db_connection():
    """Create and return a database connection"""
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

def init_db():
    """Initialize database tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Create job_descriptions table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_descriptions (
            id SERIAL PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            company VARCHAR(255) NOT NULL,
            location VARCHAR(255) NOT NULL,
            description TEXT NOT NULL,
            experience_required VARCHAR(255),
            education_required TEXT,
            job_type VARCHAR(100),
            salary_range VARCHAR(255),
            application_url TEXT,
            contact_email VARCHAR(255),
            date_posted VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Create skills tables
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_skills (
            id SERIAL PRIMARY KEY,
            job_id INTEGER REFERENCES job_descriptions(id) ON DELETE CASCADE,
            skill VARCHAR(255) NOT NULL,
            is_required BOOLEAN NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Create benefits table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_benefits (
            id SERIAL PRIMARY KEY,
            job_id INTEGER REFERENCES job_descriptions(id) ON DELETE CASCADE,
            benefit TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Create the recruiters table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recruiters (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255),
                phone VARCHAR(50),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
        
        # Create skill ratings table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_skill_ratings (
            id SERIAL PRIMARY KEY,
            job_id INTEGER NOT NULL,
            skill_name VARCHAR(255) NOT NULL,
            rating INTEGER NOT NULL,
            is_required BOOLEAN NOT NULL
        )
        """)
        
        cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'job_recruiter_assignments'
                )
            """)
        
        table_exists = cursor.fetchone()['exists']
        if not table_exists:
                # Create job_recruiter_assignments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS job_recruiter_assignments (
                        id SERIAL PRIMARY KEY,
                        job_id INTEGER NOT NULL,
                        recruiter_id INTEGER NOT NULL,
                        assigned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        CONSTRAINT fk_job
                            FOREIGN KEY(job_id)
                            REFERENCES job_descriptions(id)
                            ON DELETE CASCADE,
                        CONSTRAINT fk_recruiter
                            FOREIGN KEY(recruiter_id)
                            REFERENCES recruiters(id)
                            ON DELETE CASCADE,
                        CONSTRAINT unique_job_recruiter UNIQUE (job_id, recruiter_id)
                    )
                """)
                
                # Create indices
            cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_job_recruiter_job_id 
                    ON job_recruiter_assignments(job_id)
                """)
                
            cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_job_recruiter_recruiter_id 
                    ON job_recruiter_assignments(recruiter_id)
                """)
                
                # Create view for easier access to joined data
            cursor.execute("""
                    CREATE OR REPLACE VIEW job_recruiter_view AS
                    SELECT 
                        a.id,
                        a.job_id,
                        a.recruiter_id,
                        a.assigned_date,
                        j.title AS job_title,
                        r.name AS recruiter_name,
                        j.company AS company
                    FROM 
                        job_recruiter_assignments a
                    JOIN 
                        job_descriptions j ON a.job_id = j.id
                    JOIN 
                        recruiters r ON a.recruiter_id = r.id
                """)
                
        conn.commit()
    finally:
        cursor.close()
        conn.close()

def create_tables():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Create the table directly in the tres database (no schema needed)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS job_skill_ratings (
            id SERIAL PRIMARY KEY,
            job_id INTEGER NOT NULL,
            skill_name VARCHAR(255) NOT NULL,
            rating INTEGER NOT NULL,
            is_required BOOLEAN NOT NULL
        )
        """)
        conn.commit()  # Commit the table creation
    except Exception as e:
        print(f"Error creating table: {e}")
        conn.rollback()  # Rollback on error
    finally:
        cur.close()
        conn.close()
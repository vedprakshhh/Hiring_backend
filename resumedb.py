import psycopg2
from psycopg2 import Error
import uuid
from psycopg2.extensions import register_adapter
import psycopg2.extras

# Register UUID adapter
psycopg2.extras.register_uuid()

def connect_to_database():
    """Connect to the PostgreSQL database."""
    try:
        connection = psycopg2.connect(
            user="postgres",
            password="Temp1234",  # Replace with your actual password
            host="localhost",
            port="5432",
            database="jobsd"  # Replace with your actual database name
        )
        return connection
    except (Exception, Error) as error:
        print("Error while connecting to PostgreSQL:", error)
        return None

def create_table_if_not_exists(connection):
    """Create the table if it doesn't exist."""
    try:
        cursor = connection.cursor()
        
        # Create table query
        create_table_query = """
        CREATE TABLE IF NOT EXISTS Jd_Resume_feedback (
            id SERIAL PRIMARY KEY,
            Jd_id VARCHAR(255) NOT NULL,
            resume1 VARCHAR(255) NOT NULL,
            resume2 VARCHAR(255) NOT NULL,
            technical_skills_feedback TEXT,
            communication_skills_feedback TEXT,
            Final_Feedback TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        cursor.execute(create_table_query)
        connection.commit()
        print("Table created successfully or already exists")
        
    except (Exception, Error) as error:
        print("Error while creating table:", error)

def add_employee(connection):
    """Add a new employee to the database."""
    try:
        cursor = connection.cursor()
        
        # Generate a unique UUID
        employee_id = uuid.uuid4()
        
        # Get employee details from user
        Jd_id = input("Enter jd id: ")
        resume1  = input("Enter resume id: ")
        resume2 = input("Enter resume id: ")        
        technical_skills_feedback = input("Enter technical skills feedback: ")
        communication_skills_feedback = input("Enter communication skills feedback: ")
        Final_Feedback = input("Enter final feedback:  ")
        # Insert query
        insert_query = '''
        INSERT INTO Jd_Resume_feedback  (Jd_id, resume1, resume2, technical_skills_feedback, communication_skills_feedback, Final_Feedback)
        VALUES (%s, %s, %s, %s, %s, %s)
        '''
        
        # Execute the query
        cursor.execute(insert_query, (Jd_id, resume1, resume2, technical_skills_feedback, communication_skills_feedback, Final_Feedback))
        connection.commit()
        
        print(f"Employee added successfully with ID: {employee_id}")
        return True
        
    except (Exception, Error) as error:
        print("Error while adding employee:", error)
        return False

def main():
    """Main function to run the program."""
    connection = connect_to_database()
    
    if connection:
        create_table_if_not_exists(connection)
        
        while True:
            print("\n--- PostgreSQL Employee Data Entry ---")
            print("1. Add new employee")
            print("2. Exit")
            
            choice = input("\nEnter your choice (1-2): ")
            
            if choice == '1':
                add_employee(connection)
            elif choice == '2':
                print("Exiting program...")
                break
            else:
                print("Invalid choice. Please try again.")
        
        # Close the connection
        if connection:
            connection.close()
            print("PostgreSQL connection is closed")

if __name__ == "__main__":
    main()
import time
import mysql.connector  # Library for connecting to MySQL database
import bcrypt  # Library for secure password hashing  # For handling date and time operations
import uuid  # Add this import at the top

# ---------- CONNECTION ----------

def get_connection():
    """
    Create and return a new connection to the MySQL database.
    
    This function is called whenever we need to interact with the database.
    It establishes a new connection each time to ensure we have a fresh connection.
    
    Returns:
        A MySQL connection object
    """
    return mysql.connector.connect(
        host="localhost",      # Database server address (local machine)
        user="root",           # Database username
        database="chat_app"    # Name of the database to use
    )

# ---------- SETUP ----------

def setup_database():
    """
    Set up the database schema (tables and relationships).
    
    This function creates the necessary tables if they don't already exist:
    - users: Stores user information
    - tutorials: Stores tutorial information
    - assignments: Links users to tutorials
    - active_chats: Tracks ongoing chat sessions
    """
    # Get a database connection
    conn = get_connection()
    cursor = conn.cursor()

    # Create users table (if it doesn't exist)
    # This table stores all user information
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id VARCHAR(50) PRIMARY KEY,           -- Unique identifier for each user
            name VARCHAR(100),                    -- User's name
            password_hash VARCHAR(255),           -- Bcrypt hashed password for security
            role ENUM('admin', 'student', 'tutor'), -- User's role (limited to these 3 options)
            profile_pic TEXT                      -- Path to profile picture (optional)
        )
    """)

    # Create tutorials table (if it doesn't exist)
    # This table stores information about tutorials
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tutorials (
            id VARCHAR(50) PRIMARY KEY,  -- Unique identifier for each tutorial
            name VARCHAR(100)            -- Tutorial name
        )
    """)

    # Create assignments table (if it doesn't exist)
    # This is a many-to-many relationship table linking users to tutorials
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assignments (
            user_id VARCHAR(50),         -- User ID (foreign key)
            tutorial_id VARCHAR(50),     -- Tutorial ID (foreign key)
            FOREIGN KEY (user_id) REFERENCES users(id),       -- Reference to users table
            FOREIGN KEY (tutorial_id) REFERENCES tutorials(id), -- Reference to tutorials table
            PRIMARY KEY (user_id, tutorial_id)                -- Composite primary key
        )
    """)

    # Create active_chats table (if it doesn't exist) - MODIFIED to include chat_session_id
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS active_chats (
            tutorial_id VARCHAR(50) PRIMARY KEY,  -- Tutorial ID (primary key)
            tutor_id VARCHAR(50),                 -- Tutor ID
            start_time DOUBLE,                    -- When the chat started (as UNIX timestamp)
            end_time DOUBLE,                      -- When the chat will end (as UNIX timestamp)
            chat_session_id VARCHAR(36),          -- Unique identifier for chat session (UUID)
            FOREIGN KEY (tutorial_id) REFERENCES tutorials(id), -- Reference to tutorials table
            FOREIGN KEY (tutor_id) REFERENCES users(id)         -- Reference to users table
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INT AUTO_INCREMENT PRIMARY KEY,
            chat_session_id VARCHAR(36),        -- Link to specific chat session
            tutorial_id VARCHAR(50),            -- Tutorial ID
            student_id VARCHAR(50),             -- Student who attended
            first_join_time DOUBLE,             -- When they first joined
            last_seen_time DOUBLE,              -- Last time they were in the chat
            total_duration_seconds INT DEFAULT 0, -- Accumulated time in chat
            is_present BOOLEAN DEFAULT FALSE,    -- Current presence status
            FOREIGN KEY (student_id) REFERENCES users(id),
            FOREIGN KEY (tutorial_id) REFERENCES tutorials(id)
        )
    """)

    # Save the changes
    conn.commit()
    # Close the connection
    conn.close()

    clear_active_chats()  # Clear any existing active chats

# ---------- USER MANAGEMENT ----------

def create_user(user_id, name, password, role, profile_pic=None):
    """
    Create a new user in the database with a DiceBear avatar.
    
    Parameters:
        user_id (str): Unique identifier for the user.
        name (str): User's name.
        password (str): Plain text password (will be hashed).
        role (str): User role (admin, student, or tutor).
        profile_pic (str, optional): Path to profile picture (default is generated DiceBear avatar).
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Hash the password with bcrypt
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    
    profile_pic = generate_avatar_url(user_id)
    
    # Insert the new user into the database
    cursor.execute("INSERT INTO users (id, name, password_hash, role, profile_pic) VALUES (%s, %s, %s, %s, %s)",
                   (user_id, name, hashed.decode(), role, profile_pic))
    
    conn.commit()
    conn.close()

def get_user(user_id):
    """
    Retrieve user details from the database by user ID.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)  # Use dictionary cursor to access fields by name
    cursor.execute("SELECT id, name, password_hash, role, profile_pic FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_user_role(user_id):
    """
    Get a user's role (admin, tutor, or student).
    
    Parameters:
        user_id (str): The ID of the user
        
    Returns:
        str: The user's role if found, None otherwise
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Execute the query to find the user's role
    cursor.execute("SELECT role FROM users WHERE id = %s", (user_id,))
    
    # Get the result
    result = cursor.fetchone()
    
    # Close the connection
    conn.close()
    
    # Return the role (or None if user not found)
    return result[0] if result else None

# ---------- TUTORIALS ----------

def create_tutorial(tutorial_id, name):
    """
    Create a new tutorial in the database.
    
    Parameters:
        tutorial_id (str): Unique identifier for the tutorial
        name (str): Name of the tutorial
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Insert the new tutorial
        cursor.execute("INSERT INTO tutorials (id, name) VALUES (%s, %s)", (tutorial_id, name))
        
        # Save the changes
        conn.commit()
        return True
        
    except mysql.connector.Error as e:
        # Log the error
        print("DB Error during tutorial creation:", e)
        return False
        
    finally:
        # Close the connection (even if an error occurred)
        conn.close()

def get_tutorial(tutorial_id):  
    """
    Retrieve a tutorial from the database by its ID.
    
    Parameters:
        tutorial_id (str): The ID of the tutorial to retrieve
        
    Returns:
        dict: Tutorial information if found, None otherwise
    """
    conn = get_connection()
    # Use dictionary cursor to get results as dictionaries
    cursor = conn.cursor(dictionary=True)
    
    # Execute the query to find the tutorial
    cursor.execute("SELECT * FROM tutorials WHERE id = %s", (tutorial_id,))
    
    # Get the result
    tutorial = cursor.fetchone()
    
    # Close the connection
    conn.close()
    
    # Return the tutorial data (or None if not found)
    return tutorial

def assign_user_to_tutorial(user_id, tutorial_id):
    """
    Assign a user to a tutorial by creating an entry in the assignments table.
    
    Parameters:
        user_id (str): The ID of the user
        tutorial_id (str): The ID of the tutorial
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Create the assignment
        cursor.execute("INSERT INTO assignments (user_id, tutorial_id) VALUES (%s, %s)", (user_id, tutorial_id))
        
        # Save the changes
        conn.commit()
        return True
        
    except mysql.connector.Error as e:
        # Log the error
        print("DB Error during assignment:", e)
        return False
        
    finally:
        # Close the connection
        conn.close()

def is_tutor_already_assigned(tutorial_id):
    """
    Check if a tutor is already assigned to a tutorial.
    
    Parameters:
        tutorial_id (str): The ID of the tutorial to check
        
    Returns:
        bool: True if a tutor is assigned, False otherwise
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Execute a query to find a tutor assigned to this tutorial
    cursor.execute("""
        SELECT u.id FROM assignments a
        JOIN users u ON a.user_id = u.id
        WHERE a.tutorial_id = %s AND u.role = 'tutor'
    """, (tutorial_id,))
    
    # Get the result
    result = cursor.fetchone()
    
    # Close the connection
    conn.close()
    
    # Return True if a tutor was found, False otherwise
    return result is not None

# ---------- FETCHING TUTORIALS ----------

def get_user_tutorials(tutor_id):
    """
    Get all tutorials assigned to a specific tutor or student.
    
    Parameters:
        tutor_id (str): The ID of the tutor/student
        
    Returns:
        list: List of dictionaries containing tutorial information
    """
    conn = get_connection()
    # Use dictionary cursor to get results as dictionaries
    cursor = conn.cursor(dictionary=True)
    
    # Execute the query to find tutorials assigned to this user
    cursor.execute("""
        SELECT t.id, t.name FROM assignments a
        JOIN tutorials t ON a.tutorial_id = t.id
        WHERE a.user_id = %s
    """, (tutor_id,))
    
    # Get all results
    results = cursor.fetchall()
    
    # Close the connection
    conn.close()
    
    # Return the list of tutorials
    return results

def get_students_in_tutorial(tutorial_id):
    """
    Get all students assigned to a specific tutorial.
    
    Parameters:
        tutorial_id (str): The ID of the tutorial
        
    Returns:
        list: List of dictionaries containing student information
    """
    conn = get_connection()
    # Use dictionary cursor to get results as dictionaries
    cursor = conn.cursor(dictionary=True)
    
    # Execute the query to find students in this tutorial
    cursor.execute("""
        SELECT u.id, u.name FROM assignments a
        JOIN users u ON a.user_id = u.id
        WHERE a.tutorial_id = %s AND u.role = 'student'
    """, (tutorial_id,))
    
    # Get all results
    results = cursor.fetchall()
    
    # Close the connection
    conn.close()
    
    # Return the list of students
    return results

def get_student_tutorials(student_id):
    """
    Get all tutorials a student is assigned to.
    
    Parameters:
        student_id (str): The ID of the student
        
    Returns:
        list: List of dictionaries containing tutorial information
    """
    conn = get_connection()
    # Use dictionary cursor to get results as dictionaries
    cursor = conn.cursor(dictionary=True)
    
    # Execute the query to find tutorials this student is assigned to
    cursor.execute("""
        SELECT t.id, t.name FROM assignments a
        JOIN tutorials t ON a.tutorial_id = t.id
        WHERE a.user_id = %s
    """, (student_id,))
    
    # Get all results
    results = cursor.fetchall()
    
    # Close the connection
    conn.close()
    
    # Return the list of tutorials
    return results

def start_chat(tutorial_id, tutor_id, duration):
    """Start a chat session for a tutorial."""
    # Check if chat already active
    if get_active_chat(tutorial_id):
        return None
        
    # Generate unique session ID
    chat_session_id = str(uuid.uuid4())
    
    # Get current timestamp for the start time
    start_time = time.time()
    end_time = start_time + (duration * 60)
    
    # Store in database with the session ID
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO active_chats (tutorial_id, tutor_id, start_time, end_time, chat_session_id) VALUES (%s, %s, %s, %s, %s)",
            (tutorial_id, tutor_id, start_time, end_time, chat_session_id)
        )
        conn.commit()
    
    return chat_session_id  # Return the generated session ID


def get_active_chat(tutorial_id):
    """Check if there's an active chat for a tutorial."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT tutor_id, start_time, end_time, chat_session_id FROM active_chats WHERE tutorial_id = %s", 
            (tutorial_id,)
        )
        chat = cursor.fetchone()
    
    if chat:
        return {
            'tutor_id': chat[0],
            'start_time': chat[1],
            'end_time': chat[2],
            'chat_session_id': chat[3]  # Include session ID in returned data
        }
    return None

def end_chat(tutorial_id):
    """End a chat session by removing it from active_chats."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM active_chats WHERE tutorial_id = %s", (tutorial_id,))
        conn.commit()
        return True
    except mysql.connector.Error as e:
        print("DB Error ending chat:", e)
        return False
    finally:
        conn.close()


# Add to db.py

def initialize_attendance_for_session(chat_session_id, tutorial_id):
    """Initialize attendance records for all students in a tutorial."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get all students assigned to this tutorial
    cursor.execute("""
        SELECT users.id, users.name FROM users 
        JOIN assignments ON users.id = assignments.user_id 
        WHERE assignments.tutorial_id = %s AND users.role = 'student'
    """, (tutorial_id,))
    
    students = cursor.fetchall()
    
    # Create initial attendance records for each student (absent by default)
    for student_id, _ in students:
        cursor.execute("""
            INSERT INTO attendance 
            (chat_session_id, tutorial_id, student_id, first_join_time, last_seen_time, is_present) 
            VALUES (%s, %s, %s, 0, 0, FALSE)
        """, (chat_session_id, tutorial_id, student_id))
    
    conn.commit()
    conn.close()

def mark_student_present(chat_session_id, tutorial_id, student_id):
    """Mark a student as present when they join the chat."""
    conn = get_connection()
    cursor = conn.cursor()
    current_time = time.time()
    
    # Check if student already has an attendance record
    cursor.execute("""
        SELECT is_present, first_join_time, total_duration_seconds 
        FROM attendance 
        WHERE chat_session_id = %s AND student_id = %s
    """, (chat_session_id, student_id))
    
    result = cursor.fetchone()
    
    if result:
        is_present, first_join_time, total_duration = result
        
        if not is_present:
            # Student is rejoining - just update status and last_seen_time
            # but keep the accumulated duration
            cursor.execute("""
                UPDATE attendance SET 
                is_present = TRUE, 
                last_seen_time = %s
                WHERE chat_session_id = %s AND student_id = %s
            """, (current_time, chat_session_id, student_id))
            
            # If first time joining, update first_join_time
            if first_join_time == 0:
                cursor.execute("""
                    UPDATE attendance SET first_join_time = %s
                    WHERE chat_session_id = %s AND student_id = %s
                """, (current_time, chat_session_id, student_id))
    else:
        # No record exists - create one
        cursor.execute("""
            INSERT INTO attendance 
            (chat_session_id, tutorial_id, student_id, first_join_time, last_seen_time, is_present, total_duration_seconds) 
            VALUES (%s, %s, %s, %s, %s, TRUE, 0)
        """, (chat_session_id, tutorial_id, student_id, current_time, current_time))
    
    conn.commit()
    conn.close()

def disconnect_attendance(chat_session_id, student_id):
    """Mark a student as absent when they leave and update duration."""
    conn = get_connection()
    cursor = conn.cursor()
    current_time = time.time()
    
    # Get current data
    cursor.execute("""
        SELECT last_seen_time, total_duration_seconds FROM attendance
        WHERE chat_session_id = %s AND student_id = %s AND is_present = TRUE
    """, (chat_session_id, student_id))
    
    result = cursor.fetchone()
    
    if result:
        last_seen_time, total_duration = result
        
        # Calculate additional duration since last update
        additional_duration = int(current_time - last_seen_time)
        new_total_duration = total_duration + additional_duration
        
        # Update record - CHANGE HERE: is_present = FALSE when disconnecting
        cursor.execute("""
            UPDATE attendance SET 
            is_present = FALSE, 
            total_duration_seconds = %s,
            last_seen_time = %s
            WHERE chat_session_id = %s AND student_id = %s
        """, (new_total_duration, current_time, chat_session_id, student_id))
    
    conn.commit()
    conn.close()

def get_attendance_for_session(chat_session_id):
    """Get attendance data for all students in a chat session."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    current_time = time.time()
    
    cursor.execute("""
        SELECT a.student_id, u.name as student_name, a.is_present, 
               a.first_join_time, a.last_seen_time, a.total_duration_seconds
        FROM attendance a
        JOIN users u ON a.student_id = u.id
        WHERE a.chat_session_id = %s
    """, (chat_session_id,))
    
    attendance_data = cursor.fetchall()
    
    # Calculate current duration for present students
    for record in attendance_data:
        if record['is_present']:
            additional_duration = int(current_time - record['last_seen_time'])
            record['current_duration'] = record['total_duration_seconds'] + additional_duration
        else:
            record['current_duration'] = record['total_duration_seconds']
    
    conn.close()
    return attendance_data


def generate_avatar_url(user_id, style="adventurer", format="png"):
    """
    Generate a DiceBear avatar URL for a user in PNG format.
    
    Parameters:
        user_id (str): Unique identifier for the user.
        style (str): Avatar style (default is 'bottts').
        format (str): Image format (default is 'png').
    
    Returns:
        str: URL of the generated avatar.
    """
    base_url = "https://api.dicebear.com/6.x"
    return f"{base_url}/{style}/{format}?seed={user_id}"



























def clear_active_chats():
    """Remove all active chat sessions from the database."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM active_chats")
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error clearing active chats: {e}")
        return False
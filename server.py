import os
from dotenv import load_dotenv
import google.generativeai as genai
from flask import Flask, request, jsonify
import mysql.connector
from flask_cors import CORS
import bcrypt

app = Flask(__name__)

# Configure CORS
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Load environment variables
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("Google Gemini API Key is missing. Set GEMINI_API_KEY in .env file.")

# Configure Google Gemini AI
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-flash")

# Database connection function
def connect_db():
    """Establish a connection to the MySQL database."""
    try:
        return mysql.connector.connect(
            host="localhost",
            user="root",
            password="nithees",
            database="student_career_db",
            port=3306
        )
    except mysql.connector.Error as err:
        print("Database Error:", err)
        return None

# ------------------ Authentication Routes ------------------
@app.route("/register", methods=["POST"])
def register():
    """Handle user registration with password hashing"""
    data = request.json
    try:
        hashed_pw = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())
        conn = connect_db()
        if conn is None:
            return jsonify({"error": "Database connection failed"}), 500
            
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (email, password_hash) VALUES (%s, %s)",
            (data['email'], hashed_pw.decode('utf-8')))
        user_id = cursor.lastrowid
        conn.commit()
        return jsonify({"success": True, "user_id": user_id}), 201
        
    except mysql.connector.IntegrityError:
        return jsonify({"error": "Email already exists"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route("/login", methods=["POST"])
def login():
    """Authenticate users and return session data"""
    data = request.json
    try:
        conn = connect_db()
        if conn is None:
            return jsonify({"error": "Database connection failed"}), 500
            
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, password_hash FROM users WHERE email = %s",
            (data['email'],))
        user = cursor.fetchone()
        
        if user and bcrypt.checkpw(data['password'].encode('utf-8'), user['password_hash'].encode('utf-8')):
            return jsonify({
                "success": True,
                "user_id": user['id'],
                "email": data['email']
            }), 200
        else:
            return jsonify({"error": "Invalid credentials"}), 401
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route("/check_profile/<int:user_id>")
def check_profile(user_id):
    """Check if user has completed their profile"""
    try:
        conn = connect_db()
        if conn is None:
            return jsonify({"error": "Database connection failed"}), 500
            
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM students WHERE user_id = %s", (user_id,))
        exists = cursor.fetchone() is not None
        return jsonify({"hasProfile": exists})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

# ------------------ Modified Existing Routes ------------------

@app.route("/api/user/<int:user_id>")
def get_user(user_id):
    try:
        conn = connect_db()
        if not conn:
            return jsonify({"error": "Database connection failed"}), 500
            
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT students.*, users.email 
            FROM students 
            JOIN users ON students.user_id = users.id 
            WHERE students.user_id = %s
        """, (user_id,))
        
        user_data = cursor.fetchone()
        if not user_data:
            return jsonify({"error": "User not found"}), 404
            
        return jsonify(user_data)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()
        
@app.route("/submit", methods=["POST"])
def submit():
    """Save profile data with user association"""
    data = request.json
    if 'user_id' not in data:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        conn = connect_db()
        if conn is None:
            return jsonify({"error": "Database connection failed"}), 500
            
        cursor = conn.cursor()

        # Check for existing profile
        cursor.execute("SELECT id FROM students WHERE user_id = %s", (data['user_id'],))
        if cursor.fetchone():
            return jsonify({"error": "Profile already exists"}), 400

        # Insert new profile
        sql = '''
            INSERT INTO students (
                name, email, highest_qualification, field_of_study, known_skills,
                career_interests, expected_salary, preferred_job_location,
                strengths, long_term_goals, user_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        '''
        values = (
            data["name"], data["email"], data["highest_qualification"],
            data["field_of_study"], data["known_skills"], data["career_interests"],
            data["expected_salary"], data["preferred_job_location"],
            data["strengths"], data["long_term_goals"], data["user_id"]
        )

        cursor.execute(sql, values)
        conn.commit()

        # Generate career analysis
        career_advice = analyze_career_path(data)
        return jsonify({"message": "Data saved successfully!", "career_advice": career_advice}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route("/career_summary", methods=["POST"])
def career_summary():
    """Generate career summary with user context"""
    data = request.json
    try:
        conn = connect_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM students 
            WHERE user_id = %s
        """, (data['user_id'],))
        student_data = cursor.fetchone()
        
        if not student_data:
            return jsonify({"error": "Profile not found"}), 404
            
        career_summary = analyze_career_path(student_data)
        return jsonify({"summary": career_summary})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

@app.route("/chatbot", methods=["POST"])
def chatbot():
    """Handle chatbot requests with user context"""
    data = request.json
    user_id = data.get("user_id")
    user_message = data.get("message", "").strip()

    if not user_id:
        return jsonify({"response": "User identification missing."}), 401

    try:
        conn = connect_db()
        cursor = conn.cursor(dictionary=True)
        
        # Get complete user profile
        cursor.execute("""
            SELECT s.*, u.email 
            FROM students s
            JOIN users u ON s.user_id = u.id
            WHERE s.user_id = %s
        """, (user_id,))
        user_data = cursor.fetchone()

        # Build AI prompt
        prompt = f"""
        ### User Profile:
        - Name: {user_data.get('name','')}
        -Email: {user_data.get('email','')}
        - Qualification: {user_data.get('highest_qualification','')}
        - Field of Study: {user_data.get('field_of_study','')}
        - Skills: {user_data.get('known_skills','')}
        - Career Interests: {user_data.get('career_interests','')}
        - Strengths: {user_data.get('strengths','')}
        - Goals: {user_data.get('long_term_goals','')}

        ### Query:
        {user_message}

        ### Response Guidelines:
        1. Only respond to queries related to career development, education, skills, or professional growth.
        2. If the query is **not relevant to career** (e.g., personal questions, jokes, casual talk), respond with:
             - "I'm here to assist only with career development. Please ask questions related to your professional growth."
        3. Do not mention user's profile unless relevant to the career question.
        4. Keep responses concise (under 100 words), professional, and helpful.
        5. Avoid any unrelated, personal, or humorous responses.
        """

        # Generate response
        chat = model.start_chat(history=[])
        response = chat.send_message(prompt)
        return jsonify({"response": response.text.strip()})
        
    except Exception as e:
        return jsonify({"response": f"Error: {str(e)}"}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()
  
# ------------------ Helper Functions ------------------
def analyze_career_path(student_data):
    """Generate career advice using Gemini AI"""
    prompt = f"""
    Analyze this student profile and provide career recommendations:
    {student_data}
    Focus on matching skills to industries. Keep response under 100 words.
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Career analysis error: {str(e)}"

if __name__ == "__main__":
    app.run(debug=True)
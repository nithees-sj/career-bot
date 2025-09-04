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

# Database configuration (via environment variables, with sensible defaults for local dev)
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "nithees")
DB_NAME = os.getenv("DB_NAME", "student_career_db")
DB_PORT = int(os.getenv("DB_PORT", "3306"))

# Database connection function
def connect_db():
    """Establish a connection to the MySQL database."""
    try:
        return mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT
        )
    except mysql.connector.Error as err:
        print("Database Error:", err)
        return None

def init_db():
    """Create required tables if they do not already exist (idempotent)."""
    conn = None
    cursor = None
    try:
        conn = connect_db()
        if conn is None:
            print("[init_db] Skipped: database connection failed")
            return
        cursor = conn.cursor()

        # Core tables: users, students, doubts, doubt_messages
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL UNIQUE,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) NOT NULL,
                highest_qualification VARCHAR(255),
                field_of_study VARCHAR(255),
                known_skills TEXT,
                career_interests TEXT,
                expected_salary VARCHAR(50),
                preferred_job_location VARCHAR(255),
                strengths TEXT,
                long_term_goals TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                CONSTRAINT fk_students_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS doubts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                title VARCHAR(255) NOT NULL,
                status ENUM('open','resolved') NOT NULL DEFAULT 'open',
                resolution_notes TEXT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                INDEX idx_doubts_user (user_id),
                CONSTRAINT fk_doubts_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS doubt_messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                doubt_id INT NOT NULL,
                sender ENUM('user','bot','mentor') NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_doubt_id (doubt_id),
                CONSTRAINT fk_doubt_messages_doubt FOREIGN KEY (doubt_id) REFERENCES doubts(id) ON DELETE CASCADE ON UPDATE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )

        conn.commit()
    except Exception as e:
        print("[init_db] Error:", str(e))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

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
 
# ------------------ Doubt Clearing System ------------------
@app.route("/api/doubts", methods=["GET", "POST"])
def doubts():
    """Create a new doubt or list doubts for a user."""
    if request.method == "POST":
        data = request.json or {}
        user_id = data.get("user_id")
        try:
            user_id = int(user_id)
        except (TypeError, ValueError):
            return jsonify({"error": "Unauthorized"}), 401
        title = (data.get("title") or "").strip()
        question = (data.get("question") or "").strip()

        if not user_id:
            return jsonify({"error": "Unauthorized"}), 401
        if not title or not question:
            return jsonify({"error": "Both title and question are required"}), 400

        try:
            conn = connect_db()
            if conn is None:
                return jsonify({"error": "Database connection failed"}), 500
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO doubts (user_id, title) VALUES (%s, %s)",
                (user_id, title)
            )
            doubt_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO doubt_messages (doubt_id, sender, message) VALUES (%s, %s, %s)",
                (doubt_id, 'user', question)
            )
            # Auto-generate an initial AI response for the created doubt
            try:
                cursor_dict = conn.cursor(dictionary=True)
                # Fetch user profile for context
                cursor_dict.execute(
                    """
                    SELECT s.*, u.email
                    FROM students s
                    JOIN users u ON s.user_id = u.id
                    WHERE s.user_id = %s
                    """,
                    (user_id,),
                )
                user_data = cursor_dict.fetchone() or {}

                # Fetch the current thread (includes the initial question)
                cursor_dict.execute(
                    "SELECT sender, message FROM doubt_messages WHERE doubt_id = %s ORDER BY created_at ASC",
                    (doubt_id,),
                )
                msgs = cursor_dict.fetchall() or []
                recent_str = "\n".join([f"{m['sender']}: {m['message']}" for m in msgs])

                prompt = f"""
You are an expert academic mentor for students. Answer clearly, step-by-step, and in GitHub-Flavored Markdown.

Doubt Title: {title}
Thread So Far:
{recent_str}

Response rules:
- Output strictly in Markdown (use headings, lists, code blocks when helpful).
- Keep responses under 150 words.
- Do not ask follow-up questions for the initial doubt response; provide your best direct answer.
- Be professional and encouraging.
"""
                chat = model.start_chat(history=[])
                ai_response = chat.send_message(prompt)
                ai_text = (ai_response.text or "").strip()
                if ai_text:
                    cursor.execute(
                        "INSERT INTO doubt_messages (doubt_id, sender, message) VALUES (%s, %s, %s)",
                        (doubt_id, 'bot', ai_text),
                    )
            except Exception as _e:
                # Persist the AI error as a bot message to inform the user
                err_text = f"AI error: {str(_e)}"
                cursor.execute(
                    "INSERT INTO doubt_messages (doubt_id, sender, message) VALUES (%s, %s, %s)",
                    (doubt_id, 'bot', err_text),
                )

            conn.commit()
            return jsonify({"success": True, "doubt_id": doubt_id}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        finally:
            if 'cursor' in locals(): cursor.close()
            if 'cursor_dict' in locals(): cursor_dict.close()
            if 'conn' in locals(): conn.close()

    # GET
    user_id = request.args.get("user_id", type=int)
    status = request.args.get("status")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        conn = connect_db()
        if conn is None:
            return jsonify({"error": "Database connection failed"}), 500
        cursor = conn.cursor(dictionary=True)

        if status in ("open", "resolved"):
            cursor.execute(
                """
                SELECT id, title, status, created_at, updated_at
                FROM doubts
                WHERE user_id = %s AND status = %s
                ORDER BY updated_at DESC
                """,
                (user_id, status),
            )
        else:
            cursor.execute(
                """
                SELECT id, title, status, created_at, updated_at
                FROM doubts
                WHERE user_id = %s
                ORDER BY updated_at DESC
                """,
                (user_id,),
            )
        rows = cursor.fetchall()
        return jsonify({"doubts": rows})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()


@app.route("/api/doubts/<int:doubt_id>", methods=["GET"])
def get_doubt(doubt_id: int):
    """Get a single doubt with its message thread."""
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        conn = connect_db()
        if conn is None:
            return jsonify({"error": "Database connection failed"}), 500
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT id, user_id, title, status, resolution_notes, created_at, updated_at FROM doubts WHERE id = %s",
            (doubt_id,),
        )
        doubt = cursor.fetchone()
        if not doubt:
            return jsonify({"error": "Doubt not found"}), 404
        if doubt["user_id"] != user_id:
            return jsonify({"error": "Forbidden"}), 403

        cursor.execute(
            "SELECT id, sender, message, created_at FROM doubt_messages WHERE doubt_id = %s ORDER BY created_at ASC",
            (doubt_id,),
        )
        messages = cursor.fetchall()
        return jsonify({"doubt": doubt, "messages": messages})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()


@app.route("/api/doubts/<int:doubt_id>/reply", methods=["POST"])
def reply_doubt(doubt_id: int):
    """Append a reply to a doubt; optionally generate an AI answer as well."""
    data = request.json or {}
    user_id = data.get("user_id")
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Unauthorized"}), 401
    message = (data.get("message") or "").strip()
    use_ai = bool(data.get("use_ai", False))
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    if not message:
        return jsonify({"error": "Message is required"}), 400
    try:
        conn = connect_db()
        if conn is None:
            return jsonify({"error": "Database connection failed"}), 500
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id, user_id, title, status FROM doubts WHERE id = %s", (doubt_id,))
        doubt = cursor.fetchone()
        if not doubt:
            return jsonify({"error": "Doubt not found"}), 404
        if int(doubt["user_id"]) != int(user_id):
            return jsonify({"error": "Forbidden"}), 403

        # Insert the user's message
        cursor2 = conn.cursor()
        cursor2.execute(
            "INSERT INTO doubt_messages (doubt_id, sender, message) VALUES (%s, %s, %s)",
            (doubt_id, 'user', message),
        )

        ai_response_text = None
        if use_ai:
            # Fetch user profile for better context
            cursor.execute(
                """
                SELECT s.*, u.email
                FROM students s
                JOIN users u ON s.user_id = u.id
                WHERE s.user_id = %s
                """,
                (user_id,),
            )
            user_data = cursor.fetchone() or {}

            # Get recent messages for context (last 10)
            cursor.execute(
                """
                SELECT sender, message FROM doubt_messages
                WHERE doubt_id = %s
                ORDER BY created_at DESC
                LIMIT 10
                """,
                (doubt_id,),
            )
            recent = cursor.fetchall() or []
            recent.reverse()

            recent_str = "\n".join([f"{m['sender']}: {m['message']}" for m in recent])
            prompt = f"""
You are an expert academic mentor for students. Answer clearly, step-by-step, and in GitHub-Flavored Markdown.

Student Profile:
Name: {user_data.get('name','')}
Email: {user_data.get('email','')}
Qualification: {user_data.get('highest_qualification','')}
Field of Study: {user_data.get('field_of_study','')}
Skills: {user_data.get('known_skills','')}
Interests: {user_data.get('career_interests','')}
Strengths: {user_data.get('strengths','')}
Goals: {user_data.get('long_term_goals','')}

Doubt Title: {doubt.get('title','')}
Thread So Far:
{recent_str}

Latest Question: {message}

Response rules:
- Output strictly in Markdown (use headings, lists, code blocks when helpful).
- Keep responses under 150 words.
- Do not ask follow-up questions; provide your best direct answer.
- Be professional and encouraging.
"""
            try:
                chat = model.start_chat(history=[])
                ai_response = chat.send_message(prompt)
                ai_response_text = (ai_response.text or "").strip()
                if ai_response_text:
                    cursor2.execute(
                        "INSERT INTO doubt_messages (doubt_id, sender, message) VALUES (%s, %s, %s)",
                        (doubt_id, 'bot', ai_response_text),
                    )
            except Exception as e:
                ai_response_text = f"AI error: {str(e)}"
                cursor2.execute(
                    "INSERT INTO doubt_messages (doubt_id, sender, message) VALUES (%s, %s, %s)",
                    (doubt_id, 'bot', ai_response_text),
                )

        conn.commit()

        # Return updated messages
        cursor.execute(
            "SELECT id, sender, message, created_at FROM doubt_messages WHERE doubt_id = %s ORDER BY created_at ASC",
            (doubt_id,),
        )
        messages = cursor.fetchall()
        return jsonify({"success": True, "messages": messages, "ai": ai_response_text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'cursor2' in locals(): cursor2.close()
        if 'conn' in locals(): conn.close()


@app.route("/api/doubts/<int:doubt_id>/resolve", methods=["POST"])
def resolve_doubt(doubt_id: int):
    data = request.json or {}
    user_id = data.get("user_id")
    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return jsonify({"error": "Unauthorized"}), 401
    resolution_notes = (data.get("resolution_notes") or "").strip() or None
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        conn = connect_db()
        if conn is None:
            return jsonify({"error": "Database connection failed"}), 500
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id, user_id, status FROM doubts WHERE id = %s", (doubt_id,))
        doubt = cursor.fetchone()
        if not doubt:
            return jsonify({"error": "Doubt not found"}), 404
        if int(doubt["user_id"]) != int(user_id):
            return jsonify({"error": "Forbidden"}), 403

        cursor2 = conn.cursor()
        cursor2.execute(
            "UPDATE doubts SET status = 'resolved', resolution_notes = %s WHERE id = %s",
            (resolution_notes, doubt_id),
        )
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'cursor2' in locals(): cursor2.close()
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
    # Initialize database tables at startup (safe to run repeatedly)
    init_db()

    # Debug flag can be toggled via environment variable
    debug_flag = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    app.run(debug=debug_flag)
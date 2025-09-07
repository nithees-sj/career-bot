# Career Bot – Server (Backend)

This is the **backend** of the Career Bot project.  
It is built with **Flask (Python)** and handles API requests, logic, and environment-based configurations.

---

## Features
- Backend built with **Flask (Python)**  
- Environment variables stored in **.env** for security  
- Dependencies managed through **requirements.txt**  

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/nithees-sj/career_bot.git
cd career_bot
```

### 2. Install Python Dependencies

Ensure you have Python and `pip` installed. Then run:

```bash
pip install -r requirements.txt
```

### 3. Set Up Environment Variables

Create a `.env` file in the root directory and add the following:

```env
GEMINI_API_KEY=AIzaSyDti3nTKOlIXbHhoyxWct1qt4uxo3VFPEk
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "root"
DB_NAME = "student_career_db"
DB_PORT = 3306
```

Replace `<your_gemini_api_key>` with your actual Gemini 1.5 Flash key.

> 📌 You can generate your Gemini API Key from:  
> **https://aistudio.google.com/app/apikey**

### 4. Run the Application

#### Activate your virtual environment:

```bash
source myenv/bin/activate
```

#### Start the backend server:

```bash
python3 server.py
```

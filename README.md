# Career Bot

Welcome to **Novard**, a personalized AI-powered career consultant chatbot built especially for **school students and users across all age categories**. Novard helps guide users through academic and career choices by offering domain-specific advice based on user data and AI-driven insights.

---

## Features

- **AI Chatbot (Gemini 1.5 Flash)**  
  Interact with an intelligent chatbot that gives **personalized career suggestions** based on your interests and background.

- **User Registration & Profiling**  
  Collects and stores user details securely to tailor responses for better career guidance.

- **School-to-Domain Guidance**  
  Helps users understand which domains and career paths align with their strengths and preferences – starting from school level!

- **Database-Driven Suggestions**  
  User data is saved in a backend database to continuously refine recommendations and offer a seamless experience.

- **Doubt Clearing System**  
  Create doubts, chat in a threaded view, get optional AI-assisted answers, and mark doubts as resolved. Accessible from the chatbot page via a Chat/Doubts mode switch.

---

## Tech Stack

### Frontend
- HTML  
- CSS  
- JavaScript  

### Backend
- Python (Flask)  
- MySQL  

### AI Integration
- Gemini 1.5 Flash (via API Key)

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

#### Launch the frontend:

Open `index.html` and click **Go Live** using a Live Server extension in VS Code.

---

## Usage

- **API Key**: Generate your Gemini 1.5 Flash API key and paste it in your `.env` file.
- **User Registration**: Register and enter your personal details to receive personalized career suggestions.
- **Chatbot Interaction**: Ask career-related questions and receive tailored responses from the AI.
- **Doubts**: Switch to the Doubts tab, create a doubt (title + question), chat on the thread, optionally check "Get AI help" for AI guidance, and resolve when done. All doubts are saved and can be filtered by status.

---

## Contributing

Contributions are welcome!  
If you have suggestions for improvements or new features, feel free to **fork the repository** and submit a **pull request**.

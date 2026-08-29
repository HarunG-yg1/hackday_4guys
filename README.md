# 🚀 HackDay 2026 - AI-Powered Expense & Budget Tracker

An intelligent event expense management system built for **HackDay 2026**. This application allows organizers to set event budgets, log expenses, run automated multi-modal receipt parsing via **Google Gemini 3.6 Flash OCR**, and view real-time spending analytics.

---

## ✨ Features

* **Event Budget Management**: Set up custom budgets and define alert thresholds (e.g., notify when 80% of budget is spent).
* **AI Receipt OCR (`Gemini 3.6 Flash`)**: Extract merchant name, total amount, category, and date automatically from receipt images (`.jpg`, `.jpeg`, `.png`, `.webp`).
* **Auto-Log OCR Endpoint**: Scan a receipt image and immediately store the parsed expense directly into the database in a single step.
* **Category Spending Analytics**: Real-time spending breakdowns and percentage distributions per category for frontend chart integration.

---

## 🛠️ Tech Stack

* **Backend Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.12)
* **ASGI Server**: [Uvicorn](https://www.uvicorn.org/)
* **Database**: [Supabase](https://supabase.com/) (PostgreSQL)
* **AI Engine**: [Google Gemini API](https://ai.google.dev/) (`gemini-3.6-flash`)
* **Data Validation**: Pydantic v2

---

## 📦 Project Setup & Installation

### 1. Prerequisites
* Python 3.10+ installed
* Supabase project credentials (URL & Service/Anon Key)
* Gemini API Key

### 2. Clone the Repository
```bash
git clone <your-repo-url>
cd hackday_4guys

### 3. Setup Virtual Environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate

### 4. Install Dependencies
pip install -r requirements.txt

### 5. Configure Environment Variables
Create a .env file in the root folder based on .env.example:
SUPABASE_URL="[https://your-supabase-project.supabase.co](https://your-supabase-project.supabase.co)"
SUPABASE_KEY="your-supabase-anon-or-service-key"
GEMINI_API_KEY="your-gemini-api-key"

### Running the Application
Start the development server with auto-reload enabled:
uvicorn main:app --reload


The server will start at http://127.0.0.1:8000.

Interactive API Documentation (Swagger UI) is available at:

http://127.0.0.1:8000/docs

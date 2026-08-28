# FastAPI Backend Setup

This guide explains how to set up the FastAPI backend locally.

## 1. Prerequisites

Make sure Python 3 is installed:

```bash
python3 --version
```

If Python is not installed on Ubuntu/Debian:

```bash
sudo apt update
sudo apt install python3 python3-full
```

---

## 2. Clone the Repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd <YOUR_PROJECT_FOLDER>
```

---

## 3. Create a Virtual Environment

We use a virtual environment so that Python packages for this project do not interfere with the system Python or other projects.

```bash
python3 -m venv .venv
```

This creates:

```text
project/
├── .venv/
└── ...
```

> **Note:** `.venv` should not be committed to Git.

---

## 4. Activate the Virtual Environment

### Linux / macOS

```bash
source .venv/bin/activate
```

### Windows

**Command Prompt:**

```cmd
.venv\Scripts\activate
```

**PowerShell:**

```powershell
.venv\Scripts\Activate.ps1
```

After activation, you should see `(.venv)` at the beginning of your terminal:

```text
(.venv) user@computer:~/project$
```

---

## 5. Install Dependencies

With the virtual environment activated:

```bash
pip install fastapi uvicorn
```

If the project already contains a `requirements.txt`, use:

```bash
pip install -r requirements.txt
```

---

## 6. Run the FastAPI Server

If the main application is in `main.py` and the FastAPI instance is called `app`:

```bash
uvicorn main:app --reload
```

You should see:

```text
Uvicorn running on http://127.0.0.1:8000
```

Open:

**http://127.0.0.1:8000**

---

## 7. API Documentation

FastAPI automatically generates interactive API documentation.

### Swagger UI

Open:

```text
http://127.0.0.1:8000/docs
```

### ReDoc

Open:

```text
http://127.0.0.1:8000/redoc
```

The `/docs` page can be used to test API endpoints without needing Postman.

---

## 8. Installing a New Package

If you add a new Python package:

```bash
pip install <package-name>
```

For example:

```bash
pip install sqlalchemy
```

After installing a package, update `requirements.txt`:

```bash
pip freeze > requirements.txt
```

Then commit the updated `requirements.txt`:

```bash
git add requirements.txt
git commit -m "Update dependencies"
git push
```

---

## 9. Working on the Project Again

Every time you open a new terminal, you need to activate the virtual environment again:

```bash
cd <YOUR_PROJECT_FOLDER>
source .venv/bin/activate
```

You **do not need to reinstall FastAPI** every time.

To leave the virtual environment:

```bash
deactivate
```

---

## 10. Git Configuration

Do **not** commit `.venv` to GitHub.

Add this to `.gitignore`:

```gitignore
.venv/
__pycache__/
*.pyc
.env
```

Your repository should look something like:

```text
project/
├── .venv/              # Local only - NOT committed
├── main.py
├── requirements.txt
├── .gitignore
└── README.md
```

### Quick Setup

For Linux/macOS, after cloning the repository:

```bash
cd <YOUR_PROJECT_FOLDER>
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Then visit:

```text
http://127.0.0.1:8000/docs
```

import io
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google import genai
from google.genai import types
from PIL import Image
from pydantic import BaseModel
from supabase import Client, create_client

# ------------------------------------------------------------------------------
# 1. Environment & Path Setup
# ------------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path, override=True)

app = FastAPI(title="ClubVault API", version="1.0.0")

# Mount static assets if folder exists
static_dir = BASE_DIR / "app" / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

templates_dir = BASE_DIR / "app" / "templates"
templates = Jinja2Templates(directory=templates_dir) if templates_dir.exists() else None

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

<<<<<<< HEAD


# ------------------------------------------------------------------------------
# 1. Environment & Client Setup
# ------------------------------------------------------------------------------
=======
# Supabase Initialization
>>>>>>> fb2978e07f6b448ffdc344de6cdc39986b8d8dd1
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in .env file.")

supabase: Client = create_client(supabase_url, supabase_key)

# Gemini Initialization
gemini_api_key = os.getenv("GEMINI_API_KEY")
gemini_client = genai.Client(api_key=gemini_api_key) if gemini_api_key else None


# ------------------------------------------------------------------------------
# 2. Pydantic Schemas
# ------------------------------------------------------------------------------
class BudgetCreate(BaseModel):
    event_name: str
    total_budget: float
    alert_threshold: float = 0.8


class ExpenseCreate(BaseModel):
    budget_id: str
    title: str
    amount: float
    category: str
    receipt_url: Optional[str] = None


class ReceiptScanResult(BaseModel):
    merchant: Optional[str] = None
    amount: float
    category: str
    date: Optional[str] = None
    confidence_score: float = 1.0


class CategoryBreakdownItem(BaseModel):
    category: str
    total_spent: float
    percentage: float


class CategoryBreakdownResponse(BaseModel):
    budget_id: str
    total_spent: float
    categories: list[CategoryBreakdownItem]


class QuotationCreate(BaseModel):
    budget_id: str
    vendor_name: str
    estimated_amount: float
    description: Optional[str] = None


class ReimbursementCreate(BaseModel):
    expense_id: str
    claimant_name: str
    status: str = "Pending"


# ------------------------------------------------------------------------------
# 3. Safe Template Renderer (Prevents 500 errors if Teammate hasn't made HTML file)
# ------------------------------------------------------------------------------
def render_page_safely(request: Request, template_name: str, fallback_title: str):
    if templates:
        try:
            return templates.TemplateResponse(request=request, name=template_name)
        except Exception:
            pass
    
    # Fallback response if template isn't finished by teammate
    return HTMLResponse(content=f"""
    <!DOCTYPE html>
    <html>
    <head><title>{fallback_title} - ClubVault</title></head>
    <body style="font-family: sans-serif; padding: 40px; text-align: center;">
        <h1>{fallback_title} Module</h1>
        <p>Backend endpoint ready! Teammate's UI template (<code>{template_name}</code>) is pending integration.</p>
        <p><a href="/docs">View API Documentation & Test Endpoints</a></p>
    </body>
    </html>
    """)


# ------------------------------------------------------------------------------
# 4. Frontend HTML Page Routes
# ------------------------------------------------------------------------------
@app.get("/")
@app.get("/dashboard")
async def render_dashboard(request: Request):
    return render_page_safely(request, "dashboard.html", "Dashboard")


@app.get("/expenses-page")
async def render_expenses(request: Request):
    return render_page_safely(request, "expenses.html", "Expenses")


@app.get("/quotations-page")
async def render_quotations(request: Request):
    return render_page_safely(request, "quotations.html", "Quotations")


@app.get("/reimbursements-page")
async def render_reimbursements(request: Request):
    return render_page_safely(request, "reimbursements.html", "Reimbursements")


# ------------------------------------------------------------------------------
# 5. Budgets & Spending Alerts
# ------------------------------------------------------------------------------
@app.post("/budgets", status_code=status.HTTP_201_CREATED)
def create_budget(budget: BudgetCreate):
    try:
        response = supabase.table("budgets").insert(budget.model_dump()).execute()
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/budgets/{budget_id}")
def get_budget_summary(budget_id: str):
    try:
        budget_resp = supabase.table("budgets").select("*").eq("id", budget_id).execute()
        if not budget_resp.data:
            raise HTTPException(status_code=404, detail="Budget not found")
        budget = budget_resp.data[0]

        expenses_resp = supabase.table("expenses").select("amount").eq("budget_id", budget_id).execute()
        total_spent = sum([item["amount"] for item in expenses_resp.data])

        total_budget = budget["total_budget"]
        alert_threshold = budget.get("alert_threshold", 0.8)
        remaining = total_budget - total_spent
        is_alert = total_spent >= (total_budget * alert_threshold)

        return {
            "budget": budget,
            "total_spent": total_spent,
            "remaining_budget": remaining,
            "alert_triggered": is_alert,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/budgets/{budget_id}/analytics", response_model=CategoryBreakdownResponse)
def get_category_analytics(budget_id: str):
    try:
        res = supabase.table("expenses").select("amount, category").eq("budget_id", budget_id).execute()
        expenses = res.data or []

        total_spent = sum(e["amount"] for e in expenses)
        
        category_totals = {}
        for e in expenses:
            cat = e.get("category") or "Uncategorized"
            category_totals[cat] = category_totals.get(cat, 0.0) + float(e["amount"])

        breakdown = []
        for cat, amount in category_totals.items():
            pct = round((amount / total_spent * 100), 2) if total_spent > 0 else 0.0
            breakdown.append({
                "category": cat,
                "total_spent": round(amount, 2),
                "percentage": pct
            })

        return {
            "budget_id": budget_id,
            "total_spent": round(total_spent, 2),
            "categories": breakdown
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------------------
# 6. Expenses & Gemini OCR Scanner
# ------------------------------------------------------------------------------
@app.post("/expenses", status_code=status.HTTP_201_CREATED)
def create_expense(expense: ExpenseCreate):
    try:
        response = supabase.table("expenses").insert(expense.model_dump()).execute()
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/budgets/{budget_id}/expenses")
def list_expenses(budget_id: str):
    try:
        response = supabase.table("expenses").select("*").eq("budget_id", budget_id).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/expenses/scan", response_model=ReceiptScanResult)
async def scan_receipt(file: UploadFile = File(...)):
    if not gemini_client:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GEMINI_API_KEY environment variable is missing in .env.",
        )

    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Upload a JPEG, PNG, or WebP image.",
        )

    try:
        await file.seek(0)
        contents = await file.read()
        image = Image.open(io.BytesIO(contents))

        prompt = (
            "Analyze this receipt image and extract structured financial data. "
            "Identify the merchant/vendor name, the total grand amount paid, "
            "a suitable expense category (e.g., Food & Beverage, Venue, Marketing, Supplies, Utilities), "
            "and the transaction date if visible."
        )

        response = gemini_client.models.generate_content(
            model="gemini-3.6-flash",
            contents=[image, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ReceiptScanResult,
                temperature=0.1,
            ),
        )

        parsed_data = ReceiptScanResult.model_validate_json(response.text)
        return parsed_data

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process receipt: {str(e)}",
        )


@app.post("/expenses/scan-and-save", response_model=ExpenseCreate, status_code=201)
async def scan_and_save_receipt(
    budget_id: str = Form(...),
    file: UploadFile = File(...)
):
    budget_res = supabase.table("budgets").select("id").eq("id", budget_id).execute()
    if not budget_res.data:
        raise HTTPException(status_code=404, detail="Budget not found")

    ocr_result = await scan_receipt(file)

    expense_payload = {
        "budget_id": budget_id,
        "title": ocr_result.merchant or "Unrecognized Merchant",
        "amount": ocr_result.amount,
        "category": ocr_result.category or "General",
        "receipt_url": None
    }
    
    res = supabase.table("expenses").insert(expense_payload).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to save scanned expense")
        
    return res.data[0]


# ------------------------------------------------------------------------------
# 7. Quotations & Reimbursements Endpoints
# ------------------------------------------------------------------------------
@app.post("/quotations", status_code=status.HTTP_201_CREATED)
def create_quotation(quote: QuotationCreate):
    try:
        res = supabase.table("quotations").insert(quote.model_dump()).execute()
        return res.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/budgets/{budget_id}/quotations")
def list_quotations(budget_id: str):
    try:
        res = supabase.table("quotations").select("*").eq("budget_id", budget_id).execute()
        return res.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reimbursements", status_code=status.HTTP_201_CREATED)
def create_reimbursement(claim: ReimbursementCreate):
    try:
        res = supabase.table("reimbursements").insert(claim.model_dump()).execute()
        return res.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/reimbursements")
def list_reimbursements():
    try:
        res = supabase.table("reimbursements").select("*").execute()
        return res.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
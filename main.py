import io
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types
from PIL import Image
from pydantic import BaseModel
from supabase import Client, create_client

# Force load .env from absolute path relative to main.py
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

app = FastAPI(title="ClubVault API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# ------------------------------------------------------------------------------
# 1. Environment & Client Setup
# ------------------------------------------------------------------------------
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in .env file.")

supabase: Client = create_client(supabase_url, supabase_key)

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
    confidence_score: float


class CategoryBreakdownItem(BaseModel):
    category: str
    total_spent: float
    percentage: float


class CategoryBreakdownResponse(BaseModel):
    budget_id: str
    total_spent: float
    categories: list[CategoryBreakdownItem]


# ------------------------------------------------------------------------------
# 3. Budget & Expense Endpoints
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


@app.post("/expenses/scan-and-save", response_model=ExpenseCreate, status_code=201)
async def scan_and_save_receipt(
    budget_id: str = Form(...),
    file: UploadFile = File(...)
):
    """Scan receipt using Gemini OCR and immediately save it into Supabase."""
    # 1. Verify budget exists
    budget_res = supabase.table("budgets").select("id").eq("id", budget_id).execute()
    if not budget_res.data:
        raise HTTPException(status_code=404, detail="Budget not found")

    # 2. Extract OCR data with Gemini
    ocr_result = await scan_receipt(file)

    # 3. Insert directly into Supabase
    expense_payload = {
        "budget_id": budget_id,
        "title": ocr_result.merchant,
        "amount": ocr_result.amount,
        "category": ocr_result.category,
        "receipt_url": None
    }
    
    res = supabase.table("expenses").insert(expense_payload).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to save scanned expense")
        
    return res.data[0]


@app.get("/budgets/{budget_id}/analytics", response_model=CategoryBreakdownResponse)
def get_category_analytics(budget_id: str):
    """Calculate spending per category and percentage breakdown for charts."""
    # 1. Fetch expenses for budget
    res = supabase.table("expenses").select("amount, category").eq("budget_id", budget_id).execute()
    expenses = res.data or []

    total_spent = sum(e["amount"] for e in expenses)
    
    # 2. Group totals by category
    category_totals = {}
    for e in expenses:
        cat = e.get("category") or "Uncategorized"
        category_totals[cat] = category_totals.get(cat, 0.0) + float(e["amount"])

    # 3. Build breakdown output
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


# ------------------------------------------------------------------------------
# 4. Gemini OCR Receipt Scanner Endpoint
# ------------------------------------------------------------------------------
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
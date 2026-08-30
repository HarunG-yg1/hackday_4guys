import io
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from google import genai
from google.genai import types
from PIL import Image
from pydantic import BaseModel
from supabase import Client, create_client

import shutil
import os
from fastapi import UploadFile, File, Form

import json
from google.genai import types


# ------------------------------------------------------------------------------
# 1. Environment & Path Setup
# ------------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path, override=True)
# Ensure a folder exists to save uploaded receipts locally for the hackathon
UPLOAD_DIR = "app/static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

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

# Supabase Initialization
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
def render_page_safely(request: Request, template_name: str, fallback_title: str, context: dict = None):
    if templates:
        try:
            render_context = {"request": request}
            if context:
                render_context.update(context)
            return templates.TemplateResponse(name=template_name, context=render_context)
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
async def dashboard_page(request: Request):
    # Example logic using your database models:
    # db = next(get_db())
    # expenses = db.query(Expense).all()
    # budgets = db.query(Budget).all()

    # --- Sample calculation logic ---
    total_spending = sum(exp.amount for exp in expenses) if 'expenses' in locals() else 934.50
    monthly_limit = monthly_budget.total_limit if 'monthly_budget' in locals() else 1500.00 # fallback # Replace with dynamic sum from your budget table
    
    # Calculate category breakdowns dynamically
    category_totals = {}
    if 'expenses' in locals():
        for exp in expenses:
            cat = exp.category_name or "Other"
            category_totals[cat] = category_totals.get(cat, 0.0) + exp.amount

    return templates.TemplateResponse(
        request, 
        "dashboard.html", 
        {
            "total_spending": total_spending,
            "monthly_limit": monthly_limit,
            "spending_percentage": round((total_spending / monthly_limit) * 100, 1) if monthly_limit > 0 else 0,
            "category_totals": category_totals,
            "recent_expenses": expenses[:5] if 'expenses' in locals() else []
        }
    )


@app.get("/expenses-page")
async def expenses_page(request: Request, event_id: str | None = None):
    expenses = []
    categories = []
    active_event = None
    
    # Fetch all events so the dropdown can always show them
    events_res = supabase.table("events").select("*").execute()
    all_events = events_res.data or []
    
    if event_id and event_id != "None":
        # Find the currently active event object
        active_event = next((ev for ev in all_events if str(ev["id"]) == str(event_id)), None)
        
        expenses_res = supabase.table("expenses").select("*, category_budgets(category_name)").eq("event_id", event_id).execute()
        expenses = expenses_res.data or []
        
        categories_res = supabase.table("category_budgets").select("*").eq("event_id", event_id).execute()
        categories = categories_res.data or []

    # Calculate totals
    total_budget = float(active_event["total_budget"]) if active_event and active_event.get("total_budget") else 0.0
    total_spent = sum(float(exp.get("amount", 0)) for exp in expenses)
    remaining_funds = total_budget - total_spent
    utilized_percentage = (total_spent / total_budget * 100) if total_budget > 0 else 0.0

    return templates.TemplateResponse(
        request, 
        "expenses.html", 
        {
            "expenses": expenses,
            "categories": categories,
            "event_id": event_id,
            "all_events": all_events,
            "active_event": active_event,
            "total_budget": total_budget,
            "total_spent": total_spent,
            "remaining_funds": remaining_funds,
            "utilized_percentage": utilized_percentage
        }
    )

@app.post("/add-expense")
async def add_expense(
    event_id: str | None = Form(None),
    expense_name: str | None = Form(""),
    amount: float | None = Form(0.00),
    category_id: str | None = Form(None),
    receipt: UploadFile | None = File(None)
):
    receipt_url = None
    
    if receipt and receipt.filename:
        file_path = os.path.join(UPLOAD_DIR, receipt.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(receipt.file, buffer)
        receipt_url = f"/static/uploads/{receipt.filename}"

    # Safely convert "None" strings or empty inputs to actual Python None (SQL NULL)
    clean_event_id = event_id if event_id and event_id != "None" else None
    clean_category_id = category_id if category_id and category_id != "None" else None

    supabase.table("expenses").insert({
        "event_id": clean_event_id,
        "category_id": clean_category_id,
        "expense_name": expense_name,
        "amount": amount,
        "receipt_url": receipt_url
    }).execute()
    
    return RedirectResponse(url=f"/expenses-page?event_id={clean_event_id}", status_code=303)

@app.post("/delete-expense")
async def delete_expense(
    expense_id: str = Form(...),
    event_id: str = Form(...)
):
    supabase.table("expenses").delete().eq("id", expense_id).execute()
    return RedirectResponse(url=f"/expenses-page?event_id={event_id}", status_code=303)

@app.post("/scan-receipt-ai")
async def scan_receipt_ai(
    request: Request,
    event_id: str = Form(...),
    expense_name: str = Form(None),
    amount: float = Form(None),
    category_id: str = Form(None),
    receipt: UploadFile = File(...)
):
    detected_expense_name = expense_name
    detected_amount = amount
    detected_category_id = category_id

    if receipt and receipt.filename and gemini_client:
        try:
            await receipt.seek(0)
            contents = await receipt.read()
            image = Image.open(io.BytesIO(contents))
            
            prompt = (
                "Analyze this receipt image and extract structured financial data. "
                "Provide a valid JSON object with EXACTLY these keys: "
                "\"expense_name\" (string, e.g. merchant name), \"amount\" (number, float), "
                "\"category_name\" (string). "
                "Do not include any markdown formatting blocks like ```json ... ```, just output the raw JSON text."
            )
            
            response = gemini_client.models.generate_content(
                model="gemini-3.6-flash",
                contents=[image, prompt],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                ),
            )
            
            raw_text = response.text.strip()
            print(f"RAW GEMINI RESPONSE: {raw_text}")
            
            if raw_text.startswith("```"):
                raw_text = raw_text.split("```")[1]
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:].strip()
            
            result_data = json.loads(raw_text)
            
            # Extract values if fields were left blank by the user
            if not detected_expense_name or detected_expense_name.strip() == "":
                detected_expense_name = result_data.get("expense_name") or "Scanned Expense"
            
            if not detected_amount or detected_amount == 0.0:
                detected_amount = float(result_data.get("amount") or 0.0)

            parsed_category_name = result_data.get("category_name")
            if not detected_category_id and parsed_category_name:
                try:
                    cat_res = supabase.table("category_budgets").select("id").eq("event_id", event_id).ilike("category_name", f"%{parsed_category_name.strip()}%").execute()
                    if cat_res.data and len(cat_res.data) > 0:
                        detected_category_id = cat_res.data[0]["id"]
                except Exception as cat_err:
                    print(f"Category matching error: {cat_err}")
                    
        except Exception as e:
            print(f"Gemini scan error: {e}")
            import traceback
            traceback.print_exc()

    # Final fallbacks to avoid null insertion
    if not detected_expense_name or detected_expense_name.strip() == "":
        detected_expense_name = "Scanned Expense"
    if not detected_amount:
        detected_amount = 0.0

    # Save receipt copy locally
    receipt_url = None
    if receipt and receipt.filename:
        try:
            file_path = os.path.join(UPLOAD_DIR, receipt.filename)
            with open(file_path, "wb") as buffer:
                await receipt.seek(0)
                shutil.copyfileobj(receipt.file, buffer)
            receipt_url = f"/static/uploads/{receipt.filename}"
        except Exception as ex:
            print(f"File save error: {ex}")

    clean_event_id = event_id if event_id and event_id != "None" else None
    clean_category_id = detected_category_id if detected_category_id and detected_category_id != "None" else None

    # Insert into Supabase database
    supabase.table("expenses").insert({
        "event_id": clean_event_id,
        "category_id": clean_category_id,
        "expense_name": str(detected_expense_name)[:255],
        "amount": float(detected_amount),
        "receipt_url": receipt_url
    }).execute()

    return RedirectResponse(url=f"/expenses-page?event_id={clean_event_id}", status_code=303)

@app.get("/reimbursement-page")
async def reimbursement_page(request: Request, event_id: str = None):
    all_events_res = supabase.table("events").select("*").execute()
    all_events = all_events_res.data or []
    
    expenses = []
    current_event = None
    
    if event_id:
        # Fetch event details
        ev_res = supabase.table("events").select("*").eq("id", event_id).single().execute()
        current_event = ev_res.data
        
        # Fetch expenses with their categories
        exp_res = supabase.table("expenses").select("*, category_budgets(category_name)").eq("event_id", event_id).execute()
        expenses = exp_res.data or []
        
    return templates.TemplateResponse(
        request, 
        "reimbursement.html", 
        {
            "all_events": all_events,
            "event_id": event_id,
            "current_event": current_event,
            "expenses": expenses
        }
    )


# Route: Load Budget Page with Active Event & History
@app.get("/budget-page")
async def get_budget_page(request: Request, event_id: str = None):
    # 1. Fetch all previous events for selector dropdown / history
    events_res = supabase.table("events").select("*").order("created_at", desc=True).execute()
    all_events = events_res.data if events_res.data else []

    # 2. Identify selected event or fall back to most recent
    active_event = None
    if event_id:
        active_event = next((e for e in all_events if str(e["id"]) == event_id), None)
    elif all_events:
        active_event = all_events[0]

    # Defaults if no events exist yet
    total_budget = float(active_event.get("total_budget", 0.0)) if active_event else 0.0
    category_allocations = []

    if active_event:
        categories_res = (
            supabase.table("category_budgets")
            .select("*")
            .eq("event_id", active_event["id"])
            .execute()
        )
        category_allocations = categories_res.data if categories_res.data else []

    total_spent = sum([float(item.get("allocated_amount", 0.0)) for item in category_allocations])
    remaining_funds = total_budget - total_spent
    utilized_percentage = (total_spent / total_budget * 100) if total_budget > 0 else 0.0

    context = {
        "user": {"full_name": "David Ting", "email": "ting@mmu.edu.my", "role": "Admin", "initials": "DT"},
        "all_events": all_events,
        "active_event": active_event,
        "total_budget": total_budget,
        "remaining_funds": remaining_funds,
        "total_spent": total_spent,
        "utilized_percentage": utilized_percentage,
        "category_allocations": category_allocations,
    }

    return templates.TemplateResponse(request=request, name="budget.html", context=context)


# Route: Create New Event or Reuse Categories from a Past Event
@app.post("/create-event")
async def create_event(
    event_name: str = Form(...),
    total_budget: float = Form(...),
    reuse_event_id: str = Form(None)
):
    # Insert new event
    event_res = supabase.table("events").insert({
        "event_name": event_name,
        "total_budget": total_budget
    }).execute()
    
    new_event = event_res.data[0]
    new_event_id = new_event["id"]

    # Optional: Reuse categories from a previous event template
    if reuse_event_id and reuse_event_id != "none":
        source_categories = supabase.table("category_budgets").select("*").eq("event_id", reuse_event_id).execute()
        if source_categories.data:
            new_cats = [
                {
                    "event_id": new_event_id,
                    "category_name": cat["category_name"],
                    "allocated_amount": cat["allocated_amount"]
                }
                for cat in source_categories.data
            ]
            supabase.table("category_budgets").insert(new_cats).execute()

    return RedirectResponse(url=f"/budget-page?event_id={new_event_id}", status_code=303)


# Route: Delete a Category Allocation
@app.post("/delete-category")
async def delete_category(category_id: str = Form(...), event_id: str = Form(...)):
    supabase.table("category_budgets").delete().eq("id", category_id).execute()
    return RedirectResponse(url=f"/budget-page?event_id={event_id}", status_code=303)

# ------------------------------------------------------------------------------
# 5. Form Submission Handlers (Budget & Categories)
# ------------------------------------------------------------------------------
@app.post("/add-budget")
async def add_budget(amount: float = Form(...), action_type: Optional[str] = Form(None)):
    existing = supabase.table("budgets").select("id").limit(1).execute()
    if existing.data:
        supabase.table("budgets").update({"total_budget": amount}).eq("id", existing.data[0]["id"]).execute()
    else:
        supabase.table("budgets").insert({"event_name": "General Budget", "total_budget": amount}).execute()

    return RedirectResponse(url="/budget-page", status_code=303)


@app.post("/update-category")
async def update_category(category_id: str = Form(...), amount: float = Form(...)):
    # Update allocated_amount instead of amount
    supabase.table("category_budgets").update({
        "allocated_amount": amount
    }).eq("id", category_id).execute()
    
    return RedirectResponse(url="/budget-page", status_code=303)


@app.post("/add-category")
async def add_category(
    category: str = Form(...),
    amount: float = Form(...),
    event_id: str = Form(...)
):
    supabase.table("category_budgets").insert({
        "event_id": event_id,
        "category_name": category,
        "allocated_amount": amount
    }).execute()

    return RedirectResponse(url=f"/budget-page?event_id={event_id}", status_code=303)


# ------------------------------------------------------------------------------
# 6. Budgets & Spending Alerts
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
# 7. Expenses & Gemini OCR Scanner
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
# 8. Quotations & Reimbursements Endpoints
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


@app.post("/reimbursement", status_code=status.HTTP_201_CREATED)
def create_reimbursement(claim: ReimbursementCreate):
    try:
        res = supabase.table("reimbursement").insert(claim.model_dump()).execute()
        return res.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/reimbursement-page")
async def reimbursement_page(request: Request, event_id: str = None):
    all_events_res = supabase.table("events").select("*").execute()
    all_events = all_events_res.data or []
    
    expenses = []
    current_event = None
    
    if event_id:
        ev_res = supabase.table("events").select("*").eq("id", event_id).execute()
        current_event = ev_res.data[0] if ev_res.data else None
        
        # Fetch expenses and categories separately to prevent join crashes
        exp_res = supabase.table("expenses").select("*").eq("event_id", event_id).execute()
        raw_expenses = exp_res.data or []
        
        cat_res = supabase.table("category_budgets").select("*").eq("event_id", event_id).execute()
        categories_map = {cat["id"]: cat["category_name"] for cat in (cat_res.data or [])}
        
        expenses = []
        for exp in raw_expenses:
            cat_id = exp.get("category_id")
            exp["category_name"] = categories_map.get(cat_id, "Unassigned")
            expenses.append(exp)
            
    return templates.TemplateResponse(
        request, 
        "reimbursement.html", 
        {
            "all_events": all_events,
            "event_id": event_id,
            "current_event": current_event,
            "expenses": expenses
        }
    )
import io
import logging
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(name)s  %(message)s",
)
logger = logging.getLogger("clubvault")

app = FastAPI(title="ClubVault API", version="1.0.0")

# Mount static assets if folder exists
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

templates_dir = BASE_DIR / "templates"
templates = Jinja2Templates(directory=templates_dir) if templates_dir.exists() else None

# The frontend is served by this same app, so it needs no cross-origin access.
# Wide-open CORS with credentials would let any website call this API.
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOWED_ORIGINS if o.strip()],
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


# The single source of truth for expense categories. This list must stay in
# sync with the <select> in expenses.html and CATEGORIES in budget-page.js,
# otherwise spending will never line up with a category limit.
EXPENSE_CATEGORIES = [
    "Food & Groceries",
    "Books & Education",
    "Rent & Accommodation",
    "Entertainment",
    "Transport",
    "Savings & Investments",
]


class BudgetUpdate(BaseModel):
    event_name: Optional[str] = None
    total_budget: Optional[float] = None
    alert_threshold: Optional[float] = None


class QuotationStatusUpdate(BaseModel):
    status: str


class CategoryLimitUpsert(BaseModel):
    category: str
    limit_amount: float


class CategoryLimitItem(BaseModel):
    category: str
    limit_amount: float
    spent: float
    remaining: float
    percentage: float
    over_limit: bool


class CategoryLimitsResponse(BaseModel):
    budget_id: str
    total_allocated: float
    total_budget: float
    unallocated: float
    categories: list[CategoryLimitItem]


class QuotationCreate(BaseModel):
    budget_id: str
    vendor_name: str
    category: str
    estimated_amount: float
    description: Optional[str] = None
    status: str = "Pending"


class ReimbursementCreate(BaseModel):
    budget_id: str
    claimant_name: str
    category: str
    amount: float
    description: Optional[str] = None
    status: str = "Pending"


class ReimbursementStatusUpdate(BaseModel):
    status: str


# ------------------------------------------------------------------------------
# 3. Safe Template Renderer (Prevents 500 errors if Teammate hasn't made HTML file)
# ------------------------------------------------------------------------------
def render_page_safely(request: Request, template_name: str, fallback_title: str):
    if templates:
        try:
            return templates.TemplateResponse(request=request, name=template_name)
        except Exception:
            logger.exception("Template %s failed to render", template_name)
    
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


@app.get("/reimbursements-page")
async def render_reimbursements(request: Request):
    return render_page_safely(request, "reimbursements.html", "Reimbursements")

@app.get("/quotations-page")
async def render_quotations(request: Request):
    return render_page_safely(request, "quotations.html", "Quotations")


@app.get("/budget-page")
async def render_budget(request: Request):
    return render_page_safely(request, "budget.html", "Budgets")


@app.get("/settings-page")
async def render_settings(request: Request):
    return render_page_safely(request, "settings.html", "Settings")


# ------------------------------------------------------------------------------
# 5. Budgets & Spending Alerts
# ------------------------------------------------------------------------------
@app.post("/budgets", status_code=status.HTTP_201_CREATED)
def create_budget(budget: BudgetCreate):
    try:
        response = supabase.table("budgets").insert(budget.model_dump()).execute()
        return response.data[0]
    except Exception as e:
        logger.exception("Request failed")
        raise HTTPException(status_code=500, detail="Internal server error")


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
        logger.exception("Request failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.patch("/budgets/{budget_id}")
def update_budget(budget_id: str, update: BudgetUpdate):
    """Edit an existing budget. Only the fields you send are changed."""
    payload = {k: v for k, v in update.model_dump().items() if v is not None}
    if not payload:
        raise HTTPException(status_code=400, detail="No fields to update")
    if "total_budget" in payload and payload["total_budget"] < 0:
        raise HTTPException(status_code=400, detail="total_budget cannot be negative")
    if "alert_threshold" in payload and not (0 < payload["alert_threshold"] <= 1):
        raise HTTPException(
            status_code=400,
            detail="alert_threshold must be between 0 and 1 (e.g. 0.8 for 80%)",
        )

    try:
        res = (
            supabase.table("budgets")
            .update(payload)
            .eq("id", budget_id)
            .execute()
        )
        if not res.data:
            raise HTTPException(status_code=404, detail="Budget not found")
        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Request failed")
        raise HTTPException(status_code=500, detail="Internal server error")


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
        logger.exception("Request failed")
        raise HTTPException(status_code=500, detail="Internal server error")


# ------------------------------------------------------------------------------
# 5b. Per-Category Budget Limits
# ------------------------------------------------------------------------------
@app.get("/budgets/{budget_id}/category-limits", response_model=CategoryLimitsResponse)
def get_category_limits(budget_id: str):
    """Every category limit for this budget, joined with actual spend so far.

    Categories that have spending but no limit set are included with a limit of
    0, so unbudgeted spending is visible rather than hidden.
    """
    try:
        budget_res = (
            supabase.table("budgets")
            .select("total_budget")
            .eq("id", budget_id)
            .execute()
        )
        if not budget_res.data:
            raise HTTPException(status_code=404, detail="Budget not found")
        total_budget = float(budget_res.data[0]["total_budget"])

        limits_res = (
            supabase.table("category_budgets")
            .select("category, limit_amount")
            .eq("budget_id", budget_id)
            .execute()
        )
        limits = {
            row["category"]: float(row["limit_amount"])
            for row in (limits_res.data or [])
        }

        expenses_res = (
            supabase.table("expenses")
            .select("amount, category")
            .eq("budget_id", budget_id)
            .execute()
        )
        spent_by_cat: dict[str, float] = {}
        for e in (expenses_res.data or []):
            cat = e.get("category") or "Uncategorized"
            spent_by_cat[cat] = spent_by_cat.get(cat, 0.0) + float(e["amount"])

        categories = []
        for cat in sorted(set(limits) | set(spent_by_cat)):
            limit_amount = limits.get(cat, 0.0)
            spent = spent_by_cat.get(cat, 0.0)
            pct = round(spent / limit_amount * 100, 2) if limit_amount > 0 else 0.0
            categories.append({
                "category": cat,
                "limit_amount": round(limit_amount, 2),
                "spent": round(spent, 2),
                "remaining": round(limit_amount - spent, 2),
                "percentage": pct,
                "over_limit": limit_amount > 0 and spent > limit_amount,
            })

        total_allocated = sum(limits.values())
        return {
            "budget_id": budget_id,
            "total_allocated": round(total_allocated, 2),
            "total_budget": round(total_budget, 2),
            "unallocated": round(total_budget - total_allocated, 2),
            "categories": categories,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Request failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.put("/budgets/{budget_id}/category-limits")
def upsert_category_limit(budget_id: str, item: CategoryLimitUpsert):
    """Set or update one category's limit. Safe to call repeatedly."""
    if item.limit_amount < 0:
        raise HTTPException(status_code=400, detail="limit_amount cannot be negative")
    if not item.category.strip():
        raise HTTPException(status_code=400, detail="category cannot be empty")

    try:
        payload = {
            "budget_id": budget_id,
            "category": item.category.strip(),
            "limit_amount": item.limit_amount,
        }
        res = (
            supabase.table("category_budgets")
            .upsert(payload, on_conflict="budget_id,category")
            .execute()
        )
        if not res.data:
            raise HTTPException(status_code=500, detail="Upsert returned no row")
        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Request failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/budgets/{budget_id}/category-limits/{category}")
def delete_category_limit(budget_id: str, category: str):
    """Remove a category limit. Expenses in that category are untouched."""
    try:
        res = (
            supabase.table("category_budgets")
            .delete()
            .eq("budget_id", budget_id)
            .eq("category", category)
            .execute()
        )
        return {"deleted": len(res.data or [])}
    except Exception as e:
        logger.exception("Request failed")
        raise HTTPException(status_code=500, detail="Internal server error")


# ------------------------------------------------------------------------------
# 6. Expenses & Gemini OCR Scanner
# ------------------------------------------------------------------------------
@app.post("/expenses", status_code=status.HTTP_201_CREATED)
def create_expense(expense: ExpenseCreate):
    try:
        response = supabase.table("expenses").insert(expense.model_dump()).execute()
        return response.data[0]
    except Exception as e:
        logger.exception("Request failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/budgets/{budget_id}/expenses")
def list_expenses(budget_id: str):
    try:
        response = supabase.table("expenses").select("*").eq("budget_id", budget_id).execute()
        return response.data
    except Exception as e:
        logger.exception("Request failed")
        raise HTTPException(status_code=500, detail="Internal server error")


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
            "and the transaction date if visible. "
            "For the category, you MUST choose exactly one of these strings, "
            "copied verbatim: " + ", ".join(EXPENSE_CATEGORIES) + ". "
            "Pick the closest match; if nothing fits, use Uncategorized."
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
        logger.exception("Receipt processing failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process receipt. Check the server log for details.",
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
    """Log a vendor quotation — a planned cost, not yet spent."""
    if quote.estimated_amount < 0:
        raise HTTPException(status_code=400, detail="estimated_amount cannot be negative")
    try:
        res = supabase.table("quotations").insert(quote.model_dump()).execute()
        if not res.data:
            raise HTTPException(status_code=500, detail="Insert returned no row")
        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Request failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/budgets/{budget_id}/quotations")
def list_quotations(budget_id: str):
    """All quotations for a budget, plus how the pending ones affect headroom."""
    try:
        res = (
            supabase.table("quotations")
            .select("*")
            .eq("budget_id", budget_id)
            .order("created_at", desc=True)
            .execute()
        )
        quotes = res.data or []

        pending_total = sum(
            float(q["estimated_amount"]) for q in quotes
            if (q.get("status") or "") == "Pending"
        )
        approved_total = sum(
            float(q["estimated_amount"]) for q in quotes
            if (q.get("status") or "") == "Approved"
        )

        budget_res = (
            supabase.table("budgets").select("total_budget").eq("id", budget_id).execute()
        )
        total_budget = (
            float(budget_res.data[0]["total_budget"]) if budget_res.data else 0.0
        )

        expenses_res = (
            supabase.table("expenses").select("amount").eq("budget_id", budget_id).execute()
        )
        total_spent = sum(float(e["amount"]) for e in (expenses_res.data or []))

        return {
            "budget_id": budget_id,
            "total_budget": round(total_budget, 2),
            "total_spent": round(total_spent, 2),
            "pending_total": round(pending_total, 2),
            "approved_total": round(approved_total, 2),
            # What is left if every pending quotation gets approved.
            "projected_remaining": round(total_budget - total_spent - pending_total, 2),
            "quotations": quotes,
        }
    except Exception as e:
        logger.exception("Request failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.patch("/quotations/{quotation_id}/status")
def update_quotation_status(quotation_id: str, update: QuotationStatusUpdate):
    """Approve or reject a quotation.

    Approving converts it into a real expense, so the budget updates itself
    without the treasurer retyping anything. Rejecting just marks it.
    """
    allowed = {"Pending", "Approved", "Rejected"}
    if update.status not in allowed:
        raise HTTPException(
            status_code=400, detail=f"status must be one of {sorted(allowed)}"
        )

    try:
        current = (
            supabase.table("quotations").select("*").eq("id", quotation_id).execute()
        )
        if not current.data:
            raise HTTPException(status_code=404, detail="Quotation not found")
        quote = current.data[0]

        was_approved = (quote.get("status") or "") == "Approved"

        res = (
            supabase.table("quotations")
            .update({"status": update.status})
            .eq("id", quotation_id)
            .execute()
        )
        if not res.data:
            raise HTTPException(status_code=404, detail="Quotation not found")

        # Only create the expense on the transition into Approved, so
        # re-approving an already-approved quotation cannot double-charge.
        if update.status == "Approved" and not was_approved:
            supabase.table("expenses").insert({
                "budget_id": quote["budget_id"],
                "title": quote["vendor_name"],
                "amount": float(quote["estimated_amount"]),
                "category": quote.get("category") or "Uncategorized",
                "receipt_url": None,
            }).execute()

        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Request failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.delete("/quotations/{quotation_id}")
def delete_quotation(quotation_id: str):
    """Remove a quotation. Any expense already created from it stays."""
    try:
        res = supabase.table("quotations").delete().eq("id", quotation_id).execute()
        return {"deleted": len(res.data or [])}
    except Exception as e:
        logger.exception("Request failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/reimbursements", status_code=status.HTTP_201_CREATED)
def create_reimbursement(claim: ReimbursementCreate):
    """Submit a new reimbursement claim against a budget."""
    try:
        res = supabase.table("reimbursements").insert(claim.model_dump()).execute()
        if not res.data:
            raise HTTPException(status_code=500, detail="Insert returned no row")
        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Request failed")
        raise HTTPException(status_code=500, detail="Internal server error")


# NOTE: this must stay ABOVE any /reimbursements/{something} route,
# otherwise FastAPI matches "stats" as an id.
@app.get("/reimbursements/stats")
def reimbursement_stats(budget_id: str):
    """Live figures for the four cards at the top of the reimbursements page."""
    try:
        claims_res = (
            supabase.table("reimbursements")
            .select("amount, status")
            .eq("budget_id", budget_id)
            .execute()
        )
        claims = claims_res.data or []

        total_requests = len(claims)
        pending_review = sum(1 for c in claims if (c.get("status") or "") == "Pending")
        approved_amount = sum(
            float(c["amount"]) for c in claims if (c.get("status") or "") == "Approved"
        )

        budget_res = (
            supabase.table("budgets")
            .select("total_budget")
            .eq("id", budget_id)
            .execute()
        )
        total_budget = (
            float(budget_res.data[0]["total_budget"]) if budget_res.data else 0.0
        )

        # Money already spent counts against the budget too, otherwise this
        # card contradicts the Remaining Funds figure on the budget page.
        expenses_res = (
            supabase.table("expenses")
            .select("amount")
            .eq("budget_id", budget_id)
            .execute()
        )
        total_spent = sum(float(e["amount"]) for e in (expenses_res.data or []))

        return {
            "total_requests": total_requests,
            "pending_review": pending_review,
            "approved_amount": round(approved_amount, 2),
            "available_budget": round(total_budget - total_spent - approved_amount, 2),
        }
    except Exception as e:
        logger.exception("Request failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/reimbursements")
def list_reimbursements(budget_id: Optional[str] = None):
    """List claims, newest first. Pass budget_id to scope to one budget."""
    try:
        query = supabase.table("reimbursements").select("*")
        if budget_id:
            query = query.eq("budget_id", budget_id)
        res = query.order("created_at", desc=True).execute()
        return res.data or []
    except Exception as e:
        logger.exception("Request failed")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.patch("/reimbursements/{claim_id}/status")
def update_reimbursement_status(claim_id: str, update: ReimbursementStatusUpdate):
    """Approve or reject a claim."""
    allowed = {"Pending", "Approved", "Rejected"}
    if update.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"status must be one of {sorted(allowed)}",
        )
    try:
        res = (
            supabase.table("reimbursements")
            .update({"status": update.status})
            .eq("id", claim_id)
            .execute()
        )
        if not res.data:
            raise HTTPException(status_code=404, detail="Reimbursement not found")
        return res.data[0]
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Request failed")
        raise HTTPException(status_code=500, detail="Internal server error")
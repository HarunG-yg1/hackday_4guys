-- 1. Completely clean slate
DROP TABLE IF EXISTS public.reimbursements CASCADE;
DROP TABLE IF EXISTS public.expenses CASCADE;
DROP TABLE IF EXISTS public.category_budgets CASCADE;
DROP TABLE IF EXISTS public.savings_goals CASCADE;
DROP TABLE IF EXISTS public.budgets CASCADE;
DROP TABLE IF EXISTS public.events CASCADE;

-- 2. Events Table (Parent entity for everything)
CREATE TABLE public.events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_name TEXT NOT NULL,
    total_budget NUMERIC(10, 2) DEFAULT 0.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Category Budgets Table (Target limits per category per event)
CREATE TABLE public.category_budgets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID REFERENCES public.events(id) ON DELETE CASCADE,
    category_name TEXT NOT NULL,
    allocated_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Expenses Table (Actual tracked spending linked to events and categories)
CREATE TABLE public.expenses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID REFERENCES public.events(id) ON DELETE CASCADE,
    category_id UUID REFERENCES public.category_budgets(id) ON DELETE SET NULL,
    expense_name TEXT NOT NULL,
    amount NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 5. Savings Goals Table
CREATE TABLE public.savings_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    current_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    target_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 6. Reimbursements Table (Linked to expenses)
CREATE TABLE public.reimbursements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    expense_id UUID REFERENCES public.expenses(id) ON DELETE CASCADE,
    claimant_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 7. Disable RLS across all tables for smooth hackathon testing
ALTER TABLE public.events DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.category_budgets DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.expenses DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.savings_goals DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.reimbursements DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.expenses ADD COLUMN IF NOT EXISTS receipt_url TEXT;
NOTIFY pgrst, 'reload schema';

-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.budgets (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  event_name text NOT NULL,
  total_budget numeric NOT NULL,
  alert_threshold numeric NOT NULL DEFAULT 0.8,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT budgets_pkey PRIMARY KEY (id)
);
CREATE TABLE public.expenses (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  budget_id uuid NOT NULL,
  title text NOT NULL,
  amount numeric NOT NULL,
  category text NOT NULL,
  receipt_url text,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT expenses_pkey PRIMARY KEY (id),
  CONSTRAINT expenses_budget_id_fkey FOREIGN KEY (budget_id) REFERENCES public.budgets(id)
);
CREATE TABLE public.reimbursements (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  budget_id uuid NOT NULL,
  claimant_name text NOT NULL,
  category text NOT NULL,
  amount numeric NOT NULL CHECK (amount >= 0::numeric),
  description text,
  status text NOT NULL DEFAULT 'Pending'::text CHECK (status = ANY (ARRAY['Pending'::text, 'Approved'::text, 'Rejected'::text])),
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT reimbursements_pkey PRIMARY KEY (id),
  CONSTRAINT reimbursements_budget_id_fkey FOREIGN KEY (budget_id) REFERENCES public.budgets(id)
);
CREATE TABLE public.category_budgets (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  budget_id uuid NOT NULL,
  category text NOT NULL,
  limit_amount numeric NOT NULL CHECK (limit_amount >= 0::numeric),
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT category_budgets_pkey PRIMARY KEY (id),
  CONSTRAINT category_budgets_budget_id_fkey FOREIGN KEY (budget_id) REFERENCES public.budgets(id)
);
CREATE TABLE public.quotations (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  budget_id uuid NOT NULL,
  vendor_name text NOT NULL,
  category text NOT NULL,
  estimated_amount numeric NOT NULL CHECK (estimated_amount >= 0::numeric),
  description text,
  status text NOT NULL DEFAULT 'Pending'::text CHECK (status = ANY (ARRAY['Pending'::text, 'Approved'::text, 'Rejected'::text])),
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT quotations_pkey PRIMARY KEY (id),
  CONSTRAINT quotations_budget_id_fkey FOREIGN KEY (budget_id) REFERENCES public.budgets(id)
);
// ClubVault — shared budget context
//
// Every page needs to know which budget it's looking at. This script:
//   1. Reads ?budgetId= from the URL if present, and remembers it in localStorage.
//   2. Falls back to the last-remembered budgetId if the URL doesn't have one
//      (so refreshing or clicking a plain link doesn't lose your place).
//   3. Rewrites every sidebar nav link to carry ?budgetId= forward, so moving
//      between Dashboard / Expenses / Budgets / Reimbursements stays on the
//      same budget.
//
// Other scripts (dashboard.js, expenses.js, budget.js, reimbursement.js)
// should call window.getBudgetId() instead of reading location.search directly.

(function () {
    const STORAGE_KEY = 'clubvault_budget_id';

    const urlParams = new URLSearchParams(window.location.search);
    const urlBudgetId = urlParams.get('budgetId');

    if (urlBudgetId) {
        localStorage.setItem(STORAGE_KEY, urlBudgetId);
    }

    const activeBudgetId = urlBudgetId || localStorage.getItem(STORAGE_KEY) || null;

    window.getBudgetId = function () {
        return activeBudgetId;
    };

    window.clearBudgetId = function () {
        localStorage.removeItem(STORAGE_KEY);
    };

    document.addEventListener('DOMContentLoaded', () => {
        if (!activeBudgetId) return;

        document.querySelectorAll('.sidebar a.nav-item').forEach((link) => {
            const href = link.getAttribute('href');
            if (!href) return;

            // Don't touch external links or anchors
            if (href.startsWith('http') || href.startsWith('#')) return;

            const [path, existingQuery] = href.split('?');
            const query = new URLSearchParams(existingQuery || '');
            query.set('budgetId', activeBudgetId);
            link.setAttribute('href', `${path}?${query.toString()}`);
        });
    });
})();

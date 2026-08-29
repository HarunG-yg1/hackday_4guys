document.addEventListener('DOMContentLoaded', () => {
    const budgetId = window.getBudgetId ? window.getBudgetId() : null;
    const noBudgetCard = document.getElementById('noBudgetCard');
    const expensesContent = document.getElementById('expensesContent');

    if (!budgetId) {
        noBudgetCard.style.display = 'block';
        expensesContent.style.display = 'none';
        return;
    }

    noBudgetCard.style.display = 'none';
    expensesContent.style.display = 'block';

    loadExpenseTable(budgetId);

    const form = document.getElementById('expenseForm');
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const submitBtn = document.getElementById('expenseSubmitBtn');
        const originalText = submitBtn.textContent;
        const receiptInput = document.getElementById('expenseReceipt');
        const hasReceipt = receiptInput.files && receiptInput.files.length > 0;

        submitBtn.disabled = true;
        submitBtn.textContent = hasReceipt ? 'Scanning receipt with AI...' : 'Saving...';

        try {
            if (hasReceipt) {
                await scanAndSaveReceipt(budgetId, receiptInput.files[0]);
            } else {
                await saveManualExpense(budgetId);
            }
            form.reset();
            await loadExpenseTable(budgetId);
        } catch (error) {
            console.error('Failed to save expense:', error);
            alert('Failed to save expense. Check console for details.');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
    });
});

// Manual entry -> POST /expenses
async function saveManualExpense(budgetId) {
    const title = document.getElementById('expenseDescription').value;
    const amount = parseFloat(document.getElementById('expenseAmount').value);
    const category = document.getElementById('expenseCategory').value;

    const response = await fetch('/expenses', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            budget_id: budgetId,
            title: title,
            amount: amount,
            category: category
        })
    });

    if (!response.ok) throw new Error(`Save failed: ${response.status}`);
    return response.json();
}

// Receipt upload -> Gemini OCR endpoint that scans + saves in one call
async function scanAndSaveReceipt(budgetId, file) {
    const formData = new FormData();
    formData.append('budget_id', budgetId);
    formData.append('file', file);

    const response = await fetch('/expenses/scan-and-save', {
        method: 'POST',
        body: formData // Content-Type intentionally omitted; browser sets multipart boundary
    });

    if (!response.ok) throw new Error(`Scan failed: ${response.status}`);
    return response.json();
}

// Fetch & render the real expense list for this budget
async function loadExpenseTable(budgetId) {
    const tbody = document.getElementById('expenseTableBody');
    try {
        const response = await fetch(`/budgets/${budgetId}/expenses`);
        if (!response.ok) throw new Error('Failed to load expenses');
        const expenses = await response.json();

        if (!expenses.length) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding: 24px; color: var(--text-muted);">No expenses logged yet.</td></tr>';
            return;
        }

        // Most recent first
        expenses.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

        tbody.innerHTML = expenses.map(exp => {
            const date = new Date(exp.created_at).toLocaleDateString('en-MY', { month: 'short', day: 'numeric', year: 'numeric' });
            const badgeColor = categoryBadgeColor(exp.category);
            return `
                <tr>
                    <td class="td-date">${date}</td>
                    <td class="td-desc">${escapeHtml(exp.title)}</td>
                    <td><span class="cat-badge" style="background: ${badgeColor.bg}; color: ${badgeColor.text};">${escapeHtml(exp.category)}</span></td>
                    <td>-RM ${Number(exp.amount).toFixed(2)}</td>
                </tr>
            `;
        }).join('');
    } catch (error) {
        console.error('Error loading expenses:', error);
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding: 24px; color: var(--danger-text, #dc2626);">Failed to load expenses.</td></tr>';
    }
}

function categoryBadgeColor(category) {
    const map = {
        'Food & Groceries': { bg: '#dcfce7', text: '#16a34a' },
        'Books & Education': { bg: '#f3e8ff', text: '#7e22ce' },
        'Rent & Accommodation': { bg: '#fee2e2', text: '#dc2626' },
        'Entertainment': { bg: '#fef3c7', text: '#d97706' },
        'Transport': { bg: '#e0f2fe', text: '#2563eb' },
        'Savings & Investments': { bg: '#e0f2fe', text: '#0284c7' }
    };
    return map[category] || { bg: '#f1f5f9', text: '#475569' };
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
// ClubVault — Quotations
// A quotation is a planned cost. Approving one turns it into a real expense,
// so the budget updates without the treasurer retyping anything.
// Depends on budget-context.js for window.getBudgetId().

const QUOTE_CATEGORIES = [
    'Food & Groceries',
    'Books & Education',
    'Rent & Accommodation',
    'Entertainment',
    'Transport',
    'Savings & Investments'
];

document.addEventListener('DOMContentLoaded', () => {
    const budgetId = window.getBudgetId ? window.getBudgetId() : null;
    const noBudgetCard = document.getElementById('noBudgetCard');
    const content = document.getElementById('quotationsContent');

    if (!budgetId) {
        noBudgetCard.style.display = 'block';
        content.style.display = 'none';
        return;
    }

    noBudgetCard.style.display = 'none';
    content.style.display = 'block';

    populateCategories();
    loadQuotations(budgetId);

    const form = document.getElementById('quotationForm');
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const btn = document.getElementById('quoteSubmitBtn');
        const original = btn.textContent;
        btn.disabled = true;
        btn.textContent = 'Saving...';

        try {
            await createQuotation(budgetId);
            form.reset();
            await loadQuotations(budgetId);
        } catch (error) {
            console.error('Failed to save quotation:', error);
            alert('Could not save that quotation. Check console for details.');
        } finally {
            btn.disabled = false;
            btn.textContent = original;
        }
    });
});

async function createQuotation(budgetId) {
    const payload = {
        budget_id: budgetId,
        vendor_name: document.getElementById('quoteVendor').value,
        category: document.getElementById('quoteCategory').value,
        estimated_amount: parseFloat(document.getElementById('quoteAmount').value),
        description: document.getElementById('quoteDescription').value || null,
        status: 'Pending'
    };

    const response = await fetch('/quotations', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    if (!response.ok) throw new Error(`Save failed: ${response.status}`);
    return response.json();
}

async function loadQuotations(budgetId) {
    const tbody = document.getElementById('quotationTableBody');
    try {
        const response = await fetch(`/budgets/${budgetId}/quotations`);
        if (!response.ok) throw new Error('Failed to load quotations');
        const data = await response.json();

        setText('quotePendingTotal', money(data.pending_total));
        setText('quoteApprovedTotal', money(data.approved_total));
        setText('quoteProjected', money(data.projected_remaining));

        const projectedEl = document.getElementById('quoteProjected');
        const badge = document.getElementById('quoteProjectedBadge');
        const short = data.projected_remaining < 0;
        if (projectedEl) {
            projectedEl.style.color = short ? 'var(--danger-text)' : 'var(--success-text)';
        }
        if (badge) {
            badge.className = short ? 'badge red' : 'badge green';
            badge.textContent = short
                ? 'Quotes exceed budget'
                : 'Within budget';
        }

        if (!data.quotations.length) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 24px; color: var(--text-muted);">No quotations logged yet.</td></tr>`;
            return;
        }

        tbody.innerHTML = data.quotations.map(renderRow).join('');
        wireButtons(budgetId);
    } catch (error) {
        console.error('Error loading quotations:', error);
        tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding: 24px; color: var(--danger-text, #dc2626);">Failed to load quotations.</td></tr>`;
    }
}

function renderRow(q) {
    const date = q.created_at
        ? new Date(q.created_at).toLocaleDateString('en-MY', {
              month: 'short', day: 'numeric', year: 'numeric'
          })
        : '—';

    const actions = (q.status || 'Pending') === 'Pending'
        ? `<div class="claim-actions">
             <button class="btn-approve" data-id="${q.id}" data-status="Approved">Approve</button>
             <button class="btn-reject" data-id="${q.id}" data-status="Rejected">Reject</button>
           </div>`
        : `<div class="claim-actions">
             <button class="btn-remove" data-id="${q.id}" data-action="delete" title="Delete quotation">&times;</button>
           </div>`;

    const desc = q.description
        ? `<span style="font-size: 0.75rem; color: var(--text-muted);">${escapeHtml(q.description)}</span>`
        : '';

    return `
        <tr>
            <td class="td-date">${date}</td>
            <td>
                <div style="display: flex; flex-direction: column;">
                    <strong style="color: var(--text-main);">${escapeHtml(q.vendor_name)}</strong>
                    ${desc}
                </div>
            </td>
            <td>${escapeHtml(q.category || 'Uncategorized')}</td>
            <td>${statusBadge(q.status)}${actions}</td>
            <td>${money(q.estimated_amount)}</td>
        </tr>
    `;
}

function wireButtons(budgetId) {
    document.querySelectorAll('#quotationTableBody [data-status]').forEach((btn) => {
        btn.addEventListener('click', async () => {
            const approving = btn.dataset.status === 'Approved';
            if (approving && !confirm('Approving logs this as a real expense against the budget. Continue?')) {
                return;
            }
            btn.disabled = true;
            try {
                const response = await fetch(`/quotations/${btn.dataset.id}/status`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ status: btn.dataset.status })
                });
                if (!response.ok) throw new Error(`Update failed: ${response.status}`);
                await loadQuotations(budgetId);
            } catch (error) {
                console.error('Failed to update quotation:', error);
                alert('Could not update that quotation.');
                btn.disabled = false;
            }
        });
    });

    document.querySelectorAll('#quotationTableBody [data-action="delete"]').forEach((btn) => {
        btn.addEventListener('click', async () => {
            if (!confirm('Delete this quotation? Any expense already created from it stays.')) return;
            btn.disabled = true;
            try {
                const response = await fetch(`/quotations/${btn.dataset.id}`, { method: 'DELETE' });
                if (!response.ok) throw new Error(`Delete failed: ${response.status}`);
                await loadQuotations(budgetId);
            } catch (error) {
                console.error('Failed to delete quotation:', error);
                alert('Could not delete that quotation.');
                btn.disabled = false;
            }
        });
    });
}

// ---------------------------------------------------------------- helpers
function statusBadge(status) {
    const s = status || 'Pending';
    if (s === 'Approved') return '<span class="badge green">Approved</span>';
    if (s === 'Rejected') return '<span class="badge red">Rejected</span>';
    return '<span class="badge" style="background: var(--warning-bg); color: var(--warning-text);">Pending</span>';
}

function populateCategories() {
    const select = document.getElementById('quoteCategory');
    if (!select) return;
    select.innerHTML = '<option value="">Select a category</option>' +
        QUOTE_CATEGORIES.map(c =>
            `<option value="${c.replace(/"/g, '&quot;')}">${escapeHtml(c)}</option>`
        ).join('');
}

function money(value) {
    return `RM ${Number(value).toFixed(2)}`;
}

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str == null ? '' : str;
    return div.innerHTML;
}
// ClubVault — Budget page
// Drives the summary cards and the per-category allocation list.
// Depends on budget-context.js for window.getBudgetId().

// Must match the category list in expenses.html, or spending will never
// line up with a limit.
const CATEGORIES = [
    'Food & Groceries',
    'Books & Education',
    'Rent & Accommodation',
    'Entertainment',
    'Transport',
    'Savings & Investments'
];

const CATEGORY_COLORS = {
    'Food & Groceries': 'var(--color-food)',
    'Books & Education': 'var(--color-books)',
    'Rent & Accommodation': 'var(--color-rent)',
    'Entertainment': 'var(--color-entertainment)',
    'Transport': 'var(--color-transport)',
    'Savings & Investments': 'var(--primary)'
};

document.addEventListener('DOMContentLoaded', () => {
    const budgetId = window.getBudgetId ? window.getBudgetId() : null;
    const noBudgetCard = document.getElementById('noBudgetCard');
    const content = document.getElementById('budgetContent');

    if (!budgetId) {
        noBudgetCard.style.display = 'block';
        content.style.display = 'none';
        return;
    }

    noBudgetCard.style.display = 'none';
    content.style.display = 'block';

    populateCategoryPicker();
    refreshAll(budgetId);

    const editForm = document.getElementById('editBudgetForm');
    editForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = document.getElementById('editBudgetBtn');
        const original = btn.textContent;
        btn.disabled = true;
        btn.textContent = 'Saving...';

        try {
            await updateBudget(budgetId);
            await refreshAll(budgetId);
        } catch (error) {
            console.error('Failed to update budget:', error);
            alert('Could not save the budget. Check console for details.');
        } finally {
            btn.disabled = false;
            btn.textContent = original;
        }
    });

    const addForm = document.getElementById('addCategoryForm');
    addForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = document.getElementById('addCategoryBtn');
        const original = btn.textContent;
        btn.disabled = true;
        btn.textContent = 'Saving...';

        try {
            await saveLimit(
                budgetId,
                document.getElementById('newCategory').value,
                parseFloat(document.getElementById('newCategoryLimit').value)
            );
            addForm.reset();
            await refreshAll(budgetId);
        } catch (error) {
            console.error('Failed to set category limit:', error);
            alert('Could not save that limit. Check console for details.');
        } finally {
            btn.disabled = false;
            btn.textContent = original;
        }
    });
});

async function refreshAll(budgetId) {
    await Promise.all([loadSummary(budgetId), loadAllocations(budgetId)]);
}

// ---------------------------------------------------------------- summary
async function loadSummary(budgetId) {
    try {
        const response = await fetch(`/budgets/${budgetId}`);
        if (!response.ok) throw new Error('Failed to load budget');
        const data = await response.json();

        const total = Number(data.budget.total_budget);
        const spent = Number(data.total_spent);
        const remaining = Number(data.remaining_budget);
        const pct = total > 0 ? Math.min((spent / total) * 100, 100) : 0;

        setText('budgetEventName', data.budget.event_name || 'Budget');
        prefill('editEventName', data.budget.event_name || '');
        prefill('editTotalBudget', total.toFixed(2));
        prefill('editThreshold', Math.round((data.budget.alert_threshold ?? 0.8) * 100));
        setText('budgetTotal', `RM ${total.toFixed(2)}`);
        setText('budgetSpent', `RM ${spent.toFixed(2)}`);
        setText('budgetRemaining', `RM ${remaining.toFixed(2)}`);

        const fill = document.getElementById('budgetTotalFill');
        if (fill) {
            fill.style.width = `${pct}%`;
            fill.style.background = data.alert_triggered
                ? 'var(--danger-text)'
                : 'var(--primary)';
        }
        setText('budgetUtilisation', `${pct.toFixed(1)}% of the total budget used`);

        const remainingEl = document.getElementById('budgetRemaining');
        if (remainingEl) {
            remainingEl.style.color = remaining < 0
                ? 'var(--danger-text)'
                : 'var(--success-text)';
        }

        const badge = document.getElementById('budgetStatusBadge');
        if (badge) {
            if (remaining < 0) {
                badge.className = 'badge red';
                badge.textContent = 'Over Budget';
            } else if (data.alert_triggered) {
                badge.className = 'badge yellow';
                badge.textContent = 'Threshold Reached';
            } else {
                badge.className = 'badge green';
                badge.textContent = 'On Track';
            }
        }
    } catch (error) {
        console.error('Error loading budget summary:', error);
        ['budgetTotal', 'budgetSpent', 'budgetRemaining'].forEach(id => setText(id, '—'));
    }
}

// ------------------------------------------------------------ allocations
async function loadAllocations(budgetId) {
    const list = document.getElementById('allocationList');
    try {
        const response = await fetch(`/budgets/${budgetId}/category-limits`);
        if (!response.ok) throw new Error('Failed to load category limits');
        const data = await response.json();

        setText('allocatedTotal', `RM ${data.total_allocated.toFixed(2)}`);
        const unallocatedEl = document.getElementById('unallocatedTotal');
        if (unallocatedEl) {
            unallocatedEl.textContent = `RM ${data.unallocated.toFixed(2)}`;
            unallocatedEl.style.color = data.unallocated < 0
                ? 'var(--danger-text)'
                : 'var(--text-main)';
        }

        if (!data.categories.length) {
            list.innerHTML = `<p style="font-size: 0.875rem; color: var(--text-muted); padding: 8px 0;">
                No category limits set yet. Add one below to start tracking.
            </p>`;
            return;
        }

        list.innerHTML = data.categories.map(renderAllocation).join('');
        wireAllocationButtons(budgetId);
    } catch (error) {
        console.error('Error loading allocations:', error);
        list.innerHTML = `<p style="font-size: 0.875rem; color: var(--danger-text, #dc2626); padding: 8px 0;">
            Failed to load category allocations.
        </p>`;
    }
}

function renderAllocation(cat) {
    const color = CATEGORY_COLORS[cat.category] || 'var(--text-muted)';
    const pct = Math.min(cat.percentage, 100);

    let fillColor = 'var(--success-text)';
    if (cat.over_limit) fillColor = 'var(--danger-text)';
    else if (cat.percentage >= 80) fillColor = 'var(--warning-text)';

    const noLimit = cat.limit_amount === 0;
    const warning = cat.over_limit
        ? `<span class="badge red" style="margin-left: 8px;">Over by RM ${Math.abs(cat.remaining).toFixed(2)}</span>`
        : noLimit
            ? `<span class="badge yellow" style="margin-left: 8px;">No limit set</span>`
            : '';

    return `
        <div class="breakdown-item allocation-row">
            <div class="breakdown-info">
                <div class="category-name">
                    <div class="dot" style="background: ${color};"></div>
                    ${escapeHtml(cat.category)}${warning}
                </div>
                <div class="amount-val">RM ${cat.spent.toFixed(2)} / RM ${cat.limit_amount.toFixed(2)}</div>
            </div>

            <div class="progress-bar" style="margin-top: 8px;">
                <div class="progress-fill" style="width: ${pct}%; background: ${fillColor};"></div>
            </div>

            <div class="budget-input-group">
                <input type="number" class="budget-input" step="0.01" min="0"
                       value="${cat.limit_amount}"
                       data-category="${escapeAttr(cat.category)}"
                       placeholder="New limit...">
                <button class="btn-save" data-action="save"
                        data-category="${escapeAttr(cat.category)}">Update</button>
                <button class="btn-remove" data-action="delete"
                        data-category="${escapeAttr(cat.category)}"
                        title="Remove this limit">×</button>
            </div>
        </div>
    `;
}

function wireAllocationButtons(budgetId) {
    document.querySelectorAll('#allocationList [data-action="save"]').forEach((btn) => {
        btn.addEventListener('click', async () => {
            const category = btn.dataset.category;
            const input = document.querySelector(
                `#allocationList input[data-category="${CSS.escape(category)}"]`
            );
            const value = parseFloat(input.value);
            if (Number.isNaN(value) || value < 0) {
                alert('Enter a valid amount.');
                return;
            }

            const original = btn.textContent;
            btn.disabled = true;
            btn.textContent = 'Saving...';
            try {
                await saveLimit(budgetId, category, value);
                await refreshAll(budgetId);
            } catch (error) {
                console.error('Failed to update limit:', error);
                alert('Could not update that limit.');
                btn.disabled = false;
                btn.textContent = original;
            }
        });
    });

    document.querySelectorAll('#allocationList [data-action="delete"]').forEach((btn) => {
        btn.addEventListener('click', async () => {
            const category = btn.dataset.category;
            if (!confirm(`Remove the limit for "${category}"? Expenses stay untouched.`)) return;

            btn.disabled = true;
            try {
                const response = await fetch(
                    `/budgets/${budgetId}/category-limits/${encodeURIComponent(category)}`,
                    { method: 'DELETE' }
                );
                if (!response.ok) throw new Error(`Delete failed: ${response.status}`);
                await refreshAll(budgetId);
            } catch (error) {
                console.error('Failed to remove limit:', error);
                alert('Could not remove that limit.');
                btn.disabled = false;
            }
        });
    });
}

async function updateBudget(budgetId) {
    const thresholdPct = parseFloat(document.getElementById('editThreshold').value);
    if (Number.isNaN(thresholdPct) || thresholdPct <= 0 || thresholdPct > 100) {
        throw new Error('Alert threshold must be between 1 and 100');
    }

    const payload = {
        event_name: document.getElementById('editEventName').value,
        total_budget: parseFloat(document.getElementById('editTotalBudget').value),
        // The API stores the threshold as a fraction, the form shows a percentage.
        alert_threshold: thresholdPct / 100
    };

    const response = await fetch(`/budgets/${budgetId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    if (!response.ok) throw new Error(`Update failed: ${response.status}`);
    return response.json();
}

async function saveLimit(budgetId, category, limitAmount) {
    const response = await fetch(`/budgets/${budgetId}/category-limits`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category: category, limit_amount: limitAmount })
    });
    if (!response.ok) throw new Error(`Save failed: ${response.status}`);
    return response.json();
}

// ---------------------------------------------------------------- helpers
function populateCategoryPicker() {
    const select = document.getElementById('newCategory');
    if (!select) return;
    select.innerHTML = '<option value="">Select a category</option>' +
        CATEGORIES.map(c => `<option value="${escapeAttr(c)}">${escapeHtml(c)}</option>`).join('');
}

function prefill(id, value) {
    const el = document.getElementById(id);
    // Don't clobber what the user is currently typing.
    if (el && document.activeElement !== el) el.value = value;
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

function escapeAttr(str) {
    return String(str == null ? '' : str).replace(/"/g, '&quot;');
}
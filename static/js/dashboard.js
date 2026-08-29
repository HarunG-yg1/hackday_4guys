// ClubVault — Dashboard
// Every figure on this page comes from the API. Nothing is hardcoded.
// Depends on budget-context.js for window.getBudgetId().

const CATEGORY_COLORS = {
    'Food & Groceries': 'var(--color-food)',
    'Books & Education': 'var(--color-books)',
    'Rent & Accommodation': 'var(--color-rent)',
    'Entertainment': 'var(--color-entertainment)',
    'Transport': 'var(--color-transport)',
    'Savings & Investments': 'var(--primary)'
};

const CATEGORY_BADGES = {
    'Food & Groceries': { bg: '#dcfce7', text: '#16a34a' },
    'Books & Education': { bg: '#f3e8ff', text: '#7e22ce' },
    'Rent & Accommodation': { bg: '#fee2e2', text: '#dc2626' },
    'Entertainment': { bg: '#fef3c7', text: '#d97706' },
    'Transport': { bg: '#e0f2fe', text: '#2563eb' },
    'Savings & Investments': { bg: '#e0f2fe', text: '#0284c7' }
};

document.addEventListener('DOMContentLoaded', () => {
    const createCard = document.getElementById('createBudgetCard');
    const dashboardContent = document.getElementById('dashboardContent');
    const budgetId = window.getBudgetId ? window.getBudgetId() : null;

    if (!budgetId) {
        createCard.style.display = 'block';
        dashboardContent.style.display = 'none';
    } else {
        createCard.style.display = 'none';
        dashboardContent.style.display = 'block';
        loadDashboard(budgetId);
    }

    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            console.log('Search shortcut triggered');
        }
    });
});

async function loadDashboard(budgetId) {
    // Summary first so the headline numbers appear fast, then the rest.
    const summary = await loadSummary(budgetId);
    await Promise.all([
        loadBreakdown(budgetId),
        loadAlerts(budgetId, summary),
        loadActivity(budgetId)
    ]);
}

// ---------------------------------------------------------------- summary
async function loadSummary(budgetId) {
    try {
        const response = await fetch(`/budgets/${budgetId}`);
        if (!response.ok) throw new Error('Failed to load summary');
        const data = await response.json();

        const total = Number(data.budget.total_budget);
        const spent = Number(data.total_spent);
        const remaining = Number(data.remaining_budget);
        const pctUsed = total > 0 ? (spent / total) * 100 : 0;

        setText('dashTotalBudget', money(total));
        setText('dashEventName', data.budget.event_name || 'Active budget');
        setText('dashTotalSpent', money(spent));
        setText('dashRemaining', money(remaining));

        const usedBadge = document.getElementById('dashUsedBadge');
        if (usedBadge) {
            usedBadge.textContent = `${pctUsed.toFixed(1)}%`;
            usedBadge.className = pctUsed >= 100 ? 'badge red'
                : pctUsed >= 80 ? 'badge yellow'
                : 'badge green';
        }

        const remainingEl = document.getElementById('dashRemaining');
        if (remainingEl) {
            remainingEl.style.color = remaining < 0
                ? 'var(--danger-text)'
                : 'var(--success-text)';
        }

        const statusBadge = document.getElementById('dashStatusBadge');
        if (statusBadge) {
            if (remaining < 0) {
                statusBadge.className = 'badge red';
                statusBadge.textContent = 'Over Budget';
            } else if (data.alert_triggered) {
                statusBadge.className = 'badge yellow';
                statusBadge.textContent = 'Threshold Reached';
            } else {
                statusBadge.className = 'badge green';
                statusBadge.textContent = 'On Track';
            }
        }

        return data;
    } catch (error) {
        console.error('Error loading budget summary:', error);
        ['dashTotalBudget', 'dashTotalSpent', 'dashRemaining'].forEach(id => setText(id, '—'));
        return null;
    }
}

// -------------------------------------------------------------- breakdown
async function loadBreakdown(budgetId) {
    const list = document.getElementById('dashBreakdownList');
    try {
        const response = await fetch(`/budgets/${budgetId}/analytics`);
        if (!response.ok) throw new Error('Failed to load analytics');
        const data = await response.json();

        if (!data.categories.length) {
            list.innerHTML = emptyNote('No expenses logged yet. Add one on the Expenses page.');
            return;
        }

        // Biggest spender first.
        data.categories.sort((a, b) => b.total_spent - a.total_spent);

        list.innerHTML = data.categories.map(cat => {
            const color = CATEGORY_COLORS[cat.category] || 'var(--text-muted)';
            return `
                <div class="breakdown-item">
                    <div class="breakdown-info">
                        <div class="category-name">
                            <div class="dot" style="background: ${color};"></div>
                            ${escapeHtml(cat.category)}
                        </div>
                        <div class="amount-val">${money(cat.total_spent)}</div>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${Math.min(cat.percentage, 100)}%; background: ${color};"></div>
                    </div>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('Error loading breakdown:', error);
        list.innerHTML = emptyNote('Failed to load spending breakdown.', true);
    }
}

// ----------------------------------------------------------------- alerts
async function loadAlerts(budgetId, summary) {
    const container = document.getElementById('dashAlertList');
    const alerts = [];

    if (summary) {
        const remaining = Number(summary.remaining_budget);
        if (remaining < 0) {
            alerts.push({
                tone: 'red',
                title: 'Budget exceeded',
                body: `You are ${money(Math.abs(remaining))} over the total budget.`
            });
        } else if (summary.alert_triggered) {
            alerts.push({
                tone: 'amber',
                title: 'Spending threshold reached',
                body: `${money(summary.total_spent)} of ${money(summary.budget.total_budget)} spent. ${money(remaining)} left.`
            });
        }
    }

    // Per-category limit breaches, if the treasurer has set any.
    try {
        const response = await fetch(`/budgets/${budgetId}/category-limits`);
        if (response.ok) {
            const data = await response.json();
            data.categories
                .filter(c => c.over_limit)
                .forEach(c => alerts.push({
                    tone: 'red',
                    title: `${c.category} over its limit`,
                    body: `${money(c.spent)} spent against a ${money(c.limit_amount)} limit.`
                }));

            data.categories
                .filter(c => !c.over_limit && c.limit_amount > 0 && c.percentage >= 80)
                .forEach(c => alerts.push({
                    tone: 'amber',
                    title: `${c.category} nearing its limit`,
                    body: `${c.percentage.toFixed(0)}% of the ${money(c.limit_amount)} limit used.`
                }));
        }
    } catch (error) {
        // Category limits are optional — a missing table shouldn't break the page.
        console.warn('Category limits unavailable:', error);
    }

    if (!alerts.length) {
        alerts.push({
            tone: 'green',
            title: 'Everything on track',
            body: 'No budget thresholds have been crossed.'
        });
    }

    container.innerHTML = alerts.map(renderAlert).join('');
}

function renderAlert(alert) {
    const tones = {
        red: { icon: '!', cls: 'red' },
        amber: { icon: '!', cls: 'yellow' },
        green: { icon: '\u2713', cls: 'green' }
    };
    const tone = tones[alert.tone] || tones.green;
    return `
        <div class="alert-box">
            <div class="alert-icon ${tone.cls}">${tone.icon}</div>
            <div class="alert-content">
                <h4>${escapeHtml(alert.title)}</h4>
                <p>${escapeHtml(alert.body)}</p>
            </div>
        </div>
    `;
}

// --------------------------------------------------------------- activity
async function loadActivity(budgetId) {
    const tbody = document.getElementById('dashActivityBody');
    try {
        const response = await fetch(`/budgets/${budgetId}/expenses`);
        if (!response.ok) throw new Error('Failed to load expenses');
        const expenses = await response.json();

        if (!expenses.length) {
            tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; padding: 24px; color: var(--text-muted);">No activity yet.</td></tr>`;
            return;
        }

        expenses.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

        tbody.innerHTML = expenses.slice(0, 5).map(exp => {
            const date = exp.created_at
                ? new Date(exp.created_at).toLocaleDateString('en-MY', { month: 'short', day: 'numeric', year: 'numeric' })
                : '—';
            const badge = CATEGORY_BADGES[exp.category] || { bg: '#f1f5f9', text: '#475569' };
            return `
                <tr>
                    <td class="td-date">${date}</td>
                    <td class="td-desc">${escapeHtml(exp.title)}</td>
                    <td><span class="cat-badge" style="background: ${badge.bg}; color: ${badge.text};">${escapeHtml(exp.category)}</span></td>
                    <td>-${money(exp.amount)}</td>
                </tr>
            `;
        }).join('');
    } catch (error) {
        console.error('Error loading activity:', error);
        tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; padding: 24px; color: var(--danger-text, #dc2626);">Failed to load activity.</td></tr>`;
    }
}

// ---------------------------------------------------------------- helpers
function money(value) {
    return `RM ${Number(value).toFixed(2)}`;
}

function emptyNote(message, isError) {
    const color = isError ? 'var(--danger-text, #dc2626)' : 'var(--text-muted)';
    return `<p style="font-size: 0.875rem; color: ${color}; padding: 8px 0;">${message}</p>`;
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
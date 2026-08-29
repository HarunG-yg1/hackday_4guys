// ClubVault — Reimbursements page
// Wires the claim form, the four stat cards, and the request table to the API.
// Depends on budget-context.js for window.getBudgetId().

document.addEventListener('DOMContentLoaded', () => {
    const budgetId = window.getBudgetId ? window.getBudgetId() : null;
    const noBudgetCard = document.getElementById('noBudgetCard');
    const content = document.getElementById('reimbursementsContent');

    if (!budgetId) {
        noBudgetCard.style.display = 'block';
        content.style.display = 'none';
        return;
    }

    noBudgetCard.style.display = 'none';
    content.style.display = 'block';

    refreshAll(budgetId);

    const form = document.getElementById('reimbursementForm');
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const submitBtn = document.getElementById('reimbursementSubmitBtn');
        const originalText = submitBtn.textContent;
        submitBtn.disabled = true;
        submitBtn.textContent = 'Submitting...';

        try {
            await submitClaim(budgetId);
            form.reset();
            await refreshAll(budgetId);
        } catch (error) {
            console.error('Failed to submit reimbursement:', error);
            alert('Failed to submit reimbursement. Check console for details.');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        }
    });

    // Client-side search over the rendered table
    const search = document.getElementById('reimbursementSearch');
    if (search) {
        search.addEventListener('input', () => {
            const term = search.value.toLowerCase();
            document.querySelectorAll('#reimbursementTableBody tr').forEach((row) => {
                row.style.display = row.textContent.toLowerCase().includes(term) ? '' : 'none';
            });
        });
    }
});

async function refreshAll(budgetId) {
    await Promise.all([loadStats(budgetId), loadClaims(budgetId)]);
}

// ---------------------------------------------------------------- submit
async function submitClaim(budgetId) {
    const payload = {
        budget_id: budgetId,
        claimant_name: document.getElementById('claimantName').value,
        category: document.getElementById('claimCategory').value,
        amount: parseFloat(document.getElementById('claimAmount').value),
        description: document.getElementById('claimDescription').value || null,
        status: 'Pending'
    };

    const response = await fetch('/reimbursements', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    if (!response.ok) throw new Error(`Submit failed: ${response.status}`);
    return response.json();
}

// ---------------------------------------------------------------- stats
async function loadStats(budgetId) {
    try {
        const response = await fetch(`/reimbursements/stats?budget_id=${budgetId}`);
        if (!response.ok) throw new Error('Failed to load stats');
        const s = await response.json();

        setText('statTotalRequests', s.total_requests);
        setText('statPendingReview', s.pending_review);
        setText('statApproved', `RM ${s.approved_amount.toFixed(2)}`);
        setText('statAvailable', `RM ${s.available_budget.toFixed(2)}`);
    } catch (error) {
        console.error('Error loading reimbursement stats:', error);
        ['statTotalRequests', 'statPendingReview', 'statApproved', 'statAvailable']
            .forEach(id => setText(id, '—'));
    }
}

// ---------------------------------------------------------------- table
async function loadClaims(budgetId) {
    const tbody = document.getElementById('reimbursementTableBody');
    try {
        const response = await fetch(`/reimbursements?budget_id=${budgetId}`);
        if (!response.ok) throw new Error('Failed to load reimbursements');
        const claims = await response.json();

        if (!claims.length) {
            tbody.innerHTML = emptyRow('No reimbursement requests yet.');
            return;
        }

        tbody.innerHTML = claims.map(renderRow).join('');
        wireStatusButtons(budgetId);
    } catch (error) {
        console.error('Error loading reimbursements:', error);
        tbody.innerHTML = emptyRow('Failed to load requests.', true);
    }
}

function renderRow(claim) {
    const date = claim.created_at
        ? new Date(claim.created_at).toLocaleDateString('en-MY', {
              month: 'short', day: 'numeric', year: 'numeric'
          })
        : '—';

    const actions = claim.status === 'Pending'
        ? `<div class="claim-actions">
             <button class="btn-approve" data-id="${claim.id}" data-status="Approved">Approve</button>
             <button class="btn-reject" data-id="${claim.id}" data-status="Rejected">Reject</button>
           </div>`
        : '';

    return `
        <tr>
            <td>
                <div style="display: flex; flex-direction: column;">
                    <strong style="color: var(--text-main);">${escapeHtml(claim.description || 'Reimbursement claim')}</strong>
                    <span style="font-size: 0.75rem; color: var(--text-muted);">${escapeHtml(claim.category || 'Uncategorized')}</span>
                </div>
            </td>
            <td>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <div class="table-avatar">${initials(claim.claimant_name)}</div>
                    ${escapeHtml(claim.claimant_name || 'Unknown')}
                </div>
            </td>
            <td class="td-date">${date}</td>
            <td>${statusBadge(claim.status)}${actions}</td>
            <td>RM ${Number(claim.amount).toFixed(2)}</td>
        </tr>
    `;
}

function wireStatusButtons(budgetId) {
    document.querySelectorAll('#reimbursementTableBody [data-status]').forEach((btn) => {
        btn.addEventListener('click', async () => {
            btn.disabled = true;
            try {
                const response = await fetch(`/reimbursements/${btn.dataset.id}/status`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ status: btn.dataset.status })
                });
                if (!response.ok) throw new Error(`Status update failed: ${response.status}`);
                await refreshAll(budgetId);
            } catch (error) {
                console.error('Failed to update status:', error);
                alert('Could not update the claim status.');
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

function initials(name) {
    if (!name) return '??';
    return name.trim().split(/\s+/).slice(0, 2).map(w => w[0].toUpperCase()).join('');
}

function emptyRow(message, isError) {
    const color = isError ? 'var(--danger-text, #dc2626)' : 'var(--text-muted)';
    return `<tr><td colspan="5" style="text-align:center; padding: 24px; color: ${color};">${message}</td></tr>`;
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
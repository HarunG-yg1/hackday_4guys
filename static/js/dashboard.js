document.addEventListener('DOMContentLoaded', () => {
    const createCard = document.getElementById('createBudgetCard');
    const dashboardContent = document.getElementById('dashboardContent');
    const budgetId = window.getBudgetId ? window.getBudgetId() : null;

    if (!budgetId) {
        // No budget yet — show the create-budget form instead of the dashboard.
        createCard.style.display = 'block';
        dashboardContent.style.display = 'none';
    } else {
        createCard.style.display = 'none';
        dashboardContent.style.display = 'block';
        loadBudgetSummary(budgetId);
        loadAnalyticsBreakdown(budgetId);
    }

    // UI Interactions: Ctrl + K Search
    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            // Trigger your search modal/focus here
            console.log('Search shortcut triggered');
        }
    });
});

// Fetch Summary & Manage Alerts
async function loadBudgetSummary(budgetId) {
    try {
        const response = await fetch(`/budgets/${budgetId}`);
        if (!response.ok) throw new Error('Failed to load summary');
        const data = await response.json();

        // Update Summary Cards
        const amounts = document.querySelectorAll('#dashboardContent .summary-card .amount');
        if (amounts[1]) amounts[1].textContent = `RM ${data.budget.total_budget.toFixed(2)}`;
        if (amounts[2]) amounts[2].textContent = `RM ${data.total_spent.toFixed(2)}`;

        // Update Alert Box if threshold is reached
        const alertIcon = document.querySelector('#dashboardContent .alert-box .alert-icon.red');
        const alertBox = alertIcon ? alertIcon.closest('.alert-box') : null;
        if (alertBox) {
            if (data.alert_triggered) {
                alertBox.style.display = 'flex';
                alertBox.querySelector('h4').textContent = 'Budget Threshold Alert';
                alertBox.querySelector('p').textContent =
                    `You have spent RM ${data.total_spent.toFixed(2)} of your RM ${data.budget.total_budget.toFixed(2)} allocation.`;
            } else {
                alertBox.style.display = 'none'; // Hide if under budget
            }
        }
    } catch (error) {
        console.error('Error loading budget summary:', error);
    }
}

// Fetch Analytics & Update Progress Bars
async function loadAnalyticsBreakdown(budgetId) {
    try {
        const response = await fetch(`/budgets/${budgetId}/analytics`);
        if (!response.ok) throw new Error('Failed to load analytics');
        const analytics = await response.json();

        // Update the custom HTML progress bars
        const breakdownItems = document.querySelectorAll('#dashboardContent .breakdown-item');

        analytics.categories.forEach(catData => {
            // Find the matching HTML element by category name
            const item = Array.from(breakdownItems).find(el => el.textContent.includes(catData.category));
            if (item) {
                item.querySelector('.amount-val').textContent = `RM ${catData.total_spent.toFixed(2)}`;
                item.querySelector('.progress-fill').style.width = `${catData.percentage}%`;
            }
        });
    } catch (error) {
        console.error('Error loading analytics:', error);
    }
}
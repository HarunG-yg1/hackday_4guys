document.addEventListener('DOMContentLoaded', () => {
    // 1. Get Budget ID from URL (e.g., dashboard.html?budgetId=123)
    const urlParams = new URLSearchParams(window.location.search);
    const currentBudgetId = urlParams.get('budgetId') || 'default-budget-id'; // Replace with actual default handling

    // 2. Initialize Dashboard
    if (currentBudgetId) {
        loadBudgetSummary(currentBudgetId);
        loadAnalyticsBreakdown(currentBudgetId);
    }

    // 3. UI Interactions: Ctrl + K Search
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
        document.querySelectorAll('.summary-card .amount')[1].textContent = `RM ${data.budget.total_budget.toFixed(2)}`;
        document.querySelectorAll('.summary-card .amount')[2].textContent = `RM ${data.total_spent.toFixed(2)}`;
        
        // Update Alert Box if threshold is reached
        const alertBox = document.querySelector('.alert-box .alert-icon.red').closest('.alert-box');
        if (data.alert_triggered) {
            alertBox.style.display = 'flex';
            alertBox.querySelector('h4').textContent = 'Budget Threshold Alert';
            alertBox.querySelector('p').textContent = `You have spent RM ${data.total_spent.toFixed(2)} of your RM ${data.budget.total_budget.toFixed(2)} allocation.`;
        } else {
            alertBox.style.display = 'none'; // Hide if under budget
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
        const breakdownItems = document.querySelectorAll('.breakdown-item');
        
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
document.addEventListener('DOMContentLoaded', () => {
    const createBudgetForm = document.getElementById('createBudgetForm');

    if (createBudgetForm) {
        createBudgetForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const submitBtn = createBudgetForm.querySelector('button[type="submit"]');
            const eventName = document.getElementById('eventName').value;
            const totalAmount = document.getElementById('totalAmount').value;

            // UI Loading State
            const originalText = submitBtn.textContent;
            submitBtn.disabled = true;
            submitBtn.textContent = 'Opening Vault...';

            try {
                const newBudget = await createBudget(eventName, totalAmount);
                // Success: Route to the new budget dashboard
                window.location.href = `dashboard.html?budgetId=${newBudget.id}`;
            } catch (error) {
                console.error('Failed to create budget:', error);
                alert('Failed to create budget. Check console for details.');
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
            }
        });
    }
});

// Backend Dev's API Call
async function createBudget(eventName, totalAmount) {
    const response = await fetch('/budgets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            event_name: eventName,
            total_budget: parseFloat(totalAmount),
            alert_threshold: 0.8
        })
    });

    if (!response.ok) throw new Error('Network response was not ok');
    
    const newBudget = await response.json();
    return newBudget;
}
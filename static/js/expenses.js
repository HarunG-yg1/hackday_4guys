document.addEventListener('DOMContentLoaded', () => {
    const receiptForm = document.getElementById('receiptUploadForm');
    const urlParams = new URLSearchParams(window.location.search);
    const budgetId = urlParams.get('budgetId');

    if (receiptForm) {
        receiptForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const fileInput = document.getElementById('receiptImage');
            const submitBtn = receiptForm.querySelector('button[type="submit"]');
            
            if (!fileInput.files.length) return alert('Please select an image first.');

            // UI Loading State
            const originalText = submitBtn.textContent;
            submitBtn.disabled = true;
            submitBtn.textContent = 'Scanning with AI...';

            await scanAndSaveReceipt(budgetId, fileInput.files[0]);

            // Reset UI
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
            fileInput.value = ''; // Clear input
            
            // Refresh table
            refreshExpenseTable(budgetId);
        });
    }
});

// Backend Dev's OCR Integration
async function scanAndSaveReceipt(budgetId, imageFile) {
    const formData = new FormData();
    formData.append('budget_id', budgetId);
    formData.append('file', imageFile);

    try {
        const response = await fetch('/expenses/scan-and-save', {
            method: 'POST',
            body: formData // Content-Type is intentionally omitted
        });

        if (!response.ok) throw new Error('Failed to scan receipt');

        const newExpense = await response.json();
        alert(`Successfully logged RM ${newExpense.amount} for ${newExpense.title}`);
        return newExpense;
    } catch (err) {
        console.error('OCR Error:', err);
        alert('Failed to scan receipt. Please try again.');
    }
}

// Fetch & Render Expense List
async function refreshExpenseTable(budgetId) {
    try {
        const response = await fetch(`/budgets/${budgetId}/expenses`);
        const expenses = await response.json();
        // Logic to clear and append <tr> rows to your .activity-table goes here
        console.log('Latest Expenses:', expenses);
    } catch (error) {
        console.error('Error fetching expenses:', error);
    }
}
document.addEventListener('DOMContentLoaded', () => {
    // Keyboard Shortcut trigger for Search (Ctrl + K)
    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
            e.preventDefault();
            const searchBar = document.querySelector('.topbar-search');
            if (searchBar) {
                searchBar.click();
            }
        }
    });

    // Form confirmation guard on submitting negative allocations
    const budgetForms = document.querySelectorAll('form[action="/update-category"], form[action="/add-category"]');
    budgetForms.forEach(form => {
        form.addEventListener('submit', (e) => {
            const amountInput = form.querySelector('input[type="number"]');
            if (amountInput && parseFloat(amountInput.value) < 0) {
                e.preventDefault();
                alert('Please enter a valid positive allocation amount.');
            }
        });
    });
});

async function deleteCategory(categoryId, eventId) {
    if (confirm("Are you sure you want to remove this category?")) {
        try {
            const response = await fetch(`/delete-category/${categoryId}`, {
                method: "DELETE", // or POST depending on your FastAPI route
            });

            if (response.ok) {
                // Reload the page to reflect changes
                window.location.href = `/budget-page?event_id=${eventId}`;
            } else {
                alert("Failed to delete category.");
            }
        } catch (error) {
            console.error("Error deleting category:", error);
        }
    }
}
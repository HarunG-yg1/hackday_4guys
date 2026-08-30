```javascript
document.addEventListener('DOMContentLoaded', () => {

    // =========================================================
    // EVENT MODAL
    // =========================================================

    const eventModal = document.getElementById('eventModal');

    // Open modal
    const newEventButton = document.querySelector('.event-actions .btn-save');

    if (newEventButton && eventModal) {
        newEventButton.addEventListener('click', () => {
            eventModal.style.display = 'flex';
        });
    }

    // Close modal when clicking outside the modal
    if (eventModal) {
        eventModal.addEventListener('click', (event) => {
            if (event.target === eventModal) {
                eventModal.style.display = 'none';
            }
        });
    }

    // Close modal with ESC
    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && eventModal) {
            eventModal.style.display = 'none';
        }
    });

});
```

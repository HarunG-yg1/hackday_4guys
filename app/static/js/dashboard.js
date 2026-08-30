document.addEventListener("DOMContentLoaded", () => {
    // 1. Highlight Active Sidebar Navigation Link
    const currentPath = window.location.pathname;
    const navItems = document.querySelectorAll(".nav-item");

    navItems.forEach((item) => {
        const href = item.getAttribute("href");
        if (href && currentPath.includes(href)) {
            item.classList.add("active");
        }
    });

    // 2. Profile Dropdown Toggle
    const profileBtn = document.querySelector(".profile-menu");
    if (profileBtn) {
        profileBtn.addEventListener("click", () => {
            profileBtn.classList.toggle("open");
        });
    }
});
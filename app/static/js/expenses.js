document.addEventListener("DOMContentLoaded", () => {
    const fileInput = document.getElementById("receipt");

    if (fileInput) {
        fileInput.addEventListener("change", (e) => {
            const fileName = e.target.files[0] ? e.target.files[0].name : "No file chosen";
            console.log(`Selected receipt file: ${fileName}`);
        });
    }
});
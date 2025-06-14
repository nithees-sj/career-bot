document.getElementById("studentForm").addEventListener("submit", async function (event) {
    event.preventDefault();

    // Check authentication
    const userId = localStorage.getItem("user_id");
    const userEmail = localStorage.getItem("userEmail");
    if (!userId || !userEmail) {
        alert("Session expired. Please login again.");
        window.location.href = "login.html";
        return;
    }

    // Validate all fields before submission
    const formElements = event.target.elements;
    let isValid = true;

    Array.from(formElements).forEach(element => {
        if (element.required && !element.value.trim()) {
            isValid = false;
            element.classList.add("error");
            alert(`Please fill in: ${element.labels[0].textContent}`);
        }
    });

    if (!isValid) return;

    let formData = new FormData(event.target);
    let jsonData = {
        ...Object.fromEntries(formData.entries()),
        user_id: userId,          // Add user_id from localStorage
        email: userEmail          // Add email from localStorage
    };

    // Store data locally
    localStorage.setItem("studentData", JSON.stringify(jsonData));

    try {
        let response = await fetch("http://127.0.0.1:5000/submit", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(jsonData)
        });

        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        let result = await response.json();
        
        if (result.message.includes("success")) {
            
            window.location.href = "chatbot.html";
        } else {
            alert("Error: " + (result.error || "Submission failed"));
        }
    } catch (error) {
        alert("Connection Error: " + error.message);
        console.error("Submission Error:", error);
    }
});
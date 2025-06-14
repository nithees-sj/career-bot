function switchTab(tab) {
    document.querySelectorAll('.tab, .form').forEach(el => {
        el.classList.remove('active');
    });
    document.getElementById(`${tab}Form`).classList.add('active');
    document.querySelector(`[onclick="switchTab('${tab}')"]`).classList.add('active');
}

// Registration
document.getElementById("registerForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = document.getElementById("registerEmail").value;
    const password = document.getElementById("registerPassword").value;
    const confirmPassword = document.getElementById("confirmpassword").value;
    
    // Check if passwords match
    if (password !== confirmPassword) {
        alert("Passwords do not match!");
        return;
    }

    try {
        const response = await fetch("http://127.0.0.1:5000/register", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();
        if (response.ok) {
            localStorage.setItem("user_id", data.user_id);
            localStorage.setItem("userEmail", email);
            window.location.href = "script.html";
        } else {
            alert(data.error || "Registration failed");
        }
    } catch (error) {
        alert("Connection error");
    }
});

// Password match check (real-time)
document.getElementById("registerPassword").addEventListener("input", toggleRegisterButton);
document.getElementById("confirmpassword").addEventListener("input", toggleRegisterButton);

function toggleRegisterButton() {
    const password = document.getElementById("registerPassword").value;
    const confirmPassword = document.getElementById("confirmpassword").value;
    const registerButton = document.querySelector('button[type="submit"]');
    
    if (password === confirmPassword && password.length > 0) {
        registerButton.disabled = false;
        registerButton.classList.remove("disabled");
    } else {
        registerButton.disabled = true;
        registerButton.classList.add("disabled");
    }
}


// Login
document.getElementById("loginForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = document.getElementById("loginEmail").value;
    const password = document.getElementById("loginPassword").value;

    try {
        const response = await fetch("http://127.0.0.1:5000/login", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();
        if (data.success) {
            localStorage.setItem("user_id", data.user_id);
            localStorage.setItem("userEmail", email);
            checkProfileExists(data.user_id);
        } else {
            alert(data.error || "Login failed");
        }
    } catch (error) {
        alert("Login failed");
    }
});

async function checkProfileExists(userId) {
    try {
        const response = await fetch(`http://127.0.0.1:5000/check_profile/${userId}`);
        const data = await response.json();
        
        if (data.hasProfile) {
            window.location.href = "chatbot.html";
        } else {
            window.location.href = "script.html";
        }
    } catch (error) {
        alert("Profile check failed");
    }
}

// Auto-logout after 1 hour
setTimeout(() => {
    localStorage.clear();
    window.location.href = "login.html";
}, 3600000);
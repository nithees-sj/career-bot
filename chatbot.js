document.addEventListener("DOMContentLoaded", async function () {
    // Check authentication first
    const userId = localStorage.getItem("user_id");
    const userEmail = localStorage.getItem("userEmail");
    if (!userId || !userEmail) {
        window.location.href = "login.html";
        return;
    }

    // Clear previous session data
    sessionStorage.removeItem("chatHistory");
    document.getElementById("messages").innerHTML = "";

    let studentData = JSON.parse(localStorage.getItem("studentData"));
    let chatHistory = [];

    try {
        // Fetch user details from backend if not in localStorage
        if (!studentData) {
            const response = await fetch(`http://127.0.0.1:5000/api/user/${userId}`);
            const result = await response.json();
            
            if (!response.ok) throw new Error(result.error || "Failed to fetch user data");
            
            studentData = result;
            localStorage.setItem("studentData", JSON.stringify(result));
        }

        // Display loading state
        const loadingMsg = document.createElement("p");
        loadingMsg.textContent = "Analyzing your profile...";
        document.getElementById("messages").appendChild(loadingMsg);

        // Get career summary with proper user context
        const summaryResponse = await fetch("http://127.0.0.1:5000/career_summary", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                ...studentData,
                user_id: userId,
                email: userEmail
            })
        });

        const summaryResult = await summaryResponse.json();
        
        if (summaryResult.summary) {
            displayMessage("Hello, I'm Novard — your AI career assistant. How can I assist you?", "bot");
        } else {
            displayMessage("Could not generate career summary. Please try asking questions directly.", "bot");
        }

    } catch (error) {
        console.error("Initialization Error:", error);
        displayMessage(`Error initializing chat - ${error.message}`, "bot");
    }
});

// Modified sendMessage function
async function sendMessage() {
    const userInput = document.getElementById("userInput").value.trim();
    if (!userInput) return;

    try {
        displayMessage(`You: ${userInput}`, "user");
        
        // Clear input immediately
        document.getElementById("userInput").value = "";

        const response = await fetch("http://127.0.0.1:5000/chatbot", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: userInput,
                user_id: localStorage.getItem("user_id"),  // Use user_id instead of email
                email: localStorage.getItem("userEmail")
            })
        });

        if (!response.ok) throw new Error("Failed to get bot response");

        const result = await response.json();
        displayMessage(`${result.response}`, "bot");
        saveToHistory(result.response, "bot");

    } catch (error) {
        console.error("Chat Error:", error);
        displayMessage(`Error processing request - ${error.message}`, "bot");
    }
}
//newly added to move next usind enter button
document.getElementById("userInput").addEventListener("keypress", function(event) {
    if (event.key === "Enter") {
        sendMessage();
    }
});


// Rest of the functions remain the same with improved error handling
function displayMessage(message, sender) {
    const chatbox = document.getElementById("messages");
    const msgDiv = document.createElement("div");
    msgDiv.textContent = message;
    msgDiv.className = sender;
    
    // Add typing animation for bot messages
    if (sender === "bot") {
        msgDiv.classList.add("loading");
        setTimeout(() => msgDiv.classList.remove("loading"), 1000);
    }
    
    chatbox.appendChild(msgDiv);
    chatbox.scrollTop = chatbox.scrollHeight;
}

function saveToHistory(text, sender) {
    const chatHistory = JSON.parse(sessionStorage.getItem("chatHistory")) || [];
    chatHistory.push({ text, sender });
    sessionStorage.setItem("chatHistory", JSON.stringify(chatHistory));
}

window.addEventListener("beforeunload", () => {
    sessionStorage.removeItem("chatHistory");
});
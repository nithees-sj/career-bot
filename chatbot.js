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

    // Setup mode switch handlers (default to Doubts view initially)
    setupModes({ defaultMode: 'doubts' });
    // Initialize doubts module (load list for user)
    initDoubts();

    // OCR bind
    const extractBtn = document.getElementById("extractTextBtn");
    if (extractBtn) {
        extractBtn.addEventListener("click", extractOcrToDescription);
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

// ---------------- Doubt Module -----------------
let selectedDoubtId = null;

function setupModes(options = {}) {
    const modeChat = document.getElementById("modeChat");
    const modeDoubts = document.getElementById("modeDoubts");
    const chatSection = document.getElementById("chatSection");
    const doubtsSection = document.getElementById("doubtsSection");

    if (!modeChat || !modeDoubts) return; // If UI not present, skip

    modeChat.addEventListener("click", () => {
        modeChat.classList.add("active");
        modeDoubts.classList.remove("active");
        chatSection.classList.remove("hidden");
        doubtsSection.classList.add("hidden");
    });
    modeDoubts.addEventListener("click", () => {
        modeDoubts.classList.add("active");
        modeChat.classList.remove("active");
        chatSection.classList.add("hidden");
        doubtsSection.classList.remove("hidden");
    });

    // Default mode setup
    if (options.defaultMode === 'doubts') {
        modeDoubts.click();
    } else if (options.defaultMode === 'chat') {
        modeChat.click();
    }
}

async function initDoubts() {
    const createBtn = document.getElementById("createDoubtBtn");
    const filter = document.getElementById("doubtFilter");
    const replyBtn = document.getElementById("sendDoubtReplyBtn");
    const resolveBtn = document.getElementById("resolveDoubtBtn");

    if (createBtn) {
        createBtn.addEventListener("click", createDoubt);
    }
    if (filter) {
        filter.addEventListener("change", () => loadDoubts(filter.value));
    }
    if (replyBtn) {
        replyBtn.addEventListener("click", sendDoubtReply);
    }
    if (resolveBtn) {
        resolveBtn.addEventListener("click", resolveDoubt);
    }

    await loadDoubts("open");
}

async function loadDoubts(status = "") {
    const userId = localStorage.getItem("user_id");
    if (!userId) return;
    const params = new URLSearchParams();
    params.set("user_id", userId);
    if (status) params.set("status", status);
    const container = document.getElementById("doubtsContainer");
    if (!container) return;
    container.innerHTML = "Loading...";
    try {
        const resp = await fetch(`http://127.0.0.1:5000/api/doubts?${params.toString()}`);
        const data = await resp.json();
        const doubts = data.doubts || [];
        if (doubts.length === 0) {
            container.innerHTML = "No doubts yet.";
            renderDoubtDetail(null);
            return;
        }
        container.innerHTML = "";
        doubts.forEach(d => {
            const item = document.createElement("div");
            item.className = "doubt-item";
            item.innerHTML = `<div class="title">${escapeHtml(d.title)}</div>
                              <div class="meta">#${d.id} • ${d.status} • ${new Date(d.updated_at).toLocaleString()}</div>`;
            item.addEventListener("click", () => selectDoubt(d.id, d.title, d.status));
            container.appendChild(item);
        });
        // Auto-select first doubt if none selected
        if (!selectedDoubtId && doubts[0]) {
            selectDoubt(doubts[0].id, doubts[0].title, doubts[0].status);
        }
    } catch (e) {
        container.innerHTML = `Error loading doubts: ${e.message}`;
    }
}

async function createDoubt() {
    const titleEl = document.getElementById("doubtTitle");
    const questionEl = document.getElementById("doubtQuestion");
    const title = (titleEl?.value || "").trim();
    const question = (questionEl?.value || "").trim();
    const userId = localStorage.getItem("user_id");
    if (!title || !question) {
        alert("Please enter both title and question.");
        return;
    }
    try {
        const resp = await fetch("http://127.0.0.1:5000/api/doubts", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: userId, title, question })
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.error || "Failed to create doubt");
        titleEl.value = "";
        questionEl.value = "";
        // Load list and auto-open the newly created doubt
        await loadDoubts("open");
        if (data.doubt_id) {
            await selectDoubt(data.doubt_id, title, "open");
            // After selecting, fetch thread again to include AI auto-reply
            await loadDoubtThread();
        }
    } catch (e) {
        alert(e.message);
    }
}

async function selectDoubt(doubtId, title, status) {
    selectedDoubtId = doubtId;
    const header = document.getElementById("doubtDetailHeader");
    header.textContent = `#${doubtId} • ${title} • ${status}`;
    document.getElementById("sendDoubtReplyBtn").disabled = false;
    document.getElementById("resolveDoubtBtn").disabled = status !== "open";
    await loadDoubtThread();
}

async function loadDoubtThread() {
    if (!selectedDoubtId) return;
    const userId = localStorage.getItem("user_id");
    const msgBox = document.getElementById("doubtMessages");
    msgBox.innerHTML = "Loading...";
    try {
        const params = new URLSearchParams({ user_id: userId });
        const resp = await fetch(`http://127.0.0.1:5000/api/doubts/${selectedDoubtId}?${params.toString()}`);
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.error || "Failed to load doubt");
        renderDoubtDetail(data);
        // Ensure scroll sticks to bottom after render
        const msgBox2 = document.getElementById("doubtMessages");
        msgBox2.scrollTop = msgBox2.scrollHeight;
    } catch (e) {
        msgBox.innerHTML = `Error: ${e.message}`;
    }
}

function renderDoubtDetail(data) {
    const msgBox = document.getElementById("doubtMessages");
    if (!data) {
        document.getElementById("doubtDetailHeader").textContent = "Select a doubt to view details";
        msgBox.innerHTML = "";
        document.getElementById("sendDoubtReplyBtn").disabled = true;
        document.getElementById("resolveDoubtBtn").disabled = true;
        return;
    }
    const { doubt, messages } = data;
    document.getElementById("doubtDetailHeader").textContent = `#${doubt.id} • ${doubt.title} • ${doubt.status}`;
    document.getElementById("resolveDoubtBtn").disabled = doubt.status !== "open";
    // Virtualize/limit to last 100 messages to avoid huge DOM and scroll glitches
    msgBox.innerHTML = "";
    (messages || []).forEach(m => {
        const div = document.createElement("div");
        div.className = `doubt-msg ${m.sender}`;
        if (m.sender === 'bot') {
            // Render Markdown for bot replies
            div.innerHTML = renderMarkdown(m.message);
        } else {
            div.textContent = `You: ${m.message}`;
        }
        msgBox.appendChild(div);
    });
    msgBox.scrollTop = msgBox.scrollHeight;
}

async function sendDoubtReply() {
    if (!selectedDoubtId) return;
    const userId = localStorage.getItem("user_id");
    const text = (document.getElementById("doubtReplyInput").value || "").trim();
    const useAi = document.getElementById("useAiReply").checked;
    if (!text) return;
    try {
        const resp = await fetch(`http://127.0.0.1:5000/api/doubts/${selectedDoubtId}/reply`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: userId, message: text, use_ai: useAi })
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.error || "Failed to reply");
        document.getElementById("doubtReplyInput").value = "";
        renderDoubtDetail({ doubt: { id: selectedDoubtId, title: document.getElementById("doubtDetailHeader").textContent, status: "open" }, messages: data.messages });
        await loadDoubts(document.getElementById("doubtFilter").value || "");
    } catch (e) {
        alert(e.message);
    }
}

async function resolveDoubt() {
    if (!selectedDoubtId) return;
    const userId = localStorage.getItem("user_id");
    const notes = (document.getElementById("resolveNotes").value || "").trim();
    try {
        const resp = await fetch(`http://127.0.0.1:5000/api/doubts/${selectedDoubtId}/resolve`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_id: userId, resolution_notes: notes })
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.error || "Failed to resolve");
        document.getElementById("resolveNotes").value = "";
        await loadDoubts(document.getElementById("doubtFilter").value || "");
        // Refresh thread after resolve
        await loadDoubtThread();
    } catch (e) {
        alert(e.message);
    }
}

function escapeHtml(str) {
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

async function extractOcrToDescription() {
    const fileInput = document.getElementById("doubtImage");
    const statusEl = document.getElementById("ocrStatus");
    const questionEl = document.getElementById("doubtQuestion");
    const file = fileInput?.files?.[0];
    if (!file) {
        statusEl.textContent = "Select an image first";
        return;
    }
    statusEl.textContent = "Extracting text...";
    try {
        const { createWorker } = Tesseract;
        const worker = await createWorker('eng');
        const ret = await worker.recognize(file);
        await worker.terminate();
        const text = (ret?.data?.text || '').trim();
        if (text) {
            // Append or replace based on existing content
            if (questionEl.value.trim()) {
                questionEl.value += "\n\n" + text;
            } else {
                questionEl.value = text;
            }
            statusEl.textContent = "Text extracted";
        } else {
            statusEl.textContent = "No text found";
        }
    } catch (e) {
        console.error(e);
        statusEl.textContent = "OCR failed";
    }
}

// Minimal Markdown renderer (headings, lists, bold/italic, code)
function renderMarkdown(md) {
    let html = escapeHtml(md);
    // code blocks ```
    html = html.replace(/```([\s\S]*?)```/g, function(_, code) {
        return '<pre><code>' + code.replace(/\n/g, '<br/>') + '</code></pre>';
    });
    // inline code `code`
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    // bold **text**
    html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    // italic *text*
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    // headings
    html = html.replace(/^###\s+(.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^##\s+(.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^#\s+(.+)$/gm, '<h1>$1</h1>');
    // unordered list
    html = html.replace(/^(?:-\s+.+\n?)+/gm, function(block) {
        const items = block.trim().split(/\n/).map(li => li.replace(/^-\s+/, '')).map(t => '<li>' + t + '</li>').join('');
        return '<ul>' + items + '</ul>';
    });
    // paragraphs
    html = html.replace(/^(?!<h\d|<ul|<pre|<code)(.+)$/gm, '<p>$1</p>');
    return html;
}
const API_URL = "http://127.0.0.1:8000";

let mode = "simple";
let analyticsChart;
let stream = null;

// ================= HELPER =================
function getAuthHeaders() {
    const token = localStorage.getItem("token");

    if (!token) {
        console.warn("No token found!");
        return {};
    }

    return {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
    };
}

// ================= INIT =================
window.onload = () => {
    const token = localStorage.getItem("token");

    if (token) {
        showDashboard();

        setTimeout(() => {
            loadProfile();
            loadHistory();
            loadAnalytics();
        }, 500);

        setMode("simple");
    } else {
        showLogin();
    }

    const input = document.getElementById("chat-input");
    if (input) {
        input.addEventListener("keypress", (e) => {
            if (e.key === "Enter") sendMessage();
        });
    }

    const form = document.getElementById("healthForm");
    if (form) {
        form.addEventListener("submit", handleFormSubmit);
    }
};

// ================= UI =================
function showDashboard() {
    document.getElementById("loginPage").style.display = "none";
    document.getElementById("dashboard").style.display = "flex";
}

function showLogin() {
    document.getElementById("loginPage").style.display = "flex";
    document.getElementById("dashboard").style.display = "none";
}

// ================= LOGIN =================
async function login() {
    showLoader("Logging in...");

    try {
        const res = await fetch(`${API_URL}/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                email: email.value,
                password: password.value
            })
        });

        const data = await res.json();

        if (res.ok) {
            localStorage.setItem("token", data.access_token);
            showSuccess("Login successful 🚀");

            setTimeout(() => {
                showDashboard();
                loadProfile();
                loadHistory();
                loadAnalytics();
            }, 500);

        } else {
            showError(data.detail || "Login failed");
        }

    } catch {
        showError("Server error!");
    }
}

// ================= REGISTER =================
async function register() {
    try {
        const res = await fetch(`${API_URL}/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                email: email.value,
                password: password.value
            })
        });

        const data = await res.json();

        if (res.ok) {
            showSuccess("Registered! Now login.");
        } else {
            showError(data.detail);
        }

    } catch {
        showError("Register failed");
    }
}

// ================= LOGOUT =================
function logout() {
    localStorage.clear();
    location.reload();
}

// ================= PROFILE =================
async function loadProfile() {
    try {
        const res = await fetch(`${API_URL}/profile`, {
            headers: getAuthHeaders()
        });

        if (res.status === 401) {
            logout();
            return;
        }

        const user = await res.json();
        document.getElementById("profileBox").innerHTML =
            `<h2>👤 ${user.email || "User"}</h2>`;
    } catch {
        document.getElementById("profileBox").innerHTML = "⚠️ Profile error";
    }
}

// ================= HISTORY =================
async function loadHistory() {
    try {
        const res = await fetch(`${API_URL}/history`, {
            headers: getAuthHeaders()
        });

        if (res.status === 401) {
            logout();
            return;
        }

        const data = await res.json();

        const container = document.getElementById("history");
        container.innerHTML = "";

        if (!data.length) {
            container.innerHTML = "No history yet";
            return;
        }

        data.forEach(i => {
            container.innerHTML += `
                <div class="history-card">
                    ${i.result} (${(i.score * 100).toFixed(1)}%)
                </div>`;
        });

    } catch {
        document.getElementById("history").innerHTML = "⚠️ History error";
    }
}

// ================= ANALYTICS =================
async function loadAnalytics() {
    try {
        const res = await fetch(`${API_URL}/analytics`, {
            headers: getAuthHeaders()
        });

        if (res.status === 401) {
            logout();
            return;
        }

        const data = await res.json();

        if (analyticsChart) analyticsChart.destroy();

        analyticsChart = new Chart(document.getElementById("analyticsChart"), {
            type: "bar",
            data: {
                labels: ["Total", "High Risk"],
                datasets: [{
                    data: [data.total_scans || 0, data.high_risk_cases || 0]
                }]
            }
        });

    } catch { }
}

// ================= CHAT =================
async function sendMessage() {
    const input = document.getElementById("chat-input");
    const chatBox = document.getElementById("chat-box");

    const text = input.value.trim();
    if (!text) return;

    chatBox.innerHTML += `<div>🧑 ${text}</div>`;

    try {
        const res = await fetch(`${API_URL}/chat`, {
            method: "POST",
            headers: getAuthHeaders(),
            body: JSON.stringify({ message: text })
        });

        const data = await res.json();

        chatBox.innerHTML += `<div>🤖 ${data.reply}</div>`;
        speakText(data.reply);

    } catch {
        chatBox.innerHTML += `<div>⚠️ Error</div>`;
    }

    input.value = "";
}

// ================= VOICE =================
function startListening() {
    if (!('webkitSpeechRecognition' in window)) {
        alert("Voice not supported");
        return;
    }

    const recognition = new webkitSpeechRecognition();
    recognition.start();

    recognition.onresult = function (event) {
        const text = event.results[0][0].transcript;
        document.getElementById("chat-input").value = text;
        sendMessage();
    };
}

// ================= SPEECH =================
function speakText(text) {
    const speech = new SpeechSynthesisUtterance(text);
    window.speechSynthesis.speak(speech);
}
const API_URL = "https://ai-health-backend-g329.onrender.com";

let chart;
let analyticsChart;
let mode = localStorage.getItem("mode") || "simple";
let chatHistory = JSON.parse(localStorage.getItem("chatHistory")) || [];

// ================= SAFE ELEMENT GET =================
function getEl(id) {
    return document.getElementById(id);
}

// ================= ELEMENTS =================
const loginPage = getEl("loginPage");
const dashboard = getEl("dashboard");
const profileBox = getEl("profileBox");
const historyDiv = getEl("history");
const resultDiv = getEl("result");
const loginStatus = getEl("loginStatus");

// ================= AUTO LOAD =================
window.onload = () => {
    const token = localStorage.getItem("token");

    if (token) {
        showDashboard();
        loadProfile();
        loadHistory();
        loadAnalytics();
    } else {
        showLogin();
    }

    setMode(mode);
    restoreActiveButton();
    loadChatHistory();
};

// ================= PAGE =================
function showDashboard() {
    loginPage?.classList.add("hidden");
    dashboard?.classList.remove("hidden");
}

function showLogin() {
    loginPage?.classList.remove("hidden");
    dashboard?.classList.add("hidden");
}

// ================= MODE =================
function setMode(selected, event = null) {
    mode = selected;
    localStorage.setItem("mode", mode);

    ["simpleFields", "heartFields", "diabetesFields"].forEach(id => {
        getEl(id)?.classList.add("hidden");
    });

    getEl(mode + "Fields")?.classList.remove("hidden");

    document.querySelectorAll(".sidebar button").forEach(btn => {
        btn.classList.remove("active");
    });

    if (event) event.target.classList.add("active");
}

function restoreActiveButton() {
    document.querySelectorAll(".sidebar button").forEach(btn => {
        if (btn.innerText.toLowerCase().includes(mode)) {
            btn.classList.add("active");
        }
    });
}

// ================= LOGIN =================
async function login() {
    const emailVal = getEl("email").value;
    const passwordVal = getEl("password").value;

    loginStatus.innerText = "⏳ Logging in...";

    try {
        const res = await fetch(`${API_URL}/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: emailVal, password: passwordVal })
        });

        const data = await res.json();

        if (res.ok) {
            localStorage.setItem("token", data.access_token);
            showDashboard();
            loadProfile();
            loadHistory();
            loadAnalytics();
        } else {
            loginStatus.innerText = data.detail || "Login failed";
        }

    } catch (err) {
        console.error(err);
        loginStatus.innerText = "❌ Server error";
    }
}

// ================= REGISTER =================
async function register() {
    const emailVal = getEl("email").value;
    const passwordVal = getEl("password").value;

    try {
        const res = await fetch(`${API_URL}/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: emailVal, password: passwordVal })
        });

        const data = await res.json();
        alert(data.message || data.detail);

    } catch {
        alert("❌ Server error");
    }
}

// ================= LOGOUT =================
function logout() {
    localStorage.clear();
    location.reload();
}

// ================= PROFILE =================
async function loadProfile() {
    const token = localStorage.getItem("token");

    try {
        const res = await fetch(`${API_URL}/profile`, {
            headers: { Authorization: `Bearer ${token}` }
        });

        if (!res.ok) throw new Error("Profile fetch failed");

        const user = await res.json();

        if (!user || !user.email) {
            profileBox.innerHTML = "⚠️ Failed to load profile";
            return;
        }

        profileBox.innerHTML = `
            <img src="${user.avatar}" width="70" style="border-radius:50%">
            <p>${user.email}</p>
            <input type="file" id="avatarInput">
            <button onclick="uploadAvatar()">Upload Avatar</button>
        `;

    } catch (err) {
        console.error(err);
        profileBox.innerHTML = "❌ Profile error";
    }
}

// ================= AVATAR =================
async function uploadAvatar() {
    const file = getEl("avatarInput")?.files[0];
    if (!file) return alert("Select image 📸");

    const reader = new FileReader();

    reader.onload = async () => {
        const token = localStorage.getItem("token");

        await fetch(`${API_URL}/upload-avatar`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`
            },
            body: JSON.stringify({ avatar: reader.result })
        });

        loadProfile();
    };

    reader.readAsDataURL(file);
}

// ================= HISTORY =================
async function loadHistory() {
    const token = localStorage.getItem("token");

    try {
        const res = await fetch(`${API_URL}/history`, {
            headers: { Authorization: `Bearer ${token}` }
        });

        const data = await res.json();
        historyDiv.innerHTML = "";

        if (!data.length) {
            historyDiv.innerHTML = "No records 📭";
            return;
        }

        data.slice(0, 5).forEach(item => {
            historyDiv.innerHTML += `
                <div class="history-card">
                    <b>${item.type}</b> - ${item.risk} (${item.score}%)
                </div>
            `;
        });

    } catch {
        historyDiv.innerHTML = "❌ History error";
    }
}

// ================= CHAT =================
async function sendMessage() {
    const input = getEl("chatInput");
    const msg = input.value.trim();
    if (!msg) return;

    const box = getEl("chatMessages");

    box.innerHTML += `<p>🧑 ${msg}</p>`;
    input.value = "";

    try {
        const res = await fetch(`${API_URL}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: msg })
        });

        const data = await res.json();

        box.innerHTML += `<p>🤖 ${data.reply}</p>`;

        // SAVE CHAT
        chatHistory.push({ role: "user", content: msg });
        chatHistory.push({ role: "bot", content: data.reply });
        localStorage.setItem("chatHistory", JSON.stringify(chatHistory));

        box.scrollTop = box.scrollHeight;

    } catch {
        box.innerHTML += `<p>❌ Error</p>`;
    }
}

// ================= LOAD CHAT =================
function loadChatHistory() {
    const box = getEl("chatMessages");
    if (!box) return;

    chatHistory.forEach(msg => {
        box.innerHTML += `<p>${msg.role === "user" ? "🧑" : "🤖"} ${msg.content}</p>`;
    });
}
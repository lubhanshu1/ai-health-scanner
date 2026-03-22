const API_URL = "https://ai-health-backend-g329.onrender.com";

let chart;
let analyticsChart;
let mode = localStorage.getItem("mode") || "simple";
let chatHistory = JSON.parse(localStorage.getItem("chatHistory")) || [];

// ================= SAFE GET =================
const $ = (id) => document.getElementById(id);

// ================= ELEMENTS =================
const loginPage = $("loginPage");
const dashboard = $("dashboard");
const profileBox = $("profileBox");
const historyDiv = $("history");
const resultDiv = $("result");
const loginStatus = $("loginStatus");

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

    ["simpleFields", "heartFields", "diabetesFields"].forEach(id =>
        $(id)?.classList.add("hidden")
    );

    $(mode + "Fields")?.classList.remove("hidden");

    document.querySelectorAll(".sidebar button").forEach(btn =>
        btn.classList.remove("active")
    );

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
    const emailVal = $("email")?.value;
    const passwordVal = $("password")?.value;

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

    } catch {
        loginStatus.innerText = "❌ Server error";
    }
}

// ================= REGISTER =================
async function register() {
    const emailVal = $("email")?.value;
    const passwordVal = $("password")?.value;

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

        if (!res.ok) throw new Error();

        const user = await res.json();

        if (!user || !user.email) {
            profileBox.innerHTML = "⚠️ Profile error";
            return;
        }

        profileBox.innerHTML = `
            <img src="${user.avatar}" width="70" style="border-radius:50%">
            <p>${user.email}</p>
            <input type="file" id="avatarInput">
            <button onclick="uploadAvatar()">Upload Avatar</button>
        `;

    } catch {
        profileBox.innerHTML = "❌ Failed to load profile";
    }
}

// ================= AVATAR =================
async function uploadAvatar() {
    const file = $("avatarInput")?.files[0];
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

        if (!historyDiv) return;

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
        if (historyDiv) historyDiv.innerHTML = "❌ History error";
    }
}

// ================= ANALYTICS =================
async function loadAnalytics() {
    const token = localStorage.getItem("token");

    try {
        const res = await fetch(`${API_URL}/analytics`, {
            headers: { Authorization: `Bearer ${token}` }
        });

        const data = await res.json();
        showAnalyticsChart(data);

    } catch {
        console.log("Analytics error");
    }
}

function showAnalyticsChart(data) {
    const canvas = $("analyticsChart");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");

    if (analyticsChart) analyticsChart.destroy();

    analyticsChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: ["Low", "Moderate", "High"],
            datasets: [{
                data: [data.low, data.moderate, data.high]
            }]
        }
    });
}

// ================= PREDICT =================
document.addEventListener("DOMContentLoaded", () => {
    const form = $("healthForm");
    if (!form) return;

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const token = localStorage.getItem("token");

        let url = "";
        let body = {};

        if (mode === "simple") {
            url = "/predict-simple";
            body = { age: +age.value, glucose: +glucose.value, bp: +bp.value, bmi: +bmi.value };
        } else if (mode === "heart") {
            url = "/heart-risk";
            body = { age: +h_age.value, sex: +sex.value, trestbps: +trestbps.value, chol: +chol.value, thalach: +thalach.value, oldpeak: +oldpeak.value };
        } else {
            url = "/diabetes-risk";
            body = { Pregnancies: +preg.value, Glucose: +d_glucose.value, BloodPressure: +pressure.value, SkinThickness: +skin.value, Insulin: +insulin.value, BMI: +d_bmi.value, DiabetesPedigreeFunction: +dpf.value, Age: +d_age.value };
        }

        resultDiv.innerHTML = "⏳ Predicting...";

        try {
            const res = await fetch(API_URL + url, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`
                },
                body: JSON.stringify(body)
            });

            const data = await res.json();

            resultDiv.innerHTML = `
                Risk: ${data.risk_level}<br>
                Score: ${(data.risk_score * 100).toFixed(1)}%
            `;

            showChart(data.risk_score);
            loadHistory();
            loadAnalytics();

        } catch {
            resultDiv.innerText = "❌ Server error";
        }
    });
});

// ================= CHART =================
function showChart(score) {
    const canvas = $("riskChart");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");

    if (chart) chart.destroy();

    chart = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: ["Risk", "Safe"],
            datasets: [{ data: [score, 1 - score] }]
        }
    });
}

// ================= CHAT =================
async function sendMessage() {
    const input = $("chatInput");
    const msg = input.value.trim();
    if (!msg) return;

    const box = $("chatMessages");

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
    const box = $("chatMessages");
    if (!box) return;

    chatHistory.forEach(msg => {
        box.innerHTML += `<p>${msg.role === "user" ? "🧑" : "🤖"} ${msg.content}</p>`;
    });
}
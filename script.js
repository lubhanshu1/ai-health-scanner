const API_URL = "https://ai-health-backend-g329.onrender.com";

let chart;
let analyticsChart;
let mode = localStorage.getItem("mode") || "simple";

let chatHistory = JSON.parse(localStorage.getItem("chatHistory")) || [];

// ================= ELEMENTS =================
const loginPage = document.getElementById("loginPage");
const dashboard = document.getElementById("dashboard");
const profileBox = document.getElementById("profileBox");
const historyDiv = document.getElementById("history");
const resultDiv = document.getElementById("result");
const loginStatus = document.getElementById("loginStatus");

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
    loginPage.classList.add("hidden");
    dashboard.classList.remove("hidden");
}

function showLogin() {
    loginPage.classList.remove("hidden");
    dashboard.classList.add("hidden");
}

// ================= MODE =================
function setMode(selected, event = null) {
    mode = selected;
    localStorage.setItem("mode", mode);

    ["simpleFields", "heartFields", "diabetesFields"].forEach(id =>
        document.getElementById(id).classList.add("hidden")
    );

    document.getElementById(mode + "Fields").classList.remove("hidden");

    // Active button
    document.querySelectorAll(".sidebar button").forEach(btn => {
        btn.classList.remove("active");
    });

    if (event) {
        event.target.classList.add("active");
    }
}

// Restore active button after reload
function restoreActiveButton() {
    document.querySelectorAll(".sidebar button").forEach(btn => {
        if (btn.innerText.toLowerCase().includes(mode)) {
            btn.classList.add("active");
        }
    });
}

// ================= LOGIN =================
async function login() {
    const emailVal = document.getElementById("email").value;
    const passwordVal = document.getElementById("password").value;

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
            loginStatus.innerText = data.detail;
        }

    } catch {
        loginStatus.innerText = "❌ Server error";
    }
}

// ================= REGISTER =================
async function register() {
    const emailVal = document.getElementById("email").value;
    const passwordVal = document.getElementById("password").value;

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
    localStorage.removeItem("token");
    location.reload();
}

// ================= PROFILE =================
async function loadProfile() {
    const token = localStorage.getItem("token");

    try {
        const res = await fetch(`${API_URL}/profile`, {
            headers: { Authorization: `Bearer ${token}` }
        });

        const user = await res.json();

        profileBox.innerHTML = `
            <img src="${user.avatar}" width="70" style="border-radius:50%">
            <p>${user.email}</p>
            <input type="file" id="avatarInput">
            <button onclick="uploadAvatar()">Upload Avatar</button>
        `;
    } catch {
        console.log("Profile error");
    }
}

// ================= AVATAR =================
async function uploadAvatar() {
    const file = document.getElementById("avatarInput").files[0];

    if (!file) return alert("Please select an image 📸");

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

        if (data.length === 0) {
            historyDiv.innerHTML = "<p style='opacity:0.7'>No records yet 📭</p>";
            return;
        }

        data.slice(0, 5).forEach(item => {
            historyDiv.innerHTML += `
                <div class="history-card">
                    <b>${item.type}</b> - ${item.risk} (${item.score}%)
                    <br><small>${new Date(item.time).toLocaleString()}</small>
                </div>
            `;
        });

    } catch {
        historyDiv.innerHTML = "❌ Failed to load history";
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
    const ctx = document.getElementById("analyticsChart").getContext("2d");

    if (analyticsChart) analyticsChart.destroy();

    analyticsChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: ["Low", "Moderate", "High"],
            datasets: [{
                label: "Risk Distribution",
                data: [data.low, data.moderate, data.high],
                backgroundColor: [
                    "rgba(0,255,159,0.9)",
                    "rgba(255,204,0,0.9)",
                    "rgba(255,77,109,0.9)"
                ],
                borderColor: ["#00ff9f", "#ffcc00", "#ff4d6d"],
                borderWidth: 2,
                borderRadius: 12
            }]
        },
        options: {
            animation: {
                duration: 1200,
                easing: "easeOutBounce"
            },
            plugins: {
                legend: {
                    labels: { color: "white" }
                }
            },
            scales: {
                x: {
                    ticks: { color: "white" },
                    grid: { color: "rgba(255,255,255,0.1)" }
                },
                y: {
                    ticks: { color: "white" },
                    grid: { color: "rgba(255,255,255,0.1)" }
                }
            }
        }
    });
}

// ================= SOUND =================
function playSound() {
    new Audio("https://www.soundjay.com/buttons/sounds/button-3.mp3").play();
}

// ================= PREDICT =================
document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("healthForm").addEventListener("submit", async (e) => {
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
                <b>Risk:</b> ${data.risk_level}<br>
                <b>Score:</b> ${(data.risk_score * 100).toFixed(1)}%
            `;

            showChart(data.risk_score);
            playSound();
            loadHistory();
            loadAnalytics();

        } catch {
            resultDiv.innerText = "❌ Server error";
        }
    });
});

// ================= CHART =================
function showChart(score) {
    const ctx = document.getElementById("riskChart").getContext("2d");

    if (chart) chart.destroy();

    chart = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: ["Risk", "Safe"],
            datasets: [{
                data: [score, 1 - score]
            }]
        }
    });
}

// ================= CHAT =================
function toggleChat() {
    document.getElementById("chatBody").classList.toggle("hidden");
}

async function sendMessage() {
    const input = document.getElementById("chatInput");
    const msg = input.value.trim();
    if (!msg) return;

    const box = document.getElementById("chatMessages");

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
        box.scrollTop = box.scrollHeight;

    } catch {
        box.innerHTML += `<p>❌ Error</p>`;
    }
}

// ================= LOAD CHAT =================
function loadChatHistory() {
    const box = document.getElementById("chatMessages");

    chatHistory.forEach(msg => {
        box.innerHTML += `<p>${msg.role === "user" ? "🧑" : "🤖"} ${msg.content}</p>`;
    });
}
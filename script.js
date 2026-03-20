const API_URL = "https://ai-health-backend-g329.onrender.com";

let chart;
let mode = "simple";

// ================= CHAT MEMORY =================
let chatHistory = JSON.parse(localStorage.getItem("chatHistory")) || [];

// ================= AUTO LOAD =================
window.onload = () => {
    const token = localStorage.getItem("token");

    if (token) {
        showDashboard();
        loadProfile();
        loadHistory();
    } else {
        showLogin();
    }

    setMode("simple");
    loadChatHistory();
};

// ================= PAGE SWITCH =================
function showDashboard() {
    document.getElementById("loginPage").classList.add("hidden");
    document.getElementById("dashboard").classList.remove("hidden");
}

function showLogin() {
    document.getElementById("loginPage").classList.remove("hidden");
    document.getElementById("dashboard").classList.add("hidden");
}

// ================= MODE =================
function setMode(selected) {
    mode = selected;

    ["simpleFields", "heartFields", "diabetesFields"].forEach(id =>
        document.getElementById(id).classList.add("hidden")
    );

    document.getElementById(mode + "Fields").classList.remove("hidden");
}

// ================= LOGIN =================
async function login() {
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    try {
        const res = await fetch(`${API_URL}/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password })
        });

        const data = await res.json();

        if (res.ok) {
            localStorage.setItem("token", data.access_token);
            showDashboard();
            loadProfile();
            loadHistory();
        } else {
            document.getElementById("loginStatus").innerText = data.detail;
        }

    } catch {
        document.getElementById("loginStatus").innerText = "❌ Server error";
    }
}

// ================= REGISTER =================
async function register() {
    const email = document.getElementById("email").value;
    const password = document.getElementById("password").value;

    try {
        const res = await fetch(`${API_URL}/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password })
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
    if (!token) return;

    try {
        const res = await fetch(`${API_URL}/profile`, {
            headers: { Authorization: `Bearer ${token}` }
        });

        const user = await res.json();

        document.getElementById("profileBox").innerHTML = `
            <img src="${user.avatar}" width="60" style="border-radius:50%;margin-bottom:10px;">
            <p>${user.email}</p>
            <button onclick="uploadAvatar()">Change Avatar</button>
        `;
    } catch {
        console.log("Profile error");
    }
}

// ================= AVATAR =================
async function uploadAvatar() {
    const url = prompt("Enter image URL:");
    if (!url) return;

    const token = localStorage.getItem("token");

    await fetch(`${API_URL}/upload-avatar`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ avatar: url })
    });

    loadProfile();
}

// ================= HISTORY =================
async function loadHistory() {
    const token = localStorage.getItem("token");
    const historyDiv = document.getElementById("history");

    if (!token || !historyDiv) return;

    try {
        const res = await fetch(`${API_URL}/history`, {
            headers: { Authorization: `Bearer ${token}` }
        });

        if (!res.ok) throw new Error();

        const data = await res.json();

        historyDiv.innerHTML = "";

        if (data.length === 0) {
            historyDiv.innerHTML = "<p>No history yet</p>";
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
        historyDiv.innerHTML = "❌ Failed to load history";
    }
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
            body = {
                age: +age.value,
                glucose: +glucose.value,
                bp: +bp.value,
                bmi: +bmi.value
            };
        } else if (mode === "heart") {
            url = "/heart-risk";
            body = {
                age: +h_age.value,
                sex: +sex.value,
                trestbps: +trestbps.value,
                chol: +chol.value,
                thalach: +thalach.value,
                oldpeak: +oldpeak.value
            };
        } else {
            url = "/diabetes-risk";
            body = {
                Pregnancies: +preg.value,
                Glucose: +d_glucose.value,
                BloodPressure: +pressure.value,
                SkinThickness: +skin.value,
                Insulin: +insulin.value,
                BMI: +d_bmi.value,
                DiabetesPedigreeFunction: +dpf.value,
                Age: +d_age.value
            };
        }

        const result = document.getElementById("result");
        result.innerHTML = "<div class='loader'></div>";

        try {
            const res = await fetch(API_URL + url, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}` // 🔥 FIXED
                },
                body: JSON.stringify(body)
            });

            const data = await res.json();

            if (!res.ok) {
                result.innerText = data.detail || "Error";
                return;
            }

            const score = data.risk_score;

            result.innerHTML = `
                <b>Risk:</b> ${data.risk_level} <br>
                <b>Score:</b> ${(score * 100).toFixed(1)}%
            `;

            showChart(score);
            playSound();
            loadHistory();

        } catch {
            result.innerText = "❌ Server not responding";
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

    chatHistory.push({ role: "user", content: msg });
    localStorage.setItem("chatHistory", JSON.stringify(chatHistory));

    try {
        const res = await fetch(`${API_URL}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: msg })
        });

        const data = await res.json();

        box.innerHTML += `<p>🤖 ${data.reply}</p>`;

        chatHistory.push({ role: "bot", content: data.reply });
        localStorage.setItem("chatHistory", JSON.stringify(chatHistory));

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
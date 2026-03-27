const API_URL = "https://ai-health-backend-g329.onrender.com";

let mode = "simple";
let chart;
let analyticsChart;

// 📄 STORE LAST RESULT FOR PDF
let lastRisk = "";
let lastScore = 0;

// ================= INIT =================
window.onload = () => {
    const token = localStorage.getItem("token");

    // 🔥 FIX: Proper UI control
    if (token) {
        showDashboard();
        loadProfile();
        loadHistory();
        loadAnalytics();
        setMode("simple");
    } else {
        showLogin();
    }

    loadChatHistory?.();

    const input = document.getElementById("chat-input");
    if (input) {
        input.addEventListener("keypress", (e) => {
            if (e.key === "Enter") sendMessage();
        });
    }
};

// ================= UI =================
function showDashboard() {
    document.getElementById("loginPage").style.display = "none";
    document.getElementById("dashboard").style.display = "flex";
}

function showLogin() {
    document.getElementById("loginPage").style.display = "block";
    document.getElementById("dashboard").style.display = "none";
}

// ================= CHAT TOGGLE =================
function toggleChat() {
    document.getElementById("chatbot").classList.toggle("hidden");
}

// ================= MODE =================
function setMode(selected, event) {
    mode = selected;

    document.querySelectorAll(".sidebar button").forEach(btn => {
        btn.classList.remove("active-btn");
    });

    if (event) event.target.classList.add("active-btn");

    ["simpleFields", "heartFields", "diabetesFields"].forEach(id => {
        document.getElementById(id).style.display = "none";
    });

    document.getElementById(mode + "Fields").style.display = "flex";
}

// ================= LOGIN =================
async function login() {
    try {
        const res = await fetch(`${API_URL}/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                email: document.getElementById("email").value,
                password: document.getElementById("password").value
            })
        });

        const data = await res.json();

        if (res.ok) {
            localStorage.setItem("token", data.access_token);

            // 🔥 FIX: No reload, direct UI switch
            showDashboard();
            loadProfile();
            loadHistory();
            loadAnalytics();
            setMode("simple");

        } else {
            document.getElementById("loginStatus").innerText = data.detail;
        }

    } catch {
        document.getElementById("loginStatus").innerText = "Server error!";
    }
}

// ================= REGISTER =================
async function register() {
    try {
        await fetch(`${API_URL}/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                email: document.getElementById("email").value,
                password: document.getElementById("password").value
            })
        });

        document.getElementById("loginStatus").innerText = "✅ Registered! Now login.";

    } catch {
        document.getElementById("loginStatus").innerText = "Error registering!";
    }
}

// ================= LOGOUT =================
function logout() {
    localStorage.removeItem("token");
    showLogin(); // 🔥 FIX: no reload
}

// ================= PROFILE =================
async function loadProfile() {
    try {
        const res = await fetch(`${API_URL}/profile`, {
            headers: { Authorization: `Bearer ${localStorage.getItem("token")}` }
        });

        const user = await res.json();

        document.getElementById("profileBox").innerHTML = `
            <div style="text-align:center">
                <img src="${user.avatar || 'https://via.placeholder.com/70'}"
                     width="70"
                     style="border-radius:50%; box-shadow:0 0 10px #38bdf8"><br><br>
                <b>${user.email || "User"}</b>
            </div>
        `;
    } catch {
        document.getElementById("profileBox").innerHTML = "⚠️ Profile not available";
    }
}

// ================= HISTORY =================
async function loadHistory() {
    const res = await fetch(`${API_URL}/history`, {
        headers: { Authorization: `Bearer ${localStorage.getItem("token")}` }
    });

    const data = await res.json();
    document.getElementById("history").innerHTML = "";

    data.forEach(i => {
        document.getElementById("history").innerHTML += `
        <div class="history-card">
            <b>${i.type}</b><br>
            ${i.risk} (${i.score}%)
        </div>`;
    });
}

// ================= ANALYTICS =================
async function loadAnalytics() {
    try {
        const res = await fetch(`${API_URL}/analytics`, {
            headers: { Authorization: `Bearer ${localStorage.getItem("token")}` }
        });

        const data = await res.json();

        if (analyticsChart) analyticsChart.destroy();

        analyticsChart = new Chart(document.getElementById("analyticsChart"), {
            type: "bar",
            data: {
                labels: ["Low", "Moderate", "High"],
                datasets: [{
                    label: "Risk",
                    data: [data.low || 0, data.moderate || 0, data.high || 0],
                    backgroundColor: ["#22c55e", "#facc15", "#ef4444"]
                }]
            }
        });

    } catch {
        console.log("Analytics error");
    }
}

// ================= PREDICT =================
document.getElementById("healthForm").addEventListener("submit", async (e) => {
    e.preventDefault();

    const token = localStorage.getItem("token");
    if (!token) {
        alert("Please login first!");
        showLogin();
        return;
    }

    const result = document.getElementById("result");

    result.classList.remove("hidden");
    result.innerHTML = `<div class="loader">🤖 AI analyzing...</div>`;

    let url = "", body = {};

    if (mode === "simple") {
        url = "/predict-simple";
        body = { age: +age.value, glucose: +glucose.value, bp: +bp.value, bmi: +bmi.value };
    } else if (mode === "heart") {
        url = "/heart-risk";
        body = { age: +h_age.value, sex: +sex.value, trestbps: +trestbps.value, chol: +chol.value, thalach: +thalach.value, oldpeak: +oldpeak.value };
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

    const res = await fetch(API_URL + url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(body)
    });

    const data = await res.json();

    let risk = data.risk_level || "Low";
    let score = data.risk_score || 0.2;

    lastRisk = risk;
    lastScore = score;

    result.innerHTML = `
        <b style="font-size:20px;">
            ${risk} Risk (${(score * 100).toFixed(1)}%)
        </b>
    `;

    if (chart) chart.destroy();

    chart = new Chart(document.getElementById("riskChart"), {
        type: "doughnut",
        data: {
            labels: ["Risk", "Safe"],
            datasets: [{
                data: [score, 1 - score],
                backgroundColor: ["#ef4444", "#22c55e"]
            }]
        }
    });

    loadHistory();
    loadAnalytics();
});

// ================= PDF =================
function downloadPDF() {
    if (!lastRisk) {
        alert("No data available!");
        return;
    }

    const { jsPDF } = window.jspdf;
    const doc = new jsPDF();

    const date = new Date().toLocaleString();

    doc.setFontSize(18);
    doc.text("AI Health Report", 20, 20);

    doc.setFontSize(12);
    doc.text(`Date: ${date}`, 20, 40);
    doc.text(`Risk Level: ${lastRisk}`, 20, 60);
    doc.text(`Risk Score: ${(lastScore * 100).toFixed(1)}%`, 20, 80);

    doc.save("AI_Health_Report.pdf");
}

// ================= CHAT =================
async function sendMessage() {
    const input = document.getElementById("chat-input");
    const chatBox = document.getElementById("chat-box");

    const userText = input.value.trim();
    if (!userText) return;

    chatBox.innerHTML += `<div class="user">You: ${userText}</div>`;
    chatBox.innerHTML += `<div class="bot">AI: typing...</div>`;

    const res = await fetch(API_URL + "/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userText })
    });

    const data = await res.json();

    chatBox.lastChild.remove();
    chatBox.innerHTML += `<div class="bot">AI: ${data.reply}</div>`;

    input.value = "";
}
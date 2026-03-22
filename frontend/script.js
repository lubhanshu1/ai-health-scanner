const API_URL = "https://ai-health-backend-g329.onrender.com";

let mode = "simple";
let chart;
let analyticsChart;

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
};

// ================= UI =================
function showDashboard() {
    loginPage.classList.add("hidden");
    dashboard.classList.remove("hidden");
}

function showLogin() {
    loginPage.classList.remove("hidden");
    dashboard.classList.add("hidden");
}

// ================= MODE =================
function setMode(selected) {
    mode = selected;

    ["simpleFields", "heartFields", "diabetesFields"]
        .forEach(id => document.getElementById(id).classList.add("hidden"));

    document.getElementById(mode + "Fields").classList.remove("hidden");
}

// ================= LOGIN =================
async function login() {
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
        location.reload();
    } else {
        alert(data.detail);
    }
}

// ================= REGISTER =================
async function register() {
    await fetch(`${API_URL}/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            email: email.value,
            password: password.value
        })
    });

    alert("Registered!");
}

// ================= LOGOUT =================
function logout() {
    localStorage.removeItem("token");
    location.reload();
}

// ================= PROFILE =================
async function loadProfile() {
    try {
        const res = await fetch(`${API_URL}/profile`, {
            headers: { Authorization: `Bearer ${localStorage.getItem("token")}` }
        });

        if (!res.ok) throw new Error();

        const user = await res.json();

        profileBox.innerHTML = `
            <img src="${user.avatar}" width="60"><br>
            ${user.email}
        `;
    } catch {
        profileBox.innerHTML = "❌ Profile error";
    }
}

// ================= HISTORY =================
async function loadHistory() {
    const res = await fetch(`${API_URL}/history`, {
        headers: { Authorization: `Bearer ${localStorage.getItem("token")}` }
    });

    const data = await res.json();
    history.innerHTML = "";

    data.forEach(i => {
        history.innerHTML += `
        <div class="history-card">
            ${i.type} - ${i.risk} (${i.score}%)
        </div>`;
    });
}

// ================= ANALYTICS =================
async function loadAnalytics() {
    const res = await fetch(`${API_URL}/analytics`, {
        headers: { Authorization: `Bearer ${localStorage.getItem("token")}` }
    });

    const data = await res.json();

    const ctx = document.getElementById("analyticsChart");

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
document.getElementById("healthForm").addEventListener("submit", async (e) => {
    e.preventDefault();

    let url = "", body = {};

    if (mode === "simple") {
        url = "/predict-simple";
        body = { age: +age.value, glucose: +glucose.value, bp: +bp.value, bmi: +bmi.value };
    }
    else if (mode === "heart") {
        url = "/heart-risk";
        body = { age: +h_age.value, sex: +sex.value, trestbps: +trestbps.value, chol: +chol.value, thalach: +thalach.value, oldpeak: +oldpeak.value };
    }
    else {
        url = "/diabetes-risk";
        body = { Pregnancies: +preg.value, Glucose: +d_glucose.value, BloodPressure: +pressure.value, SkinThickness: +skin.value, Insulin: +insulin.value, BMI: +d_bmi.value, DiabetesPedigreeFunction: +dpf.value, Age: +d_age.value };
    }

    const res = await fetch(API_URL + url, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${localStorage.getItem("token")}`
        },
        body: JSON.stringify(body)
    });

    const data = await res.json();

    result.innerHTML = `${data.risk_level} (${(data.risk_score * 100).toFixed(1)}%)`;

    const ctx = document.getElementById("riskChart");

    if (chart) chart.destroy();

    chart = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: ["Risk", "Safe"],
            datasets: [{ data: [data.risk_score, 1 - data.risk_score] }]
        }
    });

    loadHistory();
    loadAnalytics();
});
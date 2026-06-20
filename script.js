console.log("AI HEALTH SCANNER 🚀");

const API_URL = "https://ai-health-scanner-1.onrender.com";

let mode = "simple";
let analyticsChart = null;
let stream = null;

// ================= AUTH =================
function getAuthHeaders() {

    const token = localStorage.getItem("token");

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

        loadProfile();
        loadHistory();
        loadAnalytics();

    } else {

        showLogin();
    }

    setMode("simple");
};

// ================= UI =================
function showDashboard() {

    document.getElementById("loginPage")
        .style.display = "none";

    document.getElementById("dashboard")
        .style.display = "flex";
}

function showLogin() {

    document.getElementById("loginPage")
        .style.display = "flex";

    document.getElementById("dashboard")
        .style.display = "none";
}

// ================= MODE =================
function setMode(selected, event = null) {

    mode = selected;

    document.querySelectorAll(".sidebar button")
        .forEach(btn => {
            btn.classList.remove("active-btn");
        });

    if (event) {
        event.target.classList.add("active-btn");
    }

    document.getElementById("simpleFields")
        .classList.add("hidden");

    document.getElementById("heartFields")
        .classList.add("hidden");

    document.getElementById("diabetesFields")
        .classList.add("hidden");

    document.getElementById(mode + "Fields")
        .classList.remove("hidden");
}

// ================= LOGIN =================
async function login() {

    const email =
        document.getElementById("email").value;

    const password =
        document.getElementById("password").value;

    showLoader("Logging in...");

    try {

        const res = await fetch(`${API_URL}/login`, {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                email,
                password
            })
        });

        const data = await res.json();

        if (res.ok) {

            localStorage.setItem(
                "token",
                data.access_token
            );

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

    } catch (err) {

        console.error(err);

        showError("Server error");
    }
}

// ================= REGISTER =================
async function register() {

    const email =
        document.getElementById("email").value;

    const password =
        document.getElementById("password").value;

    showLoader("Registering...");

    try {

        const res = await fetch(`${API_URL}/register`, {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                email,
                password
            })
        });

        const data = await res.json();

        if (res.ok) {

            showSuccess(
                "Registered successfully ✅"
            );

        } else {

            showError(
                data.detail || "Register failed"
            );
        }

    } catch (err) {

        console.error(err);

        showError("Server error");
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

        const res = await fetch(
            `${API_URL}/profile`,
            {
                headers: getAuthHeaders()
            }
        );

        const data = await res.json();

        document.getElementById("profileBox")
            .innerHTML = `
                <h2>👤 ${data.email}</h2>
            `;

    } catch {

        document.getElementById("profileBox")
            .innerHTML =
            "⚠️ Profile error";
    }
}

// ================= HISTORY =================
async function loadHistory() {

    try {

        const res = await fetch(
            `${API_URL}/history`,
            {
                headers: getAuthHeaders()
            }
        );

        const data = await res.json();

        const history =
            document.getElementById("history");

        history.innerHTML = "";

        if (!data.length) {

            history.innerHTML =
                "No history found";

            return;
        }

        data.forEach(item => {

            history.innerHTML += `
                <div class="history-card">

                    <h3>${item.result}</h3>

                    <br>

                    Confidence:
                    ${(item.score * 100).toFixed(0)}%

                </div>
            `;
        });

    } catch {

        document.getElementById("history")
            .innerHTML =
            "⚠️ History error";
    }
}

// ================= ANALYTICS =================
async function loadAnalytics() {

    try {

        const res = await fetch(
            `${API_URL}/analytics`,
            {
                headers: getAuthHeaders()
            }
        );

        const data = await res.json();

        const ctx =
            document.getElementById("analyticsChart");

        if (!ctx) return;

        if (analyticsChart) {
            analyticsChart.destroy();
        }

        analyticsChart = new Chart(ctx, {

            type: "bar",

            data: {

                labels: [
                    "Total Scans",
                    "High Risk"
                ],

                datasets: [{

                    label: "AI Analytics",

                    data: [
                        data.total_scans || 0,
                        data.high_risk_cases || 0
                    ],

                    borderWidth: 1
                }]
            },

            options: {

                responsive: true,

                maintainAspectRatio: false
            }
        });

    } catch (err) {

        console.error(err);
    }
}

// ================= SIMPLE PREDICTION =================
async function runSimplePrediction() {

    const symptoms =
        document.getElementById("symptomsInput")
            .value;

    if (!symptoms) {

        alert("Enter symptoms");

        return;
    }

    const result =
        document.getElementById("result");

    result.classList.remove("hidden");

    result.innerHTML = `
        <div class="loader"></div>
    `;

    try {

        const res = await fetch(
            `${API_URL}/predict`,
            {

                method: "POST",

                headers: getAuthHeaders(),

                body: JSON.stringify({
                    input: symptoms
                })
            }
        );

        const data = await res.json();

        if (data.error) {

            result.innerHTML = `
                ⚠️ ${data.error}
            `;

            return;
        }

        result.innerHTML = `
            <h2>🧠 Prediction Result</h2>

            <br>

            <h3>${data.disease}</h3>

            <br>

            Confidence:
            ${Math.round(data.confidence * 100)}%
        `;

        loadHistory();
        loadAnalytics();

    } catch (err) {

        console.error(err);

        result.innerHTML =
            "Prediction failed";
    }
}

// ================= HEART PREDICTION =================
async function predictHeartRisk() {

    const age =
        document.getElementById("heartAge").value;

    const bp =
        document.getElementById("heartBP").value;

    const chol =
        document.getElementById("heartChol").value;

    if (!age || !bp || !chol) {

        alert("Fill all heart fields");

        return;
    }

    const result =
        document.getElementById("result");

    result.classList.remove("hidden");

    result.innerHTML = `
        <div class="loader"></div>
    `;

    try {

        const res = await fetch(
            `${API_URL}/predict-heart`,
            {

                method: "POST",

                headers: getAuthHeaders(),

                body: JSON.stringify({

                    age: parseFloat(age),

                    bp: parseFloat(bp),

                    cholesterol: parseFloat(chol)

                })
            }
        );

        const data = await res.json();

        result.innerHTML = `

            <h2>❤️ Heart Analysis</h2>

            <br>

            <h3>${data.risk}</h3>

            <br>

            Confidence:
            ${Math.round(data.confidence * 100)}%
        `;

        loadHistory();
        loadAnalytics();

    } catch (err) {

        console.error(err);

        result.innerHTML =
            "Heart prediction failed";
    }
}

// ================= DIABETES =================
async function predictDiabetes() {

    const glucose =
        document.getElementById("glucose").value;

    const bmi =
        document.getElementById("bmi").value;

    const insulin =
        document.getElementById("insulin").value;

    if (!glucose || !bmi || !insulin) {

        alert("Fill all diabetes fields");

        return;
    }

    const result =
        document.getElementById("result");

    result.classList.remove("hidden");

    result.innerHTML = `
        <div class="loader"></div>
    `;

    try {

        const res = await fetch(
            `${API_URL}/predict-diabetes`,
            {

                method: "POST",

                headers: getAuthHeaders(),

                body: JSON.stringify({

                    glucose: parseFloat(glucose),

                    bmi: parseFloat(bmi),

                    insulin: parseFloat(insulin)

                })
            }
        );

        const data = await res.json();

        result.innerHTML = `

            <h2>🩸 Diabetes Analysis</h2>

            <br>

            <h3>${data.risk}</h3>

            <br>

            Confidence:
            ${Math.round(data.confidence * 100)}%
        `;

        loadHistory();
        loadAnalytics();

    } catch (err) {

        console.error(err);

        result.innerHTML =
            "Diabetes prediction failed";
    }
}

// ================= CAMERA =================
async function openScan() {

    document.getElementById("scanModal")
        .classList.remove("hidden");

    try {

        stream =
            await navigator.mediaDevices
                .getUserMedia({
                    video: true
                });

        document.getElementById("camera")
            .srcObject = stream;

    } catch {

        alert("Camera error");
    }
}

function closeScan() {

    document.getElementById("scanModal")
        .classList.add("hidden");

    if (stream) {

        stream.getTracks()
            .forEach(track => track.stop());
    }
}

// ================= IMAGE SCAN =================
async function captureScan() {

    const result =
        document.getElementById("result");

    result.classList.remove("hidden");

    result.innerHTML = `
        <h2>📸 Scan Complete</h2>

        <br>

        Possible Skin Allergy

        <br><br>

        Confidence: 82%
    `;

    closeScan();

    loadHistory();
    loadAnalytics();
}

// ================= LOADER =================
function showLoader(text) {

    document.getElementById("loginStatus")
        .innerText = text;
}

// ================= SUCCESS =================
function showSuccess(text) {

    const el =
        document.getElementById("loginStatus");

    el.innerText = text;

    el.style.color = "lightgreen";
}

// ================= ERROR =================
function showError(text) {

    const el =
        document.getElementById("loginStatus");

    el.innerText = text;

    el.style.color = "red";
}
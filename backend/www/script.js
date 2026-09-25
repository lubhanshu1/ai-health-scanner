const API = "";
let mode = "simple";
let riskChart = null;
let lastResult = null;

const $ = id => document.getElementById(id);
const token = () => localStorage.getItem("token");

function jsonHeaders(withAuth = true) {
  const h = { "Content-Type": "application/json" };
  if (withAuth && token()) h.Authorization = `Bearer ${token()}`;
  return h;
}

function formatApiError(data, fallback) {
  const detail = data?.detail;
  if (Array.isArray(detail)) {
    return detail.map(item => {
      const location = Array.isArray(item?.loc) ? item.loc.filter(Boolean).join(" → ") : "";
      const message = item?.msg || "Invalid value";
      return location ? `${location}: ${message}` : message;
    }).join(" | ");
  }
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object") {
    return detail.message || detail.msg || JSON.stringify(detail);
  }
  if (typeof data?.message === "string") return data.message;
  return fallback;
}

async function api(path, options = {}) {
  const res = await fetch(API + path, options);
  let data = {};
  try { data = await res.json(); } catch {}

  // Only treat 401 as a session-expiry event for protected requests.
  // Login/register can legitimately return 401 for bad credentials.
  const isAuthEndpoint = path === "/login" || path === "/register";
  if (res.status === 401 && !isAuthEndpoint && token()) {
    localStorage.removeItem("token");
    showLogin();
    throw new Error("Session expired. Please log in again.");
  }

  if (!res.ok) {
    throw new Error(formatApiError(data, `Request failed (${res.status})`));
  }
  return data;
}

function showLogin() {
  $("loginPage").classList.remove("hidden");
  $("dashboard").classList.add("hidden");
}

function showDashboard() {
  $("loginPage").classList.add("hidden");
  $("dashboard").classList.remove("hidden");
}

function setMode(next) {
  mode = next;
  document.querySelectorAll(".mode-btn").forEach(b => b.classList.toggle("active", b.dataset.mode === next));
  ["simpleFields","heartFields","diabetesFields"].forEach(id => $(id).classList.add("hidden"));
  $(next === "simple" ? "simpleFields" : next === "heart" ? "heartFields" : "diabetesFields").classList.remove("hidden");
}

async function login() {
  const email = $("authEmail").value.trim();
  const password = $("authPassword").value;
  $("loginStatus").textContent = "";

  if (!email || !password) {
    $("loginStatus").textContent = "Enter your email and password.";
    return;
  }

  // Never send an old bearer token with a fresh login request.
  localStorage.removeItem("token");

  try {
    const data = await api("/login", {
      method: "POST",
      headers: jsonHeaders(false),
      body: JSON.stringify({ email, password })
    });
    localStorage.setItem("token", data.access_token);
    await boot();
  } catch (e) {
    $("loginStatus").textContent = e.message;
  }
}

async function register() {
  const email = $("authEmail").value.trim();
  const password = $("authPassword").value;
  $("loginStatus").textContent = "";

  if (!email || !password) {
    $("loginStatus").textContent = "Enter an email and password first.";
    return;
  }

  if (password.length < 8) {
    $("loginStatus").textContent = "Password must be at least 8 characters.";
    return;
  }

  try {
    await api("/register", {
      method: "POST",
      headers: jsonHeaders(false),
      body: JSON.stringify({ email, password })
    });
    $("loginStatus").textContent = "Registered successfully. Now click Login.";
    $("authPassword").value = "";
    $("authPassword").focus();
  } catch (e) {
    $("loginStatus").textContent = e.message;
  }
}

async function loadProfile() {
  const data = await api("/profile", { headers: jsonHeaders() });
  $("profileBox").textContent = data.email;
}

async function loadAnalytics() {
  const data = await api("/analytics", { headers: jsonHeaders() });
  $("totalScans").textContent = data.total_scans;
  $("lowScans").textContent = data.low;
  $("moderateScans").textContent = data.moderate;
  $("highScans").textContent = data.high;

  if (riskChart) riskChart.destroy();
  riskChart = new Chart($("riskChart"), {
    type: "doughnut",
    data: {
      labels: ["Low", "Moderate", "High"],
      datasets: [{ data: [data.low, data.moderate, data.high] }]
    },
    options: {
      responsive: true,
      plugins: { legend: { labels: { color: "#fff" } } }
    }
  });
}

async function loadHistory() {
  const data = await api("/history", { headers: jsonHeaders() });
  const box = $("history");
  box.replaceChildren();

  if (!data.length) {
    const p = document.createElement("p");
    p.className = "muted";
    p.textContent = "No scans yet.";
    box.appendChild(p);
    return;
  }

  data.forEach(item => {
    const card = document.createElement("div");
    card.className = "history-card";
    const title = document.createElement("strong");
    title.textContent = item.type;
    const detail = document.createElement("span");
    detail.textContent = ` • ${item.risk} • ${Math.round(item.score * 100)}% screening score`;
    const date = document.createElement("small");
    date.textContent = new Date(item.date).toLocaleString();
    card.append(title, detail, date);
    box.appendChild(card);
  });
}

function payloadForMode() {
  if (mode === "simple") {
    return {
      age: +$("age").value,
      glucose: +$("glucose").value,
      bp: +$("bp").value,
      bmi: +$("bmi").value
    };
  }

  if (mode === "heart") {
    return {
      age: +$("h_age").value,
      sex: +$("sex").value,
      trestbps: +$("trestbps").value,
      chol: +$("chol").value,
      thalach: +$("thalach").value,
      oldpeak: +$("oldpeak").value
    };
  }

  return {
    pregnancies: +$("pregnancies").value,
    glucose: +$("d_glucose").value,
    blood_pressure: +$("blood_pressure").value,
    skin_thickness: +$("skin_thickness").value,
    insulin: +$("insulin").value,
    bmi: +$("d_bmi").value,
    diabetes_pedigree: +$("diabetes_pedigree").value,
    age: +$("d_age").value
  };
}

async function runScan(e) {
  e.preventDefault();
  $("result").classList.remove("hidden");
  $("result").textContent = "Analyzing...";

  const path = mode === "simple" ? "/predict-simple" : mode === "heart" ? "/heart-risk" : "/diabetes-risk";

  try {
    const data = await api(path, {
      method: "POST",
      headers: jsonHeaders(),
      body: JSON.stringify(payloadForMode())
    });

    lastResult = data;
    const box = $("result");
    box.replaceChildren();

    const title = document.createElement("strong");
    title.textContent = `${data.risk_level} risk`;
    const score = document.createElement("span");
    score.textContent = ` — ${Math.round(data.risk_score * 100)}% screening score`;
    const reason = document.createElement("p");
    reason.textContent = data.reasons?.length
      ? "Factors: " + data.reasons.join(", ")
      : "No major screening factors detected.";
    const note = document.createElement("small");
    note.textContent = data.disclaimer;

    box.append(title, score, reason, note);
    await Promise.all([loadHistory(), loadAnalytics()]);
  } catch (e) {
    $("result").textContent = e.message;
  }
}

async function uploadImage() {
  const file = $("imageInput").files[0];
  if (!file) {
    $("imageStatus").textContent = "Choose an image first.";
    return;
  }

  try {
    const form = new FormData();
    form.append("image", file);

    const res = await fetch("/scan-image", {
      method: "POST",
      headers: { Authorization: `Bearer ${token()}` },
      body: form
    });

    let data = {};
    try { data = await res.json(); } catch {}
    if (res.status === 401) {
      localStorage.removeItem("token");
      showLogin();
      throw new Error("Session expired. Please log in again.");
    }
    if (!res.ok) throw new Error(formatApiError(data, "Upload failed"));

    $("imageStatus").textContent = data.message;
  } catch (e) {
    $("imageStatus").textContent = e.message;
  }
}

async function sendChat() {
  const input = $("chatInput");
  const message = input.value.trim();
  if (!message) return;

  appendChat("You", message);
  input.value = "";

  try {
    const data = await api("/chat", {
      method: "POST",
      headers: jsonHeaders(),
      body: JSON.stringify({ message })
    });
    appendChat("AI", data.reply);
  } catch (e) {
    appendChat("AI", e.message);
  }
}

function appendChat(who, text) {
  const el = document.createElement("div");
  el.className = who === "You" ? "chat-user" : "chat-ai";
  el.textContent = `${who}: ${text}`;
  $("chatBox").appendChild(el);
  $("chatBox").scrollTop = $("chatBox").scrollHeight;
}

function downloadPDF() {
  if (!lastResult) {
    alert("Run a screening first.");
    return;
  }

  const { jsPDF } = window.jspdf;
  const doc = new jsPDF();
  doc.setFontSize(20);
  doc.text("AI Health Scanner Report", 20, 20);
  doc.setFontSize(12);
  doc.text(`Risk level: ${lastResult.risk_level}`, 20, 40);
  doc.text(`Screening score: ${Math.round(lastResult.risk_score * 100)}%`, 20, 50);
  doc.text("This is a screening result, not a diagnosis.", 20, 70);
  doc.text(`Generated: ${new Date().toLocaleString()}`, 20, 85);
  doc.save("AI_Health_Report.pdf");
}

async function boot() {
  if (!token()) {
    showLogin();
    return;
  }

  try {
    showDashboard();
    setMode("simple");
    await Promise.all([loadProfile(), loadHistory(), loadAnalytics()]);
  } catch {
    localStorage.removeItem("token");
    showLogin();
  }
}

$("loginBtn").onclick = login;
$("registerBtn").onclick = register;
$("logoutBtn").onclick = () => {
  localStorage.removeItem("token");
  showLogin();
};
document.querySelectorAll(".mode-btn").forEach(b => b.onclick = () => setMode(b.dataset.mode));
$("healthForm").onsubmit = runScan;
$("refreshBtn").onclick = () => Promise.all([loadHistory(), loadAnalytics()]);
$("downloadBtn").onclick = downloadPDF;
$("imageBtn").onclick = uploadImage;
$("chatToggle").onclick = () => $("chatbot").classList.toggle("hidden");
$("closeChat").onclick = () => $("chatbot").classList.add("hidden");
$("sendChat").onclick = sendChat;
$("chatInput").addEventListener("keydown", e => {
  if (e.key === "Enter") sendChat();
});
boot();

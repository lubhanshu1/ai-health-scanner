import React, { useState } from "react";
import axios from "axios";
import "../App.css";

const API_BASE = (process.env.REACT_APP_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);

  const loginUser = async (event) => {
    event.preventDefault();
    setStatus("");
    if (!email.trim() || !password) {
      setStatus("Enter your email and password.");
      return;
    }
    setBusy(true);
    try {
      const response = await axios.post(`${API_BASE}/login`, {
        email: email.trim(),
        password
      });
      if (!response.data?.access_token) {
        throw new Error("The server did not return an access token.");
      }
      localStorage.setItem("token", response.data.access_token);
      setStatus("Login successful. Authentication token saved.");
    } catch (error) {
      const detail = error.response?.data?.detail;
      setStatus(typeof detail === "string" ? detail : error.message || "Login failed. Check your credentials and API configuration.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="container">
      <form className="card" onSubmit={loginUser}>
        <h1>Welcome Back 👋</h1>
        <p className="subtitle">Login to continue</p>
        <input type="email" autoComplete="email" required placeholder="Enter Email"
          value={email} onChange={(e) => setEmail(e.target.value)} />
        <input type="password" autoComplete="current-password" required placeholder="Enter Password"
          value={password} onChange={(e) => setPassword(e.target.value)} />
        <button type="submit" disabled={busy}>{busy ? "Signing in…" : "Login"}</button>
        <p className="status" role="status" aria-live="polite">{status}</p>
        <p className="link">Don’t have an account?{" "}
          <span role="link" tabIndex={0} onClick={() => { window.location.href = "/"; }}
            onKeyDown={(e) => { if (e.key === "Enter") window.location.href = "/"; }}>Register</span>
        </p>
      </form>
    </div>
  );
}

export default Login;

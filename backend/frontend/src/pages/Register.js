import React, { useState } from "react";
import axios from "axios";
import "../App.css";

const API_BASE = (process.env.REACT_APP_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

function Register() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);

  const registerUser = async (event) => {
    event.preventDefault();
    setStatus("");
    if (!email.trim() || !password) {
      setStatus("Enter an email and password.");
      return;
    }
    if (password.length < 8) {
      setStatus("Password must be at least 8 characters.");
      return;
    }
    setBusy(true);
    try {
      await axios.post(`${API_BASE}/register`, { email: email.trim(), password });
      setStatus("Account created. You can now log in.");
      setPassword("");
    } catch (error) {
      const detail = error.response?.data?.detail;
      setStatus(typeof detail === "string" ? detail : "Registration failed. Check your details and try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="container">
      <form className="card" onSubmit={registerUser}>
        <h1>Create account</h1>
        <p className="subtitle">Register to use AI Health Scanner</p>
        <input type="email" autoComplete="email" required placeholder="Enter email"
          value={email} onChange={(e) => setEmail(e.target.value)} />
        <input type="password" autoComplete="new-password" required minLength={8}
          placeholder="Create password (8+ characters)" value={password}
          onChange={(e) => setPassword(e.target.value)} />
        <button type="submit" disabled={busy}>{busy ? "Creating account…" : "Register"}</button>
        <p className="status" role="status" aria-live="polite">{status}</p>
        <p className="link">Already have an account?{" "}
          <span role="link" tabIndex={0} onClick={() => { window.location.href = "/login"; }}
            onKeyDown={(e) => { if (e.key === "Enter") window.location.href = "/login"; }}>Login</span>
        </p>
        <p className="subtitle">For informational screening only; not a medical diagnosis.</p>
      </form>
    </div>
  );
}

export default Register;

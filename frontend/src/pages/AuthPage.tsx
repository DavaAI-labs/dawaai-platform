// src/pages/AuthPage.tsx
// Login or Register. Registration creates a new pharmacy + profile in one flow.

import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { signIn, signUp } from "../services/supabase";

type Tab = "login" | "register";

export default function AuthPage() {
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>("login");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Login fields
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  // Register fields
  const [regEmail, setRegEmail] = useState("");
  const [regPassword, setRegPassword] = useState("");
  const [pharmacyName, setPharmacyName] = useState("");
  const [ownerName, setOwnerName] = useState("");
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");
  const [licenseNo, setLicenseNo] = useState("");

  async function handleLogin(e: React.FormEvent) {
  e.preventDefault();
  setError(null);
  setLoading(true);
  try {
    await signIn(email, password);
    navigate("/");
  }catch (err: any) {
  setError(
    err?.message ||
    err?.error_description ||
    err?.error?.message ||
    (typeof err === "string" ? err : null) ||
    "Invalid email or password. Please try again."
  );
}finally {
    setLoading(false);
  }
}

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await signUp(regEmail, regPassword, { pharmacyName, ownerName, phone, address, licenseNo });
      navigate("/");
    } catch (err: any) {
      setError(err.message || "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        {/* Logo */}
        <div style={styles.logoRow}>
          <span style={{ fontSize: 36 }}>💊</span>
          <div>
            <h1 style={styles.logo}>DavaAI</h1>
            <p style={styles.tagline}>Smart Pharmacy Platform</p>
          </div>
        </div>

        {/* Tab switcher */}
        <div style={styles.tabs}>
          <button style={{ ...styles.tab, ...(tab === "login" ? styles.tabActive : {}) }} onClick={() => { setTab("login"); setError(null); }}>
            Login
          </button>
          <button style={{ ...styles.tab, ...(tab === "register" ? styles.tabActive : {}) }} onClick={() => { setTab("register"); setError(null); }}>
            Register Pharmacy
          </button>
        </div>

        {error && <div style={styles.error}>{error}</div>}

        {/* ── LOGIN ── */}
        {tab === "login" && (
          <form onSubmit={handleLogin} style={styles.form}>
            <Field label="Email" type="email" value={email} onChange={setEmail} placeholder="owner@pharmacy.com" required />
            <Field label="Password" type="password" value={password} onChange={setPassword} placeholder="••••••••" required />
            <button style={styles.submitBtn} type="submit" disabled={loading}>
              {loading ? "Signing in…" : "Sign In →"}
            </button>
          </form>
        )}

        {/* ── REGISTER ── */}
        {tab === "register" && (
          <form onSubmit={handleRegister} style={styles.form}>
            <p style={styles.sectionLabel}>Pharmacy Details</p>
            <Field label="Pharmacy Name" value={pharmacyName} onChange={setPharmacyName} placeholder="ABC Medical Store" required />
            <Field label="Owner Name" value={ownerName} onChange={setOwnerName} placeholder="Dr. Ramesh Kumar" required />
            <Field label="Phone" type="tel" value={phone} onChange={setPhone} placeholder="9876543210" />
            <Field label="Address" value={address} onChange={setAddress} placeholder="123 Main St, Delhi" />
            <Field label="Drug License No." value={licenseNo} onChange={setLicenseNo} placeholder="DL-HR-123456" />

            <p style={{ ...styles.sectionLabel, marginTop: 16 }}>Login Credentials</p>
            <Field label="Email" type="email" value={regEmail} onChange={setRegEmail} placeholder="owner@pharmacy.com" required />
            <Field label="Password" type="password" value={regPassword} onChange={setRegPassword} placeholder="Min 8 characters" required />

            <button style={styles.submitBtn} type="submit" disabled={loading}>
              {loading ? "Creating account…" : "Create Pharmacy Account →"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

function Field({ label, value, onChange, type = "text", placeholder, required }: {
  label: string; value: string; onChange: (v: string) => void;
  type?: string; placeholder?: string; required?: boolean;
}) {
  return (
    <div style={{ marginBottom: 12 }}>
      <label style={fieldStyles.label}>{label}{required && <span style={{ color: "#E53935" }}> *</span>}</label>
      <input
        style={fieldStyles.input}
        type={type}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        required={required}
      />
    </div>
  );
}

const fieldStyles = {
  label: { fontSize: 12, fontWeight: 600, color: "#5F5E5A", display: "block", marginBottom: 4 } as React.CSSProperties,
  input: {
    width: "100%", padding: "10px 12px", border: "1px solid #D9D7D1",
    borderRadius: 8, fontSize: 14, outline: "none", background: "#FAFAF8",
    boxSizing: "border-box",
  } as React.CSSProperties,
};

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: "100vh", background: "linear-gradient(160deg, #F0FBF7 0%, #F8F7F4 100%)",
    display: "flex", alignItems: "center", justifyContent: "center",
    padding: 16, fontFamily: "system-ui, sans-serif",
  },
  card: {
    background: "#fff", borderRadius: 20, padding: "28px 24px",
    width: "100%", maxWidth: 420,
    boxShadow: "0 4px 24px rgba(0,0,0,0.08)",
  },
  logoRow: { display: "flex", alignItems: "center", gap: 12, marginBottom: 24 },
  logo: { fontSize: 22, fontWeight: 700, margin: 0, color: "#0D7A56" },
  tagline: { fontSize: 12, color: "#888780", margin: "2px 0 0" },
  tabs: {
    display: "flex", background: "#F1EFE8", borderRadius: 10,
    padding: 3, marginBottom: 20, gap: 3,
  },
  tab: {
    flex: 1, padding: "9px 0", border: "none", background: "none",
    borderRadius: 8, fontSize: 13, fontWeight: 500, color: "#888780", cursor: "pointer",
  },
  tabActive: { background: "#fff", color: "#0D7A56", fontWeight: 600, boxShadow: "0 1px 4px rgba(0,0,0,0.08)" },
  error: {
    background: "#FEF0F0", border: "1px solid #FCA5A5", borderRadius: 8,
    padding: "10px 12px", fontSize: 13, color: "#A32D2D", marginBottom: 16,
  },
  form: { display: "flex", flexDirection: "column" },
  sectionLabel: { fontSize: 11, fontWeight: 700, color: "#B0AEA8", textTransform: "uppercase", letterSpacing: "0.07em", margin: "0 0 10px" },
  submitBtn: {
    marginTop: 8, padding: "13px 0", background: "#1D9E75", color: "#fff",
    border: "none", borderRadius: 10, fontSize: 15, fontWeight: 600, cursor: "pointer",
  },
};
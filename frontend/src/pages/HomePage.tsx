// src/pages/HomePage.tsx — v3
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { signOut } from "../services/supabase";

export default function HomePage() {
  const navigate = useNavigate();
  const { pharmacy, profile } = useAuth();
  const [signingOut, setSigningOut] = useState(false);

  async function handleSignOut() {
    setSigningOut(true);
    await signOut();
    navigate("/auth");
  }

  return (
    <div style={styles.page}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.logoRow}>
          <span style={{ fontSize: 28 }}>💊</span>
          <div>
            <h1 style={styles.logo}>DavaAI</h1>
            <p style={styles.tagline}>{pharmacy?.name || "Smart Pharmacy"}</p>
          </div>
        </div>
        <button style={styles.signOutBtn} onClick={handleSignOut} disabled={signingOut}>
          {signingOut ? "…" : "Sign Out"}
        </button>
      </div>

      {/* Welcome */}
      <div style={styles.banner}>
        <p style={styles.bannerText}>👋 Welcome back, {profile?.full_name?.split(" ")[0] || "Chemist"}!</p>
      </div>

      {/* Main actions */}
      <div style={styles.grid}>
        <ActionCard
          icon="📄"
          title="Scan Prescription"
          desc="AI reads handwritten or printed prescriptions. Auto-matches to your inventory."
          flow={["OCR + AI Fix", "Match Inventory", "Bill"]}
          cta="Start Scanning"
          onClick={() => navigate("/scan")}
        />
        <ActionCard
          icon="🔴"
          title="Scan Barcode"
          desc="Scan medicine barcode/QR to fetch details and add to bill instantly."
          flow={["Scan Code", "Medicine Details", "Add to Bill"]}
          cta="Scan Barcode"
          onClick={() => navigate("/barcode")}
        />
      </div>

      {/* Quick actions */}
      <div style={styles.quickSection}>
        <p style={styles.quickLabel}>Quick Actions</p>
        <div style={styles.quickGrid}>
          <QuickBtn icon="📦" label="Inventory" sub="Manage stock" onClick={() => navigate("/inventory")} />
          <QuickBtn icon="⚠️" label="Expiring" sub="Check alerts" onClick={() => navigate("/inventory")} />
          <QuickBtn icon="🧾" label="Bills" sub="Today's bills" onClick={() => navigate("/bills")} />
          <QuickBtn icon="🏭" label="Suppliers" sub="Manage vendors" onClick={() => navigate("/suppliers")} />
        </div>
      </div>
    </div>
  );
}

function ActionCard({ icon, title, desc, flow, cta, onClick }: {
  icon: string; title: string; desc: string; flow: string[]; cta: string; onClick: () => void;
}) {
  return (
    <button style={styles.card} onClick={onClick}>
      <span style={{ fontSize: 32 }}>{icon}</span>
      <div>
        <p style={styles.cardTitle}>{title}</p>
        <p style={styles.cardDesc}>{desc}</p>
      </div>
      <div style={styles.flowRow}>
        {flow.map((f, i) => (
          <React.Fragment key={f}>
            <span style={styles.chip}>{f}</span>
            {i < flow.length - 1 && <span style={{ color: "#1D9E75", fontSize: 10, margin: "0 2px" }}>→</span>}
          </React.Fragment>
        ))}
      </div>
      <div style={styles.cardCta}>{cta} →</div>
    </button>
  );
}

function QuickBtn({ icon, label, sub, onClick }: { icon: string; label: string; sub: string; onClick: () => void }) {
  return (
    <button style={styles.quickBtn} onClick={onClick}>
      <span style={{ fontSize: 22 }}>{icon}</span>
      <p style={styles.quickBtnLabel}>{label}</p>
      <p style={styles.quickBtnSub}>{sub}</p>
    </button>
  );
}

const styles: Record<string, React.CSSProperties> = {
  page: { minHeight: "100vh", background: "linear-gradient(160deg, #F0FBF7 0%, #F8F7F4 100%)", fontFamily: "system-ui, sans-serif", paddingBottom: 32 },
  header: { display: "flex", alignItems: "center", justifyContent: "space-between", padding: "16px 16px 12px", background: "#fff", borderBottom: "1px solid #E8F5EF" },
  logoRow: { display: "flex", alignItems: "center", gap: 10 },
  logo: { fontSize: 20, fontWeight: 700, margin: 0, color: "#0D7A56" },
  tagline: { fontSize: 11, color: "#888780", margin: "1px 0 0" },
  signOutBtn: { background: "none", border: "1px solid #E8E6E0", borderRadius: 8, padding: "6px 12px", fontSize: 12, color: "#888780", cursor: "pointer" },
  banner: { padding: "12px 16px", background: "#E6F8F2", borderBottom: "1px solid #C3ECD9" },
  bannerText: { margin: 0, fontSize: 13, color: "#0D7A56", fontWeight: 500 },
  grid: { padding: 16, display: "flex", flexDirection: "column", gap: 12 },
  card: { background: "#fff", border: "1px solid #E8E6E0", borderRadius: 16, padding: 16, textAlign: "left", cursor: "pointer", display: "flex", flexDirection: "column", gap: 10, boxShadow: "0 2px 8px rgba(0,0,0,0.05)" },
  cardTitle: { fontSize: 16, fontWeight: 700, margin: "0 0 3px", color: "#1A1916" },
  cardDesc: { fontSize: 12, color: "#888780", margin: 0, lineHeight: 1.5 },
  flowRow: { display: "flex", alignItems: "center", flexWrap: "wrap", gap: 4 },
  chip: { background: "#E1F5EE", color: "#0D7A56", fontSize: 9, fontWeight: 600, padding: "2px 6px", borderRadius: 10 },
  cardCta: { fontSize: 13, fontWeight: 600, color: "#1D9E75", borderTop: "1px solid #F0EDE7", paddingTop: 10 },
  quickSection: { padding: "0 16px" },
  quickLabel: { fontSize: 11, color: "#B0AEA8", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.07em", margin: "0 0 10px" },
  quickGrid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 },
  quickBtn: { background: "#fff", border: "1px solid #E8E6E0", borderRadius: 12, padding: "14px 12px", display: "flex", flexDirection: "column", alignItems: "center", gap: 4, cursor: "pointer" },
  quickBtnLabel: { fontSize: 13, fontWeight: 600, color: "#1A1916", margin: 0 },
  quickBtnSub: { fontSize: 11, color: "#888780", margin: 0 },
};
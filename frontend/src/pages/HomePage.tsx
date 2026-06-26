// HomePage.tsx
// Entry point: pharmacist chooses between Scan Prescription (OCR) or Scan Barcode.
// Clean two-path UI matching the product flow in the design spec.

import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function HomePage() {
  const navigate = useNavigate();
  const [time] = useState(
    new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })
  );

  return (
    <div style={styles.page}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.logoRow}>
          <span style={styles.logoIcon}>💊</span>
          <div>
            <h1 style={styles.logo}>DavaAI</h1>
            <p style={styles.tagline}>Smart Pharmacy Assistant</p>
          </div>
        </div>
        <div style={styles.timeChip}>{time}</div>
      </div>

      {/* Welcome banner */}
      <div style={styles.banner}>
        <p style={styles.bannerText}>Good day! Choose how to add medicines to a bill.</p>
      </div>

      {/* Two main action cards */}
      <div style={styles.grid}>
        {/* Prescription OCR */}
        <button style={styles.card} onClick={() => navigate("/scan")}>
          <span style={styles.cardIcon}>📄</span>
          <div style={styles.cardBody}>
            <p style={styles.cardTitle}>Scan Prescription</p>
            <p style={styles.cardDesc}>
              Take a photo of a handwritten or printed prescription. AI reads and matches medicines automatically.
            </p>
          </div>
          <div style={styles.cardFlow}>
            <Chip>OCR</Chip>
            <Arrow />
            <Chip>Medicine Detection</Chip>
            <Arrow />
            <Chip>Bill</Chip>
          </div>
          <div style={styles.cardCta}>Start Scanning →</div>
        </button>

        {/* Barcode */}
        <button style={styles.card} onClick={() => navigate("/barcode")}>
          <span style={styles.cardIcon}>🔴</span>
          <div style={styles.cardBody}>
            <p style={styles.cardTitle}>Scan Medicine Barcode</p>
            <p style={styles.cardDesc}>
              Scan a barcode or QR code on a medicine strip to instantly fetch details and add to bill.
            </p>
          </div>
          <div style={styles.cardFlow}>
            <Chip>Scan Barcode/QR</Chip>
            <Arrow />
            <Chip>Medicine Details</Chip>
            <Arrow />
            <Chip>Add to Cart</Chip>
          </div>
          <div style={styles.cardCta}>Scan Barcode →</div>
        </button>
      </div>

      {/* Recent bills shortcut */}
      <div style={styles.recentSection}>
        <p style={styles.recentLabel}>⚡ Quick Actions</p>
        <div style={styles.quickRow}>
          <QuickBtn icon="🧾" label="Today's Bills" onClick={() => navigate("/bills")} />
          <QuickBtn icon="🔍" label="Search Medicine" onClick={() => navigate("/search")} />
          <QuickBtn icon="📦" label="Low Stock" onClick={() => navigate("/stock")} />
        </div>
      </div>
    </div>
  );
}

function Chip({ children }: { children: React.ReactNode }) {
  return <span style={chipStyle}>{children}</span>;
}
function Arrow() {
  return <span style={{ color: "#1D9E75", fontSize: 10, margin: "0 2px" }}>→</span>;
}
function QuickBtn({ icon, label, onClick }: { icon: string; label: string; onClick: () => void }) {
  return (
    <button style={styles.quickBtn} onClick={onClick}>
      <span style={{ fontSize: 20 }}>{icon}</span>
      <span style={styles.quickLabel}>{label}</span>
    </button>
  );
}

const chipStyle: React.CSSProperties = {
  background: "#E1F5EE",
  color: "#0D7A56",
  fontSize: 9,
  fontWeight: 600,
  padding: "2px 6px",
  borderRadius: 10,
  whiteSpace: "nowrap",
};

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: "100vh",
    background: "linear-gradient(160deg, #F0FBF7 0%, #F8F7F4 100%)",
    fontFamily: "system-ui, -apple-system, sans-serif",
    padding: "0 0 32px",
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "20px 20px 12px",
    background: "#fff",
    borderBottom: "1px solid #E8F5EF",
  },
  logoRow: { display: "flex", alignItems: "center", gap: 10 },
  logoIcon: { fontSize: 28 },
  logo: { fontSize: 20, fontWeight: 700, margin: 0, color: "#0D7A56" },
  tagline: { fontSize: 11, color: "#888780", margin: "1px 0 0" },
  timeChip: {
    background: "#F0FBF7",
    color: "#0D7A56",
    border: "1px solid #B6E6D4",
    borderRadius: 20,
    padding: "4px 12px",
    fontSize: 13,
    fontWeight: 500,
  },
  banner: {
    padding: "14px 20px",
    background: "#E6F8F2",
    borderBottom: "1px solid #C3ECD9",
  },
  bannerText: { margin: 0, fontSize: 13, color: "#0D7A56", fontWeight: 500 },
  grid: { padding: "16px", display: "flex", flexDirection: "column", gap: 12 },
  card: {
    background: "#fff",
    border: "1px solid #E8E6E0",
    borderRadius: 16,
    padding: "18px",
    textAlign: "left",
    cursor: "pointer",
    display: "flex",
    flexDirection: "column",
    gap: 10,
    boxShadow: "0 2px 8px rgba(0,0,0,0.05)",
    transition: "transform 0.1s, box-shadow 0.1s",
  },
  cardIcon: { fontSize: 32, lineHeight: 1 },
  cardBody: {},
  cardTitle: { fontSize: 16, fontWeight: 700, margin: "0 0 4px", color: "#1A1916" },
  cardDesc: { fontSize: 12, color: "#888780", margin: 0, lineHeight: 1.5 },
  cardFlow: { display: "flex", alignItems: "center", flexWrap: "wrap", gap: 4 },
  cardCta: {
    fontSize: 13,
    fontWeight: 600,
    color: "#1D9E75",
    borderTop: "1px solid #F0EDE7",
    paddingTop: 10,
    marginTop: 2,
  },
  recentSection: { padding: "4px 16px 0" },
  recentLabel: { fontSize: 11, color: "#B0AEA8", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.07em", margin: "0 0 10px" },
  quickRow: { display: "flex", gap: 10 },
  quickBtn: {
    flex: 1,
    background: "#fff",
    border: "1px solid #E8E6E0",
    borderRadius: 12,
    padding: "12px 8px",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 6,
    cursor: "pointer",
  },
  quickLabel: { fontSize: 11, color: "#5F5E5A", fontWeight: 500 },
};
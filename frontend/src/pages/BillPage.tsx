// BillPage.tsx
// Screen 3 of 3: shows the confirmed medicines as a clean printable bill.
// Pharmacist hands this to the customer or prints it.

import React from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { ConfirmedMedicine } from "../services/api";

export default function BillPage() {
  const navigate = useNavigate();
  const location = useLocation();

  const { bill_id, medicines, pharmacy_name } = location.state || {};

  if (!bill_id) {
    navigate("/");
    return null;
  }

  const now = new Date();
  const dateStr = now.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
  const timeStr = now.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });

  function handlePrint() {
    window.print();
  }

  function handleNewScan() {
    navigate("/");
  }

  return (
    <div style={styles.page}>
      {/* Action buttons — hidden on print */}
      <div style={styles.actions} className="no-print">
        <button style={styles.printBtn} onClick={handlePrint}>🖨 Print Bill</button>
        <button style={styles.newBtn} onClick={handleNewScan}>+ New Prescription</button>
      </div>

      {/* Bill — this is what gets printed */}
      <div style={styles.bill} id="printable-bill">
        {/* Header */}
        <div style={styles.billHeader}>
          <h2 style={styles.pharmacyName}>💊 {pharmacy_name || "DavaAI Pharmacy"}</h2>
          <p style={styles.billMeta}>Bill ID: {bill_id}</p>
          <p style={styles.billMeta}>{dateStr} · {timeStr}</p>
        </div>

        <div style={styles.divider} />

        {/* Column headers */}
        <div style={styles.tableHeader}>
          <span style={{ flex: 3 }}>Medicine</span>
          <span style={{ flex: 1, textAlign: "center" }}>Qty</span>
        </div>

        {/* Medicine rows */}
        {(medicines as ConfirmedMedicine[]).map((med, idx) => (
          <div key={idx} style={styles.tableRow}>
            <div style={{ flex: 3 }}>
              <p style={styles.medName}>{med.matched_name}</p>
              {med.generic_name && (
                <p style={styles.medGeneric}>{med.generic_name}</p>
              )}
            </div>
            <span style={{ flex: 1, textAlign: "center", fontSize: 14, color: "#1A1916" }}>
              {med.quantity}
            </span>
          </div>
        ))}

        <div style={styles.divider} />

        {/* Summary */}
        <div style={styles.summary}>
          <p style={styles.summaryText}>
            Total items: <strong>{medicines?.length || 0}</strong>
          </p>
          <p style={styles.summaryText}>
            Total medicines: <strong>{medicines?.reduce((s: number, m: ConfirmedMedicine) => s + m.quantity, 0) || 0}</strong>
          </p>
        </div>

        <div style={styles.divider} />

        {/* Footer */}
        <p style={styles.footer}>
          Digitized by DavaAI · davaai.in
        </p>
      </div>

      {/* Print styles injected inline */}
      <style>{`
        @media print {
          .no-print { display: none !important; }
          body { background: white; }
          #printable-bill { box-shadow: none; border: none; }
        }
      `}</style>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: "100vh",
    background: "#F8F7F4",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    padding: "16px",
    fontFamily: "system-ui, sans-serif",
  },
  actions: {
    display: "flex",
    gap: 10,
    marginBottom: 16,
    width: "100%",
    maxWidth: 420,
  },
  printBtn: {
    flex: 1,
    padding: "12px 0",
    background: "#1D9E75",
    color: "#fff",
    border: "none",
    borderRadius: 10,
    fontSize: 14,
    fontWeight: 600,
    cursor: "pointer",
  },
  newBtn: {
    flex: 1,
    padding: "12px 0",
    background: "#fff",
    color: "#1D9E75",
    border: "1px solid #1D9E75",
    borderRadius: 10,
    fontSize: 14,
    fontWeight: 600,
    cursor: "pointer",
  },
  bill: {
    width: "100%",
    maxWidth: 420,
    background: "#fff",
    borderRadius: 16,
    padding: "20px 20px 16px",
    boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
  },
  billHeader: { textAlign: "center", marginBottom: 12 },
  pharmacyName: { fontSize: 20, fontWeight: 700, margin: "0 0 4px", color: "#1A1916" },
  billMeta: { fontSize: 12, color: "#888780", margin: "2px 0" },
  divider: { height: 1, background: "#E8E6E0", margin: "12px 0" },
  tableHeader: {
    display: "flex",
    fontSize: 11,
    fontWeight: 500,
    color: "#888780",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    marginBottom: 8,
  },
  tableRow: {
    display: "flex",
    alignItems: "flex-start",
    padding: "8px 0",
    borderBottom: "1px solid #F1EFE8",
  },
  medName: { fontSize: 14, fontWeight: 600, color: "#1A1916", margin: 0 },
  medGeneric: { fontSize: 11, color: "#888780", margin: "2px 0 0" },
  summary: { padding: "4px 0" },
  summaryText: { fontSize: 13, color: "#5F5E5A", margin: "4px 0" },
  footer: { fontSize: 11, color: "#B0AEA8", textAlign: "center", margin: "8px 0 0" },
};
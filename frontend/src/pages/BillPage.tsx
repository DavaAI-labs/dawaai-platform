// BillPage.tsx — upgraded
// Screen 3: Printable bill supporting both Prescription-OCR and Barcode-scan sources.
// Shows: medicine name, strength, MRP per unit, quantity, line total, grand total.
// Barcode-sourced bills also show batch number and expiry.

import React from "react";
import { useNavigate, useLocation } from "react-router-dom";

interface BillMedicine {
  matched_name?: string;
  brand_name?: string;
  generic_name: string;
  quantity: number;
  strength?: string;
  mrp?: number;
  batch?: string;
  expiry?: string;
}

export default function BillPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { bill_id, medicines, pharmacy_name, source } = location.state || {};

  if (!bill_id) { navigate("/"); return null; }

  const now = new Date();
  const dateStr = now.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
  const timeStr = now.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
  const isBarcode = source === "barcode";

  const totalQty = (medicines as BillMedicine[]).reduce((s, m) => s + m.quantity, 0);
  const totalMrp = (medicines as BillMedicine[]).reduce((s, m) => s + (m.mrp || 0) * m.quantity, 0);
  const hasMrp = (medicines as BillMedicine[]).some(m => m.mrp);

  return (
    <div style={styles.page}>
      {/* Action buttons */}
      <div style={{ ...styles.actions, display: "flex" }} className="no-print">
        <button style={styles.printBtn} onClick={() => window.print()}>🖨 Print Bill</button>
        <button style={styles.shareBtn} onClick={() => {
          if (navigator.share) navigator.share({ title: "Medicine Bill", text: `Bill ${bill_id}` });
        }}>📤 Share</button>
        <button style={styles.newBtn} onClick={() => navigate("/")}>+ New</button>
      </div>

      {/* Printable Bill */}
      <div style={styles.bill} id="printable-bill">
        {/* Header */}
        <div style={styles.billHeader}>
          <h2 style={styles.pharmacyName}>💊 {pharmacy_name || "DavaAI Pharmacy"}</h2>
          <p style={styles.billMeta}>Bill ID: {bill_id}</p>
          <p style={styles.billMeta}>{dateStr} · {timeStr}</p>
          {isBarcode && (
            <span style={styles.sourceBadge}>Barcode Scan</span>
          )}
        </div>

        <div style={styles.divider} />

        {/* Column headers */}
        <div style={styles.tableHeader}>
          <span style={{ flex: 3 }}>Medicine</span>
          <span style={{ flex: 1, textAlign: "center" as const }}>Qty</span>
          {hasMrp && <span style={{ flex: 1, textAlign: "right" as const }}>MRP</span>}
          {hasMrp && <span style={{ flex: 1, textAlign: "right" as const }}>Total</span>}
        </div>

        {/* Medicine rows */}
        {(medicines as BillMedicine[]).map((med, idx) => {
          const name = med.matched_name || med.brand_name || "Unknown";
          const lineTotal = (med.mrp || 0) * med.quantity;
          return (
            <div key={idx} style={styles.tableRow}>
              <div style={{ flex: 3 }}>
                <p style={styles.medName}>{name}</p>
                {med.generic_name && <p style={styles.medGeneric}>{med.generic_name}{med.strength ? ` · ${med.strength}` : ""}</p>}
                {isBarcode && med.batch && (
                  <p style={styles.medMeta}>Batch: {med.batch} · Exp: {med.expiry}</p>
                )}
              </div>
              <span style={{ flex: 1, textAlign: "center" as const, fontSize: 14, color: "#1A1916", fontWeight: 500 }}>{med.quantity}</span>
              {hasMrp && <span style={{ flex: 1, textAlign: "right" as const, fontSize: 13, color: "#5F5E5A" }}>₹{(med.mrp || 0).toFixed(2)}</span>}
              {hasMrp && <span style={{ flex: 1, textAlign: "right" as const, fontSize: 13, fontWeight: 600, color: "#1A1916" }}>₹{lineTotal.toFixed(2)}</span>}
            </div>
          );
        })}

        <div style={styles.divider} />

        {/* Summary */}
        <div style={styles.summary}>
          <SummaryRow label="Total items" value={String(medicines?.length || 0)} />
          <SummaryRow label="Total medicines" value={String(totalQty)} />
          {hasMrp && (
            <SummaryRow label="Total MRP" value={`₹${totalMrp.toFixed(2)}`} highlight />
          )}
        </div>

        <div style={styles.divider} />

        <p style={styles.footer}>Powered by DavaAI · davaai.in</p>
        <p style={styles.footer}>This bill is computer generated</p>
      </div>

      <style>{`
        @media print {
          .no-print { display: none !important; }
          body { background: white; }
          #printable-bill { box-shadow: none !important; border: none !important; max-width: 100% !important; }
        }
      `}</style>
    </div>
  );
}

function SummaryRow({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", padding: "4px 0" }}>
      <p style={{ fontSize: 13, color: "#5F5E5A", margin: 0 }}>{label}</p>
      <p style={{ fontSize: highlight ? 16 : 13, fontWeight: highlight ? 700 : 500, color: highlight ? "#0D7A56" : "#1A1916", margin: 0 }}>{value}</p>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: "100vh", background: "#F8F7F4",
    display: "flex", flexDirection: "column", alignItems: "center",
    padding: "16px", fontFamily: "system-ui, sans-serif",
  },
  actions: { gap: 8, marginBottom: 16, width: "100%", maxWidth: 420 },
  printBtn: {
    flex: 2, padding: "12px 0", background: "#1D9E75", color: "#fff",
    border: "none", borderRadius: 10, fontSize: 14, fontWeight: 600, cursor: "pointer",
  },
  shareBtn: {
    flex: 1, padding: "12px 0", background: "#E1F5EE", color: "#0D7A56",
    border: "1px solid #C3ECD9", borderRadius: 10, fontSize: 14, fontWeight: 600, cursor: "pointer",
  },
  newBtn: {
    flex: 1, padding: "12px 0", background: "#fff", color: "#1D9E75",
    border: "1px solid #1D9E75", borderRadius: 10, fontSize: 14, fontWeight: 600, cursor: "pointer",
  },
  bill: {
    width: "100%", maxWidth: 420, background: "#fff",
    borderRadius: 16, padding: "20px 20px 16px",
    boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
  },
  billHeader: { textAlign: "center", marginBottom: 12 },
  pharmacyName: { fontSize: 20, fontWeight: 700, margin: "0 0 4px", color: "#1A1916" },
  billMeta: { fontSize: 12, color: "#888780", margin: "2px 0" },
  sourceBadge: {
    display: "inline-block", marginTop: 6,
    background: "#E1F5EE", color: "#0D7A56",
    border: "1px solid #C3ECD9", borderRadius: 12,
    padding: "2px 10px", fontSize: 11, fontWeight: 600,
  },
  divider: { height: 1, background: "#E8E6E0", margin: "12px 0" },
  tableHeader: {
    display: "flex", fontSize: 11, fontWeight: 500, color: "#888780",
    textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 8,
  },
  tableRow: {
    display: "flex", alignItems: "flex-start",
    padding: "8px 0", borderBottom: "1px solid #F1EFE8",
  },
  medName: { fontSize: 14, fontWeight: 600, color: "#1A1916", margin: 0 },
  medGeneric: { fontSize: 11, color: "#888780", margin: "2px 0 0" },
  medMeta: { fontSize: 10, color: "#B0AEA8", margin: "2px 0 0" },
  summary: { padding: "4px 0" },
  footer: { fontSize: 11, color: "#B0AEA8", textAlign: "center", margin: "4px 0 0" },
};
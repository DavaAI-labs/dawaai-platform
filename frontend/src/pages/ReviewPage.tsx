// ReviewPage.tsx
// Screen 2 of 3: pharmacist sees OCR suggestions, confirms or edits each line.
// This is the most important screen — trust is built or lost here.

import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import ConfidenceBadge from "../components/ConfidenceBadge";
import { confirmPrescription, ScanResponse, ScanLine, MedicineSuggestion, ConfirmedMedicine } from "../services/api";

interface LineState {
  ocr_raw: string;
  ocr_confidence: number;
  selected: MedicineSuggestion | null;   // which suggestion pharmacist picked
  custom_name: string;                    // if pharmacist typed manually
  is_manual: boolean;                     // true = pharmacist typed, not from suggestions
  quantity: number;
  original_suggestion: MedicineSuggestion | null; // first suggestion — to detect edits
}

export default function ReviewPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const scanResult: ScanResponse = location.state?.scanResult;


  // Build initial line states from scan result
  const [lines, setLines] = useState<LineState[]>(
    scanResult.lines.map((line: ScanLine) => ({
      ocr_raw: line.ocr_raw,
      ocr_confidence: line.confidence,
      selected: line.suggestions[0] || null,         // auto-select top suggestion
      custom_name: "",
      is_manual: false,
      quantity: 1,
      original_suggestion: line.suggestions[0] || null,
    }))
  );

  const [expandedLine, setExpandedLine] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pharmacyName] = useState("My Pharmacy");

  if (!scanResult) {
  navigate("/");
  return null;
}

  function selectSuggestion(lineIdx: number, suggestion: MedicineSuggestion) {
    setLines(prev => prev.map((l, i) =>
      i === lineIdx ? { ...l, selected: suggestion, is_manual: false, custom_name: "" } : l
    ));
    setExpandedLine(null);
  }

  function setQuantity(lineIdx: number, qty: number) {
    setLines(prev => prev.map((l, i) =>
      i === lineIdx ? { ...l, quantity: Math.max(1, qty) } : l
    ));
  }

  function removeLine(lineIdx: number) {
    setLines(prev => prev.filter((_, i) => i !== lineIdx));
  }

  async function handleConfirm() {
    const confirmedLines = lines.filter(l => l.selected || l.is_manual);
    if (confirmedLines.length === 0) {
      setError("Please confirm at least one medicine.");
      return;
    }

    setLoading(true);
    setError(null);

    const medicines: ConfirmedMedicine[] = confirmedLines.map(l => {
      const wasEdited =
        l.is_manual ||
        (l.selected?.matched_name !== l.original_suggestion?.matched_name);

      return {
        ocr_raw:      l.ocr_raw,
        matched_name: l.is_manual ? l.custom_name : (l.selected?.matched_name || ""),
        brand_name:   l.selected?.brand_name || "",
        generic_name: l.selected?.generic_name || "",
        strength:     l.selected?.strength || "",
        quantity:     l.quantity,
        was_edited:   wasEdited,
      };
    });

    try {
      const { bill_id } = await confirmPrescription(
        scanResult.scan_id,
        medicines,
        pharmacyName
      );
      navigate("/bill", { state: { bill_id, medicines, pharmacy_name: pharmacyName } });
    } catch {
      setError("Failed to confirm. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  const confirmedCount = lines.filter(l => l.selected || l.is_manual).length;

  return (
    <div style={styles.page}>
      {/* Header */}
      <div style={styles.header}>
        <button style={styles.back} onClick={() => navigate("/")}>← Back</button>
        <div>
          <h2 style={styles.title}>Review Medicines</h2>
          <p style={styles.sub}>{scanResult.lines.length} lines detected · tap to change</p>
        </div>
      </div>

      {/* Medicine lines */}
      <div style={styles.list}>
        {lines.map((line, idx) => {
          const suggestions = scanResult.lines[idx]?.suggestions || [];
          const isExpanded = expandedLine === idx;
          const conf = line.selected?.confidence_label || "low";

          return (
            <div key={idx} style={styles.card}>
              {/* OCR raw text */}
              <p style={styles.ocrRaw}>OCR: "{line.ocr_raw}"</p>

              {/* Selected medicine or placeholder */}
              <div style={styles.selectedRow}>
                <div style={{ flex: 1 }}>
                  {line.selected ? (
                    <>
                      <p style={styles.medicineName}>{line.selected.matched_name}</p>
                      <p style={styles.medicineDetail}>
                        {line.selected.generic_name} · {line.selected.form} · {line.selected.manufacturer}
                      </p>
                    </>
                  ) : (
                    <p style={{ color: "#A32D2D", fontSize: 14 }}>⚠ No match — type manually</p>
                  )}
                </div>
                <ConfidenceBadge label={conf} score={Math.round((line.selected?.score || 0))} size="sm" />
              </div>

              {/* Controls row */}
              <div style={styles.controls}>
                {/* Quantity */}
                <div style={styles.qtyRow}>
                  <button style={styles.qtyBtn} onClick={() => setQuantity(idx, line.quantity - 1)}>−</button>
                  <span style={styles.qtyNum}>{line.quantity}</span>
                  <button style={styles.qtyBtn} onClick={() => setQuantity(idx, line.quantity + 1)}>+</button>
                </div>

                {/* Change / expand */}
                <button
                  style={styles.changeBtn}
                  onClick={() => setExpandedLine(isExpanded ? null : idx)}
                >
                  {isExpanded ? "Close" : "Change ↓"}
                </button>

                {/* Remove line */}
                <button style={styles.removeBtn} onClick={() => removeLine(idx)}>✕</button>
              </div>

              {/* Suggestions dropdown */}
              {isExpanded && (
                <div style={styles.suggestions}>
                  <p style={styles.suggTitle}>Top matches:</p>
                  {suggestions.map((s: any, si: number) => (
                    <div
                      key={si}
                      style={{
                        ...styles.suggItem,
                        background: s.matched_name === line.selected?.matched_name ? "#E1F5EE" : "#fff",
                      }}
                      onClick={() => selectSuggestion(idx, s)}
                    >
                      <div style={{ flex: 1 }}>
                        <p style={styles.suggName}>{s.matched_name}</p>
                        <p style={styles.suggDetail}>{s.generic_name} · {s.manufacturer}</p>
                      </div>
                      <ConfidenceBadge label={s.confidence_label} score={s.score} size="sm" />
                    </div>
                  ))}

                  {/* Manual entry */}
                  <div style={styles.manualRow}>
                    <input
                      style={styles.manualInput}
                      placeholder="Type medicine name manually…"
                      value={line.custom_name}
                      onChange={e => setLines(prev => prev.map((l, i) =>
                        i === idx ? { ...l, custom_name: e.target.value, is_manual: true } : l
                      ))}
                    />
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {error && <p style={styles.error}>{error}</p>}

      {/* Confirm button */}
      <div style={styles.footer}>
        <button
          style={{ ...styles.confirmBtn, opacity: loading ? 0.7 : 1 }}
          onClick={handleConfirm}
          disabled={loading || confirmedCount === 0}
        >
          {loading ? "Confirming…" : `Confirm ${confirmedCount} Medicine${confirmedCount !== 1 ? "s" : ""} →`}
        </button>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  page: { minHeight: "100vh", background: "#F8F7F4", fontFamily: "system-ui, sans-serif", paddingBottom: 100 },
  header: { display: "flex", alignItems: "flex-start", gap: 12, padding: "16px 16px 8px", background: "#fff", borderBottom: "1px solid #E8E6E0" },
  back: { background: "none", border: "none", fontSize: 14, color: "#1D9E75", cursor: "pointer", padding: "4px 0", marginTop: 2 },
  title: { fontSize: 18, fontWeight: 600, margin: 0, color: "#1A1916" },
  sub: { fontSize: 12, color: "#888780", margin: "2px 0 0" },
  list: { padding: "12px 16px", display: "flex", flexDirection: "column", gap: 12 },
  card: { background: "#fff", borderRadius: 12, padding: 14, border: "1px solid #E8E6E0" },
  ocrRaw: { fontSize: 11, color: "#B0AEA8", fontFamily: "monospace", margin: "0 0 8px", background: "#F8F7F4", padding: "3px 7px", borderRadius: 6 },
  selectedRow: { display: "flex", alignItems: "flex-start", gap: 10, marginBottom: 10 },
  medicineName: { fontSize: 15, fontWeight: 600, color: "#1A1916", margin: 0 },
  medicineDetail: { fontSize: 11, color: "#888780", margin: "2px 0 0" },
  controls: { display: "flex", alignItems: "center", gap: 8 },
  qtyRow: { display: "flex", alignItems: "center", gap: 6, background: "#F8F7F4", borderRadius: 8, padding: "4px 8px" },
  qtyBtn: { background: "none", border: "none", fontSize: 18, cursor: "pointer", color: "#1D9E75", lineHeight: 1, padding: "0 2px" },
  qtyNum: { fontSize: 14, fontWeight: 500, minWidth: 20, textAlign: "center" },
  changeBtn: { fontSize: 12, color: "#1D9E75", background: "none", border: "1px solid #1D9E75", borderRadius: 8, padding: "4px 10px", cursor: "pointer" },
  removeBtn: { fontSize: 14, color: "#B0AEA8", background: "none", border: "none", cursor: "pointer", marginLeft: "auto" },
  suggestions: { marginTop: 10, borderTop: "1px solid #E8E6E0", paddingTop: 10 },
  suggTitle: { fontSize: 11, color: "#888780", margin: "0 0 6px", textTransform: "uppercase", letterSpacing: "0.05em" },
  suggItem: { display: "flex", alignItems: "center", gap: 8, padding: "8px 10px", borderRadius: 8, cursor: "pointer", marginBottom: 4, border: "1px solid #E8E6E0" },
  suggName: { fontSize: 13, fontWeight: 500, color: "#1A1916", margin: 0 },
  suggDetail: { fontSize: 11, color: "#888780", margin: "1px 0 0" },
  manualRow: { marginTop: 8 },
  manualInput: { width: "100%", padding: "8px 12px", border: "1px solid #D9D7D1", borderRadius: 8, fontSize: 13, outline: "none", boxSizing: "border-box" },
  footer: { position: "fixed", bottom: 0, left: 0, right: 0, padding: "12px 16px", background: "#fff", borderTop: "1px solid #E8E6E0" },
  confirmBtn: { width: "100%", padding: "14px 0", background: "#1D9E75", color: "#fff", border: "none", borderRadius: 12, fontSize: 16, fontWeight: 600, cursor: "pointer" },
  error: { color: "#A32D2D", fontSize: 13, textAlign: "center", padding: "0 16px" },
};

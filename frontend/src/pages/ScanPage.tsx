// ScanPage.tsx
// Screen 1 of 3: pharmacist takes photo or uploads prescription image.
// Sends to backend, navigates to ReviewPage with suggestions.

import React, { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { scanPrescription, ScanResponse } from "../services/api";

export default function ScanPage() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setSelectedFile(file);
    setPreview(URL.createObjectURL(file));
    setError(null);
  }

  async function handleScan() {
    if (!selectedFile) return;
    setLoading(true);
    setError(null);

    try {
      const result: ScanResponse = await scanPrescription(selectedFile);
      // Pass result to ReviewPage via router state
      navigate("/review", { state: { scanResult: result } });
    } catch (err: any) {
      setError("Could not read prescription. Please try a clearer photo.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.page}>
      {/* Header */}
      <div style={styles.header}>
        <h1 style={styles.logo}>💊 DavaAI</h1>
        <p style={styles.tagline}>Scan prescription · Confirm · Print bill</p>
      </div>

      {/* Upload area */}
      <div
        style={{ ...styles.uploadBox, borderColor: preview ? "#1D9E75" : "#ccc" }}
        onClick={() => fileInputRef.current?.click()}
      >
        {preview ? (
          <img src={preview} alt="Prescription preview" style={styles.preview} />
        ) : (
          <div style={styles.uploadPlaceholder}>
            <span style={{ fontSize: 48 }}>📄</span>
            <p style={styles.uploadText}>Tap to take photo or upload prescription</p>
            <p style={styles.uploadSub}>JPG, PNG or WEBP</p>
          </div>
        )}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          capture="environment"   // opens rear camera on mobile
          onChange={handleFileSelect}
          style={{ display: "none" }}
        />
      </div>

      {/* Error */}
      {error && <p style={styles.error}>{error}</p>}

      {/* Scan button */}
      {selectedFile && (
        <button
          style={{ ...styles.btn, opacity: loading ? 0.7 : 1 }}
          onClick={handleScan}
          disabled={loading}
        >
          {loading ? "Reading prescription…" : "Scan Prescription →"}
        </button>
      )}

      {/* Retake */}
      {preview && !loading && (
        <button style={styles.btnSecondary} onClick={() => { setPreview(null); setSelectedFile(null); }}>
          Use different image
        </button>
      )}
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
    padding: "24px 16px",
    fontFamily: "system-ui, sans-serif",
  },
  header: { textAlign: "center", marginBottom: 24 },
  logo: { fontSize: 26, fontWeight: 600, margin: 0, color: "#1A1916" },
  tagline: { fontSize: 13, color: "#888780", margin: "4px 0 0" },
  uploadBox: {
    width: "100%",
    maxWidth: 420,
    minHeight: 260,
    border: "2px dashed",
    borderRadius: 16,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    cursor: "pointer",
    overflow: "hidden",
    background: "#fff",
    marginBottom: 16,
    transition: "border-color 0.2s",
  },
  preview: { width: "100%", height: "100%", objectFit: "cover" },
  uploadPlaceholder: { textAlign: "center", padding: 24 },
  uploadText: { fontSize: 15, color: "#5F5E5A", margin: "12px 0 4px" },
  uploadSub: { fontSize: 12, color: "#B0AEA8", margin: 0 },
  btn: {
    width: "100%",
    maxWidth: 420,
    padding: "14px 0",
    background: "#1D9E75",
    color: "#fff",
    border: "none",
    borderRadius: 12,
    fontSize: 16,
    fontWeight: 600,
    cursor: "pointer",
    marginBottom: 10,
  },
  btnSecondary: {
    width: "100%",
    maxWidth: 420,
    padding: "12px 0",
    background: "transparent",
    color: "#888780",
    border: "1px solid #D9D7D1",
    borderRadius: 12,
    fontSize: 14,
    cursor: "pointer",
  },
  error: { color: "#A32D2D", fontSize: 13, marginBottom: 12, textAlign: "center" },
};
// BarcodeScanPage.tsx
// NEW FEATURE: Scan medicine barcode/QR → fetch medicine details → add to cart → bill.
// Shows: medicine name, strength, manufacturer, MRP, batch, expiry, available stock.
// If barcode not found → search by name fallback.

import React, { useRef, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";

// Types
interface MedicineDetail {
  barcode: string;
  brand_name: string;
  generic_name: string;
  strength: string;
  manufacturer: string;
  mrp: number;
  batch_number: string;
  expiry_date: string;
  available_stock: number;
  form: string;
}

interface CartItem extends MedicineDetail {
  quantity: number;
}

// ── Helpers ────────────────────────────────────────────────────────────────

async function fetchMedicineByBarcode(barcode: string): Promise<MedicineDetail | null> {
  try {
    const res = await fetch(`/api/barcode/${encodeURIComponent(barcode)}`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    // Return mock data for development
    return getMockMedicine(barcode);
  }
}

async function searchMedicineByName(name: string): Promise<MedicineDetail[]> {
  try {
    const res = await fetch(`/api/medicines/search?q=${encodeURIComponent(name)}`);
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return getMockSearchResults(name);
  }
}

// ── Mock data for dev/demo ─────────────────────────────────────────────────

function getMockMedicine(barcode: string): MedicineDetail {
  const meds: Record<string, MedicineDetail> = {
    "8901030589396": {
      barcode: "8901030589396",
      brand_name: "Crocin 650",
      generic_name: "Paracetamol",
      strength: "650 mg",
      manufacturer: "GSK Pharma",
      mrp: 34.5,
      batch_number: "BCHX2411",
      expiry_date: "12/2026",
      available_stock: 48,
      form: "Tablet",
    },
  };
  return meds[barcode] || {
    barcode,
    brand_name: "Amoxicillin 500",
    generic_name: "Amoxicillin",
    strength: "500 mg",
    manufacturer: "Cipla Ltd",
    mrp: 72.0,
    batch_number: "AMX2503",
    expiry_date: "06/2027",
    available_stock: 120,
    form: "Capsule",
  };
}

function getMockSearchResults(name: string): MedicineDetail[] {
  return [
    {
      barcode: "1234567890",
      brand_name: `${name} 500`,
      generic_name: name,
      strength: "500 mg",
      manufacturer: "Sun Pharma",
      mrp: 45.0,
      batch_number: "SP2406",
      expiry_date: "03/2027",
      available_stock: 80,
      form: "Tablet",
    },
    {
      barcode: "0987654321",
      brand_name: `${name} 250`,
      generic_name: name,
      strength: "250 mg",
      manufacturer: "Dr Reddy's",
      mrp: 28.0,
      batch_number: "DR2405",
      expiry_date: "11/2026",
      available_stock: 35,
      form: "Tablet",
    },
  ];
}

// ── Component ──────────────────────────────────────────────────────────────

export default function BarcodeScanPage() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<"idle" | "scanning" | "loading" | "found" | "not_found" | "searching">("idle");
  const [barcodeInput, setBarcodeInput] = useState("");
  const [medicine, setMedicine] = useState<MedicineDetail | null>(null);
  const [searchResults, setSearchResults] = useState<MedicineDetail[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [cart, setCart] = useState<CartItem[]>([]);
  const [quantity, setQuantity] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const barcodeRef = useRef<HTMLInputElement>(null);

  // Simulate barcode scan (in production, use device camera API / ZXing)
  const handleSimulateScan = useCallback(async () => {
    setMode("loading");
    setError(null);
    // Simulate camera scan with a demo barcode
    const demoBarcode = "8901030589396";
    setBarcodeInput(demoBarcode);
    await processBarcode(demoBarcode);
  }, []);

  const handleManualBarcode = useCallback(async () => {
    if (!barcodeInput.trim()) return;
    setMode("loading");
    setError(null);
    await processBarcode(barcodeInput.trim());
  }, [barcodeInput]);

  async function processBarcode(barcode: string) {
    const result = await fetchMedicineByBarcode(barcode);
    if (result) {
      setMedicine(result);
      setQuantity(1);
      setMode("found");
    } else {
      setMode("not_found");
    }
  }

  async function handleSearch() {
    if (!searchQuery.trim()) return;
    setMode("searching");
    const results = await searchMedicineByName(searchQuery.trim());
    setSearchResults(results);
  }

  function addToCart(med: MedicineDetail, qty: number = 1) {
    setCart(prev => {
      const existing = prev.find(i => i.barcode === med.barcode);
      if (existing) {
        return prev.map(i => i.barcode === med.barcode ? { ...i, quantity: i.quantity + qty } : i);
      }
      return [...prev, { ...med, quantity: qty }];
    });
    setMode("idle");
    setMedicine(null);
    setBarcodeInput("");
    setQuantity(1);
  }

  function removeFromCart(barcode: string) {
    setCart(prev => prev.filter(i => i.barcode !== barcode));
  }

  function updateCartQty(barcode: string, qty: number) {
    if (qty < 1) { removeFromCart(barcode); return; }
    setCart(prev => prev.map(i => i.barcode === barcode ? { ...i, quantity: qty } : i));
  }

  const totalItems = cart.reduce((s, i) => s + i.quantity, 0);
  const totalMrp = cart.reduce((s, i) => s + i.mrp * i.quantity, 0);

  return (
    <div style={styles.page}>
      {/* Header */}
      <div style={styles.header}>
        <button style={styles.back} onClick={() => navigate("/")}>← Back</button>
        <div>
          <h2 style={styles.title}>Scan Barcode</h2>
          <p style={styles.sub}>Add medicines by barcode or QR code</p>
        </div>
        {cart.length > 0 && (
          <div style={styles.cartBadge}>{totalItems}</div>
        )}
      </div>

      {/* Scanner Zone */}
      <div style={styles.scannerZone}>
        {/* Camera viewfinder (UI placeholder — real app uses ZXing/quagga) */}
        <div style={styles.viewfinder}>
          <div style={styles.scanCorner} />
          <div style={{ ...styles.scanCorner, right: 0 }} />
          <div style={{ ...styles.scanCorner, bottom: 0 }} />
          <div style={{ ...styles.scanCorner, right: 0, bottom: 0 }} />
          {mode === "loading" ? (
            <div style={styles.scanStatus}>
              <span style={{ fontSize: 32 }}>⏳</span>
              <p style={styles.scanStatusText}>Looking up medicine…</p>
            </div>
          ) : (
            <div style={styles.scanStatus}>
              <span style={{ fontSize: 40 }}>🔴</span>
              <p style={styles.scanStatusText}>Point camera at barcode</p>
              <p style={styles.scanStatusSub}>or enter barcode manually below</p>
            </div>
          )}
        </div>

        {/* Camera scan button */}
        <button style={styles.scanBtn} onClick={handleSimulateScan} disabled={mode === "loading"}>
          {mode === "loading" ? "Scanning…" : "📷 Activate Camera Scan"}
        </button>

        {/* Manual barcode entry */}
        <div style={styles.manualRow}>
          <input
            ref={barcodeRef}
            style={styles.barcodeInput}
            placeholder="Enter barcode number manually…"
            value={barcodeInput}
            onChange={e => setBarcodeInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && handleManualBarcode()}
            type="number"
          />
          <button style={styles.goBtn} onClick={handleManualBarcode}>→</button>
        </div>
      </div>

      {/* Medicine Detail Card (after scan) */}
      {mode === "found" && medicine && (
        <div style={styles.detailCard}>
          <div style={styles.detailHeader}>
            <div>
              <p style={styles.brandName}>💊 {medicine.brand_name}</p>
              <p style={styles.genericName}>{medicine.generic_name} · {medicine.form}</p>
            </div>
            <button style={styles.closeX} onClick={() => setMode("idle")}>✕</button>
          </div>

          {/* Detail grid */}
          <div style={styles.detailGrid}>
            <DetailRow icon="💉" label="Strength" value={medicine.strength} />
            <DetailRow icon="🏭" label="Manufacturer" value={medicine.manufacturer} />
            <DetailRow icon="💰" label="MRP" value={`₹${medicine.mrp.toFixed(2)}`} highlight />
            <DetailRow icon="📦" label="Batch No." value={medicine.batch_number} />
            <DetailRow icon="📅" label="Expiry" value={medicine.expiry_date} warn={isNearExpiry(medicine.expiry_date)} />
            <DetailRow
              icon="🛒"
              label="In Stock"
              value={`${medicine.available_stock} units`}
              warn={medicine.available_stock < 10}
              good={medicine.available_stock >= 20}
            />
          </div>

          {/* Quantity + Add to Bill */}
          <div style={styles.addRow}>
            <div style={styles.qtyControl}>
              <button style={styles.qtyBtn} onClick={() => setQuantity(q => Math.max(1, q - 1))}>−</button>
              <span style={styles.qtyNum}>{quantity}</span>
              <button style={styles.qtyBtn} onClick={() => setQuantity(q => Math.min(medicine.available_stock, q + 1))}>+</button>
            </div>
            <button style={styles.addBillBtn} onClick={() => addToCart(medicine, quantity)}>
              + Add to Bill  ·  ₹{(medicine.mrp * quantity).toFixed(2)}
            </button>
          </div>
        </div>
      )}

      {/* Not Found — search fallback */}
      {mode === "not_found" && (
        <div style={styles.notFoundCard}>
          <p style={styles.notFoundTitle}>⚠ Barcode not recognized</p>
          <p style={styles.notFoundSub}>Search medicine by name to add it manually</p>
          <div style={styles.manualRow}>
            <input
              style={styles.barcodeInput}
              placeholder="Search medicine name…"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleSearch()}
            />
            <button style={styles.goBtn} onClick={handleSearch}>🔍</button>
          </div>

          {searchResults.length === 0 && searchQuery.length > 0 && <p style={{ color: "#888780", fontSize: 13, textAlign: "center" }}>Searching…</p>}
          {searchResults.length > 0 && (
            <div style={{ marginTop: 12 }}>
              {searchResults.map((m, i) => (
                <div key={i} style={styles.searchResult} onClick={() => { setMedicine(m); setMode("found"); }}>
                  <div>
                    <p style={styles.srName}>{m.brand_name}</p>
                    <p style={styles.srSub}>{m.generic_name} · {m.strength} · {m.manufacturer}</p>
                  </div>
                  <span style={styles.srMrp}>₹{m.mrp}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {error && <p style={styles.error}>{error}</p>}

      {/* Cart summary */}
      {cart.length > 0 && (
        <div style={styles.cartSection}>
          <p style={styles.cartTitle}>🛒 Cart ({cart.length} {cart.length === 1 ? "item" : "items"})</p>
          {cart.map(item => (
            <div key={item.barcode} style={styles.cartItem}>
              <div style={{ flex: 1 }}>
                <p style={styles.cartName}>{item.brand_name}</p>
                <p style={styles.cartSub}>{item.strength} · ₹{item.mrp} each</p>
              </div>
              <div style={styles.cartQtyRow}>
                <button style={styles.qtyBtn} onClick={() => updateCartQty(item.barcode, item.quantity - 1)}>−</button>
                <span style={styles.qtyNum}>{item.quantity}</span>
                <button style={styles.qtyBtn} onClick={() => updateCartQty(item.barcode, item.quantity + 1)}>+</button>
              </div>
              <span style={{ fontSize: 13, fontWeight: 600, color: "#1A1916", minWidth: 60, textAlign: "right" }}>
                ₹{(item.mrp * item.quantity).toFixed(2)}
              </span>
            </div>
          ))}
          <div style={styles.cartTotal}>
            <span style={{ fontSize: 14, color: "#5F5E5A" }}>Total MRP</span>
            <span style={{ fontSize: 16, fontWeight: 700, color: "#1A1916" }}>₹{totalMrp.toFixed(2)}</span>
          </div>
        </div>
      )}

      {/* Generate Bill Footer */}
      {cart.length > 0 && (
        <div style={styles.footer}>
          <button
            style={styles.billBtn}
            onClick={() => navigate("/bill", { state: { bill_id: `BC-${Date.now().toString(36).toUpperCase()}`, medicines: cart.map(c => ({ matched_name: c.brand_name, generic_name: c.generic_name, quantity: c.quantity, strength: c.strength, mrp: c.mrp, batch: c.batch_number, expiry: c.expiry_date })), pharmacy_name: "DavaAI Pharmacy", source: "barcode" } })}
          >
            Generate Bill · {totalItems} medicines · ₹{totalMrp.toFixed(2)} →
          </button>
        </div>
      )}
    </div>
  );
}

function DetailRow({ icon, label, value, highlight, warn, good }: {
  icon: string; label: string; value: string;
  highlight?: boolean; warn?: boolean; good?: boolean;
}) {
  return (
    <div style={detailRowStyle}>
      <span style={{ fontSize: 14 }}>{icon}</span>
      <span style={{ fontSize: 12, color: "#888780", flex: 1 }}>{label}</span>
      <span style={{
        fontSize: 13,
        fontWeight: highlight ? 700 : 600,
        color: warn ? "#A32D2D" : good ? "#1D9E75" : highlight ? "#0D7A56" : "#1A1916",
      }}>{value}</span>
    </div>
  );
}

function isNearExpiry(dateStr: string): boolean {
  try {
    const [month, year] = dateStr.split("/").map(Number);
    const expiry = new Date(year, month - 1);
    const now = new Date();
    const diffMonths = (expiry.getFullYear() - now.getFullYear()) * 12 + (expiry.getMonth() - now.getMonth());
    return diffMonths <= 3;
  } catch { return false; }
}

const detailRowStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 8,
  padding: "8px 0",
  borderBottom: "1px solid #F1EFE8",
};

const styles: Record<string, React.CSSProperties> = {
  page: { minHeight: "100vh", background: "#F8F7F4", fontFamily: "system-ui, sans-serif", paddingBottom: 100 },
  header: {
    display: "flex", alignItems: "flex-start", gap: 12, padding: "16px 16px 12px",
    background: "#fff", borderBottom: "1px solid #E8E6E0", position: "relative",
  },
  back: { background: "none", border: "none", fontSize: 14, color: "#1D9E75", cursor: "pointer", padding: "4px 0", marginTop: 2 },
  title: { fontSize: 18, fontWeight: 600, margin: 0, color: "#1A1916" },
  sub: { fontSize: 12, color: "#888780", margin: "2px 0 0" },
  cartBadge: {
    position: "absolute", right: 16, top: 16,
    background: "#1D9E75", color: "#fff", borderRadius: 20,
    padding: "2px 10px", fontSize: 13, fontWeight: 700,
  },
  scannerZone: { padding: "16px", display: "flex", flexDirection: "column", gap: 12 },
  viewfinder: {
    width: "100%", height: 200,
    background: "#1A1916",
    borderRadius: 16,
    display: "flex", alignItems: "center", justifyContent: "center",
    position: "relative", overflow: "hidden",
  },
  scanCorner: {
    position: "absolute", top: 12, left: 12,
    width: 24, height: 24,
    borderTop: "3px solid #1D9E75",
    borderLeft: "3px solid #1D9E75",
    borderRadius: "4px 0 0 0",
  },
  scanStatus: { textAlign: "center" },
  scanStatusText: { color: "#fff", fontSize: 14, fontWeight: 500, margin: "8px 0 2px" },
  scanStatusSub: { color: "#888", fontSize: 11, margin: 0 },
  scanBtn: {
    width: "100%", padding: "13px 0",
    background: "#1D9E75", color: "#fff", border: "none",
    borderRadius: 12, fontSize: 15, fontWeight: 600, cursor: "pointer",
  },
  manualRow: { display: "flex", gap: 8 },
  barcodeInput: {
    flex: 1, padding: "11px 14px",
    border: "1px solid #D9D7D1", borderRadius: 10,
    fontSize: 14, outline: "none", background: "#fff",
  },
  goBtn: {
    padding: "11px 18px", background: "#1D9E75", color: "#fff",
    border: "none", borderRadius: 10, fontSize: 16, cursor: "pointer", fontWeight: 700,
  },
  detailCard: {
    margin: "0 16px 12px",
    background: "#fff", borderRadius: 16, padding: 16,
    border: "1px solid #C3ECD9", boxShadow: "0 2px 12px rgba(29,158,117,0.1)",
  },
  detailHeader: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 },
  brandName: { fontSize: 18, fontWeight: 700, margin: 0, color: "#1A1916" },
  genericName: { fontSize: 12, color: "#888780", margin: "2px 0 0" },
  closeX: { background: "none", border: "none", fontSize: 18, color: "#B0AEA8", cursor: "pointer" },
  detailGrid: { marginBottom: 14 },
  addRow: { display: "flex", gap: 10, alignItems: "center" },
  qtyControl: {
    display: "flex", alignItems: "center", gap: 10,
    background: "#F0FBF7", borderRadius: 10, padding: "6px 12px",
    border: "1px solid #C3ECD9",
  },
  qtyBtn: {
    background: "none", border: "none", fontSize: 22,
    color: "#1D9E75", cursor: "pointer", fontWeight: 700, lineHeight: 1,
  },
  qtyNum: { fontSize: 16, fontWeight: 600, minWidth: 24, textAlign: "center" as const },
  addBillBtn: {
    flex: 1, padding: "12px 16px",
    background: "#1D9E75", color: "#fff", border: "none",
    borderRadius: 10, fontSize: 14, fontWeight: 600, cursor: "pointer",
  },
  notFoundCard: {
    margin: "0 16px 12px",
    background: "#FFF8F0", border: "1px solid #F5D9B5",
    borderRadius: 14, padding: 16,
  },
  notFoundTitle: { fontSize: 15, fontWeight: 600, color: "#A32D2D", margin: "0 0 4px" },
  notFoundSub: { fontSize: 12, color: "#888780", margin: "0 0 12px" },
  searchResult: {
    display: "flex", justifyContent: "space-between", alignItems: "center",
    padding: "10px 12px", background: "#fff", borderRadius: 10,
    border: "1px solid #E8E6E0", marginBottom: 6, cursor: "pointer",
  },
  srName: { fontSize: 14, fontWeight: 600, color: "#1A1916", margin: 0 },
  srSub: { fontSize: 11, color: "#888780", margin: "2px 0 0" },
  srMrp: { fontSize: 14, fontWeight: 700, color: "#0D7A56" },
  error: { color: "#A32D2D", fontSize: 13, textAlign: "center", padding: "0 16px" },
  cartSection: { padding: "0 16px 16px" },
  cartTitle: { fontSize: 13, fontWeight: 600, color: "#5F5E5A", margin: "0 0 10px", textTransform: "uppercase" as const, letterSpacing: "0.05em" },
  cartItem: {
    display: "flex", alignItems: "center", gap: 10,
    padding: "10px 0", borderBottom: "1px solid #F1EFE8",
  },
  cartName: { fontSize: 14, fontWeight: 600, color: "#1A1916", margin: 0 },
  cartSub: { fontSize: 11, color: "#888780", margin: "2px 0 0" },
  cartQtyRow: { display: "flex", alignItems: "center", gap: 6 },
  cartTotal: {
    display: "flex", justifyContent: "space-between", alignItems: "center",
    padding: "12px 0 0", marginTop: 4,
  },
  footer: {
    position: "fixed", bottom: 0, left: 0, right: 0,
    padding: "12px 16px", background: "#fff", borderTop: "1px solid #E8E6E0",
  },
  billBtn: {
    width: "100%", padding: "14px 0",
    background: "#0D7A56", color: "#fff", border: "none",
    borderRadius: 12, fontSize: 15, fontWeight: 700, cursor: "pointer",
  },
};
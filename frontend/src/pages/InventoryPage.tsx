// src/pages/InventoryPage.tsx
// Full inventory management: add, edit, delete medicines.
// Shows: stock quantity, expiry date (with color alerts), purchase price, MRP, margin %.
// Tabs: All Stock | ⚠ Expiring | 📦 Low Stock

import React, { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import {
  getInventory, addInventoryItem, updateInventoryItem, deleteInventoryItem,
  getExpiryAlerts, getLowStockAlerts, getSuppliers,
  InventoryItem, ExpiryAlert, Supplier,
} from "../services/supabase";

type ActiveTab = "all" | "expiring" | "lowstock";

export default function InventoryPage() {
  const navigate = useNavigate();
  const { pharmacy } = useAuth();
  const [tab, setTab] = useState<ActiveTab>("all");
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [expiryAlerts, setExpiryAlerts] = useState<ExpiryAlert[]>([]);
  const [lowStock, setLowStock] = useState<InventoryItem[]>([]);
  const [suppliers, setSuppliers] = useState<Supplier[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editItem, setEditItem] = useState<InventoryItem | null>(null);

  const load = useCallback(async () => {
    if (!pharmacy) return;
    setLoading(true);
    const [inv, exp, low, sup] = await Promise.all([
      getInventory(pharmacy.id),
      getExpiryAlerts(pharmacy.id),
      getLowStockAlerts(pharmacy.id),
      getSuppliers(pharmacy.id),
    ]);
    setItems(inv);
    setExpiryAlerts(exp);
    setLowStock(low);
    setSuppliers(sup);
    setLoading(false);
  }, [pharmacy]);

  useEffect(() => { load(); }, [load]);

  const filtered = items.filter(i =>
    i.brand_name.toLowerCase().includes(search.toLowerCase()) ||
    i.generic_name.toLowerCase().includes(search.toLowerCase())
  );

  const displayItems = tab === "all" ? filtered : tab === "expiring" ? expiryAlerts : lowStock;

  function getExpiryColor(dateStr: string): string {
    const expiry = new Date(dateStr);
    const now = new Date();
    const days = Math.floor((expiry.getTime() - now.getTime()) / 86400000);
    if (days <= 30) return "#A32D2D";
    if (days <= 90) return "#C97A00";
    return "#1D9E75";
  }

  function getExpiryBg(dateStr: string): string {
    const expiry = new Date(dateStr);
    const now = new Date();
    const days = Math.floor((expiry.getTime() - now.getTime()) / 86400000);
    if (days <= 30) return "#FEF0F0";
    if (days <= 90) return "#FFF8E6";
    return "#F0FBF7";
  }

  function formatExpiry(dateStr: string): string {
    return new Date(dateStr).toLocaleDateString("en-IN", { month: "short", year: "numeric" });
  }

  async function handleDelete(id: string) {
    if (!window.confirm("Remove this medicine from inventory?")) return;
    await deleteInventoryItem(id);
    load();
  }

  return (
    <div style={styles.page}>
      {/* Header */}
      <div style={styles.header}>
        <button style={styles.back} onClick={() => navigate("/")}>← Home</button>
        <div>
          <h2 style={styles.title}>Inventory</h2>
          <p style={styles.sub}>{pharmacy?.name}</p>
        </div>
        <button style={styles.addBtn} onClick={() => { setEditItem(null); setShowForm(true); }}>+ Add</button>
      </div>

      {/* Alert strip */}
      {(expiryAlerts.length > 0 || lowStock.length > 0) && (
        <div style={styles.alertStrip}>
          {expiryAlerts.filter(e => e.alert_level === "critical").length > 0 && (
            <AlertChip color="#A32D2D" bg="#FEF0F0" label={`🔴 ${expiryAlerts.filter(e => e.alert_level === "critical").length} expiring in <30 days`} onClick={() => setTab("expiring")} />
          )}
          {expiryAlerts.filter(e => e.alert_level === "warning").length > 0 && (
            <AlertChip color="#C97A00" bg="#FFF8E6" label={`🟡 ${expiryAlerts.filter(e => e.alert_level === "warning").length} expiring in <3 months`} onClick={() => setTab("expiring")} />
          )}
          {lowStock.length > 0 && (
            <AlertChip color="#1D5FA3" bg="#EEF4FF" label={`📦 ${lowStock.length} low stock`} onClick={() => setTab("lowstock")} />
          )}
        </div>
      )}

      {/* Tabs */}
      <div style={styles.tabRow}>
        {(["all", "expiring", "lowstock"] as ActiveTab[]).map(t => (
          <button key={t} style={{ ...styles.tabBtn, ...(tab === t ? styles.tabBtnActive : {}) }} onClick={() => setTab(t)}>
            {t === "all" ? `All (${items.length})` : t === "expiring" ? `⚠ Expiring (${expiryAlerts.length})` : `📦 Low Stock (${lowStock.length})`}
          </button>
        ))}
      </div>

      {/* Search */}
      {tab === "all" && (
        <div style={{ padding: "0 16px 10px" }}>
          <input style={styles.search} placeholder="🔍 Search medicine…" value={search} onChange={e => setSearch(e.target.value)} />
        </div>
      )}

      {/* List */}
      <div style={styles.list}>
        {loading ? (
          <p style={styles.empty}>Loading…</p>
        ) : displayItems.length === 0 ? (
          <p style={styles.empty}>{tab === "all" ? "No medicines yet. Tap + Add to start." : "All clear! ✓"}</p>
        ) : (
          (displayItems as InventoryItem[]).map(item => (
            <div key={item.id} style={styles.card}>
              <div style={styles.cardTop}>
                <div style={{ flex: 1 }}>
                  <p style={styles.brandName}>{item.brand_name}</p>
                  <p style={styles.genericName}>{item.generic_name}{item.strength ? ` · ${item.strength}` : ""}{item.form ? ` · ${item.form}` : ""}</p>
                  {item.manufacturer && <p style={styles.mfg}>🏭 {item.manufacturer}</p>}
                </div>
                <div style={styles.cardActions}>
                  <button style={styles.editBtn} onClick={() => { setEditItem(item); setShowForm(true); }}>✏</button>
                  <button style={styles.delBtn} onClick={() => handleDelete(item.id)}>🗑</button>
                </div>
              </div>

              <div style={styles.cardGrid}>
                {/* Stock */}
                <Stat
                  label="Stock"
                  value={`${item.quantity} units`}
                  color={item.quantity <= item.low_stock_threshold ? "#A32D2D" : "#1D9E75"}
                  bg={item.quantity <= item.low_stock_threshold ? "#FEF0F0" : "#F0FBF7"}
                />
                {/* Expiry */}
                <Stat
                  label="Expiry"
                  value={formatExpiry(item.expiry_date)}
                  color={getExpiryColor(item.expiry_date)}
                  bg={getExpiryBg(item.expiry_date)}
                />
                {/* MRP */}
                {item.mrp && <Stat label="MRP" value={`₹${item.mrp}`} color="#1A1916" bg="#F8F7F4" />}
                {/* Margin */}
                {item.margin_pct != null && (
                  <Stat label="Margin" value={`${item.margin_pct}%`} color="#0D7A56" bg="#F0FBF7" />
                )}
              </div>

              {item.batch_number && (
                <p style={styles.batch}>Batch: {item.batch_number}{(item as any).suppliers?.name ? ` · ${(item as any).suppliers.name}` : ""}</p>
              )}
            </div>
          ))
        )}
      </div>

      {/* Add / Edit Form Modal */}
      {showForm && (
        <InventoryForm
          item={editItem}
          pharmacyId={pharmacy!.id}
          suppliers={suppliers}
          onSave={() => { setShowForm(false); load(); }}
          onClose={() => setShowForm(false)}
        />
      )}
    </div>
  );
}

// ── Stat chip ──────────────────────────────────────────────────────────────

function Stat({ label, value, color, bg }: { label: string; value: string; color: string; bg: string }) {
  return (
    <div style={{ background: bg, borderRadius: 8, padding: "6px 10px", textAlign: "center" as const }}>
      <p style={{ fontSize: 10, color: "#888780", margin: "0 0 2px", fontWeight: 600, textTransform: "uppercase" as const }}>{label}</p>
      <p style={{ fontSize: 13, fontWeight: 700, color, margin: 0 }}>{value}</p>
    </div>
  );
}

// ── Alert chip ─────────────────────────────────────────────────────────────

function AlertChip({ label, color, bg, onClick }: { label: string; color: string; bg: string; onClick: () => void }) {
  return (
    <button onClick={onClick} style={{ background: bg, color, border: `1px solid ${color}30`, borderRadius: 20, padding: "4px 10px", fontSize: 12, fontWeight: 600, cursor: "pointer" }}>
      {label}
    </button>
  );
}

// ── Add/Edit Form ──────────────────────────────────────────────────────────

function InventoryForm({ item, pharmacyId, suppliers, onSave, onClose }: {
  item: InventoryItem | null; pharmacyId: string; suppliers: Supplier[];
  onSave: () => void; onClose: () => void;
}) {
  const [form, setForm] = useState({
    brand_name: item?.brand_name || "",
    generic_name: item?.generic_name || "",
    strength: item?.strength || "",
    form: item?.form || "Tablet",
    manufacturer: item?.manufacturer || "",
    barcode: item?.barcode || "",
    quantity: String(item?.quantity || ""),
    low_stock_threshold: String(item?.low_stock_threshold || "10"),
    purchase_price: String(item?.purchase_price || ""),
    mrp: String(item?.mrp || ""),
    batch_number: item?.batch_number || "",
    expiry_date: item?.expiry_date || "",
    supplier_id: item?.supplier_id || "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function set(key: string, value: string) { setForm(f => ({ ...f, [key]: value })); }

  async function handleSave() {
    if (!form.brand_name || !form.generic_name || !form.expiry_date || !form.quantity) {
      setError("Brand name, generic name, quantity and expiry date are required."); return;
    }
    setSaving(true); setError(null);
    const payload: any = {
      ...form,
      pharmacy_id: pharmacyId,
      quantity: parseInt(form.quantity),
      low_stock_threshold: parseInt(form.low_stock_threshold),
      purchase_price: form.purchase_price ? parseFloat(form.purchase_price) : null,
      mrp: form.mrp ? parseFloat(form.mrp) : null,
      supplier_id: form.supplier_id || null,
    };
    try {
      if (item) await updateInventoryItem(item.id, payload);
      else await addInventoryItem(payload);
      onSave();
    } catch (e: any) { setError(e.message); }
    finally { setSaving(false); }
  }

  const F = ({ label, field, type = "text", options }: { label: string; field: string; type?: string; options?: string[] }) => (
    <div style={{ marginBottom: 10 }}>
      <label style={fStyle.label}>{label}</label>
      {options ? (
        <select style={fStyle.input} value={(form as any)[field]} onChange={e => set(field, e.target.value)}>
          {options.map(o => <option key={o}>{o}</option>)}
        </select>
      ) : (
        <input style={fStyle.input} type={type} value={(form as any)[field]} onChange={e => set(field, e.target.value)} />
      )}
    </div>
  );

  return (
    <div style={modalStyles.overlay}>
      <div style={modalStyles.modal}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
          <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>{item ? "Edit Medicine" : "Add Medicine"}</h3>
          <button style={{ background: "none", border: "none", fontSize: 20, cursor: "pointer", color: "#888" }} onClick={onClose}>✕</button>
        </div>

        {error && <div style={{ background: "#FEF0F0", color: "#A32D2D", borderRadius: 8, padding: "8px 12px", marginBottom: 12, fontSize: 13 }}>{error}</div>}

        <div style={{ overflowY: "auto", maxHeight: "65vh" }}>
          <SectionLabel>Medicine Identity</SectionLabel>
          <F label="Brand Name *" field="brand_name" />
          <F label="Generic Name *" field="generic_name" />
          <F label="Strength (e.g. 500 mg)" field="strength" />
          <F label="Form" field="form" options={["Tablet", "Capsule", "Syrup", "Injection", "Cream", "Drops", "Inhaler", "Other"]} />
          <F label="Manufacturer" field="manufacturer" />
          <F label="Barcode / QR" field="barcode" />

          <SectionLabel>Stock</SectionLabel>
          <F label="Quantity *" field="quantity" type="number" />
          <F label="Low Stock Alert Threshold" field="low_stock_threshold" type="number" />
          <F label="Batch Number" field="batch_number" />
          <F label="Expiry Date *" field="expiry_date" type="date" />

          <SectionLabel>Pricing</SectionLabel>
          <F label="Purchase Price (₹)" field="purchase_price" type="number" />
          <F label="MRP (₹)" field="mrp" type="number" />
          {form.purchase_price && form.mrp && (
            <p style={{ fontSize: 12, color: "#0D7A56", margin: "-4px 0 10px", fontWeight: 600 }}>
              Margin: {(((parseFloat(form.mrp) - parseFloat(form.purchase_price)) / parseFloat(form.purchase_price)) * 100).toFixed(1)}%
            </p>
          )}

          <SectionLabel>Supplier</SectionLabel>
          <div style={{ marginBottom: 10 }}>
            <label style={fStyle.label}>Supplier</label>
            <select style={fStyle.input} value={form.supplier_id} onChange={e => set("supplier_id", e.target.value)}>
              <option value="">-- None --</option>
              {suppliers.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
            </select>
          </div>
        </div>

        <button style={{ ...fStyle.submitBtn, marginTop: 12 }} onClick={handleSave} disabled={saving}>
          {saving ? "Saving…" : item ? "Update Medicine" : "Add to Inventory"}
        </button>
      </div>
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <p style={{ fontSize: 10, fontWeight: 700, color: "#B0AEA8", textTransform: "uppercase" as const, letterSpacing: "0.07em", margin: "12px 0 6px" }}>{children}</p>;
}

const fStyle = {
  label: { fontSize: 12, fontWeight: 600, color: "#5F5E5A", display: "block", marginBottom: 3 } as React.CSSProperties,
  input: { width: "100%", padding: "9px 11px", border: "1px solid #D9D7D1", borderRadius: 8, fontSize: 14, outline: "none", boxSizing: "border-box" } as React.CSSProperties,
  submitBtn: { width: "100%", padding: "13px 0", background: "#1D9E75", color: "#fff", border: "none", borderRadius: 10, fontSize: 15, fontWeight: 600, cursor: "pointer" } as React.CSSProperties,
};

const modalStyles = {
  overlay: { position: "fixed" as const, inset: 0, background: "rgba(0,0,0,0.45)", zIndex: 100, display: "flex", alignItems: "flex-end", justifyContent: "center" },
  modal: { background: "#fff", borderRadius: "20px 20px 0 0", padding: "20px 20px 32px", width: "100%", maxWidth: 480, fontFamily: "system-ui, sans-serif" },
};

const styles: Record<string, React.CSSProperties> = {
  page: { minHeight: "100vh", background: "#F8F7F4", fontFamily: "system-ui, sans-serif", paddingBottom: 32 },
  header: { display: "flex", alignItems: "flex-start", gap: 12, padding: "16px 16px 12px", background: "#fff", borderBottom: "1px solid #E8E6E0" },
  back: { background: "none", border: "none", fontSize: 14, color: "#1D9E75", cursor: "pointer", padding: "4px 0", marginTop: 4 },
  title: { fontSize: 18, fontWeight: 700, margin: 0, color: "#1A1916" },
  sub: { fontSize: 12, color: "#888780", margin: "2px 0 0" },
  addBtn: { marginLeft: "auto", padding: "8px 16px", background: "#1D9E75", color: "#fff", border: "none", borderRadius: 8, fontSize: 13, fontWeight: 600, cursor: "pointer" },
  alertStrip: { padding: "10px 16px", display: "flex", gap: 8, flexWrap: "wrap", background: "#FAFAF8", borderBottom: "1px solid #F1EFE8" },
  tabRow: { display: "flex", gap: 0, padding: "10px 16px 6px", overflowX: "auto" },
  tabBtn: { padding: "7px 14px", border: "1px solid #E8E6E0", background: "#fff", borderRadius: 20, fontSize: 12, fontWeight: 500, color: "#5F5E5A", cursor: "pointer", whiteSpace: "nowrap", marginRight: 6 },
  tabBtnActive: { background: "#1D9E75", color: "#fff", border: "1px solid #1D9E75", fontWeight: 600 },
  search: { width: "100%", padding: "10px 14px", border: "1px solid #D9D7D1", borderRadius: 10, fontSize: 14, outline: "none", background: "#fff", boxSizing: "border-box" },
  list: { padding: "0 16px", display: "flex", flexDirection: "column", gap: 10, marginTop: 4 },
  empty: { textAlign: "center", color: "#B0AEA8", fontSize: 14, padding: "40px 0" },
  card: { background: "#fff", borderRadius: 14, padding: 14, border: "1px solid #E8E6E0", boxShadow: "0 1px 4px rgba(0,0,0,0.04)" },
  cardTop: { display: "flex", alignItems: "flex-start", gap: 8, marginBottom: 10 },
  brandName: { fontSize: 15, fontWeight: 700, color: "#1A1916", margin: 0 },
  genericName: { fontSize: 12, color: "#888780", margin: "2px 0 0" },
  mfg: { fontSize: 11, color: "#B0AEA8", margin: "2px 0 0" },
  cardActions: { display: "flex", gap: 6 },
  editBtn: { background: "#F0FBF7", border: "none", borderRadius: 8, padding: "6px 10px", cursor: "pointer", fontSize: 14 },
  delBtn: { background: "#FEF0F0", border: "none", borderRadius: 8, padding: "6px 10px", cursor: "pointer", fontSize: 14 },
  cardGrid: { display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 6, marginBottom: 8 },
  batch: { fontSize: 11, color: "#B0AEA8", margin: 0 },
};
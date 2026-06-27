// src/services/supabase.ts
// Single source of truth for all Supabase calls.
// Replace VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in your .env

import { createClient } from "@supabase/supabase-js";

const SUPABASE_URL = process.env.REACT_APP_SUPABASE_URL!;
const SUPABASE_ANON_KEY = process.env.REACT_APP_SUPABASE_ANON_KEY!;

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// ── Types ──────────────────────────────────────────────────────────────────

export interface Pharmacy {
  id: string;
  name: string;
  owner_name: string;
  phone?: string;
  address?: string;
  license_no?: string;
}

export interface Profile {
  id: string;
  pharmacy_id: string;
  full_name: string;
  role: "owner" | "staff";
}

export interface Supplier {
  id: string;
  pharmacy_id: string;
  name: string;
  contact_name?: string;
  phone?: string;
  email?: string;
}

export interface InventoryItem {
  id: string;
  pharmacy_id: string;
  supplier_id?: string;
  brand_name: string;
  generic_name: string;
  strength?: string;
  form?: string;
  manufacturer?: string;
  barcode?: string;
  quantity: number;
  low_stock_threshold: number;
  purchase_price?: number;
  mrp?: number;
  margin_pct?: number;     // computed by DB
  batch_number?: string;
  expiry_date: string;     // ISO date string
  created_at: string;
  updated_at: string;
  // joined
  suppliers?: Supplier;
}

export interface ExpiryAlert extends InventoryItem {
  alert_level: "critical" | "warning";
  days_until_expiry: number;
  pharmacy_name: string;
}

export interface Bill {
  id: string;
  pharmacy_id: string;
  bill_number: string;
  source: "prescription" | "barcode" | "manual";
  patient_name?: string;
  total_mrp: number;
  total_items: number;
  created_at: string;
}

export interface BillItem {
  id: string;
  bill_id: string;
  inventory_id?: string;
  brand_name: string;
  generic_name?: string;
  strength?: string;
  quantity: number;
  mrp: number;
  line_total: number;
}

// ── Auth ───────────────────────────────────────────────────────────────────

export async function signUp(email: string, password: string, pharmacyData: {
  pharmacyName: string; ownerName: string; phone: string; address: string; licenseNo: string;
}) {
  const { data: authData, error: authError } = await supabase.auth.signUp({ email, password });
  if (authError) throw authError;

  const userId = authData.user?.id;
  if (!userId) throw new Error("Signup failed — no user ID returned");

  // If email confirmation is enabled, there's no live session yet — inserts would fail RLS
  if (!authData.session) {
    throw new Error("CONFIRM_EMAIL");
  }

  // Create pharmacy
  const { data: pharmacy, error: pError } = await supabase
    .from("pharmacies").insert({
      name: pharmacyData.pharmacyName,
      owner_name: pharmacyData.ownerName,
      phone: pharmacyData.phone,
      address: pharmacyData.address,
      license_no: pharmacyData.licenseNo,
    }).select().single();
  if (pError) throw pError;

  // Create profile
  const { error: profError } = await supabase.from("profiles").insert({
    id: userId,
    pharmacy_id: pharmacy.id,
    full_name: pharmacyData.ownerName,
    role: "owner",
  });
  if (profError) throw profError;

  return { user: authData.user, pharmacy };
}

export async function signIn(email: string, password: string) {
  const { data, error } = await supabase.auth.signInWithPassword({ email, password });
  if (error) throw error;
  return data;
}

export async function signOut() {
  await supabase.auth.signOut();
}

export async function getProfile(): Promise<Profile | null> {
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return null;
  const { data } = await supabase.from("profiles").select("*").eq("id", user.id).single();
  return data;
}

export async function getPharmacy(pharmacyId: string): Promise<Pharmacy | null> {
  const { data } = await supabase.from("pharmacies").select("*").eq("id", pharmacyId).single();
  return data;
}

// ── Inventory ──────────────────────────────────────────────────────────────

export async function getInventory(pharmacyId: string): Promise<InventoryItem[]> {
  const { data, error } = await supabase
    .from("inventory")
    .select("*, suppliers(name, phone)")
    .eq("pharmacy_id", pharmacyId)
    .order("brand_name");
  if (error) throw error;
  return data || [];
}

export async function addInventoryItem(item: Omit<InventoryItem, "id" | "created_at" | "updated_at" | "margin_pct">) {
  const { data, error } = await supabase.from("inventory").insert(item).select().single();
  if (error) throw error;
  return data;
}

export async function updateInventoryItem(id: string, updates: Partial<InventoryItem>) {
  const { data, error } = await supabase.from("inventory").update(updates).eq("id", id).select().single();
  if (error) throw error;
  return data;
}

export async function deleteInventoryItem(id: string) {
  const { error } = await supabase.from("inventory").delete().eq("id", id);
  if (error) throw error;
}

export async function decrementStock(inventoryId: string, qty: number) {
  const { error } = await supabase.rpc("decrement_stock", { item_id: inventoryId, amount: qty });
  if (error) {
    // Fallback: fetch then update
    const { data } = await supabase.from("inventory").select("quantity").eq("id", inventoryId).single();
    if (data) {
      await supabase.from("inventory").update({ quantity: Math.max(0, data.quantity - qty) }).eq("id", inventoryId);
    }
  }
}

// ── Expiry Alerts ──────────────────────────────────────────────────────────

export async function getExpiryAlerts(pharmacyId: string): Promise<ExpiryAlert[]> {
  const { data, error } = await supabase
    .from("expiry_alerts")
    .select("*")
    .eq("pharmacy_id", pharmacyId);
  if (error) throw error;
  return data || [];
}

// ── Low Stock ──────────────────────────────────────────────────────────────

export async function getLowStockAlerts(pharmacyId: string): Promise<InventoryItem[]> {
  const { data, error } = await supabase
    .from("low_stock_alerts")
    .select("*")
    .eq("pharmacy_id", pharmacyId);
  if (error) throw error;
  return data || [];
}

// ── Suppliers ──────────────────────────────────────────────────────────────

export async function getSuppliers(pharmacyId: string): Promise<Supplier[]> {
  const { data, error } = await supabase
    .from("suppliers").select("*").eq("pharmacy_id", pharmacyId).order("name");
  if (error) throw error;
  return data || [];
}

export async function addSupplier(supplier: Omit<Supplier, "id">) {
  const { data, error } = await supabase.from("suppliers").insert(supplier).select().single();
  if (error) throw error;
  return data;
}

// ── Bills ──────────────────────────────────────────────────────────────────

export async function createBill(bill: Omit<Bill, "id" | "created_at">, items: Omit<BillItem, "id" | "bill_id" | "line_total">[]) {
  const { data: billData, error: bError } = await supabase.from("bills").insert(bill).select().single();
  if (bError) throw bError;

  const billItems = items.map(i => ({ ...i, bill_id: billData.id }));
  const { error: iError } = await supabase.from("bill_items").insert(billItems);
  if (iError) throw iError;

  // Decrement stock for each item
  for (const item of items) {
    if (item.inventory_id) {
      await decrementStock(item.inventory_id, item.quantity);
    }
  }

  return billData;
}

export async function getBills(pharmacyId: string): Promise<Bill[]> {
  const { data, error } = await supabase
    .from("bills").select("*").eq("pharmacy_id", pharmacyId)
    .order("created_at", { ascending: false }).limit(50);
  if (error) throw error;
  return data || [];
}

export async function getBillItems(billId: string): Promise<BillItem[]> {
  const { data, error } = await supabase.from("bill_items").select("*").eq("bill_id", billId);
  if (error) throw error;
  return data || [];
}

// ── Barcode lookup ─────────────────────────────────────────────────────────

export async function getMedicineByBarcode(pharmacyId: string, barcode: string): Promise<InventoryItem | null> {
  const { data } = await supabase
    .from("inventory")
    .select("*")
    .eq("pharmacy_id", pharmacyId)
    .eq("barcode", barcode)
    .single();
  return data;
}

export async function searchInventory(pharmacyId: string, query: string): Promise<InventoryItem[]> {
  const { data } = await supabase
    .from("inventory")
    .select("*")
    .eq("pharmacy_id", pharmacyId)
    .or(`brand_name.ilike.%${query}%,generic_name.ilike.%${query}%`)
    .limit(8);
  return data || [];
}
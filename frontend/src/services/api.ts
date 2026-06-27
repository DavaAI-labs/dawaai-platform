// api.ts — Production version
// Sends pharmacy_id header on all backend calls so the server can scope
// inventory lookups to the logged-in pharmacy.

import axios from "axios";

const BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000/api";

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
});

// Inject pharmacy_id header automatically on every request
// Set by AuthContext after login
let _pharmacyId: string | null = null;
export function setPharmacyId(id: string | null) {
  _pharmacyId = id;
}

api.interceptors.request.use((config) => {
  if (_pharmacyId) {
    config.headers["x-pharmacy-id"] = _pharmacyId;
  }
  return config;
});

// ── Types ──────────────────────────────────────────────────────────────────

export interface MedicineSuggestion {
  inventory_id?: string;
  matched_name: string;
  brand_name: string;
  generic_name: string;
  strength: string;
  mrp?: number;
  quantity?: number;
  score: number;
  confidence_label: "high" | "medium" | "low";
}

export interface ScanLine {
  ocr_raw: string;
  corrected_name: string;
  ocr_confidence: number;
  strength_from_rx?: string;
  frequency?: string;
  duration?: string;
  matched: boolean;
  inventory_id?: string;
  matched_name: string;
  generic_name: string;
  strength: string;
  mrp?: number;
  available_stock: number;
  score: number;
  confidence: number;
  confidence_label: "high" | "medium" | "low";
  flagged_for_review: boolean;
  suggestions: MedicineSuggestion[];
}

export interface ScanResponse {
  scan_id: string;
  scanned_at: string;
  total_detected: number;
  flagged_count: number;
  avg_confidence: number;
  lines: ScanLine[];
}

export interface ConfirmedMedicine {
  ocr_raw: string;
  matched_name: string;
  brand_name: string;
  generic_name: string;
  strength: string;
  quantity: number;
  was_edited: boolean;
}

export interface BillItem {
  name: string;
  brand: string;
  strength: string;
  quantity: number;
}

export interface BillResponse {
  bill_id: string;
  pharmacy_name: string;
  items: BillItem[];
  total_items: number;
  generated_at: string;
}

// ── API calls ──────────────────────────────────────────────────────────────

export async function scanPrescription(imageFile: File): Promise<ScanResponse> {
  const formData = new FormData();
  formData.append("file", imageFile);
  const response = await api.post<ScanResponse>("/scan", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function confirmPrescription(
  scan_id: string,
  medicines: ConfirmedMedicine[],
  pharmacy_name = "Pharmacy"
): Promise<{ bill_id: string; corrections_captured: number }> {
  const response = await api.post("/confirm", { scan_id, pharmacy_name, medicines });
  return response.data;
}

export async function getBill(bill_id: string): Promise<BillResponse> {
  const response = await api.get<BillResponse>(`/bill/${bill_id}`);
  return response.data;
}

export async function getMedicineByBarcode(barcode: string) {
  const response = await api.get(`/barcode/${barcode}`);
  return response.data;
}

export async function searchMedicines(q: string) {
  const response = await api.get(`/medicines/search`, { params: { q } });
  return response.data;
}

export async function createBarcodeBill(payload: {
  pharmacy_id?: string;
  pharmacy_name?: string;
  cart: {
    barcode: string;
    brand_name: string;
    generic_name: string;
    strength: string;
    quantity: number;
    mrp: number;
    batch_number?: string;
    expiry_date?: string;
  }[];
}) {
  const response = await api.post("/barcode/bill", payload);
  return response.data;
}

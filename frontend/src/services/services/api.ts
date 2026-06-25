// api.ts
// All backend calls live here. Never call fetch() directly from a component.
// Base URL reads from .env so it works in dev and production without changes.

import axios from "axios";

const BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000/api";

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000, // 30s — OCR can be slow on large images
});


// ── Types ──────────────────────────────────────────────────────────────────

export interface MedicineSuggestion {
  matched_name: string;
  brand_name: string;
  generic_name: string;
  strength: string;
  manufacturer: string;
  form: string;
  score: number;
  confidence_label: "high" | "medium" | "low";
}

export interface ScanLine {
  ocr_raw: string;
  confidence: number;      // 0.0 – 1.0 from OCR engine
  suggestions: MedicineSuggestion[];
}

export interface ScanResponse {
  scan_id: string;
  lines: ScanLine[];
  scanned_at: string;
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

/**
 * Upload prescription image → get OCR lines + medicine suggestions
 */
export async function scanPrescription(imageFile: File): Promise<ScanResponse> {
  const formData = new FormData();
  formData.append("file", imageFile);

  const response = await api.post<ScanResponse>("/scan", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

/**
 * Pharmacist confirms medicines → get bill_id
 */
export async function confirmPrescription(
  scan_id: string,
  medicines: ConfirmedMedicine[],
  pharmacy_name: string = "Pharmacy"
): Promise<{ bill_id: string; corrections_captured: number }> {
  const response = await api.post("/confirm", {
    scan_id,
    pharmacy_name,
    medicines,
  });
  return response.data;
}

/**
 * Fetch structured bill by bill_id for printing
 */
export async function getBill(bill_id: string): Promise<BillResponse> {
  const response = await api.get<BillResponse>(`/bill/${bill_id}`);
  return response.data;
}
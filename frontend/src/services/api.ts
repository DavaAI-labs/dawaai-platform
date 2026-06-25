import axios from "axios";
const BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000/api";
const api = axios.create({ baseURL: BASE_URL, timeout: 30000 });
export interface MedicineSuggestion { matched_name: string; brand_name: string; generic_name: string; strength: string; manufacturer: string; form: string; score: number; confidence_label: "high" | "medium" | "low"; }
export interface ScanLine { ocr_raw: string; confidence: number; suggestions: MedicineSuggestion[]; }
export interface ScanResponse { scan_id: string; lines: ScanLine[]; scanned_at: string; }
export interface ConfirmedMedicine { ocr_raw: string; matched_name: string; brand_name: string; generic_name: string; strength: string; quantity: number; was_edited: boolean; }
export interface BillResponse { bill_id: string; pharmacy_name: string; items: any[]; total_items: number; generated_at: string; }
export async function scanPrescription(imageFile: File): Promise<ScanResponse> { const formData = new FormData(); formData.append("file", imageFile); const response = await api.post<ScanResponse>("/scan", formData, { headers: { "Content-Type": "multipart/form-data" } }); return response.data; }
export async function confirmPrescription(scan_id: string, medicines: ConfirmedMedicine[], pharmacy_name: string = "Pharmacy"): Promise<{ bill_id: string; corrections_captured: number }> { const response = await api.post("/confirm", { scan_id, pharmacy_name, medicines }); return response.data; }
export async function getBill(bill_id: string): Promise<BillResponse> { const response = await api.get<BillResponse>("/bill/" + bill_id); return response.data; }

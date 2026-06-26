# DavaAI v2.0 — Upgrade Notes

## What's new vs v1

### 🏠 Home Screen (NEW)
- Dual-entry UI: **Scan Prescription** (OCR path) vs **Scan Medicine Barcode** (new path)
- Quick action shortcuts: Today's Bills, Search Medicine, Low Stock
- Shows flow diagrams so pharmacist knows what each path does

---

### 🔴 Barcode Scan (NEW — `BarcodeScanPage.tsx` + `barcode_routes.py`)
Full new feature matching the design spec:

**After scanning a barcode, shows:**
- 💊 Medicine name + generic name
- 💉 Strength (e.g., 500 mg)
- 🏭 Manufacturer
- 💰 Price (MRP)
- 📦 Batch number
- 📅 Expiry date (highlighted red if ≤3 months away)
- 🛒 Available stock (highlighted red if < 10 units)
- **+ Add to Bill** button with quantity selector and line total (₹)

**If barcode isn't recognized:**
- Search medicine by name fallback
- Top 5 results with MRP shown
- Select → shows full detail card → add to bill

**Cart:**
- Running cart with qty adjustment + remove
- Grand total MRP shown live
- One-tap "Generate Bill" with full breakdown

**Backend endpoints added:**
```
GET  /api/barcode/{barcode}          → medicine details by barcode
GET  /api/medicines/search?q=name    → name-based search fallback
POST /api/barcode/bill               → create bill from cart (decrements stock)
```

**Sample medicine DB:** `data/medicine_db/medicines_with_barcodes.csv`  
Add your medicines with columns: `barcode, brand_name, generic_name, strength, manufacturer, mrp, batch_number, expiry_date, available_stock, form`

---

### 🧾 Bill Page (upgraded)
- Supports both OCR prescriptions and barcode-scanned bills
- Shows MRP per unit + line totals + grand total for barcode bills
- Barcode bills display batch number and expiry per line
- Source badge ("Barcode Scan" vs prescription)
- Share button (Web Share API for WhatsApp/PDF)
- Print layout improved for thermal printers

---

### 🔧 Technical upgrades

**Frontend**
- Added `react-router-dom v6` route for `/barcode`
- Added `@zxing/library` for real camera barcode scanning (plug into `BarcodeScanPage` — see comment in component)
- All pages use `proxy: "http://localhost:8000"` so API calls work in dev

**Backend**
- `barcode_routes.py` — new router, auto-loaded in `main.py`
- In-memory barcode index with CSV loader; falls back to seeded demo data in dev
- Stock decrement on bill creation (in-memory for v2; swap for DB write in production)
- `main.py` now mounts both routers under `/api`

---

## Running locally

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm start
```

Open http://localhost:3000 — Home screen → choose Scan Prescription or Scan Barcode.

---

## Connecting a real barcode camera

In `BarcodeScanPage.tsx`, replace `handleSimulateScan` with ZXing:

```typescript
import { BrowserMultiFormatReader } from "@zxing/library";

const reader = new BrowserMultiFormatReader();
const result = await reader.decodeFromVideoDevice(null, videoRef.current, (res) => {
  if (res) {
    reader.reset();
    processBarcode(res.getText());
  }
});
```

Attach a `<video ref={videoRef}>` inside the viewfinder div.

---

## Adding medicines to barcode DB

Edit `data/medicine_db/medicines_with_barcodes.csv`:

```csv
barcode,brand_name,generic_name,strength,manufacturer,mrp,batch_number,expiry_date,available_stock,form
8901030512345,YourMed 250,Active Ingredient,250 mg,Manufacturer,45.00,BATCH001,06/2027,100,Tablet
```

The backend loads this at startup. Restart the server after changes.
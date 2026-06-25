# 💊 DavaAI — Phase 1

Prescription digitizer for Indian pharmacies.
Camera → OCR → Fuzzy match → Pharmacist confirms → Bill printed.

---

## Project structure

```
davaai/
├── backend/
│   ├── main.py                      ← FastAPI entry point
│   ├── requirements.txt
│   ├── api/
│   │   └── routes.py                ← /scan  /confirm  /bill
│   └── services/
│       ├── ocr_service.py           ← Google Vision API
│       ├── fuzzy_match.py           ← rapidfuzz medicine matching
│       └── correction_store.py      ← flywheel: saves pharmacist edits
├── frontend/
│   └── src/
│       ├── App.tsx                  ← routing
│       ├── pages/
│       │   ├── ScanPage.tsx         ← camera / upload
│       │   ├── ReviewPage.tsx       ← confirm medicines
│       │   └── BillPage.tsx         ← printable bill
│       ├── components/
│       │   └── ConfidenceBadge.tsx  ← 🟢🟡🔴 trust indicator
│       └── services/
│           └── api.ts               ← all backend calls
└── data/
    ├── medicine_db/
    │   └── medicines.csv            ← top-500 Indian medicines
    └── corrections/
        └── corrections.jsonl        ← flywheel training pairs (auto-created)
```

---

## Setup

### 1. Get a Google Vision API key
- Go to https://console.cloud.google.com
- Enable the **Cloud Vision API**
- Create an API key under Credentials
- Paste it into `.env`

### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example ../.env        # fill in your API key
uvicorn main:app --reload --port 8000
```

Backend runs at: http://localhost:8000
API docs at:     http://localhost:8000/docs

### 3. Frontend

```bash
cd frontend
npm install
npm start
```

Frontend runs at: http://localhost:3000

---

## Testing without a Google Vision API key

If `GOOGLE_VISION_API_KEY` is not set, the OCR service returns **mock data** —
realistic prescription lines with common OCR errors. You can test the full
Scan → Review → Bill flow without any API key.

---

## The flywheel

Every time a pharmacist changes a suggestion, the correction is saved to:
```
data/corrections/corrections.jsonl
```

Each line looks like:
```json
{"scan_id":"a3f9bc","ocr_raw":"Tab Amoxici1lin 500mg","corrected_to":"Amoxicillin 500mg","brand_name":"Novamox","timestamp":"2024-01-15T10:32:11"}
```

After ~5,000 lines, you have a fine-tuning dataset. That's your moat.

---

## Phase 2 (do not build yet)

- Dosage risk engine (flag 5000mg vs 500mg)
- Offline mode / sync queue
- Basic inventory deduction
- Multi-tenant isolation
- Model retraining pipeline
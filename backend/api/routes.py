# routes.py — 3 endpoints for phase 1
# POST /api/scan       → upload prescription image, get medicine suggestions
# POST /api/confirm    → pharmacist submits confirmed medicines, saves correction pairs
# GET  /api/bill/{id}  → get structured bill for confirmed prescription

import uuid
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional

from services.ocr_service import run_ocr
from services.fuzzy_match import match_medicines
from services.correction_store import save_corrections

router = APIRouter()

# In-memory store for confirmed prescriptions (phase 1 — no DB needed)
import json as _json

STORE_PATH = Path(__file__).parent.parent.parent / "data" / "confirmed_store.json"

def _load_store() -> dict:
    if STORE_PATH.exists():
        return _json.loads(STORE_PATH.read_text())
    return {}

def _save_store(store: dict):
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STORE_PATH.write_text(_json.dumps(store))

confirmed_store: dict = _load_store()

CORRECTIONS_PATH = Path(__file__).parent.parent.parent / "data" / "corrections" / "corrections.jsonl"


# ── Request / Response models ──────────────────────────────────────────────

class MedicineLine(BaseModel):
    ocr_raw: str                   # what OCR read
    matched_name: str              # what pharmacist confirmed
    brand_name: Optional[str] = None
    generic_name: Optional[str] = None
    strength: Optional[str] = None
    quantity: Optional[int] = 1
    was_edited: bool = False       # did pharmacist change the suggestion?

class ConfirmRequest(BaseModel):
    scan_id: str
    pharmacy_name: Optional[str] = "Pharmacy"
    medicines: List[MedicineLine]


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.post("/scan")
async def scan_prescription(file: UploadFile = File(...)):
    """
    Takes a prescription image.
    Returns OCR text + top medicine suggestions per line.
    """
    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(status_code=400, detail="Upload a JPG, PNG or WEBP image")

    image_bytes = await file.read()
    scan_id = str(uuid.uuid4())[:8]

    # Step 1: OCR
    ocr_lines = run_ocr(image_bytes)

    # Step 2: fuzzy match each line against medicine DB
    suggestions = []
    for line in ocr_lines:
        matches = match_medicines(line["text"])
        suggestions.append({
            "ocr_raw": line["text"],
            "confidence": line["confidence"],  # 0.0 – 1.0
            "suggestions": matches             # top 3 matches
        })

    return {
        "scan_id": scan_id,
        "lines": suggestions,
        "scanned_at": datetime.utcnow().isoformat()
    }


@router.post("/confirm")
async def confirm_prescription(body: ConfirmRequest):
    """
    Pharmacist submits final confirmed medicines.
    Saves correction pairs for flywheel.
    Returns bill_id.
    """
    bill_id = str(uuid.uuid4())[:8]

    # Save confirmed prescription for bill retrieval
    confirmed_store[bill_id] = {
        "bill_id": bill_id,
        "scan_id": body.scan_id,
        "pharmacy_name": body.pharmacy_name,
        "medicines": [m.dict() for m in body.medicines],
        "confirmed_at": datetime.utcnow().isoformat()
    }
    _save_store(confirmed_store)

    # Save corrections to flywheel file
    edited_lines = [m for m in body.medicines if m.was_edited]
    if edited_lines:
        save_corrections(body.scan_id, edited_lines)

    return {
        "bill_id": bill_id,
        "medicine_count": len(body.medicines),
        "corrections_captured": len(edited_lines)
    }


@router.get("/bill/{bill_id}")
async def get_bill(bill_id: str):
    """
    Returns structured bill data for printing.
    """
    if bill_id not in confirmed_store:
        raise HTTPException(status_code=404, detail="Bill not found")

    data = confirmed_store[bill_id]

    # Build printable line items
    items = []
    for m in data["medicines"]:
        items.append({
            "name": m["matched_name"],
            "brand": m.get("brand_name", ""),
            "strength": m.get("strength", ""),
            "quantity": m.get("quantity", 1),
        })

    return {
        "bill_id": bill_id,
        "pharmacy_name": data["pharmacy_name"],
        "items": items,
        "total_items": len(items),
        "generated_at": datetime.utcnow().isoformat()
    }
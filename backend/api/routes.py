# api/routes.py — v3
# Prescription scan endpoint. Now pulls inventory from Supabase for fuzzy matching.

import uuid
from datetime import datetime
from fastapi import APIRouter, File, UploadFile, Header, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import httpx

from services.ocr_service import process_prescription

router = APIRouter()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")  # server-side key


async def get_pharmacy_inventory(pharmacy_id: str) -> list[dict]:
    """Fetch inventory for a pharmacy from Supabase (server-side)."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return []  # fallback: empty inventory
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SUPABASE_URL}/rest/v1/inventory",
            params={"pharmacy_id": f"eq.{pharmacy_id}", "select": "id,brand_name,generic_name,strength,mrp,quantity"},
            headers={
                "apikey": SUPABASE_SERVICE_KEY,
                "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            },
            timeout=10,
        )
        if resp.status_code != 200:
            return []
        return resp.json()


@router.post("/scan")
async def scan_prescription(
    file: UploadFile = File(...),
    x_pharmacy_id: Optional[str] = Header(None),
):
    """
    Upload prescription image → OCR → AI extraction → fuzzy match against inventory.
    Returns structured list of detected medicines with match confidence.
    """
    image_bytes = await file.read()

    # Fetch this pharmacy's inventory for matching
    inventory = []
    if x_pharmacy_id:
        inventory = await get_pharmacy_inventory(x_pharmacy_id)

    # Full pipeline
    results = process_prescription(image_bytes, inventory)

    scan_id = str(uuid.uuid4())[:8].upper()
    flagged_count = sum(1 for r in results if r.get("flagged_for_review"))
    avg_confidence = (sum(r.get("confidence", 0) for r in results) / len(results)) if results else 0

    return {
        "scan_id": scan_id,
        "scanned_at": datetime.utcnow().isoformat(),
        "total_detected": len(results),
        "flagged_count": flagged_count,
        "avg_confidence": round(avg_confidence, 2),
        "lines": results,
    }


@router.post("/corrections")
async def save_correction(body: dict):
    """Record pharmacist corrections to improve future matching."""
    # In production: write to Supabase corrections table or a JSONL file
    return {"status": "ok"}
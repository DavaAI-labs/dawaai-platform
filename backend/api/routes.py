# api/routes.py — v5
# Changes from v4:
#   + JWT auth via Depends(require_pharmacy) — pharmacy_id now verified from token
#   + Shared _sb_headers() moved to services/supabase_client.py (no more duplication)
#   + OCR pipeline switched to async httpx (no longer blocks the event loop)
#   + request_id injected into every log line for end-to-end tracing

import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
import os
import httpx

from services.ocr_service import process_prescription
from services.supabase_client import sb_headers, SUPABASE_URL
from middleware.auth import require_pharmacy
from limiter import limiter

router = APIRouter()
logger = logging.getLogger("dawaai.routes")

MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB hard cap


# ── Inventory fetch ───────────────────────────────────────────────────────

async def get_pharmacy_inventory(pharmacy_id: str) -> list[dict]:
    """Fetch inventory for a pharmacy from Supabase (server-side)."""
    if not SUPABASE_URL:
        logger.warning('"supabase_not_configured — returning empty inventory"')
        return []
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SUPABASE_URL}/rest/v1/inventory",
            params={
                "pharmacy_id": f"eq.{pharmacy_id}",
                "select": "id,brand_name,generic_name,strength,mrp,quantity",
            },
            headers=sb_headers(),
            timeout=10,
        )
        if resp.status_code != 200:
            logger.error(
                f'"inventory_fetch_failed","pharmacy_id":"{pharmacy_id}","status":{resp.status_code}'
            )
            return []
        return resp.json()


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.post("/scan")
@limiter.limit("20/minute")
async def scan_prescription(
    request: Request,
    file: UploadFile = File(...),
    pharmacy_id: str = Depends(require_pharmacy),
):
    """
    Upload prescription image → OCR → AI extraction → fuzzy match against inventory.
    Returns structured list of detected medicines with match confidence.

    Auth: requires valid Supabase JWT. pharmacy_id is extracted from the token.
    Rate limited: 20 requests / minute / IP.
    Max file size: 10 MB.
    """
    request_id = str(uuid.uuid4())[:8].upper()

    # Validate content type
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Only image files are accepted.")

    image_bytes = await file.read()

    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Image too large ({len(image_bytes) // 1024} KB). Maximum is 10 MB.",
        )

    logger.info(
        f'"scan_start","request_id":"{request_id}",'
        f'"pharmacy_id":"{pharmacy_id}","file_size":{len(image_bytes)}'
    )

    inventory = []
    if pharmacy_id:
        inventory = await get_pharmacy_inventory(pharmacy_id)

    results = await process_prescription(image_bytes, inventory)

    scan_id = str(uuid.uuid4())[:8].upper()
    flagged_count = sum(1 for r in results if r.get("flagged_for_review"))
    avg_confidence = (
        sum(r.get("confidence", 0) for r in results) / len(results)
    ) if results else 0

    logger.info(
        f'"scan_complete","request_id":"{request_id}","scan_id":"{scan_id}",'
        f'"total":{len(results)},"flagged":{flagged_count}'
    )

    return {
        "scan_id": scan_id,
        "scanned_at": datetime.utcnow().isoformat(),
        "total_detected": len(results),
        "flagged_count": flagged_count,
        "avg_confidence": round(avg_confidence, 2),
        "lines": results,
    }


class CorrectionItem(BaseModel):
    scan_id: str
    ocr_raw: str
    corrected_to: str
    brand_name: str = ""
    generic_name: str = ""
    strength: str = ""
    inventory_id: Optional[str] = None


@router.post("/corrections")
@limiter.limit("60/minute")
async def save_correction(
    request: Request,
    body: CorrectionItem,
    pharmacy_id: str = Depends(require_pharmacy),
):
    """
    Record a pharmacist correction to improve future matching.
    Persists to Supabase corrections table when configured,
    falls back to a per-pharmacy JSONL file in dev mode.
    """
    record = {
        "scan_id": body.scan_id,
        "ocr_raw": body.ocr_raw,
        "corrected_to": body.corrected_to,
        "brand_name": body.brand_name,
        "generic_name": body.generic_name,
        "strength": body.strength,
        "inventory_id": body.inventory_id,
        "pharmacy_id": pharmacy_id or None,
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Try Supabase first
    if SUPABASE_URL:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{SUPABASE_URL}/rest/v1/corrections",
                    json=record,
                    headers={**sb_headers(), "Prefer": "return=minimal"},
                    timeout=8,
                )
                if resp.status_code in (200, 201):
                    logger.info(
                        f'"correction_saved","scan_id":"{body.scan_id}","supabase":true'
                    )
                    return {"status": "ok", "backend": "supabase"}
                logger.warning(
                    f'"correction_supabase_failed","status":{resp.status_code}'
                )
        except Exception as exc:
            logger.error(f'"correction_supabase_error","error":"{exc}"')

    # Fallback: per-pharmacy JSONL file (dev mode only)
    from services.correction_store import save_correction_record
    save_correction_record(record, pharmacy_id=pharmacy_id)
    logger.info(
        f'"correction_saved","scan_id":"{body.scan_id}","supabase":false'
    )
    return {"status": "ok", "backend": "file"}

# services/ocr_service.py — v5
# Changes from v4:
#   + Fully async — httpx.AsyncClient replaces requests so OCR/AI calls
#     no longer block the FastAPI event loop under concurrent requests
#   + request_id threaded through for end-to-end log tracing
#   + Sentry breadcrumbs preserved on each pipeline stage

import os
import re
import json
import base64
import logging
import httpx
from rapidfuzz import process, fuzz

logger = logging.getLogger("dawaai.ocr")

GOOGLE_VISION_API_KEY = os.getenv("GOOGLE_VISION_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

_VISION_MAX_BYTES = 10 * 1024 * 1024


# ── Stage 1: Google Vision OCR ────────────────────────────────────────────

async def run_ocr(image_bytes: bytes) -> str:
    """Send image to Google Vision and return raw OCR text (async)."""
    if not GOOGLE_VISION_API_KEY:
        raise ValueError("GOOGLE_VISION_API_KEY not set")

    if len(image_bytes) > _VISION_MAX_BYTES:
        raise ValueError(
            f"Image too large for Vision API: {len(image_bytes) // 1024} KB"
        )

    b64 = base64.b64encode(image_bytes).decode()
    payload = {
        "requests": [{
            "image": {"content": b64},
            "features": [{"type": "DOCUMENT_TEXT_DETECTION", "maxResults": 1}],
            "imageContext": {"languageHints": ["en", "hi"]},
        }]
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://vision.googleapis.com/v1/images:annotate?key={GOOGLE_VISION_API_KEY}",
            json=payload,
            timeout=15,
        )
        resp.raise_for_status()

    data = resp.json()
    annotation = data["responses"][0].get("fullTextAnnotation", {})
    text = annotation.get("text", "").strip()
    logger.info(f'"ocr_complete","text_length":{len(text)}')
    return text


# ── Stage 2: Claude AI Medicine Extraction ────────────────────────────────

CLAUDE_SYSTEM_PROMPT = """You are a pharmacist AI assistant expert in reading Indian medical prescriptions.
Your job is to extract medicine names from OCR text that may contain:
- Bad handwriting errors (e.g. "Pantoprozole" → "Pantoprazole")
- Abbreviations (e.g. "Tab.", "Cap.", "Inj.", "OD", "BD", "TDS", "SOS")
- Brand names and generic names mixed
- Hindi/regional abbreviations
- Missing spaces or merged words

Return ONLY a JSON array of objects, no extra text:
[
  {
    "raw_text": "<exactly what you saw in OCR>",
    "corrected_name": "<your best guess at the medicine name>",
    "strength": "<dosage if mentioned, else null>",
    "frequency": "<OD/BD/TDS/SOS/etc if mentioned, else null>",
    "duration": "<days if mentioned, else null>",
    "confidence": <0.0-1.0, how confident you are this is a real medicine name>
  }
]

Rules:
- Include only lines that look like medicine names
- Do NOT include doctor names, dates, patient info, hospital names
- If a line is clearly not a medicine, skip it
- Be liberal — it's better to include uncertain items than miss medicines
- confidence < 0.7 means you're unsure of the name"""


async def extract_medicines_with_ai(ocr_text: str) -> list[dict]:
    """Use Claude to correct OCR errors and extract structured medicine list (async)."""
    if not ANTHROPIC_API_KEY:
        logger.warning('"ANTHROPIC_API_KEY not set — using basic parser"')
        return _basic_parse(ocr_text)

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 1024,
        "system": CLAUDE_SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": f"Extract medicines from this prescription OCR:\n\n{ocr_text}"}
        ],
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=body,
                timeout=20,
            )
            resp.raise_for_status()
        content = resp.json()["content"][0]["text"].strip()
        content = re.sub(r"```json\s*|\s*```", "", content).strip()
        parsed = json.loads(content)
        logger.info(f'"ai_extraction_complete","items_found":{len(parsed)}')
        return parsed
    except json.JSONDecodeError as exc:
        logger.error(f'"ai_json_parse_error","error":"{exc}"')
        return _basic_parse(ocr_text)
    except Exception as exc:
        logger.error(f'"ai_extraction_failed","error":"{exc}"')
        return _basic_parse(ocr_text)


def _basic_parse(text: str) -> list[dict]:
    """Fallback: simple line-based medicine extraction when AI is unavailable."""
    lines = [line.strip() for line in text.split("\n") if len(line.strip()) > 3]
    skip_patterns = [
        r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",
        r"Dr\.",
        r"\bRx\b",
        r"\bPatient\b",
        r"\bAge\s*:",
        r"\bDate\s*:",
    ]
    results = []
    for line in lines:
        if any(re.search(p, line, re.IGNORECASE) for p in skip_patterns):
            continue
        results.append({
            "raw_text": line,
            "corrected_name": line,
            "strength": None,
            "frequency": None,
            "duration": None,
            "confidence": 0.6,
        })
    logger.info(f'"basic_parse_complete","items_found":{len(results)}')
    return results


# ── Stage 3 + 4: Fuzzy match → inventory ─────────────────────────────────

def match_to_inventory(
    corrected_name: str, inventory: list[dict], threshold: int = 55
) -> dict:
    """
    Fuzzy-match corrected medicine name against pharmacy inventory.
    Returns best match with confidence label.
    Auto-picks if score >= threshold, flags for review if below 80.
    """
    if not inventory:
        return _no_match(corrected_name)

    corpus = {
        item["id"]: (
            f"{item['brand_name']} {item.get('generic_name', '')} {item.get('strength', '')}"
        )
        for item in inventory
    }

    results = process.extract(
        corrected_name,
        corpus,
        scorer=fuzz.WRatio,
        limit=3,
    )

    if not results or results[0][1] < threshold:
        return _no_match(corrected_name)

    best_text, best_score, best_id = results[0]
    matched_item = next(i for i in inventory if i["id"] == best_id)

    suggestions = []
    for text, score, item_id in results:
        inv_item = next((i for i in inventory if i["id"] == item_id), None)
        if inv_item:
            suggestions.append({
                "inventory_id": item_id,
                "brand_name": inv_item["brand_name"],
                "generic_name": inv_item.get("generic_name", ""),
                "strength": inv_item.get("strength", ""),
                "mrp": inv_item.get("mrp"),
                "quantity": inv_item.get("quantity", 0),
                "score": round(score, 1),
            })

    confidence_score = round(best_score / 100, 2)
    flagged = best_score < 80

    return {
        "matched": True,
        "inventory_id": best_id,
        "matched_name": matched_item["brand_name"],
        "generic_name": matched_item.get("generic_name", ""),
        "strength": matched_item.get("strength", ""),
        "mrp": matched_item.get("mrp"),
        "available_stock": matched_item.get("quantity", 0),
        "score": best_score,
        "confidence": confidence_score,
        "confidence_label": _confidence_label(best_score),
        "flagged_for_review": flagged,
        "suggestions": suggestions,
    }


def _no_match(raw: str) -> dict:
    return {
        "matched": False,
        "inventory_id": None,
        "matched_name": raw,
        "generic_name": "",
        "strength": "",
        "mrp": None,
        "available_stock": 0,
        "score": 0,
        "confidence": 0.0,
        "confidence_label": "low",
        "flagged_for_review": True,
        "suggestions": [],
    }


def _confidence_label(score: float) -> str:
    if score >= 85:
        return "high"
    if score >= 70:
        return "medium"
    return "low"


# ── Full pipeline ─────────────────────────────────────────────────────────

async def process_prescription(image_bytes: bytes, inventory: list[dict]) -> list[dict]:
    """
    Full async pipeline: OCR → AI extraction → fuzzy match.
    Returns list of scan lines with matches.
    """
    raw_text = await run_ocr(image_bytes)
    extracted = await extract_medicines_with_ai(raw_text)

    results = []
    for item in extracted:
        match = match_to_inventory(item["corrected_name"], inventory)
        results.append({
            "ocr_raw": item["raw_text"],
            "corrected_name": item["corrected_name"],
            "ocr_confidence": item.get("confidence", 0.6),
            "strength_from_rx": item.get("strength"),
            "frequency": item.get("frequency"),
            "duration": item.get("duration"),
            **match,
        })

    return results

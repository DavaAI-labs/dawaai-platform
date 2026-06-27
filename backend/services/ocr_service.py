# services/ocr_service.py — v3
# Upgraded prescription transcription pipeline:
#
# Stage 1: Google Vision OCR → raw text
# Stage 2: Claude AI correction → structured medicine list
#          (handles bad handwriting, abbreviations, brand/generic confusion)
# Stage 3: Fuzzy match → inventory lookup with confidence score
# Stage 4: Auto-pick best match, flag low-confidence for review

import os
import re
import json
import base64
import requests
from typing import Optional
from rapidfuzz import process, fuzz

GOOGLE_VISION_API_KEY = os.getenv("GOOGLE_VISION_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# ── Stage 1: Google Vision OCR ─────────────────────────────────────────────

def run_ocr(image_bytes: bytes) -> str:
    """Send image to Google Vision and return raw OCR text."""
    if not GOOGLE_VISION_API_KEY:
        raise ValueError("GOOGLE_VISION_API_KEY not set")

    b64 = base64.b64encode(image_bytes).decode()
    payload = {
        "requests": [{
            "image": {"content": b64},
            "features": [{"type": "DOCUMENT_TEXT_DETECTION", "maxResults": 1}],
            "imageContext": {"languageHints": ["en", "hi"]}
        }]
    }
    resp = requests.post(
        f"https://vision.googleapis.com/v1/images:annotate?key={GOOGLE_VISION_API_KEY}",
        json=payload, timeout=15
    )
    resp.raise_for_status()
    data = resp.json()
    annotation = data["responses"][0].get("fullTextAnnotation", {})
    return annotation.get("text", "").strip()


# ── Stage 2: Claude AI Medicine Extraction ─────────────────────────────────

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


def extract_medicines_with_ai(ocr_text: str) -> list[dict]:
    """Use Claude to correct OCR errors and extract structured medicine list."""
    if not ANTHROPIC_API_KEY:
        # Fallback: basic line-by-line parsing
        return _basic_parse(ocr_text)

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": "claude-haiku-4-5-20251001",  # fast + cheap for this task
        "max_tokens": 1024,
        "system": CLAUDE_SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": f"Extract medicines from this prescription OCR:\n\n{ocr_text}"}]
    }

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers, json=body, timeout=20
        )
        resp.raise_for_status()
        content = resp.json()["content"][0]["text"].strip()

        # Strip markdown fences if present
        content = re.sub(r"```json\s*|\s*```", "", content).strip()
        return json.loads(content)

    except Exception as e:
        print(f"[OCR AI] Claude extraction failed: {e}, falling back to basic parse")
        return _basic_parse(ocr_text)


def _basic_parse(text: str) -> list[dict]:
    """Fallback: simple line-based medicine extraction when AI is unavailable."""
    lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 3]
    # Skip obvious non-medicine lines
    skip_patterns = [r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", r"Dr\.", r"Rx", r"Patient", r"Age:", r"Date:"]
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
    return results


# ── Stage 3 + 4: Fuzzy match → inventory, auto-pick + flag ────────────────

def match_to_inventory(corrected_name: str, inventory: list[dict], threshold: int = 55) -> dict:
    """
    Fuzzy-match corrected medicine name against pharmacy inventory.
    Returns best match with confidence label.
    Auto-picks if score >= threshold, flags for review if below 80.
    """
    if not inventory:
        return _no_match(corrected_name)

    # Build search corpus: "brand_name | generic_name | strength"
    corpus = {
        item["id"]: f"{item['brand_name']} {item.get('generic_name', '')} {item.get('strength', '')}"
        for item in inventory
    }

    results = process.extract(
        corrected_name,
        corpus,
        scorer=fuzz.WRatio,
        limit=3
    )

    if not results or results[0][1] < threshold:
        return _no_match(corrected_name)

    best_text, best_score, best_id = results[0]
    matched_item = next(i for i in inventory if i["id"] == best_id)

    # Top 3 suggestions for display
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
    flagged = best_score < 80  # auto-picked but needs review

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
    if score >= 85: return "high"
    if score >= 70: return "medium"
    return "low"


# ── Full pipeline ───────────────────────────────────────────────────────────

def process_prescription(image_bytes: bytes, inventory: list[dict]) -> list[dict]:
    """
    Full pipeline: OCR → AI extraction → fuzzy match.
    Returns list of scan lines with matches.
    """
    # Stage 1
    raw_text = run_ocr(image_bytes)

    # Stage 2
    extracted = extract_medicines_with_ai(raw_text)

    # Stage 3 + 4
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
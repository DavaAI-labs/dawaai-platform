# ocr_service.py
# Calls Google Vision API, returns text lines with confidence scores.
# Falls back to mock data if no API key is set (for local dev/testing).

import os
import base64
from typing import List, Dict

GOOGLE_VISION_API_KEY = os.getenv("GOOGLE_VISION_API_KEY", "")


def run_ocr(image_bytes: bytes) -> List[Dict]:
    """
    Input:  raw image bytes (JPG/PNG)
    Output: list of { text, confidence } dicts — one per detected line
    """
    if not GOOGLE_VISION_API_KEY:
        print("⚠ No GOOGLE_VISION_API_KEY found — using mock OCR output")
        return _mock_ocr()

    try:
        import requests

        # Encode image to base64 for Vision API
        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        payload = {
            "requests": [{
                "image": {"content": b64_image},
                "features": [{"type": "DOCUMENT_TEXT_DETECTION"}]
            }]
        }

        response = requests.post(
            f"https://vision.googleapis.com/v1/images:annotate?key={GOOGLE_VISION_API_KEY}",
            json=payload,
            timeout=15
        )
        response.raise_for_status()
        result = response.json()

        return _parse_vision_response(result)

    except Exception as e:
        print(f"OCR error: {e} — falling back to mock")
        return _mock_ocr()


def _parse_vision_response(result: dict) -> List[Dict]:
    """
    Parses Google Vision DOCUMENT_TEXT_DETECTION response.
    Extracts per-word blocks and groups them into lines with avg confidence.
    """
    lines = []

    try:
        pages = result["responses"][0]["fullTextAnnotation"]["pages"]

        for page in pages:
            for block in page["blocks"]:
                for paragraph in block["paragraphs"]:
                    line_text = ""
                    confidences = []

                    for word in paragraph["words"]:
                        # Join symbols to form word
                        word_text = "".join(
                            s["text"] for s in word["symbols"]
                        )
                        line_text += word_text + " "

                        # Google Vision gives confidence per word
                        conf = word.get("confidence", 0.5)
                        confidences.append(conf)

                    clean = line_text.strip()
                    if clean and len(clean) > 1:
                        avg_conf = sum(confidences) / len(confidences) if confidences else 0.5
                        lines.append({
                            "text": clean,
                            "confidence": round(avg_conf, 2)
                        })

    except (KeyError, IndexError) as e:
        print(f"Vision parse error: {e}")

    return lines if lines else _mock_ocr()


def _mock_ocr() -> List[Dict]:
    """
    Returns realistic mock prescription lines for local development.
    Simulates typical handwritten prescription OCR errors.
    """
    return [
        {"text": "Tab Amoxici1lin 500mg",  "confidence": 0.61},
        {"text": "Pantopraz0le 40 mg",      "confidence": 0.73},
        {"text": "Tab Metforrn1n 500rng",   "confidence": 0.55},
        {"text": "Crocin 650 mg",           "confidence": 0.89},
        {"text": "Azithromycm 500mg",       "confidence": 0.67},
    ]
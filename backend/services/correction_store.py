# correction_store.py
# Every time a pharmacist edits an OCR suggestion, we save it here.
# Format: one JSON object per line (JSONL) — easy to read, easy to train on.
# This file IS the flywheel. After 5,000 lines, you have a fine-tuning dataset.

import json
from datetime import datetime
from pathlib import Path
from typing import List

CORRECTIONS_FILE = Path(__file__).parent.parent.parent / "data" / "corrections" / "corrections.jsonl"


def save_corrections(scan_id: str, edited_medicines: List) -> int:
    """
    Saves pharmacist-corrected medicine lines as training pairs.

    Each line written to corrections.jsonl looks like:
    {
        "scan_id": "a3f9bc",
        "ocr_raw": "Tab Amoxici1lin 500mg",
        "corrected_to": "Amoxicillin 500mg",
        "brand_name": "Novamox",
        "timestamp": "2024-01-15T10:32:11"
    }

    Input:  scan_id + list of MedicineLine objects where was_edited=True
    Output: number of pairs saved
    """
    CORRECTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)

    saved = 0
    with open(CORRECTIONS_FILE, "a", encoding="utf-8") as f:
        for med in edited_medicines:
            # Only log lines where pharmacist actually changed something
            if not med.was_edited:
                continue

            pair = {
                "scan_id":      scan_id,
                "ocr_raw":      med.ocr_raw,
                "corrected_to": med.matched_name,
                "brand_name":   med.brand_name or "",
                "generic_name": med.generic_name or "",
                "strength":     med.strength or "",
                "timestamp":    datetime.utcnow().isoformat()
            }
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")
            saved += 1

    if saved:
        print(f"✓ Flywheel: {saved} correction(s) saved for scan {scan_id}")

    return saved


def get_correction_count() -> int:
    """Returns total number of correction pairs collected so far."""
    if not CORRECTIONS_FILE.exists():
        return 0
    with open(CORRECTIONS_FILE, "r", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())
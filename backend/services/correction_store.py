# services/correction_store.py — v4
# Changes from v3:
#   + save_correction_record() accepts a plain dict (used as fallback from routes.py)
#   + save_corrections() retained for backward compat with any callers passing ORM objects
#   + Structured logging replacing print()

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List

logger = logging.getLogger("dawaai.correction_store")

CORRECTIONS_FILE = (
    Path(__file__).parent.parent.parent / "data" / "corrections" / "corrections.jsonl"
)


def save_correction_record(record: dict, pharmacy_id: str = "") -> None:
    """
    Save a single correction record dict to a per-pharmacy JSONL file.
    Used as fallback when Supabase is not configured.

    Each pharmacy writes to its own file (corrections_{pharmacy_id}.jsonl)
    to prevent cross-tenant data leakage in dev/fallback mode.
    """
    import re
    safe_pid = re.sub(r"[^a-zA-Z0-9_-]", "_", pharmacy_id) if pharmacy_id else "shared"
    target = CORRECTIONS_FILE.parent / f"corrections_{safe_pid}.jsonl"
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    logger.info(f'"correction_file_saved","scan_id":"{record.get("scan_id")}","pharmacy_id":"{safe_pid}"')


def save_corrections(scan_id: str, edited_medicines: List) -> int:
    """
    Saves pharmacist-corrected medicine lines as training pairs.
    Accepts a list of objects with .was_edited, .ocr_raw, etc. attributes.
    Returns number of pairs saved.
    """
    CORRECTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)

    saved = 0
    with open(CORRECTIONS_FILE, "a", encoding="utf-8") as f:
        for med in edited_medicines:
            if not med.was_edited:
                continue
            pair = {
                "scan_id": scan_id,
                "ocr_raw": med.ocr_raw,
                "corrected_to": med.matched_name,
                "brand_name": med.brand_name or "",
                "generic_name": med.generic_name or "",
                "strength": med.strength or "",
                "timestamp": datetime.utcnow().isoformat(),
            }
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")
            saved += 1

    if saved:
        logger.info(f'"flywheel_saved","count":{saved},"scan_id":"{scan_id}"')

    return saved


def get_correction_count() -> int:
    """Returns total number of correction pairs collected so far."""
    if not CORRECTIONS_FILE.exists():
        return 0
    with open(CORRECTIONS_FILE, "r", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())

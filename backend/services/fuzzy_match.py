# services/fuzzy_match.py — v4
# Changes from v3:
#   + Structured logging replacing print()
#   + Graceful handling if medicines.csv is missing (warns instead of crashing)

import csv
import logging
import re
from pathlib import Path
from typing import List, Dict

from rapidfuzz import fuzz, process

logger = logging.getLogger("dawaai.fuzzy_match")

DB_PATH = Path(__file__).parent.parent.parent / "data" / "medicine_db" / "medicines.csv"

_medicine_db: List[Dict] = []
_search_index: List[str] = []
_index_to_medicine: List[int] = []


def _load_db():
    global _medicine_db, _search_index
    if _medicine_db:
        return

    if not DB_PATH.exists():
        logger.warning(f'"medicines_csv_missing","path":"{DB_PATH}"')
        return

    with open(DB_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            _medicine_db.append(row)
            _search_index.append(f"{row['brand_name']} {row['strength']}")
            _index_to_medicine.append(i)
            _search_index.append(f"{row['generic_name']} {row['strength']}")
            _index_to_medicine.append(i)

    if not _medicine_db:
        logger.warning('"medicines_csv_empty — fuzzy matching will return no results"')
    else:
        logger.info(f'"medicine_db_loaded","count":{len(_medicine_db)}')


_load_db()


def _clean_text(text: str) -> str:
    """Pre-process OCR text before matching."""
    text = text.lower().strip()
    text = re.sub(r"\b0\b", "o", text)
    text = re.sub(r"(?<=[a-zA-Z])1|1(?=[a-zA-Z])", "l", text)
    text = text.replace("rn", "m")
    text = re.sub(r"tab\.?\s*", "", text)
    text = re.sub(r"cap\.?\s*", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def match_medicines(ocr_text: str, top_n: int = 3) -> List[Dict]:
    """
    Input:  raw OCR text for one prescription line
    Output: top N medicine matches with confidence scores
    """
    cleaned = _clean_text(ocr_text)

    if not cleaned or len(cleaned) < 2:
        return []

    results = process.extract(
        cleaned,
        _search_index,
        scorer=fuzz.token_sort_ratio,
        limit=top_n * 2,
    )

    seen_brands: set = set()
    matches = []

    for match_str, score, idx in results:
        medicine_idx = _index_to_medicine[idx]
        if medicine_idx >= len(_medicine_db):
            continue

        med = _medicine_db[medicine_idx]
        brand = med["brand_name"]

        if brand in seen_brands:
            continue
        seen_brands.add(brand)

        if score >= 80:
            label = "high"
        elif score >= 55:
            label = "medium"
        else:
            label = "low"

        matches.append({
            "matched_name": f"{brand} {med['strength']}",
            "brand_name": brand,
            "generic_name": med["generic_name"],
            "strength": med["strength"],
            "manufacturer": med["manufacturer"],
            "form": med["form"],
            "score": score,
            "confidence_label": label,
        })

        if len(matches) >= top_n:
            break

    return matches

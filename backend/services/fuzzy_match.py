# fuzzy_match.py
# Matches dirty OCR text against the medicine database.
# Uses rapidfuzz for Levenshtein + token sort ratio.
# Returns top 3 ranked matches with confidence scores.

import csv
import re
from pathlib import Path
from typing import List, Dict
from rapidfuzz import fuzz, process

# ── Load medicine DB once at startup ──────────────────────────────────────

DB_PATH = Path(__file__).parent.parent.parent / "data" / "medicine_db" / "medicines.csv"

_medicine_db: List[Dict] = []
_search_index: List[str] = []   # flat list of searchable strings


def _load_db():
    global _medicine_db, _search_index
    if _medicine_db:
        return  # already loaded

    with open(DB_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            _medicine_db.append(row)
            # Index both brand and generic name for matching
            _search_index.append(f"{row['brand_name']} {row['strength']}")
            _search_index.append(f"{row['generic_name']} {row['strength']}")


_load_db()


# ── Matching logic ─────────────────────────────────────────────────────────

def _clean_text(text: str) -> str:
    """
    Pre-process OCR text before matching.
    Fixes common OCR errors in medicine names.
    e.g. '0' → 'o', '1' → 'l', 'rn' → 'm'
    """
    text = text.lower().strip()
    # Common OCR character confusions in drug names
    text = re.sub(r'\b0\b', 'o', text)   # standalone zero → o
    text = text.replace('1', 'l')         # 1 → l  (Amoxici1lin)
    text = text.replace('rn', 'm')        # rn → m  (Metforrn1n)
    text = re.sub(r'tab\.?\s*', '', text) # remove "Tab" prefix
    text = re.sub(r'cap\.?\s*', '', text) # remove "Cap" prefix
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def match_medicines(ocr_text: str, top_n: int = 3) -> List[Dict]:
    """
    Input:  raw OCR text for one prescription line
    Output: top N medicine matches, each with:
            - matched_name
            - brand_name, generic_name, strength, manufacturer
            - score (0–100)
            - confidence_label: 'high' | 'medium' | 'low'
    """
    cleaned = _clean_text(ocr_text)

    if not cleaned or len(cleaned) < 2:
        return []

    # rapidfuzz: token_sort_ratio handles word-order differences
    # e.g. "500mg Amoxicillin" still matches "Amoxicillin 500mg"
    results = process.extract(
        cleaned,
        _search_index,
        scorer=fuzz.token_sort_ratio,
        limit=top_n * 2   # fetch extra, deduplicate below
    )

    seen_brands = set()
    matches = []

    for match_str, score, idx in results:
        # Map index back to medicine row
        # Each medicine has 2 index entries (brand + generic)
        medicine_idx = idx // 2
        if medicine_idx >= len(_medicine_db):
            continue

        med = _medicine_db[medicine_idx]
        brand = med["brand_name"]

        # Deduplicate — don't return same brand twice
        if brand in seen_brands:
            continue
        seen_brands.add(brand)

        # Confidence label for UI badge
        if score >= 80:
            label = "high"
        elif score >= 55:
            label = "medium"
        else:
            label = "low"

        matches.append({
            "matched_name": f"{brand} {med['strength']}",
            "brand_name":   brand,
            "generic_name": med["generic_name"],
            "strength":     med["strength"],
            "manufacturer": med["manufacturer"],
            "form":         med["form"],
            "score":        score,
            "confidence_label": label
        })

        if len(matches) >= top_n:
            break

    return matches
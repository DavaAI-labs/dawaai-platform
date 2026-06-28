#!/usr/bin/env python3
"""
scripts/seed_medicine_db.py — DavaAI v5
========================================
Seeds data/medicine_db/medicines.csv from two free public sources:

  1. OpenFDA Drug Labels API  (https://api.fda.gov/drug/label.json)
     — covers international brands; good for generic + strength data

  2. Jan Aushadhi CSV         (https://janaushadhi.gov.in)
     — India-specific generic drug names and prices (manual download)
     — place file at: data/medicine_db/jan_aushadhi_raw.csv

Usage:
  # Full seed (OpenFDA only, no Jan Aushadhi file needed):
  python scripts/seed_medicine_db.py

  # With Jan Aushadhi file:
  python scripts/seed_medicine_db.py --jan-aushadhi data/medicine_db/jan_aushadhi_raw.csv

  # Limit OpenFDA fetch (default: 1000 drugs):
  python scripts/seed_medicine_db.py --limit 5000

The output file (data/medicine_db/medicines.csv) is what fuzzy_match.py loads.
Run this script once at setup and periodically to refresh the drug database.
"""

import argparse
import csv
import json
import re
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("pip install requests  — then re-run this script")
    sys.exit(1)

OUTPUT_PATH = Path(__file__).parent.parent / "data" / "medicine_db" / "medicines.csv"
FIELDNAMES = ["brand_name", "generic_name", "strength", "manufacturer", "form", "barcode"]

OPENFDA_URL = "https://api.fda.gov/drug/label.json"


# ── OpenFDA fetch ─────────────────────────────────────────────────────────

def _clean(text: str | list | None) -> str:
    """Flatten lists and strip whitespace from FDA API strings."""
    if isinstance(text, list):
        text = text[0] if text else ""
    return re.sub(r"\s+", " ", (text or "")).strip()


def fetch_openfda(limit: int) -> list[dict]:
    """
    Fetch drug label records from OpenFDA.
    Returns a list of normalised dicts ready for CSV output.
    """
    results = []
    skip = 0
    page_size = 100  # OpenFDA max per request
    seen_brands: set[str] = set()

    print(f"Fetching up to {limit} drugs from OpenFDA …")

    while len(results) < limit:
        try:
            resp = requests.get(
                OPENFDA_URL,
                params={
                    "search": "openfda.product_type:HUMAN+PRESCRIPTION+DRUG",
                    "limit": page_size,
                    "skip": skip,
                },
                timeout=15,
            )
            if resp.status_code == 404:
                break  # no more results
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            print(f"  OpenFDA error at skip={skip}: {exc}")
            break

        for entry in data.get("results", []):
            openfda = entry.get("openfda", {})
            brand = _clean(openfda.get("brand_name"))
            generic = _clean(openfda.get("generic_name"))
            manufacturer = _clean(openfda.get("manufacturer_name"))
            dosage_form = _clean(openfda.get("dosage_form"))
            strength_raw = _clean(openfda.get("strength") or entry.get("dosage_and_administration"))
            # Extract first dosage figure (e.g. "500 mg" from longer text)
            strength_match = re.search(r"\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|%|IU)", strength_raw, re.I)
            strength = strength_match.group() if strength_match else ""

            if not brand or not generic:
                continue
            dedup_key = f"{brand.lower()}|{strength.lower()}"
            if dedup_key in seen_brands:
                continue
            seen_brands.add(dedup_key)

            results.append({
                "brand_name": brand,
                "generic_name": generic,
                "strength": strength,
                "manufacturer": manufacturer,
                "form": dosage_form,
                "barcode": "",  # OpenFDA doesn't provide barcodes
            })

        skip += page_size
        total_available = data.get("meta", {}).get("results", {}).get("total", 0)
        print(f"  fetched {len(results)} / {min(limit, total_available)} …", end="\r")

        if skip >= total_available:
            break

        time.sleep(0.25)  # OpenFDA rate limit: 240 req/min without key

    print(f"\nOpenFDA: {len(results)} drugs fetched.")
    return results


# ── Jan Aushadhi CSV ──────────────────────────────────────────────────────

def load_jan_aushadhi(filepath: str) -> list[dict]:
    """
    Load Jan Aushadhi generic drug list.

    The Jan Aushadhi CSV can be downloaded from:
      https://janaushadhi.gov.in/ProductList.aspx

    Expected columns (flexible — we match by name):
      generic_name / Generic Name / medicine_name
      strength     / Strength / dose
      manufacturer / Manufacturer
      form         / Form / dosage_form

    Returns normalised dicts in the same shape as fetch_openfda().
    """
    results = []
    path = Path(filepath)
    if not path.exists():
        print(f"Jan Aushadhi file not found: {filepath} — skipping")
        return []

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        # Normalise header names to lower-snake-case
        fields = {k.lower().replace(" ", "_"): k for k in (reader.fieldnames or [])}

        def get(row, *candidates):
            for c in candidates:
                val = row.get(fields.get(c, ""), "")
                if val:
                    return val.strip()
            return ""

        for row in reader:
            generic = get(row, "generic_name", "medicine_name", "product_name")
            strength = get(row, "strength", "dose", "dosage")
            form = get(row, "form", "dosage_form", "product_form")
            manufacturer = get(row, "manufacturer", "company")

            if not generic:
                continue

            results.append({
                "brand_name": generic,       # Jan Aushadhi = generics only; brand = generic
                "generic_name": generic,
                "strength": strength,
                "manufacturer": manufacturer or "Jan Aushadhi",
                "form": form,
                "barcode": "",
            })

    print(f"Jan Aushadhi: {len(results)} drugs loaded from {filepath}")
    return results


# ── Write CSV ─────────────────────────────────────────────────────────────

def write_csv(rows: list[dict], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWrote {len(rows)} medicines → {output}")


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Seed DavaAI medicine database")
    parser.add_argument("--limit", type=int, default=1000,
                        help="Max drugs to fetch from OpenFDA (default: 1000)")
    parser.add_argument("--jan-aushadhi", metavar="FILE",
                        help="Path to Jan Aushadhi CSV file")
    parser.add_argument("--output", default=str(OUTPUT_PATH),
                        help=f"Output CSV path (default: {OUTPUT_PATH})")
    args = parser.parse_args()

    all_rows: list[dict] = []

    # Source 1: OpenFDA
    all_rows.extend(fetch_openfda(args.limit))

    # Source 2: Jan Aushadhi
    if args.jan_aushadhi:
        all_rows.extend(load_jan_aushadhi(args.jan_aushadhi))

    if not all_rows:
        print("No drugs fetched — check your network connection or API limits.")
        sys.exit(1)

    # Deduplicate on brand + strength
    seen: set[str] = set()
    deduped = []
    for row in all_rows:
        key = f"{row['brand_name'].lower()}|{row['strength'].lower()}"
        if key not in seen:
            seen.add(key)
            deduped.append(row)

    print(f"Total after dedup: {len(deduped)} unique medicines")
    write_csv(deduped, Path(args.output))


if __name__ == "__main__":
    main()

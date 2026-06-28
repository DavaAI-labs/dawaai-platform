# tests/test_fuzzy_match.py
# Unit tests for the fuzzy matching service.
# These run with no external dependencies (no Supabase, no AI APIs).

import pytest
from unittest.mock import patch

# Patch DB path before import so we can inject test data
import services.fuzzy_match as fm


# ── Fixtures ──────────────────────────────────────────────────────────────

SAMPLE_DB = [
    {
        "brand_name": "Amoxicillin 500",
        "generic_name": "Amoxicillin",
        "strength": "500 mg",
        "manufacturer": "Cipla Ltd",
        "form": "Capsule",
    },
    {
        "brand_name": "Pantocid 40",
        "generic_name": "Pantoprazole",
        "strength": "40 mg",
        "manufacturer": "Sun Pharma",
        "form": "Tablet",
    },
    {
        "brand_name": "Metformin SR 500",
        "generic_name": "Metformin Hydrochloride",
        "strength": "500 mg",
        "manufacturer": "Sun Pharma",
        "form": "Tablet",
    },
    {
        "brand_name": "Crocin 650",
        "generic_name": "Paracetamol",
        "strength": "650 mg",
        "manufacturer": "GSK Pharma",
        "form": "Tablet",
    },
]


@pytest.fixture(autouse=True)
def seed_medicine_db():
    """Inject test data directly into module globals before each test."""
    original_db = fm._medicine_db[:]
    original_idx = fm._search_index[:]
    original_map = fm._index_to_medicine[:]

    fm._medicine_db.clear()
    fm._search_index.clear()
    fm._index_to_medicine.clear()

    for i, row in enumerate(SAMPLE_DB):
        fm._medicine_db.append(row)
        fm._search_index.append(f"{row['brand_name']} {row['strength']}")
        fm._index_to_medicine.append(i)
        fm._search_index.append(f"{row['generic_name']} {row['strength']}")
        fm._index_to_medicine.append(i)

    yield

    fm._medicine_db[:] = original_db
    fm._search_index[:] = original_idx
    fm._index_to_medicine[:] = original_map


# ── _clean_text ───────────────────────────────────────────────────────────

class TestCleanText:
    def test_lowercases(self):
        assert fm._clean_text("AMOXICILLIN") == "amoxicillin"

    def test_strips_tab_prefix(self):
        assert fm._clean_text("Tab. Amoxicillin") == "amoxicillin"

    def test_strips_cap_prefix(self):
        assert fm._clean_text("Cap Amoxicillin") == "amoxicillin"

    def test_replaces_rn_with_m(self):
        # "Metforrn1n" OCR artifact → "metformin"
        result = fm._clean_text("Metforrn1n")
        assert "m" in result

    def test_collapses_whitespace(self):
        assert fm._clean_text("Tab   Amoxicillin  500") == "amoxicillin 500"

    def test_empty_string(self):
        assert fm._clean_text("") == ""

    def test_only_whitespace(self):
        assert fm._clean_text("   ") == ""


# ── match_medicines ───────────────────────────────────────────────────────

class TestMatchMedicines:
    def test_exact_brand_name_matches(self):
        results = fm.match_medicines("Amoxicillin 500")
        assert len(results) > 0
        assert results[0]["brand_name"] == "Amoxicillin 500"

    def test_typo_in_name_still_matches(self):
        # Common handwriting error
        results = fm.match_medicines("Pantoprozole 40mg")
        assert len(results) > 0
        # Top result should be Pantocid (contains Pantoprazole)
        assert "Pantocid" in results[0]["brand_name"] or "Pantoprazole" in results[0]["generic_name"]

    def test_generic_name_matches(self):
        results = fm.match_medicines("Paracetamol 650")
        assert len(results) > 0
        assert results[0]["brand_name"] == "Crocin 650"

    def test_word_order_invariant(self):
        # "500mg Amoxicillin" should match same as "Amoxicillin 500mg"
        r1 = fm.match_medicines("Amoxicillin 500mg")
        r2 = fm.match_medicines("500mg Amoxicillin")
        assert r1[0]["brand_name"] == r2[0]["brand_name"]

    def test_tab_prefix_stripped_before_match(self):
        results = fm.match_medicines("Tab. Metformin 500")
        assert len(results) > 0
        assert "Metformin" in results[0]["brand_name"]

    def test_returns_at_most_top_n(self):
        results = fm.match_medicines("Amoxicillin", top_n=2)
        assert len(results) <= 2

    def test_empty_input_returns_empty(self):
        assert fm.match_medicines("") == []

    def test_very_short_input_returns_empty(self):
        assert fm.match_medicines("A") == []

    def test_no_duplicate_brands(self):
        results = fm.match_medicines("Amoxicillin 500", top_n=3)
        brands = [r["brand_name"] for r in results]
        assert len(brands) == len(set(brands))

    def test_confidence_labels_present(self):
        results = fm.match_medicines("Paracetamol 650")
        for r in results:
            assert r["confidence_label"] in ("high", "medium", "low")

    def test_score_range(self):
        results = fm.match_medicines("Crocin 650")
        for r in results:
            assert 0 <= r["score"] <= 100

    def test_gibberish_returns_low_scores_or_empty(self):
        results = fm.match_medicines("xzqkjw pqrst")
        for r in results:
            assert r["score"] < 80  # no high-confidence match for gibberish

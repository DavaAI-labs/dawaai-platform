# tests/test_ocr_service.py
# Unit tests for the OCR pipeline.
# All external calls (Google Vision, Claude) are mocked — no API keys needed.
# v5: tests are async to match the async pipeline.

import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import httpx

import services.ocr_service as ocr


# ── Helpers ───────────────────────────────────────────────────────────────

def _mock_httpx_response(payload: dict, status_code: int = 200) -> MagicMock:
    """Create a mock httpx response."""
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = status_code
    mock.json.return_value = payload
    mock.raise_for_status = MagicMock()
    return mock


def _vision_payload(text: str) -> dict:
    return {"responses": [{"fullTextAnnotation": {"text": text}}]}


def _claude_payload(medicines: list) -> dict:
    return {"content": [{"text": json.dumps(medicines)}]}


SAMPLE_INVENTORY = [
    {"id": "inv-1", "brand_name": "Amoxicillin 500", "generic_name": "Amoxicillin", "strength": "500 mg", "mrp": 72.0, "quantity": 100},
    {"id": "inv-2", "brand_name": "Pantocid 40", "generic_name": "Pantoprazole", "strength": "40 mg", "mrp": 85.5, "quantity": 60},
    {"id": "inv-3", "brand_name": "Crocin 650", "generic_name": "Paracetamol", "strength": "650 mg", "mrp": 34.5, "quantity": 0},
]


# ── run_ocr ───────────────────────────────────────────────────────────────

class TestRunOcr:
    @pytest.mark.anyio
    async def test_returns_text_on_success(self):
        mock_resp = _mock_httpx_response(_vision_payload("Amoxicillin 500mg OD"))
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
        with patch("services.ocr_service.httpx.AsyncClient", return_value=mock_client):
            ocr.GOOGLE_VISION_API_KEY = "fake-key"
            result = await ocr.run_ocr(b"fake-image-bytes")
        assert result == "Amoxicillin 500mg OD"
        ocr.GOOGLE_VISION_API_KEY = ""

    @pytest.mark.anyio
    async def test_raises_when_key_missing(self):
        ocr.GOOGLE_VISION_API_KEY = ""
        with pytest.raises(ValueError, match="GOOGLE_VISION_API_KEY"):
            await ocr.run_ocr(b"fake-image-bytes")

    @pytest.mark.anyio
    async def test_raises_when_image_too_large(self):
        ocr.GOOGLE_VISION_API_KEY = "fake-key"
        big_image = b"x" * (11 * 1024 * 1024)
        with pytest.raises(ValueError, match="too large"):
            await ocr.run_ocr(big_image)
        ocr.GOOGLE_VISION_API_KEY = ""

    @pytest.mark.anyio
    async def test_empty_response_returns_empty_string(self):
        mock_resp = _mock_httpx_response({"responses": [{}]})
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
        with patch("services.ocr_service.httpx.AsyncClient", return_value=mock_client):
            ocr.GOOGLE_VISION_API_KEY = "fake-key"
            result = await ocr.run_ocr(b"blank-image")
        assert result == ""
        ocr.GOOGLE_VISION_API_KEY = ""


# ── extract_medicines_with_ai ─────────────────────────────────────────────

class TestExtractMedicinesWithAi:
    def setup_method(self):
        ocr.ANTHROPIC_API_KEY = "fake-anthropic-key"

    def teardown_method(self):
        ocr.ANTHROPIC_API_KEY = ""

    @pytest.mark.anyio
    async def test_parses_valid_claude_response(self):
        medicines = [
            {"raw_text": "Amoxicillin 500", "corrected_name": "Amoxicillin", "strength": "500 mg", "frequency": "BD", "duration": "5 days", "confidence": 0.95},
        ]
        mock_resp = _mock_httpx_response(_claude_payload(medicines))
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
        with patch("services.ocr_service.httpx.AsyncClient", return_value=mock_client):
            result = await ocr.extract_medicines_with_ai("Amoxicillin 500 BD 5 days")
        assert len(result) == 1
        assert result[0]["corrected_name"] == "Amoxicillin"
        assert result[0]["frequency"] == "BD"

    @pytest.mark.anyio
    async def test_falls_back_on_json_error(self):
        mock_resp = _mock_httpx_response({"content": [{"text": "not-valid-json!!!"}]})
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
        with patch("services.ocr_service.httpx.AsyncClient", return_value=mock_client):
            result = await ocr.extract_medicines_with_ai("Amoxicillin 500")
        assert isinstance(result, list)

    @pytest.mark.anyio
    async def test_falls_back_when_api_key_missing(self):
        ocr.ANTHROPIC_API_KEY = ""
        result = await ocr.extract_medicines_with_ai("Amoxicillin 500\nPantoprazole 40")
        assert isinstance(result, list)

    @pytest.mark.anyio
    async def test_strips_markdown_fences(self):
        medicines = [{"raw_text": "test", "corrected_name": "Paracetamol", "strength": None, "frequency": None, "duration": None, "confidence": 0.9}]
        fenced = f"```json\n{json.dumps(medicines)}\n```"
        mock_resp = _mock_httpx_response({"content": [{"text": fenced}]})
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
        with patch("services.ocr_service.httpx.AsyncClient", return_value=mock_client):
            result = await ocr.extract_medicines_with_ai("test")
        assert result[0]["corrected_name"] == "Paracetamol"


# ── _basic_parse ──────────────────────────────────────────────────────────

class TestBasicParse:
    def test_skips_date_lines(self):
        text = "Amoxicillin 500\n12/06/2024\nPantoprazole 40"
        result = ocr._basic_parse(text)
        names = [r["raw_text"] for r in result]
        assert not any("2024" in n for n in names)

    def test_skips_doctor_lines(self):
        text = "Dr. Sharma\nAmoxicillin 500"
        result = ocr._basic_parse(text)
        assert all("Dr." not in r["raw_text"] for r in result)

    def test_skips_rx_line(self):
        text = "Rx\nAmoxicillin 500"
        result = ocr._basic_parse(text)
        assert all(r["raw_text"] != "Rx" for r in result)

    def test_includes_medicine_lines(self):
        text = "Amoxicillin 500\nPantoprazole 40"
        result = ocr._basic_parse(text)
        assert len(result) == 2

    def test_default_confidence_is_0_6(self):
        result = ocr._basic_parse("Amoxicillin 500")
        assert result[0]["confidence"] == 0.6


# ── match_to_inventory ────────────────────────────────────────────────────

class TestMatchToInventory:
    def test_high_confidence_match_not_flagged(self):
        result = ocr.match_to_inventory("Amoxicillin 500 mg", SAMPLE_INVENTORY)
        assert result["matched"] is True
        if result["score"] >= 80:
            assert result["flagged_for_review"] is False

    def test_no_match_below_threshold(self):
        result = ocr.match_to_inventory("xzqkjwpqrst", SAMPLE_INVENTORY, threshold=55)
        assert result["matched"] is False
        assert result["confidence"] == 0.0

    def test_empty_inventory_returns_no_match(self):
        result = ocr.match_to_inventory("Amoxicillin 500", [])
        assert result["matched"] is False

    def test_suggestions_returned(self):
        result = ocr.match_to_inventory("Pantoprazole 40", SAMPLE_INVENTORY)
        if result["matched"]:
            assert isinstance(result["suggestions"], list)
            assert len(result["suggestions"]) >= 1

    def test_score_in_range(self):
        result = ocr.match_to_inventory("Crocin 650", SAMPLE_INVENTORY)
        assert 0 <= result["score"] <= 100

    def test_available_stock_returned(self):
        result = ocr.match_to_inventory("Crocin 650 mg", SAMPLE_INVENTORY)
        if result["matched"] and result["matched_name"] == "Crocin 650":
            assert result["available_stock"] == 0


# ── process_prescription (integration) ───────────────────────────────────

class TestProcessPrescription:
    @pytest.mark.anyio
    async def test_full_pipeline_happy_path(self):
        ocr.GOOGLE_VISION_API_KEY = "fake-key"
        ocr.ANTHROPIC_API_KEY = "fake-anthropic-key"

        medicines = [
            {"raw_text": "Amox 500", "corrected_name": "Amoxicillin", "strength": "500 mg",
             "frequency": "BD", "duration": "5 days", "confidence": 0.9},
        ]

        vision_resp = _mock_httpx_response(_vision_payload("Amox 500 BD 5 days"))
        claude_resp = _mock_httpx_response(_claude_payload(medicines))

        call_count = 0

        async def fake_post(url, **kwargs):
            nonlocal call_count
            call_count += 1
            return vision_resp if call_count == 1 else claude_resp

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.post = fake_post

        with patch("services.ocr_service.httpx.AsyncClient", return_value=mock_client):
            results = await ocr.process_prescription(b"fake-image", SAMPLE_INVENTORY)

        assert len(results) == 1
        result = results[0]
        assert result["ocr_raw"] == "Amox 500"
        assert result["corrected_name"] == "Amoxicillin"
        assert result["frequency"] == "BD"
        assert "matched" in result
        assert "confidence" in result

        ocr.GOOGLE_VISION_API_KEY = ""
        ocr.ANTHROPIC_API_KEY = ""


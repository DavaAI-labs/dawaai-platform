# tests/test_routes.py
# Integration tests for the FastAPI routes.
# Uses httpx.AsyncClient + pytest-anyio to test the full request/response cycle
# without hitting real external APIs.

import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport

from main import app
from middleware.auth import require_pharmacy


# ── Auth override ─────────────────────────────────────────────────────────
# Override the JWT dependency so tests don't need a real Supabase JWT.
# All tests run as pharmacy "test-pharmacy-123" by default.

TEST_PHARMACY_ID = "test-pharmacy-123"

app.dependency_overrides[require_pharmacy] = lambda: TEST_PHARMACY_ID


# ── Fixtures ──────────────────────────────────────────────────────────────

FAKE_SCAN_RESULT = [
    {
        "ocr_raw": "Amoxicillin 500",
        "corrected_name": "Amoxicillin",
        "ocr_confidence": 0.95,
        "strength_from_rx": "500 mg",
        "frequency": "BD",
        "duration": "5 days",
        "matched": True,
        "inventory_id": "inv-1",
        "matched_name": "Amoxicillin 500",
        "generic_name": "Amoxicillin",
        "strength": "500 mg",
        "mrp": 72.0,
        "available_stock": 100,
        "score": 92.0,
        "confidence": 0.92,
        "confidence_label": "high",
        "flagged_for_review": False,
        "suggestions": [],
    }
]


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


# ── /health ───────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_health_returns_ok(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "rate_limiting" in body


# ── /api/scan ─────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_scan_returns_structured_result(client):
    with patch("api.routes.get_pharmacy_inventory", new_callable=AsyncMock, return_value=[]):
        with patch("api.routes.process_prescription", new_callable=AsyncMock, return_value=FAKE_SCAN_RESULT):
            resp = await client.post(
                "/api/scan",
                files={"file": ("rx.jpg", b"fake-jpeg-bytes", "image/jpeg")},
            )
    assert resp.status_code == 200
    body = resp.json()
    assert "scan_id" in body
    assert "lines" in body
    assert body["total_detected"] == 1
    assert body["flagged_count"] == 0


@pytest.mark.anyio
async def test_scan_rejects_non_image(client):
    resp = await client.post(
        "/api/scan",
        files={"file": ("doc.pdf", b"fake-pdf-bytes", "application/pdf")},
    )
    assert resp.status_code == 415


@pytest.mark.anyio
async def test_scan_rejects_oversized_file(client):
    big = b"x" * (11 * 1024 * 1024)  # 11 MB
    resp = await client.post(
        "/api/scan",
        files={"file": ("big.jpg", big, "image/jpeg")},
    )
    assert resp.status_code == 413


@pytest.mark.anyio
async def test_scan_works_without_pharmacy_id(client):
    with patch("api.routes.process_prescription", new_callable=AsyncMock, return_value=[]):
        resp = await client.post(
            "/api/scan",
            files={"file": ("rx.jpg", b"fake-jpeg-bytes", "image/jpeg")},
        )
    assert resp.status_code == 200
    assert resp.json()["total_detected"] == 0


# ── /api/corrections ──────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_corrections_returns_ok(client):
    with patch("api.routes.SUPABASE_URL", ""), patch("api.routes.SUPABASE_SERVICE_KEY", ""):
        with patch("services.correction_store.save_correction_record"):
            resp = await client.post(
                "/api/corrections",
                json={
                    "scan_id": "ABC123",
                    "ocr_raw": "Amox 500",
                    "corrected_to": "Amoxicillin 500",
                    "brand_name": "Amoxicillin 500",
                    "generic_name": "Amoxicillin",
                    "strength": "500 mg",
                },
            )
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.anyio
async def test_corrections_missing_required_fields(client):
    resp = await client.post("/api/corrections", json={"scan_id": "ABC"})
    assert resp.status_code == 422  # Pydantic validation error


# ── /api/barcode/{barcode} ────────────────────────────────────────────────

@pytest.mark.anyio
async def test_barcode_invalid_format_returns_422(client):
    resp = await client.get("/api/barcode/NOT-A-BARCODE")
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_barcode_not_found_returns_404(client):
    with patch("api.barcode_routes.SUPABASE_URL", ""):
        resp = await client.get("/api/barcode/9999999999999")
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_barcode_demo_data_returned(client):
    with patch("api.barcode_routes.SUPABASE_URL", ""):
        resp = await client.get("/api/barcode/8901030589396")
    assert resp.status_code == 200
    body = resp.json()
    assert body["brand_name"] == "Crocin 650"
    assert body["generic_name"] == "Paracetamol"


# ── /api/medicines/search ─────────────────────────────────────────────────

@pytest.mark.anyio
async def test_search_too_short_returns_422(client):
    resp = await client.get("/api/medicines/search?q=a")
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_search_returns_results_from_demo(client):
    with patch("api.barcode_routes.SUPABASE_URL", ""):
        resp = await client.get("/api/medicines/search?q=Crocin")
    assert resp.status_code == 200
    results = resp.json()
    assert any("Crocin" in r["brand_name"] for r in results)


# ── /api/barcode/bill ─────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_bill_empty_cart_returns_422(client):
    resp = await client.post(
        "/api/barcode/bill",
        json={"pharmacy_name": "Test Pharmacy", "cart": []},
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_bill_negative_quantity_returns_422(client):
    resp = await client.post(
        "/api/barcode/bill",
        json={
            "cart": [{
                "barcode": "8901030589396",
                "brand_name": "Crocin 650",
                "generic_name": "Paracetamol",
                "strength": "650 mg",
                "quantity": -1,
                "mrp": 34.5,
            }]
        },
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_bill_created_locally_when_no_supabase(client):
    with patch("api.barcode_routes.SUPABASE_URL", ""), \
         patch("api.barcode_routes.STORE_PATH") as mock_path:
        mock_path.exists.return_value = False
        mock_path.parent.mkdir = MagicMock()
        mock_path.write_text = MagicMock()
        resp = await client.post(
            "/api/barcode/bill",
            json={
                "pharmacy_name": "Test Pharmacy",
                "cart": [{
                    "barcode": "8901030589396",
                    "brand_name": "Crocin 650",
                    "generic_name": "Paracetamol",
                    "strength": "650 mg",
                    "quantity": 2,
                    "mrp": 34.5,
                }],
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    assert "bill_id" in body
    assert body["bill_id"].startswith("BC-")
    assert body["total_mrp"] == pytest.approx(69.0)
    assert body["total_quantity"] == 2

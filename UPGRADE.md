# DavaAI v5 — Upgrade Notes

## What changed from v4 (and why)

### 1. JWT auth enforcement — pharmacy_id is now verified

**Problem:** In v4, `pharmacy_id` came from a plain `x-pharmacy-id` HTTP header that any HTTP client could forge. Row-Level Security in Supabase was the only guard.

**Fix — `middleware/auth.py`:** Every route now uses `Depends(require_pharmacy)` which verifies the Supabase JWT, extracts `pharmacy_id` from `app_metadata`, and rejects mismatches with 403.

Dev mode: when `SUPABASE_JWT_SECRET` is unset, auth is bypassed with a warning and `x-pharmacy-id` is accepted directly.

**Required action:** Add `SUPABASE_JWT_SECRET` to your env (Supabase dashboard → Settings → API → JWT Settings). Update frontend to send `Authorization: Bearer <token>`.

---

### 2. Shared Supabase client

**Problem:** `_sb_headers()` was copy-pasted in both route files.

**Fix:** `services/supabase_client.py` — one source of truth for credentials and headers.

---

### 3. Async OCR pipeline

**Problem:** `ocr_service.py` used `requests` (sync), blocking the event loop during Vision + Claude calls (~3–8s each).

**Fix:** All HTTP calls now use `httpx.AsyncClient`. `process_prescription()` is now `async def`.

---

### 4. Per-pharmacy JSONL fallback

**Problem:** All pharmacies shared one `corrections.jsonl` and `confirmed_store.json` in dev/fallback mode.

**Fix:** Fallback files are namespaced: `corrections_{pharmacy_id}.jsonl` and `confirmed_store_{pharmacy_id}.json`.

---

### 5. Docker + CI/CD

Added `Dockerfile` (multi-stage, non-root), `docker-compose.yml` (hot-reload dev), and `.github/workflows/ci.yml` (lint → typecheck → test ≥80% → Docker build → Railway deploy).

```bash
docker compose up --build   # one-command local dev
```

---

### 6. Medicine database seeding

Added `scripts/seed_medicine_db.py` to seed `medicines.csv` from OpenFDA and Jan Aushadhi:

```bash
python scripts/seed_medicine_db.py --limit 2000
python scripts/seed_medicine_db.py --jan-aushadhi data/medicine_db/jan_aushadhi_raw.csv
```

---

## How to upgrade from v4

1. Add `SUPABASE_JWT_SECRET` to your environment.
2. Update frontend to send `Authorization: Bearer <token>` on all requests.
3. Seed the medicine DB: `python scripts/seed_medicine_db.py --limit 2000`
4. Re-run `supabase/schema.sql` in Supabase SQL Editor (safe to re-run).
5. Deploy: `uvicorn main:app` or `docker compose up`
6. Run tests: `pytest -v --cov=. --cov-fail-under=80`

No breaking changes to API response shapes or DB schema.

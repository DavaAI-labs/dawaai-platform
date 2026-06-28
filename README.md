# DavaAI v5 — Smart Pharmacy Assistant

AI-powered prescription OCR + barcode inventory management for Indian pharmacies.

## What it does

| Feature | How |
|---|---|
| Prescription scan | Photo → Google Vision OCR → Claude AI extraction → fuzzy match against inventory |
| Barcode lookup | Scan barcode → instant medicine detail from Supabase or local CSV |
| Billing | Add items to cart → atomic stock decrement → bill saved to Supabase |
| Corrections flywheel | Every pharmacist edit is saved as an OCR training pair |
| Expiry / low-stock alerts | DB views; query from any frontend |

## Architecture

```
Frontend (React)
    │  JWT (Supabase Auth)
    ▼
FastAPI backend  ──► Google Vision API (OCR)
    │            ──► Claude AI (medicine extraction)
    ▼
Supabase (Postgres + Auth + Storage)
```

---

## Quick start (local)

### 1. Clone and configure

```bash
git clone https://github.com/your-org/dawaai.git
cd dawaai
cp .env.example .env
# Fill in .env — at minimum: SUPABASE_URL, SUPABASE_SERVICE_KEY,
# SUPABASE_JWT_SECRET, GOOGLE_VISION_API_KEY, ANTHROPIC_API_KEY
```

### 2. Run the database schema

In the Supabase SQL Editor, run `supabase/schema.sql` (safe to re-run — uses
`CREATE … IF NOT EXISTS` and `CREATE OR REPLACE` throughout).

### 3. Seed the medicine database

```bash
pip install requests
python scripts/seed_medicine_db.py --limit 2000
# Optional: add Jan Aushadhi CSV
python scripts/seed_medicine_db.py --jan-aushadhi data/medicine_db/jan_aushadhi_raw.csv
```

The Jan Aushadhi product list can be downloaded from
https://janaushadhi.gov.in/ProductList.aspx (no account needed).

### 4. Start with Docker Compose

```bash
docker compose up --build
# API available at http://localhost:8000
# Interactive docs at http://localhost:8000/docs
```

### 5. Run tests

```bash
cd backend
pip install -r requirements.txt
pytest -v
```

---

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `SUPABASE_URL` | Yes | Your Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Yes | `service_role` key (backend only) |
| `SUPABASE_JWT_SECRET` | Yes (prod) | JWT secret from Supabase dashboard → Settings → API |
| `GOOGLE_VISION_API_KEY` | Yes | Google Cloud Vision API key |
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key |
| `SENTRY_DSN` | Recommended | Sentry DSN for error tracking |
| `ALLOWED_ORIGINS` | Prod | Comma-separated list of frontend origins |
| `ENVIRONMENT` | Prod | `production` / `staging` / `development` |
| `WORKERS` | Optional | Uvicorn worker count (default: 4) |

> `SUPABASE_JWT_SECRET` is in your Supabase dashboard → Project Settings → API → JWT Settings.
> Without it, auth runs in dev-bypass mode (logs a warning, accepts `x-pharmacy-id` header).

---

## Authentication

Every API route (except `/health` and `/docs`) requires a Supabase JWT in the
`Authorization: Bearer <token>` header. The JWT is issued by Supabase Auth on
frontend login and must contain `pharmacy_id` in `app_metadata` or
`user_metadata` (set by a Supabase DB trigger on `profiles` insert).

**Dev mode** (no `SUPABASE_JWT_SECRET` set): auth is bypassed and the
`x-pharmacy-id` header is accepted directly. This is intentional for local
development but must not be used in production.

---

## Deployment (Railway)

1. Create a new Railway project and link this repo.
2. Set all environment variables in Railway's dashboard.
3. Railway auto-detects the `Dockerfile` at the repo root and builds it.
4. The CI/CD pipeline (`.github/workflows/ci.yml`) deploys to Railway on
   every push to `main` after all tests pass.

To get `RAILWAY_TOKEN`: Railway dashboard → Account → Tokens → New Token.
Add it as a GitHub secret named `RAILWAY_TOKEN`.

---

## API reference

Full interactive docs are available at `/docs` (Swagger UI) and `/redoc`.

### Key endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/api/scan` | JWT | Upload prescription image, get medicine list |
| `POST` | `/api/corrections` | JWT | Save pharmacist correction |
| `GET` | `/api/barcode/{barcode}` | JWT | Look up medicine by barcode |
| `GET` | `/api/medicines/search?q=` | JWT | Search medicines by name |
| `POST` | `/api/barcode/bill` | JWT | Create bill and decrement stock |
| `GET` | `/health` | None | Health check |

---

## Upgrading from v4

1. **Run new schema additions** in Supabase SQL Editor (the full `schema.sql`
   is safe to re-run).

2. **Add `SUPABASE_JWT_SECRET`** to your environment. Get it from:
   Supabase dashboard → Project Settings → API → JWT Settings → JWT Secret.

3. **Update your frontend** to send `Authorization: Bearer <token>` on every
   API request. The token is the Supabase session access token.

4. **Re-seed the medicine database** if you want a larger drug list:
   ```bash
   python scripts/seed_medicine_db.py --limit 5000
   ```

5. **Deploy the new backend** — same entry point: `uvicorn main:app`.

No breaking changes to API response shapes.

---

## Medicine data sources

| Source | Coverage | How to get |
|---|---|---|
| OpenFDA Drug Labels | ~100k international drugs | Auto-fetched by `seed_medicine_db.py` |
| Jan Aushadhi | ~2000 Indian generic drugs | Download CSV from janaushadhi.gov.in |
| CDSCO (manual) | Indian branded drugs | Manual CSV; add via `--jan-aushadhi` flag |

---

## Project structure

```
dawaai-v5/
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── .github/
│   └── workflows/
│       └── ci.yml              # lint + test + docker build + deploy
├── scripts/
│   └── seed_medicine_db.py     # seeds medicines.csv from OpenFDA + Jan Aushadhi
├── supabase/
│   └── schema.sql              # full DB schema with RLS, indexes, RPC functions
└── backend/
    ├── main.py                 # FastAPI app, middleware, rate limiting, Sentry
    ├── requirements.txt
    ├── pytest.ini
    ├── middleware/
    │   └── auth.py             # JWT verification, require_pharmacy dependency
    ├── api/
    │   ├── routes.py           # /scan, /corrections
    │   └── barcode_routes.py   # /barcode/*, /medicines/search, /barcode/bill
    ├── services/
    │   ├── supabase_client.py  # shared headers, URL
    │   ├── ocr_service.py      # async OCR + AI pipeline
    │   ├── fuzzy_match.py      # medicines.csv fuzzy matching
    │   └── correction_store.py # per-pharmacy JSONL fallback
    └── tests/
        ├── conftest.py
        ├── test_fuzzy_match.py
        ├── test_ocr_service.py
        └── test_routes.py
```

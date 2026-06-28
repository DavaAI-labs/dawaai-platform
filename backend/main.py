# main.py — DavaAI v5
# Changes from v4:
#   + JWT auth middleware (middleware/auth.py) — pharmacy_id now verified from token
#   + Shared Supabase client (services/supabase_client.py) — no more duplicated headers
#   + Async OCR pipeline — httpx replaces requests throughout
#   + Per-pharmacy JSONL fallback — multi-tenant isolation in dev mode

import logging
import os

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from limiter import limiter

from api.routes import router as prescription_router
from api.barcode_routes import router as barcode_router

# ── Structured logging ────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":%(message)s}',
)
logger = logging.getLogger("dawaai")

# ── Sentry ────────────────────────────────────────────────────────────────
SENTRY_DSN = os.getenv("SENTRY_DSN", "")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=0.2,   # 20% of requests traced for performance
        environment=os.getenv("ENVIRONMENT", "production"),
    )
    logger.info('"Sentry initialised"')
else:
    logger.warning('"SENTRY_DSN not set — error tracking disabled"')

# ── Rate limiting ─────────────────────────────────────────────────────────
# Per-IP limits. Tightest on the AI scan endpoint (costs money per call).
# Override at deploy time via env vars if needed.
# limiter moved to limiter.py

# ── App ───────────────────────────────────────────────────────────────────
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:3001",
).split(",")

app = FastAPI(
    title="DavaAI API",
    description="Smart Pharmacy Assistant — Prescription OCR + Barcode Medicine Lookup",
    version="5.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(prescription_router, prefix="/api")
app.include_router(barcode_router, prefix="/api")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "version": "5.0.0",
        "sentry": bool(SENTRY_DSN),
        "rate_limiting": True,
        "auth": bool(os.getenv("SUPABASE_JWT_SECRET")),
    }


@app.get("/")
async def root():
    return {"message": "DavaAI API is running", "docs": "/docs"}

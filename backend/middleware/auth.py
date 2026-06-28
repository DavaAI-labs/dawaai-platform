# middleware/auth.py — DavaAI v5
# Enforces JWT-based tenant isolation at the API layer.
#
# Problem solved: In v4, pharmacy_id was read from a plain x-pharmacy-id header
# that any HTTP client could forge to impersonate another pharmacy. Row-Level
# Security in Supabase guards the DB layer, but the API layer had no verification.
#
# Fix: Every authenticated request must carry a Supabase-issued JWT in the
# Authorization header. We verify the JWT signature using the Supabase JWT
# secret (same secret Supabase uses) and extract the pharmacy_id from the
# user's profile claim (populated by a DB trigger on auth.users insert).
#
# Routes that opt into auth add: pharmacy_id: str = Depends(require_pharmacy)
# Unauthenticated routes (/health, /docs) are unaffected.

import os
import logging
from functools import lru_cache
from typing import Optional

import jwt
from fastapi import Header, HTTPException, status

logger = logging.getLogger("dawaai.auth")

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")

# Supabase JWTs always use HS256
_ALGORITHM = "HS256"


@lru_cache(maxsize=1)
def _jwt_secret() -> str:
    """Lazy-load so tests can patch os.environ before import."""
    return os.getenv("SUPABASE_JWT_SECRET", "")


def _decode_token(token: str) -> dict:
    """
    Verify and decode a Supabase JWT.
    Raises HTTPException 401 on any failure so callers get a clean response.
    """
    secret = _jwt_secret()
    if not secret:
        # Auth is disabled in dev — log loudly and allow through
        logger.warning('"jwt_auth_disabled — SUPABASE_JWT_SECRET not set"')
        return {}
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[_ALGORITHM],
            options={"verify_aud": False},  # Supabase omits aud in service tokens
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as exc:
        logger.warning(f'"invalid_jwt","error":"{exc}"')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_pharmacy(
    authorization: Optional[str] = Header(None),
    x_pharmacy_id: Optional[str] = Header(None),
) -> str:
    """
    FastAPI dependency that returns the verified pharmacy_id for the request.

    Token path  (production): reads pharmacy_id from the JWT's app_metadata
    Fallback path (dev/test): accepts x-pharmacy-id header when JWT secret is unset.

    Usage in a route:
        @router.post("/scan")
        async def scan(pharmacy_id: str = Depends(require_pharmacy)):
            ...
    """
    secret = _jwt_secret()

    # ── JWT path (production) ─────────────────────────────────────────────
    if authorization:
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header must use Bearer scheme.",
            )
        token = authorization.removeprefix("Bearer ")
        payload = _decode_token(token)

        # Supabase stores user metadata in app_metadata or user_metadata
        app_meta = payload.get("app_metadata", {})
        user_meta = payload.get("user_metadata", {})
        pharmacy_id = (
            app_meta.get("pharmacy_id")
            or user_meta.get("pharmacy_id")
        )

        if not pharmacy_id:
            # JWT is valid but the user has no pharmacy linked — onboarding gap
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No pharmacy linked to this account. Complete onboarding first.",
            )

        # Extra safety: if the client also sent x-pharmacy-id, it must match
        if x_pharmacy_id and x_pharmacy_id != pharmacy_id:
            logger.warning(
                f'"pharmacy_id_mismatch",'
                f'"header":"{x_pharmacy_id}","token":"{pharmacy_id}"'
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="pharmacy_id header does not match authenticated user.",
            )

        logger.info(f'"auth_ok","pharmacy_id":"{pharmacy_id}"')
        return pharmacy_id

    # ── Dev/test fallback (no JWT secret configured) ──────────────────────
    if not secret:
        if x_pharmacy_id:
            logger.warning(
                f'"auth_bypass_dev","pharmacy_id":"{x_pharmacy_id}" — '
                f'set SUPABASE_JWT_SECRET to enforce auth'
            )
            return x_pharmacy_id
        # Neither header present — return a sentinel so routes can skip DB ops
        return ""

    # JWT secret is set but no Authorization header — reject
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authorization header is required.",
        headers={"WWW-Authenticate": "Bearer"},
    )

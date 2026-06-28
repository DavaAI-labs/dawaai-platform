# tests/test_auth.py
# Unit tests for the JWT auth middleware.
# Tests cover: valid token, expired token, wrong secret, dev bypass, mismatch.

import time
import pytest
import jwt as pyjwt
from fastapi import HTTPException
from unittest.mock import patch

from middleware.auth import require_pharmacy, _jwt_secret

TEST_SECRET = "test-super-secret-jwt-key-for-testing"
TEST_PHARMACY_ID = "pharm-abc-123"


def _make_token(pharmacy_id: str = TEST_PHARMACY_ID, exp_offset: int = 3600) -> str:
    """Create a signed JWT with pharmacy_id in app_metadata."""
    payload = {
        "sub": "user-uuid-123",
        "app_metadata": {"pharmacy_id": pharmacy_id},
        "exp": int(time.time()) + exp_offset,
        "iat": int(time.time()),
    }
    return pyjwt.encode(payload, TEST_SECRET, algorithm="HS256")


# ── Valid token ───────────────────────────────────────────────────────────

def test_valid_token_returns_pharmacy_id():
    token = _make_token()
    with patch("middleware.auth._jwt_secret", return_value=TEST_SECRET):
        result = require_pharmacy(
            authorization=f"Bearer {token}",
            x_pharmacy_id=None,
        )
    assert result == TEST_PHARMACY_ID


def test_valid_token_with_matching_header():
    token = _make_token()
    with patch("middleware.auth._jwt_secret", return_value=TEST_SECRET):
        result = require_pharmacy(
            authorization=f"Bearer {token}",
            x_pharmacy_id=TEST_PHARMACY_ID,  # matches token — OK
        )
    assert result == TEST_PHARMACY_ID


# ── Invalid token ─────────────────────────────────────────────────────────

def test_expired_token_raises_401():
    token = _make_token(exp_offset=-60)  # expired 60s ago
    with patch("middleware.auth._jwt_secret", return_value=TEST_SECRET):
        with pytest.raises(HTTPException) as exc:
            require_pharmacy(authorization=f"Bearer {token}", x_pharmacy_id=None)
    assert exc.value.status_code == 401
    assert "expired" in exc.value.detail.lower()


def test_wrong_secret_raises_401():
    token = _make_token()
    with patch("middleware.auth._jwt_secret", return_value="wrong-secret"):
        with pytest.raises(HTTPException) as exc:
            require_pharmacy(authorization=f"Bearer {token}", x_pharmacy_id=None)
    assert exc.value.status_code == 401


def test_malformed_token_raises_401():
    with patch("middleware.auth._jwt_secret", return_value=TEST_SECRET):
        with pytest.raises(HTTPException) as exc:
            require_pharmacy(authorization="Bearer not.a.jwt", x_pharmacy_id=None)
    assert exc.value.status_code == 401


def test_wrong_scheme_raises_401():
    with patch("middleware.auth._jwt_secret", return_value=TEST_SECRET):
        with pytest.raises(HTTPException) as exc:
            require_pharmacy(authorization="Basic credentials", x_pharmacy_id=None)
    assert exc.value.status_code == 401


# ── pharmacy_id mismatch ──────────────────────────────────────────────────

def test_pharmacy_id_mismatch_raises_403():
    token = _make_token(pharmacy_id="real-pharmacy")
    with patch("middleware.auth._jwt_secret", return_value=TEST_SECRET):
        with pytest.raises(HTTPException) as exc:
            require_pharmacy(
                authorization=f"Bearer {token}",
                x_pharmacy_id="different-pharmacy",  # doesn't match token
            )
    assert exc.value.status_code == 403


# ── Token with no pharmacy_id ─────────────────────────────────────────────

def test_token_without_pharmacy_raises_403():
    payload = {
        "sub": "user-uuid-456",
        "app_metadata": {},  # no pharmacy_id
        "exp": int(time.time()) + 3600,
    }
    token = pyjwt.encode(payload, TEST_SECRET, algorithm="HS256")
    with patch("middleware.auth._jwt_secret", return_value=TEST_SECRET):
        with pytest.raises(HTTPException) as exc:
            require_pharmacy(authorization=f"Bearer {token}", x_pharmacy_id=None)
    assert exc.value.status_code == 403


# ── Dev bypass (no JWT secret) ────────────────────────────────────────────

def test_dev_bypass_accepts_header():
    with patch("middleware.auth._jwt_secret", return_value=""):
        result = require_pharmacy(
            authorization=None,
            x_pharmacy_id="dev-pharmacy-123",
        )
    assert result == "dev-pharmacy-123"


def test_dev_bypass_no_header_returns_empty():
    with patch("middleware.auth._jwt_secret", return_value=""):
        result = require_pharmacy(authorization=None, x_pharmacy_id=None)
    assert result == ""


# ── No auth header when secret is set ────────────────────────────────────

def test_missing_auth_header_with_secret_raises_401():
    with patch("middleware.auth._jwt_secret", return_value=TEST_SECRET):
        with pytest.raises(HTTPException) as exc:
            require_pharmacy(authorization=None, x_pharmacy_id=None)
    assert exc.value.status_code == 401

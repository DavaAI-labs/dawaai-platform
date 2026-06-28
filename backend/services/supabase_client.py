# services/supabase_client.py — v5
# Single source of truth for Supabase credentials and headers.
# Previously _sb_headers() was copy-pasted in both api/routes.py and
# api/barcode_routes.py. Any credential change had to be applied in two places.

import os

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")


def sb_headers() -> dict:
    """Return the headers required for Supabase REST API calls."""
    return {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
    }

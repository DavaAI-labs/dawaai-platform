# api/barcode_routes.py — v5
# Changes from v4:
#   + JWT auth via Depends(require_pharmacy) on all mutating endpoints
#   + Shared sb_headers() from services/supabase_client (no duplication)
#   + Per-pharmacy JSONL fallback path (fixes multi-tenant isolation in dev mode)

import uuid
import logging
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, field_validator
from typing import List, Optional
import csv
import json
import re
import httpx

from limiter import limiter
from middleware.auth import require_pharmacy
from services.supabase_client import sb_headers, SUPABASE_URL

router = APIRouter()
logger = logging.getLogger("dawaai.barcode")

BARCODE_DB_PATH = (
    Path(__file__).parent.parent.parent / "data" / "medicine_db" / "medicines_with_barcodes.csv"
)
STORE_PATH = (
    Path(__file__).parent.parent.parent / "data" / "confirmed_store.json"
)

_barcode_index: dict = {}
_name_index: list = []


def _load_barcode_db():
    global _barcode_index, _name_index
    if _barcode_index:
        return
    if not BARCODE_DB_PATH.exists():
        _seed_demo_data()
        return
    with open(BARCODE_DB_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            _barcode_index[row["barcode"]] = row
            _name_index.append(row)
    logger.info(f'"barcode_db_loaded","count":{len(_barcode_index)}')


def _seed_demo_data():
    demo = [
        {
            "barcode": "8901030589396", "brand_name": "Crocin 650", "generic_name": "Paracetamol",
            "strength": "650 mg", "manufacturer": "GSK Pharma", "mrp": "34.50",
            "batch_number": "BCHX2411", "expiry_date": "12/2026", "available_stock": "48", "form": "Tablet",
        },
        {
            "barcode": "8901030512301", "brand_name": "Amoxicillin 500", "generic_name": "Amoxicillin",
            "strength": "500 mg", "manufacturer": "Cipla Ltd", "mrp": "72.00",
            "batch_number": "AMX2503", "expiry_date": "06/2027", "available_stock": "120", "form": "Capsule",
        },
        {
            "barcode": "8901030554412", "brand_name": "Metformin SR 500",
            "generic_name": "Metformin Hydrochloride",
            "strength": "500 mg", "manufacturer": "Sun Pharma", "mrp": "28.00",
            "batch_number": "MF2502", "expiry_date": "09/2026", "available_stock": "7", "form": "Tablet",
        },
        {
            "barcode": "8901030577892", "brand_name": "Pantocid 40", "generic_name": "Pantoprazole",
            "strength": "40 mg", "manufacturer": "Sun Pharma", "mrp": "85.50",
            "batch_number": "PAN2601", "expiry_date": "08/2027", "available_stock": "60", "form": "Tablet",
        },
        {
            "barcode": "8901030533345", "brand_name": "Azithral 500", "generic_name": "Azithromycin",
            "strength": "500 mg", "manufacturer": "Alembic Pharma", "mrp": "110.00",
            "batch_number": "AZ2504", "expiry_date": "03/2027", "available_stock": "30", "form": "Tablet",
        },
    ]
    for row in demo:
        _barcode_index[row["barcode"]] = row
        _name_index.append(row)
    logger.info('"barcode_db_seeded_with_demo_data"')


_load_barcode_db()


# ── Models ─────────────────────────────────────────────────────────────────

class MedicineDetail(BaseModel):
    barcode: str
    brand_name: str
    generic_name: str
    strength: str
    manufacturer: str
    mrp: float
    batch_number: str
    expiry_date: str
    available_stock: int
    form: str


class CartItem(BaseModel):
    barcode: str
    brand_name: str
    generic_name: str
    strength: str
    quantity: int
    mrp: float
    inventory_id: Optional[str] = None   # required for stock decrement
    batch_number: Optional[str] = None
    expiry_date: Optional[str] = None

    @field_validator("quantity")
    @classmethod
    def quantity_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("quantity must be ≥ 1")
        return v

    @field_validator("mrp")
    @classmethod
    def mrp_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("mrp cannot be negative")
        return v


class BarcodeBillRequest(BaseModel):
    pharmacy_id: Optional[str] = None
    pharmacy_name: Optional[str] = "Pharmacy"
    cart: List[CartItem]

    @field_validator("cart")
    @classmethod
    def cart_not_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("cart cannot be empty")
        return v


# ── Supabase helpers ──────────────────────────────────────────────────────

async def _supabase_barcode_lookup(pharmacy_id: str, barcode: str):
    """Look up barcode in Supabase inventory for the given pharmacy."""
    if not SUPABASE_URL:
        return None
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SUPABASE_URL}/rest/v1/inventory",
            params={
                "pharmacy_id": f"eq.{pharmacy_id}",
                "barcode": f"eq.{barcode}",
                "select": "*",
            },
            headers=sb_headers(),
            timeout=8,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data[0] if data else None
    return None


async def _decrement_stock_atomic(inventory_id: str, qty: int, client: httpx.AsyncClient) -> bool:
    """
    Atomically decrement stock using a Postgres RPC.
    The function (defined in schema.sql) uses UPDATE … WHERE quantity >= amount
    so it never goes negative and is safe under concurrent requests.
    Returns True on success, False if insufficient stock.
    """
    resp = await client.post(
        f"{SUPABASE_URL}/rest/v1/rpc/decrement_stock",
        json={"item_id": inventory_id, "amount": qty},
        headers=sb_headers(),
        timeout=8,
    )
    if resp.status_code == 200:
        result = resp.json()
        # The RPC returns the new quantity; None means the WHERE clause failed (no stock)
        return result is not None
    logger.error(
        f'"decrement_stock_failed","inventory_id":"{inventory_id}","status":{resp.status_code}'
    )
    return False


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/barcode/{barcode}", response_model=MedicineDetail)
@limiter.limit("120/minute")
async def get_medicine_by_barcode(
    request: Request,
    barcode: str,
    pharmacy_id: str = Depends(require_pharmacy),
):
    # Basic barcode sanity check (digits only, 8–14 chars — covers EAN-8/13, UPC-A)
    if not re.fullmatch(r"\d{8,14}", barcode):
        raise HTTPException(status_code=422, detail="Invalid barcode format.")

    if pharmacy_id and SUPABASE_URL:
        med = await _supabase_barcode_lookup(pharmacy_id, barcode)
        if med:
            logger.info(f'"barcode_hit","barcode":"{barcode}","source":"supabase"')
            return MedicineDetail(
                barcode=barcode,
                brand_name=med.get("brand_name", ""),
                generic_name=med.get("generic_name", ""),
                strength=med.get("strength", ""),
                manufacturer=med.get("manufacturer", ""),
                mrp=float(med.get("mrp") or 0),
                batch_number=med.get("batch_number", ""),
                expiry_date=str(med.get("expiry_date", "")),
                available_stock=int(med.get("quantity") or 0),
                form=med.get("form", ""),
            )

    med = _barcode_index.get(barcode)
    if not med:
        logger.warning(f'"barcode_miss","barcode":"{barcode}"')
        raise HTTPException(status_code=404, detail=f"No medicine found for barcode {barcode}")

    logger.info(f'"barcode_hit","barcode":"{barcode}","source":"csv"')
    return MedicineDetail(
        barcode=barcode,
        brand_name=med["brand_name"],
        generic_name=med["generic_name"],
        strength=med["strength"],
        manufacturer=med["manufacturer"],
        mrp=float(med["mrp"]),
        batch_number=med["batch_number"],
        expiry_date=med["expiry_date"],
        available_stock=int(med["available_stock"]),
        form=med["form"],
    )


@router.get("/medicines/search")
@limiter.limit("120/minute")
async def search_medicines(
    request: Request,
    q: str = Query(..., min_length=2, max_length=100),
    pharmacy_id: str = Depends(require_pharmacy),
):
    if pharmacy_id and SUPABASE_URL:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/inventory",
                params={
                    "pharmacy_id": f"eq.{pharmacy_id}",
                    "or": f"brand_name.ilike.%{q}%,generic_name.ilike.%{q}%",
                    "select": "*",
                    "limit": "8",
                },
                headers=sb_headers(),
                timeout=8,
            )
            if resp.status_code == 200 and resp.json():
                return [
                    {
                        "barcode": m.get("barcode", ""),
                        "brand_name": m["brand_name"],
                        "generic_name": m.get("generic_name", ""),
                        "strength": m.get("strength", ""),
                        "manufacturer": m.get("manufacturer", ""),
                        "mrp": float(m.get("mrp") or 0),
                        "batch_number": m.get("batch_number", ""),
                        "expiry_date": str(m.get("expiry_date", "")),
                        "available_stock": int(m.get("quantity") or 0),
                        "form": m.get("form", ""),
                    }
                    for m in resp.json()
                ]

    q_lower = q.lower()
    results = []
    for med in _name_index:
        if q_lower in med["brand_name"].lower() or q_lower in med["generic_name"].lower():
            results.append({
                "barcode": med["barcode"],
                "brand_name": med["brand_name"],
                "generic_name": med["generic_name"],
                "strength": med["strength"],
                "manufacturer": med["manufacturer"],
                "mrp": float(med["mrp"]),
                "batch_number": med["batch_number"],
                "expiry_date": med["expiry_date"],
                "available_stock": int(med["available_stock"]),
                "form": med["form"],
            })
            if len(results) >= 8:
                break
    return results


@router.post("/barcode/bill")
@limiter.limit("30/minute")
async def create_barcode_bill(
    request: Request,
    body: BarcodeBillRequest,
    pharmacy_id: str = Depends(require_pharmacy),
):
    # Use verified pharmacy_id from JWT; body.pharmacy_id is advisory only
    effective_pharmacy_id = pharmacy_id or body.pharmacy_id
    bill_id = f"BC-{str(uuid.uuid4())[:6].upper()}"
    total_mrp = round(sum(i.mrp * i.quantity for i in body.cart), 2)

    if effective_pharmacy_id and SUPABASE_URL:
        async with httpx.AsyncClient() as client:
            # 1. Insert bill
            bill_payload = {
                "pharmacy_id": effective_pharmacy_id,
                "bill_number": bill_id,
                "source": "barcode",
                "total_mrp": total_mrp,
                "total_items": len(body.cart),
            }
            bill_resp = await client.post(
                f"{SUPABASE_URL}/rest/v1/bills",
                json=bill_payload,
                headers={**sb_headers(), "Prefer": "return=representation"},
                timeout=8,
            )
            if bill_resp.status_code not in (200, 201):
                logger.error(f'"bill_insert_failed","status":{bill_resp.status_code}')
                raise HTTPException(status_code=502, detail="Failed to save bill.")

            bill_row = bill_resp.json()
            bill_db_id = (bill_row[0] if isinstance(bill_row, list) else bill_row).get("id")

            # 2. Insert bill items
            if bill_db_id:
                items_payload = [
                    {
                        "bill_id": bill_db_id,
                        "inventory_id": i.inventory_id,
                        "brand_name": i.brand_name,
                        "generic_name": i.generic_name,
                        "strength": i.strength,
                        "quantity": i.quantity,
                        "mrp": i.mrp,
                    }
                    for i in body.cart
                ]
                await client.post(
                    f"{SUPABASE_URL}/rest/v1/bill_items",
                    json=items_payload,
                    headers=sb_headers(),
                    timeout=8,
                )

                # 3. Atomically decrement stock for each item that has an inventory_id
                stock_failures = []
                for item in body.cart:
                    if item.inventory_id:
                        ok = await _decrement_stock_atomic(item.inventory_id, item.quantity, client)
                        if not ok:
                            stock_failures.append(item.brand_name)

                if stock_failures:
                    logger.error(
                        f'"stock_decrement_insufficient","items":{stock_failures},"bill_id":"{bill_id}"'
                    )

        logger.info(f'"bill_created","bill_id":"{bill_id}","total_mrp":{total_mrp}')
    else:
        # Fallback: per-pharmacy JSON file (dev mode only)
        # Each pharmacy writes to its own file to prevent cross-tenant data leakage.
        safe_pid = re.sub(r"[^a-zA-Z0-9_-]", "_", effective_pharmacy_id or "anon")
        store_path = STORE_PATH.parent / f"confirmed_store_{safe_pid}.json"
        store: dict = {}
        if store_path.exists():
            try:
                store = json.loads(store_path.read_text())
            except json.JSONDecodeError:
                store = {}
        store[bill_id] = {
            "bill_id": bill_id,
            "source": "barcode",
            "pharmacy_name": body.pharmacy_name,
            "pharmacy_id": effective_pharmacy_id,
            "medicines": [item.model_dump() for item in body.cart],
            "created_at": datetime.utcnow().isoformat(),
        }
        store_path.parent.mkdir(parents=True, exist_ok=True)
        store_path.write_text(json.dumps(store, indent=2))
        logger.info(f'"bill_created_local","bill_id":"{bill_id}","pharmacy_id":"{effective_pharmacy_id}"')

    return {
        "bill_id": bill_id,
        "total_items": len(body.cart),
        "total_quantity": sum(i.quantity for i in body.cart),
        "total_mrp": total_mrp,
    }


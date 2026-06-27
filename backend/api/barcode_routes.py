# barcode_routes.py — Production Version
# Uses Supabase inventory instead of in-memory / CSV when configured.

import uuid
import os
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, Header
from pydantic import BaseModel
from typing import List, Optional
import csv
import json
import httpx

router = APIRouter()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

BARCODE_DB_PATH = Path(__file__).parent.parent.parent / "data" / "medicine_db" / "medicines_with_barcodes.csv"
STORE_PATH = Path(__file__).parent.parent.parent / "data" / "confirmed_store.json"

# In-memory fallback indexes (used only if Supabase not configured)
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


def _seed_demo_data():
    demo = [
        {"barcode": "8901030589396", "brand_name": "Crocin 650", "generic_name": "Paracetamol",
         "strength": "650 mg", "manufacturer": "GSK Pharma", "mrp": "34.50",
         "batch_number": "BCHX2411", "expiry_date": "12/2026", "available_stock": "48", "form": "Tablet"},
        {"barcode": "8901030512301", "brand_name": "Amoxicillin 500", "generic_name": "Amoxicillin",
         "strength": "500 mg", "manufacturer": "Cipla Ltd", "mrp": "72.00",
         "batch_number": "AMX2503", "expiry_date": "06/2027", "available_stock": "120", "form": "Capsule"},
        {"barcode": "8901030554412", "brand_name": "Metformin SR 500", "generic_name": "Metformin Hydrochloride",
         "strength": "500 mg", "manufacturer": "Sun Pharma", "mrp": "28.00",
         "batch_number": "MF2502", "expiry_date": "09/2026", "available_stock": "7", "form": "Tablet"},
        {"barcode": "8901030577892", "brand_name": "Pantocid 40", "generic_name": "Pantoprazole",
         "strength": "40 mg", "manufacturer": "Sun Pharma", "mrp": "85.50",
         "batch_number": "PAN2601", "expiry_date": "08/2027", "available_stock": "60", "form": "Tablet"},
        {"barcode": "8901030533345", "brand_name": "Azithral 500", "generic_name": "Azithromycin",
         "strength": "500 mg", "manufacturer": "Alembic Pharma", "mrp": "110.00",
         "batch_number": "AZ2504", "expiry_date": "03/2027", "available_stock": "30", "form": "Tablet"},
    ]
    for row in demo:
        _barcode_index[row["barcode"]] = row
        _name_index.append(row)


_load_barcode_db()


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
    batch_number: Optional[str] = None
    expiry_date: Optional[str] = None


class BarcodeBillRequest(BaseModel):
    pharmacy_id: Optional[str] = None
    pharmacy_name: Optional[str] = "Pharmacy"
    cart: List[CartItem]


async def _supabase_barcode_lookup(pharmacy_id: str, barcode: str):
    """Look up barcode in Supabase inventory for the given pharmacy."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        return None
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SUPABASE_URL}/rest/v1/inventory",
            params={"pharmacy_id": f"eq.{pharmacy_id}", "barcode": f"eq.{barcode}", "select": "*"},
            headers={"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"},
            timeout=8,
        )
        if resp.status_code == 200:
            data = resp.json()
            return data[0] if data else None
    return None


@router.get("/barcode/{barcode}", response_model=MedicineDetail)
async def get_medicine_by_barcode(
    barcode: str,
    x_pharmacy_id: Optional[str] = Header(None),
):
    # Try Supabase first (per-pharmacy inventory)
    if x_pharmacy_id and SUPABASE_URL:
        med = await _supabase_barcode_lookup(x_pharmacy_id, barcode)
        if med:
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

    # Fallback: global CSV/demo index
    med = _barcode_index.get(barcode)
    if not med:
        raise HTTPException(status_code=404, detail=f"No medicine found for barcode {barcode}")

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
async def search_medicines(
    q: str = Query(..., min_length=2),
    x_pharmacy_id: Optional[str] = Header(None),
):
    # Try Supabase inventory search
    if x_pharmacy_id and SUPABASE_URL and SUPABASE_SERVICE_KEY:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/inventory",
                params={
                    "pharmacy_id": f"eq.{x_pharmacy_id}",
                    "or": f"brand_name.ilike.%{q}%,generic_name.ilike.%{q}%",
                    "select": "*",
                    "limit": "5",
                },
                headers={"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"},
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

    # Fallback: global index
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
            if len(results) >= 5:
                break
    return results


@router.post("/barcode/bill")
async def create_barcode_bill(body: BarcodeBillRequest):
    bill_id = f"BC-{str(uuid.uuid4())[:6].upper()}"

    # If Supabase configured, save bill there
    if body.pharmacy_id and SUPABASE_URL and SUPABASE_SERVICE_KEY:
        async with httpx.AsyncClient() as client:
            bill_payload = {
                "pharmacy_id": body.pharmacy_id,
                "bill_number": bill_id,
                "source": "barcode",
                "total_mrp": sum(i.mrp * i.quantity for i in body.cart),
                "total_items": len(body.cart),
            }
            bill_resp = await client.post(
                f"{SUPABASE_URL}/rest/v1/bills",
                json=bill_payload,
                headers={
                    "apikey": SUPABASE_SERVICE_KEY,
                    "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                    "Prefer": "return=representation",
                    "Content-Type": "application/json",
                },
                timeout=8,
            )
            if bill_resp.status_code in (200, 201):
                bill_row = bill_resp.json()[0] if isinstance(bill_resp.json(), list) else bill_resp.json()
                bill_db_id = bill_row.get("id")
                if bill_db_id:
                    items_payload = [
                        {
                            "bill_id": bill_db_id,
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
                        headers={
                            "apikey": SUPABASE_SERVICE_KEY,
                            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
                            "Content-Type": "application/json",
                        },
                        timeout=8,
                    )
    else:
        # Fallback: persist to local JSON
        store: dict = {}
        if STORE_PATH.exists():
            store = json.loads(STORE_PATH.read_text())
        store[bill_id] = {
            "bill_id": bill_id,
            "source": "barcode",
            "pharmacy_name": body.pharmacy_name,
            "medicines": [item.dict() for item in body.cart],
            "created_at": datetime.utcnow().isoformat(),
        }
        STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STORE_PATH.write_text(json.dumps(store, indent=2))

    return {
        "bill_id": bill_id,
        "total_items": len(body.cart),
        "total_quantity": sum(i.quantity for i in body.cart),
        "total_mrp": round(sum(i.mrp * i.quantity for i in body.cart), 2),
    }

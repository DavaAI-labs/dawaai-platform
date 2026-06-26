# barcode_routes.py
# New endpoints for barcode/QR code medicine lookup.
#
# GET  /api/barcode/{barcode}        → fetch full medicine details by barcode
# GET  /api/medicines/search?q=name  → search medicines by name (fallback)
# POST /api/barcode/bill             → create bill from barcode-scanned cart

import uuid
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
import csv
import json

router = APIRouter()

# ── Medicine DB (barcode-indexed) ──────────────────────────────────────────

BARCODE_DB_PATH = Path(__file__).parent.parent.parent / "data" / "medicine_db" / "medicines_with_barcodes.csv"
STORE_PATH = Path(__file__).parent.parent.parent / "data" / "confirmed_store.json"

# In-memory indexes
_barcode_index: dict = {}   # barcode → medicine row
_name_index: list = []       # all medicines for name search

def _load_barcode_db():
    global _barcode_index, _name_index
    if _barcode_index:
        return

    if not BARCODE_DB_PATH.exists():
        # Seed with demo data if no CSV exists
        _seed_demo_data()
        return

    with open(BARCODE_DB_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            _barcode_index[row["barcode"]] = row
            _name_index.append(row)

def _seed_demo_data():
    """Populate in-memory demo data for development."""
    demo = [
        {
            "barcode": "8901030589396",
            "brand_name": "Crocin 650",
            "generic_name": "Paracetamol",
            "strength": "650 mg",
            "manufacturer": "GSK Pharma",
            "mrp": "34.50",
            "batch_number": "BCHX2411",
            "expiry_date": "12/2026",
            "available_stock": "48",
            "form": "Tablet",
        },
        {
            "barcode": "8901030512301",
            "brand_name": "Amoxicillin 500",
            "generic_name": "Amoxicillin",
            "strength": "500 mg",
            "manufacturer": "Cipla Ltd",
            "mrp": "72.00",
            "batch_number": "AMX2503",
            "expiry_date": "06/2027",
            "available_stock": "120",
            "form": "Capsule",
        },
        {
            "barcode": "8901030554412",
            "brand_name": "Metformin SR 500",
            "generic_name": "Metformin Hydrochloride",
            "strength": "500 mg",
            "manufacturer": "Sun Pharma",
            "mrp": "28.00",
            "batch_number": "MF2502",
            "expiry_date": "09/2026",
            "available_stock": "7",   # low stock demo
            "form": "Tablet",
        },
        {
            "barcode": "8901030577892",
            "brand_name": "Pantocid 40",
            "generic_name": "Pantoprazole",
            "strength": "40 mg",
            "manufacturer": "Sun Pharma",
            "mrp": "85.50",
            "batch_number": "PAN2601",
            "expiry_date": "08/2027",
            "available_stock": "60",
            "form": "Tablet",
        },
        {
            "barcode": "8901030533345",
            "brand_name": "Azithral 500",
            "generic_name": "Azithromycin",
            "strength": "500 mg",
            "manufacturer": "Alembic Pharma",
            "mrp": "110.00",
            "batch_number": "AZ2504",
            "expiry_date": "03/2027",
            "available_stock": "30",
            "form": "Tablet",
        },
    ]
    for row in demo:
        _barcode_index[row["barcode"]] = row
        _name_index.append(row)

_load_barcode_db()


# ── Response models ────────────────────────────────────────────────────────

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
    pharmacy_name: Optional[str] = "Pharmacy"
    cart: List[CartItem]


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/barcode/{barcode}", response_model=MedicineDetail)
async def get_medicine_by_barcode(barcode: str):
    """
    Lookup medicine details by barcode or QR code.
    Returns full medicine info: name, strength, MRP, batch, expiry, stock.
    """
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
async def search_medicines(q: str = Query(..., min_length=2)):
    """
    Search medicines by brand or generic name.
    Used as fallback when barcode is not recognized.
    Returns top 5 matches.
    """
    q_lower = q.lower()
    results = []

    for med in _name_index:
        name_match = q_lower in med["brand_name"].lower() or q_lower in med["generic_name"].lower()
        if name_match:
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
    """
    Creates a bill from a barcode-scanned cart.
    Returns bill_id for retrieval.
    """
    bill_id = f"BC-{str(uuid.uuid4())[:6].upper()}"

    # Decrement stock (in production this would write to DB)
    for item in body.cart:
        med = _barcode_index.get(item.barcode)
        if med:
            new_stock = max(0, int(med["available_stock"]) - item.quantity)
            _barcode_index[item.barcode]["available_stock"] = str(new_stock)

    # Persist bill
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

    total_qty = sum(i.quantity for i in body.cart)
    total_mrp = sum(i.mrp * i.quantity for i in body.cart)

    return {
        "bill_id": bill_id,
        "total_items": len(body.cart),
        "total_quantity": total_qty,
        "total_mrp": round(total_mrp, 2),
    }
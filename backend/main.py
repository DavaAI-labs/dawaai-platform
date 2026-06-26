# main.py — upgraded DavaAI backend
# Serves both prescription OCR routes and new barcode lookup routes.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router as prescription_router
from api.barcode_routes import router as barcode_router

app = FastAPI(
    title="DavaAI API",
    description="Smart Pharmacy Assistant — Prescription OCR + Barcode Medicine Lookup",
    version="2.0.0",
)

# CORS — allow React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(prescription_router, prefix="/api")
app.include_router(barcode_router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}
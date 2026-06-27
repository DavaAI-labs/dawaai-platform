# main.py — DavaAI Production Backend
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from api.routes import router as prescription_router
from api.barcode_routes import router as barcode_router

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:3001"
).split(",")

app = FastAPI(
    title="DavaAI API",
    description="Smart Pharmacy Assistant — Prescription OCR + Barcode Medicine Lookup",
    version="3.0.0",
)

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
    return {"status": "ok", "version": "3.0.0"}


@app.get("/")
async def root():
    return {"message": "DavaAI API is running", "docs": "/docs"}

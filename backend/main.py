# DavaAI — Phase 1 Backend
# Run: uvicorn main:app --reload --port 8000

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router

app = FastAPI(
    title="DavaAI",
    description="Prescription digitizer for Indian pharmacies",
    version="1.0.0"
)

# Allow React frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

@app.get("/")
def health_check():
    return {"status": "DavaAI running", "version": "1.0.0"}
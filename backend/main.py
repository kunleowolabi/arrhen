"""
FastAPI application entry point.

Run with:
    uvicorn backend.main:app --reload --port 8000

API docs available at:
    http://localhost:8000/docs      (Swagger UI)
    http://localhost:8000/redoc     (ReDoc)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.router import router

app = FastAPI(
    title="Carbon Emission Tracking Platform",
    description=(
        "A sustainability data management platform for tracking, "
        "calculating, and reporting greenhouse gas emissions. "
        "Built on the GHG Protocol framework."
    ),
    version="0.1.0",
    contact={
        "name": "Arrhen",
    },
    license_info={
        "name": "Business Source License 1.1",
    },
)

# CORS — allows the React frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok", "version": "0.1.0"}
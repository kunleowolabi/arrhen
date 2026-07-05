"""
FastAPI application entry point.

Run with:
    uvicorn backend.main:app --reload --port 8000

API docs available at:
    http://localhost:8000/docs      (Swagger UI)
    http://localhost:8000/redoc     (ReDoc)
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from backend.api.router import router

limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

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
# Add your production domain to ALLOWED_ORIGINS in .env
import os as _os
_raw_origins = _os.getenv("ALLOWED_ORIGINS", "")
_extra_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
] + _extra_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok", "version": "0.1.0"}
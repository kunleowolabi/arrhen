"""
Central API router — registers all endpoint groups with their prefixes.
Imported by main.py and mounted on the FastAPI app.
"""

from fastapi import APIRouter
from backend.api import (
    organisations,
    activity,
    calculations,
    factors,
    dashboard,
    geo,
    reports,
)

router = APIRouter()

router.include_router(
    organisations.router,
    prefix="/organisations",
    tags=["Organisations"],
)
router.include_router(
    activity.router,
    prefix="/activity",
    tags=["Activity Records"],
)
router.include_router(
    calculations.router,
    prefix="/calculations",
    tags=["Calculations"],
)
router.include_router(
    factors.router,
    prefix="/factors",
    tags=["Emission Factors"],
)
router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["Dashboard"],
)
router.include_router(
    geo.router,
    prefix="/geo",
    tags=["Geospatial"],
)
router.include_router(
    reports.router,
    prefix="/reports",
    tags=["Reports"],
)
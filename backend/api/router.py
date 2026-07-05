"""
Central API router.
All routes under /api/v1/ require authentication except /health.
Auth is enforced via Depends(get_current_user) on the main router.
"""

from fastapi import APIRouter, Depends
from backend.api.auth import get_current_user
from backend.api import (
    organisations,
    activity,
    calculations,
    factors,
    dashboard,
    geo,
    reports,
)
from backend.api import auth_router

# Protected router — all included routes require valid JWT
router = APIRouter(dependencies=[Depends(get_current_user)])

router.include_router(
    auth_router.router,
    prefix="/auth",
    tags=["Auth"],
)
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

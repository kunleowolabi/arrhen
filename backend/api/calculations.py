"""
Calculation endpoints.

POST   /calculations/run                 — trigger batch calculation
GET    /calculations/{record_id}         — get emission record for activity
GET    /calculations/pending             — get pending record count
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import UUID
from datetime import datetime

from backend.db.database import get_db
from backend.models import ActivityRecord, EmissionRecord, Site, DataLineage
from backend.schemas.emission import (
    CalculationRequest,
    CalculationResponse,
    EmissionRecordResponse,
)
from backend.core.calculations.engine import calculate_batch, CalculationError
from backend.models.enums import DataStatus

router = APIRouter()


@router.get("/pending")
def get_pending_summary(
    organisation_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Returns:
    - pending_count: activity records with status=validated and no emission record
    - uploads_since_last_calc: lineage records created after last calculation
    - last_calculated_at: timestamp of most recent emission record calculation
    - is_up_to_date: True if no pending records exist
    """

    # ── Most recent calculation timestamp for this org ─────
    last_calc = (
        db.query(func.max(EmissionRecord.calculated_at))
        .join(
            ActivityRecord,
            EmissionRecord.activity_record_id == ActivityRecord.id,
        )
        .join(Site, ActivityRecord.site_id == Site.id)
        .filter(Site.organisation_id == organisation_id)
        .scalar()
    )

    # ── Pending records — validated with no emission record ─
    calculated_ids = (
        db.query(EmissionRecord.activity_record_id)
        .join(
            ActivityRecord,
            EmissionRecord.activity_record_id == ActivityRecord.id,
        )
        .join(Site, ActivityRecord.site_id == Site.id)
        .filter(Site.organisation_id == organisation_id)
        .subquery()
    )

    pending_count = (
        db.query(ActivityRecord)
        .join(Site, ActivityRecord.site_id == Site.id)
        .filter(
            Site.organisation_id == organisation_id,
            ActivityRecord.status == DataStatus.validated,
            ActivityRecord.is_flagged_duplicate == False,
            ~ActivityRecord.id.in_(calculated_ids),
        )
        .count()
    )

    # ── Uploads since last calculation ─────────────────────
    lineage_query = db.query(DataLineage)

    if last_calc:
        lineage_query = lineage_query.filter(
            DataLineage.uploaded_at > last_calc
        )

    uploads_since = lineage_query.count()

    return {
        "pending_count": pending_count,
        "uploads_since_last_calc": uploads_since,
        "last_calculated_at": last_calc.isoformat() if last_calc else None,
        "is_up_to_date": pending_count == 0,
    }


@router.post("/run", response_model=CalculationResponse)
def run_calculations(
    payload: CalculationRequest,
    db: Session = Depends(get_db),
):
    if not any([
        payload.site_id,
        payload.organisation_id,
        payload.period_year,
    ]):
        raise HTTPException(
            status_code=400,
            detail=(
                "At least one filter required: "
                "site_id, organisation_id, or period_year"
            ),
        )

    try:
        results = calculate_batch(
            db=db,
            gwp_version=payload.gwp_version,
            site_id=payload.site_id,
            organisation_id=payload.organisation_id,
            period_year=payload.period_year,
            period_month=payload.period_month,
            scope=payload.scope,
        )
        return results
    except CalculationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{record_id}", response_model=EmissionRecordResponse)
def get_emission_record(
    record_id: UUID,
    db: Session = Depends(get_db),
):
    activity = db.query(ActivityRecord).filter_by(id=record_id).first()
    if not activity:
        raise HTTPException(
            status_code=404,
            detail="Activity record not found",
        )
    if not activity.emission_record:
        raise HTTPException(
            status_code=404,
            detail="No emission record found — run calculation first",
        )
    return activity.emission_record
"""
Report generation endpoints.

POST   /reports/generate/json            — generate JSON inventory export
POST   /reports/generate/pdf             — generate PDF report
"""
import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from uuid import UUID
import io

from backend.db.database import get_db
from backend.models import Organisation
from backend.core.reporting.report_generator import (
    generate_json_report,
    generate_pdf_report,
)

router = APIRouter()


@router.get("/json")
def export_json_report(
    organisation_id: UUID,
    period_year: int,
    db: Session = Depends(get_db),
):
    """
    Generates a full JSON emission inventory for the given
    organisation and year. Machine-readable export for
    third-party tools or regulatory portals.
    """
    org = db.query(Organisation).filter_by(id=organisation_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organisation not found")

    report = generate_json_report(
        db=db,
        organisation_id=organisation_id,
        period_year=period_year,
    )
    return JSONResponse(content=report)


@router.get("/pdf")
def export_pdf_report(
    organisation_id: UUID,
    period_year: int,
    db: Session = Depends(get_db),
):
    """
    Generates a formatted PDF emission report.
    Returns the PDF as a downloadable file stream.
    """
    org = db.query(Organisation).filter_by(id=organisation_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organisation not found")

    pdf_bytes = generate_pdf_report(
        db=db,
        organisation=org,
        period_year=period_year,
    )

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f"attachment; filename="
                f"{org.name.replace(' ', '_')}_{period_year}_emissions.pdf"
            )
        },
    )

@router.get("/audit-trail")
def export_audit_trail(
    organisation_id: UUID,
    period_year: int,
    db: Session = Depends(get_db),
):
    """
    Generates a full audit trail — every emission record with its
    source activity, factor applied, GWP version, and timestamp.
    """
    from backend.models import Site, EmissionFactor
    import json

    org = db.query(Organisation).filter_by(id=organisation_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organisation not found")

    from backend.models import ActivityRecord, EmissionRecord
    rows = (
        db.query(ActivityRecord, EmissionRecord, EmissionFactor, Site)
        .join(
            EmissionRecord,
            ActivityRecord.id == EmissionRecord.activity_record_id,
        )
        .join(
            EmissionFactor,
            EmissionRecord.emission_factor_id == EmissionFactor.id,
        )
        .join(Site, ActivityRecord.site_id == Site.id)
        .filter(
            Site.organisation_id == organisation_id,
            ActivityRecord.period_year == period_year,
        )
        .order_by(ActivityRecord.period_month, Site.site_code)
        .all()
    )

    trail = []
    for activity, emission, factor, site in rows:
        trail.append({
            "emission_record_id": str(emission.id),
            "activity_record_id": str(activity.id),
            "site_code": site.site_code,
            "site_name": site.name,
            "scope": activity.scope.value,
            "ghg_category": activity.ghg_category,
            "fuel_or_material": activity.fuel_or_material,
            "quantity": activity.quantity,
            "unit": activity.unit,
            "period_year": activity.period_year,
            "period_month": activity.period_month,
            "emission_factor_source": factor.source.value,
            "emission_factor_version": factor.version,
            "emission_factor_region": factor.region or "global",
            "fallback_used": emission.factor_fallback_used,
            "gwp_version": emission.gwp_version.value,
            "total_co2e_kg": emission.total_co2e_kg,
            "total_co2e_tonnes": emission.total_co2e_tonnes,
            "calculated_at": emission.calculated_at.isoformat(),
            "data_lineage_id": str(activity.data_lineage_id)
            if activity.data_lineage_id else None,
        })

    return JSONResponse(content={
        "generated_at": datetime.utcnow().isoformat(),
        "organisation": org.name,
        "period_year": period_year,
        "record_count": len(trail),
        "audit_trail": trail,
    })
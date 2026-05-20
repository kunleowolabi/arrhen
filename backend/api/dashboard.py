"""
Dashboard endpoints — aggregated data for frontend charts.

GET    /dashboard/overview               — full dashboard summary
GET    /dashboard/scope-breakdown        — CO2e by scope
GET    /dashboard/sites                  — emissions by site
GET    /dashboard/materiality            — materiality screen results
GET    /dashboard/trends                 — year-on-year trend data
GET    /dashboard/scope2-summary         — location vs market-based
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from backend.db.database import get_db
from backend.models import Organisation, Target, EmissionRecord, ActivityRecord, Site
from backend.schemas.dashboard import (
    DashboardOverview,
    ScopeBreakdown,
    MaterialityScreenResult,
    TrendResponse,
    TrendDataPoint,
    Scope2Summary,
    TargetProgress,
    SiteEmissionSummary,
)
from backend.core.materiality.screener import (
    run_materiality_screen,
    get_scope_breakdown,
    get_site_breakdown,
)
from backend.core.calculations.scope2_handler import get_scope2_summary
from backend.models.enums import ScopeType

router = APIRouter()


@router.get("/overview", response_model=DashboardOverview)
def get_overview(
    organisation_id: UUID,
    period_year: int,
    db: Session = Depends(get_db),
):
    org = db.query(Organisation).filter_by(id=organisation_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organisation not found")

    scope_data = get_scope_breakdown(db, organisation_id, period_year)
    site_data = get_site_breakdown(db, organisation_id, period_year)
    materiality = run_materiality_screen(db, organisation_id, period_year)
    targets = _get_target_progress(db, organisation_id, period_year)

    return DashboardOverview(
        organisation_id=str(organisation_id),
        organisation_name=org.name,
        period_year=period_year,
        scope_breakdown=ScopeBreakdown(**scope_data),
        top_sites=[SiteEmissionSummary(**s) for s in site_data[:5]],
        top_sources=materiality["sources"][:5],
        target_progress=targets,
    )


@router.get("/scope-breakdown", response_model=ScopeBreakdown)
def scope_breakdown(
    organisation_id: UUID,
    period_year: int,
    db: Session = Depends(get_db),
):
    return get_scope_breakdown(db, organisation_id, period_year)


@router.get("/sites", response_model=list[SiteEmissionSummary])
def sites_breakdown(
    organisation_id: UUID,
    period_year: int,
    db: Session = Depends(get_db),
):
    return get_site_breakdown(db, organisation_id, period_year)


@router.get("/materiality", response_model=MaterialityScreenResult)
def materiality_screen(
    organisation_id: UUID,
    period_year: int,
    threshold_pct: float = Query(1.0, ge=0.1, le=100.0),
    db: Session = Depends(get_db),
):
    return run_materiality_screen(
        db=db,
        organisation_id=organisation_id,
        period_year=period_year,
        threshold_pct=threshold_pct,
    )


@router.get("/scope2-summary", response_model=Scope2Summary)
def scope2_summary(
    organisation_id: UUID,
    period_year: int,
    db: Session = Depends(get_db),
):
    return get_scope2_summary(db, organisation_id, period_year)


@router.get("/trends", response_model=TrendResponse)
def get_trends(
    organisation_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Returns monthly emission totals across all available years
    for year-on-year trend charts.
    """
    rows = (
        db.query(ActivityRecord, EmissionRecord)
        .join(
            EmissionRecord,
            ActivityRecord.id == EmissionRecord.activity_record_id,
        )
        .join(Site, ActivityRecord.site_id == Site.id)
        .filter(Site.organisation_id == organisation_id)
        .order_by(ActivityRecord.period_year, ActivityRecord.period_month)
        .all()
    )

    # Aggregate by year + month
    aggregated = {}
    for activity, emission in rows:
        key = (activity.period_year, activity.period_month)
        if key not in aggregated:
            aggregated[key] = {
                "period_year": activity.period_year,
                "period_month": activity.period_month,
                "scope_1_tco2e": 0.0,
                "scope_2_tco2e": 0.0,
                "scope_3_tco2e": 0.0,
                "total_tco2e": 0.0,
            }
        tco2e = emission.total_co2e_tonnes
        if activity.scope == ScopeType.scope_1:
            aggregated[key]["scope_1_tco2e"] += tco2e
        elif activity.scope == ScopeType.scope_2:
            aggregated[key]["scope_2_tco2e"] += tco2e
        else:
            aggregated[key]["scope_3_tco2e"] += tco2e
        aggregated[key]["total_tco2e"] += tco2e

    data_points = [
        TrendDataPoint(**{
            **v,
            "scope_1_tco2e": round(v["scope_1_tco2e"], 4),
            "scope_2_tco2e": round(v["scope_2_tco2e"], 4),
            "scope_3_tco2e": round(v["scope_3_tco2e"], 4),
            "total_tco2e": round(v["total_tco2e"], 4),
        })
        for v in aggregated.values()
    ]

    return TrendResponse(
        organisation_id=str(organisation_id),
        data_points=data_points,
    )


def _get_target_progress(
    db: Session,
    organisation_id: UUID,
    current_year: int,
) -> list[TargetProgress]:
    """
    Calculates progress against each target for the organisation.
    """
    targets = db.query(Target).filter_by(organisation_id=organisation_id).all()
    scope_data = get_scope_breakdown(db, organisation_id, current_year)

    results = []
    for target in targets:
        from backend.models.enums import ScopeCoverage
        if target.scope_coverage == ScopeCoverage.scope_1_only:
            current = scope_data["scope_1_tco2e"]
        elif target.scope_coverage == ScopeCoverage.scope_1_2:
            current = scope_data["scope_1_tco2e"] + scope_data["scope_2_tco2e"]
        else:
            current = scope_data["total_tco2e"]

        baseline = target.baseline_emissions_tco2e
        reduction_pct = (
            ((baseline - current) / baseline * 100)
            if baseline > 0 else 0.0
        )

        results.append(TargetProgress(
            target_name=target.name,
            baseline_year=target.baseline_year,
            target_year=target.target_year,
            baseline_emissions_tco2e=baseline,
            target_emissions_tco2e=target.target_emissions_tco2e,
            target_reduction_pct=target.target_reduction_pct,
            current_emissions_tco2e=round(current, 4),
            current_reduction_pct=round(reduction_pct, 2),
            on_track=current <= target.target_emissions_tco2e,
            aligned_to=target.aligned_to,
        ))

    return results
"""
Materiality Screener

After calculations run, the screener analyses all emission records
for an organisation and identifies which sources are material —
i.e. significant enough to warrant focused data quality effort.

GHG Protocol guidance: sources representing >= 1% of total emissions
are generally considered material and should be measured directly
rather than estimated.

The screener produces a ranked list of emission sources showing:
- Absolute CO2e contribution
- Percentage share of total
- Whether the source is above the materiality threshold
- Whether fallback factors were used (data quality flag)

This output is used by:
1. The dashboard materiality widget
2. The methodology report (data quality section)
3. To guide where organisations should improve data collection

Usage:
    from backend.core.materiality.screener import run_materiality_screen

    results = run_materiality_screen(
        db=db,
        organisation_id=org_id,
        period_year=2024,
        threshold_pct=1.0,
    )
"""

from sqlalchemy.orm import Session
from backend.models import (
    ActivityRecord,
    EmissionRecord,
    Site,
)
from backend.models.enums import ScopeType
import uuid
import structlog

log = structlog.get_logger()

# Default materiality threshold — sources >= this % of total are material
DEFAULT_THRESHOLD_PCT = 1.0


def run_materiality_screen(
    db: Session,
    organisation_id: uuid.UUID,
    period_year: int,
    threshold_pct: float = DEFAULT_THRESHOLD_PCT,
) -> dict:
    """
    Runs materiality screening for an organisation and reporting year.

    Args:
        db:               SQLAlchemy session
        organisation_id:  Organisation UUID
        period_year:      Reporting year to screen
        threshold_pct:    Materiality threshold as percentage (default 1.0)

    Returns:
        {
            "organisation_id": str,
            "period_year": int,
            "threshold_pct": float,
            "total_co2e_tonnes": float,
            "material_source_count": int,
            "sources": [
                {
                    "rank": int,
                    "scope": str,
                    "ghg_category": str,
                    "fuel_or_material": str,
                    "total_co2e_tonnes": float,
                    "percentage_of_total": float,
                    "is_material": bool,
                    "fallback_used": bool,
                    "record_count": int,
                },
                ...
            ]
        }
    """

    # ── Fetch all emission records for this org and year ───────────────────────
    rows = (
        db.query(ActivityRecord, EmissionRecord)
        .join(
            EmissionRecord,
            ActivityRecord.id == EmissionRecord.activity_record_id,
        )
        .join(Site, ActivityRecord.site_id == Site.id)
        .filter(
            Site.organisation_id == organisation_id,
            ActivityRecord.period_year == period_year,
        )
        .all()
    )

    if not rows:
        log.info(
            "materiality_screen_no_data",
            organisation_id=str(organisation_id),
            period_year=period_year,
        )
        return _empty_result(organisation_id, period_year, threshold_pct)

    # ── Aggregate by scope + ghg_category + fuel_or_material ──────────────────
    # This groups e.g. all diesel generator records across all sites
    # into one source entry
    aggregated = {}

    for activity, emission in rows:
        key = (
            activity.scope.value,
            activity.ghg_category,
            activity.fuel_or_material,
        )

        if key not in aggregated:
            aggregated[key] = {
                "scope": activity.scope.value,
                "ghg_category": activity.ghg_category,
                "fuel_or_material": activity.fuel_or_material,
                "total_co2e_tonnes": 0.0,
                "fallback_used": False,
                "record_count": 0,
            }

        aggregated[key]["total_co2e_tonnes"] += emission.total_co2e_tonnes
        aggregated[key]["record_count"] += 1

        # Flag fallback if any record in this group used a fallback factor
        if emission.factor_fallback_used:
            aggregated[key]["fallback_used"] = True

    # ── Calculate total and percentages ───────────────────────────────────────
    total_co2e = sum(s["total_co2e_tonnes"] for s in aggregated.values())

    sources = []
    for source in aggregated.values():
        pct = (
            (source["total_co2e_tonnes"] / total_co2e * 100)
            if total_co2e > 0
            else 0.0
        )
        sources.append({
            **source,
            "total_co2e_tonnes": round(source["total_co2e_tonnes"], 4),
            "percentage_of_total": round(pct, 2),
            "is_material": pct >= threshold_pct,
        })

    # ── Rank by CO2e descending ────────────────────────────────────────────────
    sources.sort(key=lambda x: x["total_co2e_tonnes"], reverse=True)
    for i, source in enumerate(sources, start=1):
        source["rank"] = i

    material_count = sum(1 for s in sources if s["is_material"])

    log.info(
        "materiality_screen_complete",
        organisation_id=str(organisation_id),
        period_year=period_year,
        total_co2e_tonnes=round(total_co2e, 4),
        source_count=len(sources),
        material_source_count=material_count,
    )

    return {
        "organisation_id": str(organisation_id),
        "period_year": period_year,
        "threshold_pct": threshold_pct,
        "total_co2e_tonnes": round(total_co2e, 4),
        "material_source_count": material_count,
        "sources": sources,
    }


def get_scope_breakdown(
    db: Session,
    organisation_id: uuid.UUID,
    period_year: int,
) -> dict:
    """
    Returns total CO2e broken down by scope.
    Used by the dashboard overview donut chart.

    Returns:
        {
            "scope_1_tco2e": float,
            "scope_2_tco2e": float,
            "scope_3_tco2e": float,
            "total_tco2e": float,
        }
    """
    rows = (
        db.query(ActivityRecord, EmissionRecord)
        .join(
            EmissionRecord,
            ActivityRecord.id == EmissionRecord.activity_record_id,
        )
        .join(Site, ActivityRecord.site_id == Site.id)
        .filter(
            Site.organisation_id == organisation_id,
            ActivityRecord.period_year == period_year,
        )
        .all()
    )

    totals = {
        ScopeType.scope_1: 0.0,
        ScopeType.scope_2: 0.0,
        ScopeType.scope_3: 0.0,
    }

    for activity, emission in rows:
        totals[activity.scope] += emission.total_co2e_tonnes

    total = sum(totals.values())

    return {
        "scope_1_tco2e": round(totals[ScopeType.scope_1], 4),
        "scope_2_tco2e": round(totals[ScopeType.scope_2], 4),
        "scope_3_tco2e": round(totals[ScopeType.scope_3], 4),
        "total_tco2e": round(total, 4),
    }


def get_site_breakdown(
    db: Session,
    organisation_id: uuid.UUID,
    period_year: int,
) -> list:
    """
    Returns total CO2e per site, ranked by emissions.
    Used by the dashboard site/branch table.

    Returns:
        [
            {
                "rank": int,
                "site_code": str,
                "site_name": str,
                "region": str,
                "total_co2e_tonnes": float,
                "record_count": int,
            },
            ...
        ]
    """
    rows = (
        db.query(ActivityRecord, EmissionRecord, Site)
        .join(
            EmissionRecord,
            ActivityRecord.id == EmissionRecord.activity_record_id,
        )
        .join(Site, ActivityRecord.site_id == Site.id)
        .filter(
            Site.organisation_id == organisation_id,
            ActivityRecord.period_year == period_year,
        )
        .all()
    )

    site_totals = {}
    for activity, emission, site in rows:
        site_id = str(site.id)
        if site_id not in site_totals:
            site_totals[site_id] = {
                "site_code": site.site_code,
                "site_name": site.name,
                "region": site.region,
                "total_co2e_tonnes": 0.0,
                "record_count": 0,
            }
        site_totals[site_id]["total_co2e_tonnes"] += emission.total_co2e_tonnes
        site_totals[site_id]["record_count"] += 1

    results = [
        {**v, "total_co2e_tonnes": round(v["total_co2e_tonnes"], 4)}
        for v in site_totals.values()
    ]
    results.sort(key=lambda x: x["total_co2e_tonnes"], reverse=True)
    for i, site in enumerate(results, start=1):
        site["rank"] = i

    return results


def _empty_result(
    organisation_id: uuid.UUID,
    period_year: int,
    threshold_pct: float,
) -> dict:
    return {
        "organisation_id": str(organisation_id),
        "period_year": period_year,
        "threshold_pct": threshold_pct,
        "total_co2e_tonnes": 0.0,
        "material_source_count": 0,
        "sources": [],
    }
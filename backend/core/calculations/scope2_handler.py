"""
Scope 2 Dual Methodology Handler

Routes Scope 2 ActivityRecords to the correct emission factor
based on scope_2_method (location_based or market_based).

Both paths delegate to _compute_and_write() from engine.py —
no calculation logic is duplicated here.

Location-based: uses regional grid factor, falls back to global.
Market-based:   requires explicit contractual factor — no fallback.
"""

from datetime import date
from sqlalchemy.orm import Session

from backend.models import ActivityRecord, EmissionRecord, GWPVersion
from backend.models.enums import Scope2Method, ScopeType
from backend.core.calculations.engine import (
    calculate,
    _compute_and_write,
    CalculationError,
)
from backend.core.calculations.factor_selector import (
    select_factor,
    FactorNotFoundError,
)
import structlog

log = structlog.get_logger()


def calculate_scope2(
    db: Session,
    activity_record: ActivityRecord,
    gwp_version: GWPVersion,
) -> EmissionRecord:
    """
    Calculates Scope 2 emissions using the appropriate methodology.
    Does NOT commit — caller owns the transaction.
    """
    if activity_record.scope != ScopeType.scope_2:
        raise CalculationError(
            f"scope2_handler received a non-Scope 2 record: "
            f"ActivityRecord {activity_record.id} is {activity_record.scope}."
        )

    method = activity_record.scope_2_method or Scope2Method.location_based

    if method == Scope2Method.location_based:
        return _calculate_location_based(db, activity_record, gwp_version)
    else:
        return _calculate_market_based(db, activity_record, gwp_version)


def _calculate_location_based(
    db: Session,
    activity_record: ActivityRecord,
    gwp_version: GWPVersion,
) -> EmissionRecord:
    """
    Location-based Scope 2 — delegates directly to the standard engine.
    """
    log.info(
        "scope2_location_based",
        activity_record_id=str(activity_record.id),
        fuel=activity_record.fuel_or_material,
    )
    return calculate(db=db, activity_record=activity_record, gwp_version=gwp_version)


def _calculate_market_based(
    db: Session,
    activity_record: ActivityRecord,
    gwp_version: GWPVersion,
) -> EmissionRecord:
    """
    Market-based Scope 2.
    Requires an explicit contractual factor — no fallback to location-based.
    """
    site = activity_record.site
    region = site.region if site else None

    if activity_record.period_month:
        reference_date = date(
            activity_record.period_year,
            activity_record.period_month,
            1,
        )
    else:
        reference_date = date(activity_record.period_year, 1, 1)

    market_activity_type = "purchased_electricity_market_based"

    try:
        factor, fallback_used = select_factor(
            db=db,
            activity_type=market_activity_type,
            fuel_or_material=activity_record.fuel_or_material,
            region=region,
            reference_date=reference_date,
        )
    except FactorNotFoundError:
        raise CalculationError(
            f"No market-based emission factor found for "
            f"fuel='{activity_record.fuel_or_material}', "
            f"region='{region}'. "
            f"Add a factor with activity_type='{market_activity_type}' "
            f"or switch to location-based method."
        )

    log.info(
        "scope2_market_based",
        activity_record_id=str(activity_record.id),
        fuel=activity_record.fuel_or_material,
        factor_version=factor.version,
    )

    return _compute_and_write(
        db=db,
        activity_record=activity_record,
        factor=factor,
        gwp_version=gwp_version,
        fallback_used=fallback_used,
    )


def get_scope2_summary(
    db: Session,
    organisation_id,
    period_year: int,
) -> dict:
    """
    Returns Scope 2 totals split by methodology.
    Used by the dashboard scope2-summary endpoint.
    """
    from backend.models import Site, ActivityRecord, EmissionRecord

    scope2_records = (
        db.query(ActivityRecord, EmissionRecord)
        .join(EmissionRecord, ActivityRecord.id == EmissionRecord.activity_record_id)
        .join(Site, ActivityRecord.site_id == Site.id)
        .filter(
            Site.organisation_id == organisation_id,
            ActivityRecord.period_year == period_year,
            ActivityRecord.scope == ScopeType.scope_2,
        )
        .all()
    )

    location_total = 0.0
    market_total = 0.0

    for activity, emission in scope2_records:
        method = activity.scope_2_method or Scope2Method.location_based
        if method == Scope2Method.location_based:
            location_total += emission.total_co2e_tonnes
        else:
            market_total += emission.total_co2e_tonnes

    return {
        "location_based_tco2e": round(location_total, 4),
        "market_based_tco2e": round(market_total, 4),
        "record_count": len(scope2_records),
    }

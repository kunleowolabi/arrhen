"""
Scope 2 Dual Methodology Handler

Scope 2 emissions (purchased electricity, heat, steam, cooling) can be
calculated under two methodologies per the GHG Protocol:

1. LOCATION-BASED
   Uses the average emission factor for the grid where energy is consumed.
   Reflects the actual carbon intensity of the local electricity system.
   Example: Nigeria grid factor (0.432 kgCO2e/kWh)

2. MARKET-BASED
   Uses contractual instruments — renewable energy certificates (RECs),
   power purchase agreements (PPAs), or supplier-specific factors.
   Reflects what the organisation has chosen to purchase.
   Example: A company with a solar PPA may have a near-zero market factor.

Both methods must be reported where data is available (GHG Protocol requirement).
This handler routes each Scope 2 ActivityRecord to the correct factor
based on its scope_2_method field.

If scope_2_method is not set, defaults to location-based.

Usage:
    from backend.core.calculations.scope2_handler import calculate_scope2

    emission_record = calculate_scope2(db, activity_record, GWPVersion.AR6)
"""

from datetime import date
from sqlalchemy.orm import Session

from backend.models import ActivityRecord, EmissionRecord, GWPVersion
from backend.models.enums import Scope2Method, ScopeType
from backend.core.calculations.engine import calculate, CalculationError
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

    Routes to location-based or market-based factor depending on
    the scope_2_method field of the activity record.

    For location-based: uses regional grid factor (falls back to global)
    For market-based: looks for a market-based factor for the fuel/material.
                      If none found, raises CalculationError — market-based
                      requires explicit contractual data, no fallback.

    Args:
        db:              SQLAlchemy session
        activity_record: Must be a Scope 2 ActivityRecord
        gwp_version:     GWPVersion.AR5 or GWPVersion.AR6

    Returns:
        EmissionRecord written to database

    Raises:
        CalculationError if record is not Scope 2, or if market-based
        factor cannot be found
    """

    # ── Validate this is a Scope 2 record ─────────────────────────────────────
    if activity_record.scope != ScopeType.scope_2:
        raise CalculationError(
            f"scope2_handler received a non-Scope 2 record: "
            f"ActivityRecord {activity_record.id} is {activity_record.scope}. "
            f"Use engine.calculate() for Scope 1 and 3 records."
        )

    # ── Determine methodology ──────────────────────────────────────────────────
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
    Location-based Scope 2 calculation.
    Uses the standard engine — regional grid factor with global fallback.
    No special handling needed beyond routing.
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
    Market-based Scope 2 calculation.

    Looks for a factor with activity_type="purchased_electricity_market_based".
    No fallback to location-based — if no market factor exists, raises error.
    The organisation must supply contractual instrument data explicitly.

    This strict no-fallback policy is intentional:
    Market-based reporting without contractual data would be misleading.
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

    # Market-based factors use a distinct activity_type
    # so they never accidentally mix with location-based factors
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
            f"to the emission_factors table, or switch to location-based method."
        )

    log.info(
        "scope2_market_based",
        activity_record_id=str(activity_record.id),
        fuel=activity_record.fuel_or_material,
        factor_version=factor.version,
    )

    # Use the engine but with the market factor already resolved
    # We call calculate() which will re-select the factor internally
    # To avoid double selection, we directly use engine internals here
    from backend.core.calculations.engine import (
        _update_emission_record,
    )
    from backend.models import EmissionRecord as EmissionRecordModel
    from backend.models.enums import DataStatus
    from backend.core.calculations.gwp import get_gas_gwp, GAS_KEYS

    qty = activity_record.quantity

    gas_kg = {
        "co2": qty * factor.co2_factor,
        "ch4": qty * factor.ch4_factor,
        "n2o": qty * factor.n2o_factor,
        "hfc": qty * factor.hfc_factor,
        "pfc": qty * factor.pfc_factor,
        "sf6": qty * factor.sf6_factor,
        "nf3": qty * factor.nf3_factor,
    }

    gas_co2e = {}
    for gas in GAS_KEYS:
        gwp_value = get_gas_gwp(gas, gwp_version)
        gas_co2e[gas] = gas_kg[gas] * gwp_value

    total_co2e_kg = sum(gas_co2e.values())
    total_co2e_tonnes = total_co2e_kg / 1000

    existing = db.query(EmissionRecordModel).filter_by(
        activity_record_id=activity_record.id
    ).first()

    if existing:
        _update_emission_record(
            record=existing,
            gas_kg=gas_kg,
            gas_co2e=gas_co2e,
            total_co2e_kg=total_co2e_kg,
            total_co2e_tonnes=total_co2e_tonnes,
            factor_id=factor.id,
            gwp_version=gwp_version,
            fallback_used=fallback_used,
        )
        emission_record = existing
    else:
        emission_record = EmissionRecordModel(
            activity_record_id=activity_record.id,
            emission_factor_id=factor.id,
            co2_kg=gas_kg["co2"],
            ch4_kg=gas_kg["ch4"],
            n2o_kg=gas_kg["n2o"],
            hfc_kg=gas_kg["hfc"],
            pfc_kg=gas_kg["pfc"],
            sf6_kg=gas_kg["sf6"],
            nf3_kg=gas_kg["nf3"],
            co2_co2e=gas_co2e["co2"],
            ch4_co2e=gas_co2e["ch4"],
            n2o_co2e=gas_co2e["n2o"],
            hfc_co2e=gas_co2e["hfc"],
            pfc_co2e=gas_co2e["pfc"],
            sf6_co2e=gas_co2e["sf6"],
            nf3_co2e=gas_co2e["nf3"],
            total_co2e_kg=total_co2e_kg,
            total_co2e_tonnes=total_co2e_tonnes,
            gwp_version=gwp_version,
            factor_fallback_used=fallback_used,
        )
        db.add(emission_record)

    activity_record.status = DataStatus.calculated
    db.commit()
    db.refresh(emission_record)

    return emission_record


def get_scope2_summary(
    db: Session,
    organisation_id,
    period_year: int,
) -> dict:
    """
    Returns a summary of Scope 2 emissions broken down by methodology.
    Used by the dashboard to show both location-based and market-based totals.

    Args:
        db:               SQLAlchemy session
        organisation_id:  Organisation UUID
        period_year:      Reporting year

    Returns:
        {
            "location_based_tco2e": float,
            "market_based_tco2e": float,
            "record_count": int,
        }
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
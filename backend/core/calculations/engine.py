"""
Calculation Engine

Core logic for converting activity records into emission records.

For each ActivityRecord:
1. Select the appropriate emission factor (with regional fallback)
2. Multiply quantity by each gas factor to get raw kg per gas
3. Multiply each gas kg by its GWP to get CO2e per gas
4. Sum all gas CO2e to get total CO2e
5. Write EmissionRecord to database
6. Update ActivityRecord status to "calculated"

Usage:
    from backend.core.calculations.engine import calculate, calculate_batch

    # Single record
    emission_record = calculate(db, activity_record, GWPVersion.AR6)

    # All pending records for a site/period
    results = calculate_batch(
        db=db,
        site_id=site_id,
        period_year=2024,
        gwp_version=GWPVersion.AR6,
    )
"""

from datetime import date
from sqlalchemy.orm import Session
from backend.models import ActivityRecord, EmissionRecord, GWPVersion
from backend.models.enums import DataStatus, ScopeType
from backend.core.calculations.gwp import get_gas_gwp, GAS_KEYS
from backend.core.calculations.factor_selector import (
    select_factor,
    FactorNotFoundError,
)
import uuid
import structlog

log = structlog.get_logger()


class CalculationError(Exception):
    """Raised when a calculation cannot be completed."""
    pass


def calculate(
    db: Session,
    activity_record: ActivityRecord,
    gwp_version: GWPVersion,
) -> EmissionRecord:
    """
    Calculates emissions for a single ActivityRecord.

    Steps:
    1. Resolve the site region for factor selection
    2. Select the best emission factor
    3. Calculate raw gas masses (kg)
    4. Apply GWP to get CO2e per gas
    5. Sum to total CO2e
    6. Write and return EmissionRecord

    Args:
        db:              SQLAlchemy session
        activity_record: The validated ActivityRecord to calculate
        gwp_version:     GWPVersion.AR5 or GWPVersion.AR6

    Returns:
        EmissionRecord written to database

    Raises:
        CalculationError if factor not found or calculation fails
    """

    # ── Resolve region from site ───────────────────────────────────────────────
    site = activity_record.site
    region = site.region if site else None

    # ── Determine reference date for factor validity check ────────────────────
    if activity_record.period_month:
        reference_date = date(
            activity_record.period_year,
            activity_record.period_month,
            1,
        )
    else:
        reference_date = date(activity_record.period_year, 1, 1)

    # ── Select emission factor ─────────────────────────────────────────────────
    try:
        factor, fallback_used = select_factor(
            db=db,
            activity_type=activity_record.ghg_category,
            fuel_or_material=activity_record.fuel_or_material,
            region=region,
            reference_date=reference_date,
        )
    except FactorNotFoundError as e:
        raise CalculationError(
            f"Cannot calculate ActivityRecord {activity_record.id}: {e}"
        )

    # ── Calculate raw gas masses (kg) ─────────────────────────────────────────
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

    # ── Apply GWP to get CO2e per gas ─────────────────────────────────────────
    gas_co2e = {}
    for gas in GAS_KEYS:
        gwp_value = get_gas_gwp(gas, gwp_version)
        gas_co2e[gas] = gas_kg[gas] * gwp_value

    # ── Sum to total CO2e ─────────────────────────────────────────────────────
    total_co2e_kg = sum(gas_co2e.values())
    total_co2e_tonnes = total_co2e_kg / 1000

    # ── Check if EmissionRecord already exists — update if so ─────────────────
    existing = db.query(EmissionRecord).filter_by(
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
        emission_record = EmissionRecord(
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

    # ── Update ActivityRecord status ───────────────────────────────────────────
    activity_record.status = DataStatus.calculated
    db.commit()
    db.refresh(emission_record)

    log.info(
        "emission_calculated",
        activity_record_id=str(activity_record.id),
        total_co2e_tonnes=round(total_co2e_tonnes, 4),
        gwp_version=gwp_version,
        fallback_used=fallback_used,
    )

    return emission_record


def calculate_batch(
    db: Session,
    gwp_version: GWPVersion,
    site_id: uuid.UUID | None = None,
    organisation_id: uuid.UUID | None = None,
    period_year: int | None = None,
    period_month: int | None = None,
    scope: ScopeType | None = None,
) -> dict:
    """
    Runs calculations for multiple ActivityRecords matching the given filters.
    At least one filter must be provided.

    Args:
        db:               SQLAlchemy session
        gwp_version:      GWPVersion to apply
        site_id:          Optional — filter by site
        organisation_id:  Optional — filter by organisation (all sites)
        period_year:      Optional — filter by year
        period_month:     Optional — filter by month
        scope:            Optional — filter by scope

    Returns:
        Dictionary with counts:
        {
            "total": int,
            "success": int,
            "failed": int,
            "errors": list of error strings
        }
    """
    if not any([site_id, organisation_id, period_year]):
        raise CalculationError(
            "At least one of site_id, organisation_id, or period_year "
            "must be provided for batch calculation."
        )

    # ── Build query ───────────────────────────────────────────────────────────
    query = db.query(ActivityRecord).filter(
        ActivityRecord.status == DataStatus.validated,
        ActivityRecord.is_flagged_duplicate == False,  # noqa: E712
    )

    if site_id:
        query = query.filter(ActivityRecord.site_id == site_id)

    if organisation_id:
        from backend.models import Site
        query = query.join(Site).filter(
            Site.organisation_id == organisation_id
        )

    if period_year:
        query = query.filter(ActivityRecord.period_year == period_year)

    if period_month:
        query = query.filter(ActivityRecord.period_month == period_month)

    if scope:
        query = query.filter(ActivityRecord.scope == scope)

    records = query.all()

    # ── Run calculations ───────────────────────────────────────────────────────
    results = {
        "total": len(records),
        "success": 0,
        "failed": 0,
        "errors": [],
    }

    for record in records:
        try:
            calculate(db=db, activity_record=record, gwp_version=gwp_version)
            results["success"] += 1
        except CalculationError as e:
            results["failed"] += 1
            results["errors"].append(str(e))
            log.error(
                "calculation_failed",
                activity_record_id=str(record.id),
                error=str(e),
            )

    log.info(
        "batch_calculation_complete",
        **{k: v for k, v in results.items() if k != "errors"},
    )

    return results


def _update_emission_record(
    record: EmissionRecord,
    gas_kg: dict,
    gas_co2e: dict,
    total_co2e_kg: float,
    total_co2e_tonnes: float,
    factor_id: uuid.UUID,
    gwp_version: GWPVersion,
    fallback_used: bool,
) -> None:
    """
    Updates an existing EmissionRecord in place.
    Called when a recalculation is triggered (e.g. GWP version change).
    """
    record.emission_factor_id = factor_id
    record.co2_kg = gas_kg["co2"]
    record.ch4_kg = gas_kg["ch4"]
    record.n2o_kg = gas_kg["n2o"]
    record.hfc_kg = gas_kg["hfc"]
    record.pfc_kg = gas_kg["pfc"]
    record.sf6_kg = gas_kg["sf6"]
    record.nf3_kg = gas_kg["nf3"]
    record.co2_co2e = gas_co2e["co2"]
    record.ch4_co2e = gas_co2e["ch4"]
    record.n2o_co2e = gas_co2e["n2o"]
    record.hfc_co2e = gas_co2e["hfc"]
    record.pfc_co2e = gas_co2e["pfc"]
    record.sf6_co2e = gas_co2e["sf6"]
    record.nf3_co2e = gas_co2e["nf3"]
    record.total_co2e_kg = total_co2e_kg
    record.total_co2e_tonnes = total_co2e_tonnes
    record.gwp_version = gwp_version
    record.factor_fallback_used = fallback_used
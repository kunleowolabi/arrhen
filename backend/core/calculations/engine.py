"""
Calculation Engine

Core logic for converting activity records into emission records.

For each ActivityRecord:
1. Validate quantity
2. Select the appropriate emission factor (with regional fallback)
3. Multiply quantity by each gas factor to get raw kg per gas
4. Multiply each gas kg by its GWP to get CO2e per gas
5. Sum all gas CO2e to get total CO2e
6. Write EmissionRecord to database
7. Update ActivityRecord status to "calculated"

Batch calculations flush per record but commit once at the end.
Failed records are marked with status=error and logged — they do
not crash the batch or prevent other records from being processed.

Usage:
    from backend.core.calculations.engine import calculate, calculate_batch

    # Single record
    emission_record = calculate(db, activity_record, GWPVersion.AR6)

    # All pending records for an organisation
    results = calculate_batch(
        db=db,
        organisation_id=org_id,
        gwp_version=GWPVersion.AR6,
    )
"""

from datetime import date
from sqlalchemy.orm import Session
from backend.models import ActivityRecord, EmissionRecord, EmissionFactor, GWPVersion
from backend.models.enums import DataStatus, ScopeType
from backend.core.calculations.gwp import get_gas_gwp, GAS_KEYS
from backend.core.calculations.factor_selector import (
    select_factor,
    FactorNotFoundError,
)
from backend.models.enums import Scope2Method
import uuid
import structlog

log = structlog.get_logger()


class CalculationError(Exception):
    """Raised when a calculation cannot be completed."""
    pass


def _compute_and_write(
    db: Session,
    activity_record: ActivityRecord,
    factor,
    gwp_version: GWPVersion,
    fallback_used: bool,
) -> EmissionRecord:
    """
    Shared compute-and-persist function.
    Called by both the standard engine and the Scope 2 market-based handler.

    Takes a resolved emission factor and writes the EmissionRecord.
    Flushes to the session but does NOT commit — the caller owns the commit.
    """
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

    # Per-compound GWP resolution for HFC/PFC
    # compound_fallback tracks if aggregate GWP was used instead of
    # a per-compound value — merged with factor_fallback_used on the record
    gas_co2e = {}
    compound_fallback = False
    fuel = activity_record.fuel_or_material
    for gas in GAS_KEYS:
        gwp_value, used_aggregate = get_gas_gwp(gas, gwp_version, fuel)
        gas_co2e[gas] = gas_kg[gas] * gwp_value
        if used_aggregate:
            compound_fallback = True

    # Either factor OR compound fallback triggers the flag
    effective_fallback = fallback_used or compound_fallback

    total_co2e_kg = sum(gas_co2e.values())
    total_co2e_tonnes = total_co2e_kg / 1000

    existing = db.query(EmissionRecord).filter_by(
        activity_record_id=activity_record.id
    ).first()

    if existing:
        existing.emission_factor_id = factor.id
        existing.co2_kg = gas_kg["co2"]
        existing.ch4_kg = gas_kg["ch4"]
        existing.n2o_kg = gas_kg["n2o"]
        existing.hfc_kg = gas_kg["hfc"]
        existing.pfc_kg = gas_kg["pfc"]
        existing.sf6_kg = gas_kg["sf6"]
        existing.nf3_kg = gas_kg["nf3"]
        existing.co2_co2e = gas_co2e["co2"]
        existing.ch4_co2e = gas_co2e["ch4"]
        existing.n2o_co2e = gas_co2e["n2o"]
        existing.hfc_co2e = gas_co2e["hfc"]
        existing.pfc_co2e = gas_co2e["pfc"]
        existing.sf6_co2e = gas_co2e["sf6"]
        existing.nf3_co2e = gas_co2e["nf3"]
        existing.total_co2e_kg = total_co2e_kg
        existing.total_co2e_tonnes = total_co2e_tonnes
        existing.gwp_version = gwp_version
        existing.factor_fallback_used = effective_fallback
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
            factor_fallback_used=effective_fallback,
        )
        db.add(emission_record)

    activity_record.status = DataStatus.calculated
    db.flush()
    return emission_record


def calculate(
    db: Session,
    activity_record: ActivityRecord,
    gwp_version: GWPVersion,
    factor_cache: dict | None = None,
) -> EmissionRecord:
    """
    Calculates emissions for a single ActivityRecord.
    Resolves factor, delegates to _compute_and_write.
    Does NOT commit — caller owns the transaction.

    factor_cache: optional pre-loaded {(activity_type, fuel, region): factor}
    index (see calculate_batch). When provided and a matching key exists,
    skips the DB query in select_factor(). Falls back to select_factor()
    on a cache miss so single-record calls (factor_cache=None) are unaffected.
    """

    # ── Validate quantity ──────────────────────────────────────────────────────
    if activity_record.quantity is None:
        raise CalculationError(
            f"ActivityRecord {activity_record.id} has no quantity value."
        )
    if activity_record.quantity <= 0:
        raise CalculationError(
            f"ActivityRecord {activity_record.id} has invalid quantity "
            f"{activity_record.quantity} — must be greater than zero."
        )

    # ── Resolve region from site ───────────────────────────────────────────────
    site = activity_record.site
    region = site.region if site else None

    # ── Determine reference date ───────────────────────────────────────────────
    if activity_record.period_month:
        reference_date = date(
            activity_record.period_year,
            activity_record.period_month,
            1,
        )
    else:
        reference_date = date(activity_record.period_year, 1, 1)

    # ── Select emission factor — cache hit avoids a DB round trip ─────────────
    factor = None
    fallback_used = False

    if factor_cache is not None:
        cache_key = (
            activity_record.ghg_category,
            activity_record.fuel_or_material,
            region,
        )
        cached = factor_cache.get(cache_key)
        if cached is not None:
            factor = cached
        else:
            # Region-specific miss — try global-default key before falling
            # back to a full DB lookup, since the batch cache indexes both
            global_key = (activity_record.ghg_category, activity_record.fuel_or_material, None)
            cached = factor_cache.get(global_key)
            if cached is not None:
                factor = cached
                fallback_used = True

    if factor is None:
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

    emission_record = _compute_and_write(
        db=db,
        activity_record=activity_record,
        factor=factor,
        gwp_version=gwp_version,
        fallback_used=fallback_used,
    )

    log.info(
        "emission_calculated",
        activity_record_id=str(activity_record.id),
        total_co2e_tonnes=round(emission_record.total_co2e_tonnes, 4),
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
    Runs calculations for multiple ActivityRecords matching filters.
    At least one filter must be provided.

    Batch behaviour:
    - Each record is calculated and flushed individually
    - A single commit is issued at the end of the batch
    - If a record fails, it is marked status=error with a reason
      and the batch continues — partial failure does not abort
    - Only the final commit can fail (e.g. DB connection loss)
      in which case no records from this batch are persisted

    Returns summary dict with counts and any error messages.
    """
    if not any([site_id, organisation_id, period_year]):
        raise CalculationError(
            "At least one of site_id, organisation_id, or period_year "
            "must be provided for batch calculation."
        )

    # ── Pre-load emission factors for the batch ───────────────────────────────
    # Fetch all factors once and resolve in memory — avoids N queries per batch
    all_factors = db.query(EmissionFactor).filter(
        (EmissionFactor.valid_to == None) |  # noqa: E711
        (EmissionFactor.valid_to >= date.today())
    ).all()

    # Index by (activity_type, fuel_or_material, region)
    # region=None = global default
    factor_index: dict = {}
    for f in all_factors:
        key = (f.activity_type, f.fuel_or_material, f.region)
        # Keep most recent valid_from if duplicates exist
        if key not in factor_index or f.valid_from > factor_index[key].valid_from:
            factor_index[key] = f

    # ── Build query ────────────────────────────────────────────────────────────
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

    results = {
        "total": len(records),
        "success": 0,
        "failed": 0,
        "errors": [],
    }

    # ── Process each record — flush per record, commit once ────────────────────
    for record in records:
        try:
            # Scope 2 records dispatch on method — market-based needs its own
            # factor resolution path (no location fallback allowed)
            if (
                record.scope == ScopeType.scope_2
                and record.scope_2_method == Scope2Method.market_based
            ):
                from backend.core.calculations.scope2_handler import calculate_scope2
                calculate_scope2(db=db, activity_record=record, gwp_version=gwp_version)
            else:
                calculate(
                    db=db,
                    activity_record=record,
                    gwp_version=gwp_version,
                    factor_cache=factor_index,
                )
            results["success"] += 1
        except (CalculationError, Exception) as e:
            results["failed"] += 1
            error_msg = str(e)
            results["errors"].append(error_msg)
            # Mark record as error so it is visible in Flags & Quarantine
            record.status = DataStatus.quarantined
            record.flag_reason = f"Calculation error: {error_msg}"
            db.flush()
            log.error(
                "calculation_failed",
                activity_record_id=str(record.id),
                error=error_msg,
            )

    # ── Single commit for the entire batch ─────────────────────────────────────
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        log.error("batch_commit_failed", error=str(e))
        raise CalculationError(
            f"Batch commit failed — no records were saved: {e}"
        )

    log.info(
        "batch_calculation_complete",
        **{k: v for k, v in results.items() if k != "errors"},
    )

    return results

"""
Emission Factor Selector

Finds the most appropriate emission factor for a given activity record.

Selection priority:
1. Region-specific factor matching activity_type, fuel_or_material, and region
2. Global default factor matching activity_type and fuel_or_material (region=None)
3. If only global found, sets factor_fallback_used=True on the emission record

If no factor is found at all, raises FactorNotFoundError.

Usage:
    from backend.core.calculations.factor_selector import select_factor

    factor, fallback_used = select_factor(
        db=db,
        activity_type="stationary_combustion",
        fuel_or_material="diesel",
        region="NG",
        reference_date=date(2024, 1, 1),
    )
"""

from datetime import date
from sqlalchemy.orm import Session
from backend.models.emission import EmissionFactor


class FactorNotFoundError(Exception):
    """
    Raised when no emission factor can be found for a given
    activity type and fuel combination.
    """
    pass


def select_factor(
    db: Session,
    activity_type: str,
    fuel_or_material: str,
    region: str | None,
    reference_date: date,
) -> tuple[EmissionFactor, bool]:
    """
    Selects the best available emission factor for a given activity.

    Args:
        db:                 SQLAlchemy database session
        activity_type:      e.g. "stationary_combustion", "purchased_electricity"
        fuel_or_material:   e.g. "diesel", "grid_electricity", "HFC-410A"
        region:             ISO country code e.g. "NG", or None for global
        reference_date:     The date the activity occurred — used to find
                            a factor valid at that point in time

    Returns:
        Tuple of (EmissionFactor, fallback_used)
        fallback_used=True means a global default was used instead of
        a region-specific factor

    Raises:
        FactorNotFoundError if no matching factor exists at all
    """

    # ── Step 1: Try region-specific factor first ──────────────────────────────
    if region:
        regional_factor = _query_factor(
            db=db,
            activity_type=activity_type,
            fuel_or_material=fuel_or_material,
            region=region,
            reference_date=reference_date,
        )
        if regional_factor:
            return regional_factor, False

    # ── Step 2: Fall back to global default ───────────────────────────────────
    global_factor = _query_factor(
        db=db,
        activity_type=activity_type,
        fuel_or_material=fuel_or_material,
        region=None,
        reference_date=reference_date,
    )

    if global_factor:
        fallback_used = region is not None
        # fallback_used=True only if we wanted regional but had to use global
        # fallback_used=False if region was None to begin with
        return global_factor, fallback_used

    # ── Step 3: No factor found at all ────────────────────────────────────────
    raise FactorNotFoundError(
        f"No emission factor found for: "
        f"activity_type='{activity_type}', "
        f"fuel_or_material='{fuel_or_material}', "
        f"region='{region}', "
        f"date='{reference_date}'. "
        f"Add a matching factor to the emission_factors table."
    )


def _query_factor(
    db: Session,
    activity_type: str,
    fuel_or_material: str,
    region: str | None,
    reference_date: date,
) -> EmissionFactor | None:
    """
    Internal query — finds a single emission factor matching all criteria.
    Returns None if not found.

    A factor is valid if:
    - valid_from <= reference_date
    - valid_to is None (currently active) OR valid_to >= reference_date
    """
    query = db.query(EmissionFactor).filter(
        EmissionFactor.activity_type == activity_type,
        EmissionFactor.fuel_or_material == fuel_or_material,
        EmissionFactor.region == region,
        EmissionFactor.valid_from <= reference_date,
    ).filter(
        # valid_to is None (still active) OR valid_to >= reference_date
        (EmissionFactor.valid_to == None) |  # noqa: E711
        (EmissionFactor.valid_to >= reference_date)
    ).order_by(
        EmissionFactor.valid_from.desc()
        # most recent factor first if multiple versions exist
    ).first()

    return query


def list_available_factors(
    db: Session,
    activity_type: str | None = None,
    region: str | None = None,
) -> list[EmissionFactor]:
    """
    Returns all available emission factors, optionally filtered.
    Used by the API to power the emission factor browser in the frontend.

    Args:
        db:             SQLAlchemy session
        activity_type:  Optional filter e.g. "stationary_combustion"
        region:         Optional filter e.g. "NG"

    Returns:
        List of EmissionFactor objects
    """
    query = db.query(EmissionFactor)

    if activity_type:
        query = query.filter(EmissionFactor.activity_type == activity_type)
    if region is not None:
        query = query.filter(EmissionFactor.region == region)

    return query.order_by(
        EmissionFactor.activity_type,
        EmissionFactor.fuel_or_material,
        EmissionFactor.valid_from.desc()
    ).all()
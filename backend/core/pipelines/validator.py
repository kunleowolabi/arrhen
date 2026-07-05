"""
Pipeline Validator

Shared validation logic used by all data ingestion pipelines.
Every row of incoming data passes through this validator before
being written to the database as an ActivityRecord.

Validation checks:
1. Required fields present
2. Correct data types
3. Valid enum values (scope, ghg_category, fuel_or_material, unit)
4. Quantity is positive
5. Period year is plausible
6. Period month is valid (1-12) if provided

Returns a ValidationResult for each row — either valid with a
cleaned data dict, or invalid with a list of error reasons.

Usage:
    from backend.core.pipelines.validator import validate_row

    result = validate_row(row_dict, valid_sites)
    if result.is_valid:
        # use result.cleaned_data
    else:
        # use result.errors
"""

from dataclasses import dataclass, field
from backend.models.enums import ScopeType, Scope2Method, DataStatus
import structlog

log = structlog.get_logger()

# Valid values for controlled fields
VALID_SCOPES = {s.value for s in ScopeType}

VALID_GHG_CATEGORIES = {
    "stationary_combustion",
    "mobile_combustion",
    "company_vehicles",
    "fugitive_emissions",
    "purchased_electricity",
    "purchased_heat_steam",
    "purchased_cooling",
    "purchased_goods_services",
    "capital_goods",
    "fuel_energy_activities",
    "upstream_transportation",
    "waste_operations",
    "business_travel",
    "employee_commuting",
    "upstream_leased_assets",
    "downstream_transportation",
    "processing_sold_products",
    "use_of_sold_products",
    "end_of_life_treatment",
    "downstream_leased_assets",
    "franchises",
    "investments",
}

VALID_UNITS = {
    "litre",
    "litres",
    "kWh",
    "kwh",
    "km",
    "kg",
    "tonne",
    "tonnes",
    "cubic_metre",
    "cubic_metres",
    "passenger_km",
    "m3",
    "MWh",
    "mwh",
}

# Normalise unit aliases to canonical forms
UNIT_NORMALISATION = {
    "litres": "litre",
    "kwh": "kWh",
    "mwh": "MWh",
    "cubic_metres": "cubic_metre",
    "m3": "cubic_metre",
    "tonnes": "tonne",
}

REQUIRED_FIELDS = [
    "site_code",
    "scope",
    "ghg_category",
    "fuel_or_material",
    "quantity",
    "unit",
    "period_year",
]

MIN_YEAR = 1990
MAX_YEAR = 2100


# Characters that trigger formula injection in spreadsheet applications
CSV_INJECTION_CHARS = ('=', '+', '-', '@', chr(9), chr(13))


def _sanitise_field(value: str) -> str:
    """
    Strips leading characters that could trigger CSV/formula injection
    in spreadsheet applications. Applied to all free-text fields.
    """
    if not isinstance(value, str):
        return value
    value = value.strip()
    while value and value[0] in CSV_INJECTION_CHARS:
        value = value[1:].strip()
    return value


@dataclass
class ValidationResult:
    """Result of validating a single data row."""
    is_valid: bool
    cleaned_data: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)


def validate_row(
    row: dict,
    valid_site_codes: set[str],
) -> ValidationResult:
    """
    Validates a single row of incoming activity data.

    Args:
        row:              Raw row dictionary from CSV or API
        valid_site_codes: Set of site codes belonging to the organisation
                          Used to verify the site_code in the row is real

    Returns:
        ValidationResult with is_valid, cleaned_data, errors, warnings
    """
    errors = []
    warnings = []
    cleaned = {}

    # ── 1. Required fields ────────────────────────────────────────────────────
    for field_name in REQUIRED_FIELDS:
        value = row.get(field_name)
        if value is None or str(value).strip() == "":
            errors.append(f"Missing required field: '{field_name}'")

    if errors:
        return ValidationResult(is_valid=False, errors=errors)

    # ── 2. Site code ──────────────────────────────────────────────────────────
    site_code = str(row["site_code"]).strip().upper()
    if site_code not in valid_site_codes:
        errors.append(
            f"Unknown site_code '{site_code}'. "
            f"Valid codes: {sorted(valid_site_codes)}"
        )
    else:
        cleaned["site_code"] = site_code

    # ── 3. Scope ──────────────────────────────────────────────────────────────
    scope_raw = str(row["scope"]).strip().lower()
    # Accept shorthand: "1" → "scope_1", "scope1" → "scope_1"
    scope_normalised = _normalise_scope(scope_raw)
    if scope_normalised not in VALID_SCOPES:
        errors.append(
            f"Invalid scope '{row['scope']}'. "
            f"Valid values: 1, 2, 3, scope_1, scope_2, scope_3"
        )
    else:
        cleaned["scope"] = scope_normalised

    # ── 4. GHG Category ───────────────────────────────────────────────────────
    ghg_category = str(row["ghg_category"]).strip().lower()
    if ghg_category not in VALID_GHG_CATEGORIES:
        errors.append(
            f"Invalid ghg_category '{row['ghg_category']}'. "
            f"See docs/data_dictionary.md for valid categories."
        )
    else:
        cleaned["ghg_category"] = ghg_category

    # ── 5. Fuel or material ───────────────────────────────────────────────────
    fuel = str(row["fuel_or_material"]).strip()
    if not fuel:
        errors.append("fuel_or_material cannot be empty")
    else:
        cleaned["fuel_or_material"] = fuel

    # ── 6. Quantity ───────────────────────────────────────────────────────────
    try:
        quantity = float(row["quantity"])
        if quantity <= 0:
            errors.append(
                f"quantity must be positive, got {quantity}"
            )
        else:
            cleaned["quantity"] = quantity
    except (ValueError, TypeError):
        errors.append(
            f"quantity must be a number, got '{row['quantity']}'"
        )

    # ── 7. Unit ───────────────────────────────────────────────────────────────
    unit_raw = str(row["unit"]).strip()
    unit_lower = unit_raw.lower()
    unit_normalised = UNIT_NORMALISATION.get(unit_lower, unit_raw)
    if unit_normalised not in VALID_UNITS and unit_raw not in VALID_UNITS:
        errors.append(
            f"Invalid unit '{unit_raw}'. "
            f"Valid units: {sorted(VALID_UNITS)}"
        )
    else:
        cleaned["unit"] = unit_normalised

    # ── 8. Period year ────────────────────────────────────────────────────────
    try:
        period_year = int(row["period_year"])
        if not (MIN_YEAR <= period_year <= MAX_YEAR):
            errors.append(
                f"period_year {period_year} is outside valid range "
                f"({MIN_YEAR}–{MAX_YEAR})"
            )
        else:
            cleaned["period_year"] = period_year
    except (ValueError, TypeError):
        errors.append(
            f"period_year must be an integer, got '{row['period_year']}'"
        )

    # ── 9. Period month (optional) ────────────────────────────────────────────
    month_raw = row.get("period_month")
    if month_raw is not None and str(month_raw).strip() != "":
        try:
            period_month = int(month_raw)
            if not (1 <= period_month <= 12):
                errors.append(
                    f"period_month must be 1–12, got {period_month}"
                )
            else:
                cleaned["period_month"] = period_month
        except (ValueError, TypeError):
            errors.append(
                f"period_month must be an integer 1–12, got '{month_raw}'"
            )
    else:
        cleaned["period_month"] = None

    # ── 10. Scope 2 method (optional) ─────────────────────────────────────────
    scope_2_method_raw = row.get("scope_2_method")
    if scope_2_method_raw and str(scope_2_method_raw).strip():
        method = str(scope_2_method_raw).strip().lower()
        valid_methods = {m.value for m in Scope2Method}
        if method not in valid_methods:
            warnings.append(
                f"Invalid scope_2_method '{scope_2_method_raw}' — "
                f"defaulting to location_based. "
                f"Valid: {valid_methods}"
            )
            cleaned["scope_2_method"] = Scope2Method.location_based.value
        else:
            cleaned["scope_2_method"] = method
    else:
        cleaned["scope_2_method"] = None

    # ── 11. Optional fields ───────────────────────────────────────────────────
    cleaned["activity_description"] = _sanitise_field(
        str(row.get("activity_description", "") or "")
    ) or None

    cleaned["supplier_name"] = _sanitise_field(
        str(row.get("supplier_name", "") or "")
    ) or None

    supplier_tier_raw = row.get("supplier_tier")
    if supplier_tier_raw is not None and str(supplier_tier_raw).strip():
        try:
            cleaned["supplier_tier"] = int(supplier_tier_raw)
        except (ValueError, TypeError):
            warnings.append(
                f"supplier_tier must be an integer, got '{supplier_tier_raw}' — ignored"
            )
            cleaned["supplier_tier"] = None
    else:
        cleaned["supplier_tier"] = None

    is_valid = len(errors) == 0
    return ValidationResult(
        is_valid=is_valid,
        cleaned_data=cleaned if is_valid else {},
        errors=errors,
        warnings=warnings,
    )


def check_duplicate(
    cleaned_row: dict,
    existing_keys: set[tuple],
) -> bool:
    """
    Checks if a validated row duplicates an already-seen record
    within the current upload batch or in existing database records.

    A duplicate is defined as same:
    site_code + scope + ghg_category + fuel_or_material + period_year + period_month

    Args:
        cleaned_row:   Validated and cleaned row dict
        existing_keys: Set of tuples representing already-seen records

    Returns:
        True if duplicate, False if new
    """
    key = (
        cleaned_row.get("site_code"),
        cleaned_row.get("scope"),
        cleaned_row.get("ghg_category"),
        cleaned_row.get("fuel_or_material"),
        cleaned_row.get("period_year"),
        cleaned_row.get("period_month"),
    )
    return key in existing_keys


def _normalise_scope(raw: str) -> str:
    """
    Normalises various scope input formats to the canonical enum value.
    Accepts: "1", "2", "3", "scope1", "scope_1", "Scope 1" etc.
    """
    cleaned = raw.strip().lower().replace(" ", "_")
    mapping = {
        "1": "scope_1",
        "2": "scope_2",
        "3": "scope_3",
        "scope1": "scope_1",
        "scope2": "scope_2",
        "scope3": "scope_3",
        "scope_1": "scope_1",
        "scope_2": "scope_2",
        "scope_3": "scope_3",
    }
    return mapping.get(cleaned, cleaned)
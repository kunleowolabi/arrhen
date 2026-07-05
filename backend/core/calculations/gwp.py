"""
GWP (Global Warming Potential) constants for AR5 and AR6 (GWP100).

Source:
- AR5: IPCC Fifth Assessment Report (2013)
- AR6: IPCC Sixth Assessment Report (2021)

All values are GWP100 — 100-year warming potential relative to CO2.
CO2 is always 1.0 by definition.

Usage:
    from backend.core.calculations.gwp import get_gwp, get_gas_gwp
    from backend.models.enums import GWPVersion

    gwp = get_gwp(GWPVersion.AR6)
    ch4_co2e = ch4_kg * get_gas_gwp("ch4", GWPVersion.AR6)

Note: get_gas_gwp() accepts gas keys: co2, ch4, n2o, hfc, pfc, sf6, nf3
      For compound-specific GWP (e.g. hfc_134a), use GWP_AR6 directly.
      HFC and PFC aggregate keys use representative compounds as fallback
      and are flagged when used — see get_gas_gwp() docstring.
"""

from backend.models.enums import GWPVersion

# ── AR5 GWP100 values ─────────────────────────────────────────────────────────
GWP_AR5 = {
    "co2":      1.0,
    "ch4":      28.0,
    "n2o":      265.0,
    # HFC compounds
    "hfc_134a": 1300.0,
    "hfc_410a": 2088.0,
    "hfc_32":   677.0,
    "hfc_125":  3170.0,
    "hfc_143a": 4800.0,
    "hfc_152a": 138.0,
    # PFC compounds
    "pfc_14":   6630.0,
    "pfc_116":  11100.0,
    # Other
    "sf6":      23500.0,
    "nf3":      16100.0,
}

# ── AR6 GWP100 values ─────────────────────────────────────────────────────────
GWP_AR6 = {
    "co2":      1.0,
    "ch4":      27.9,
    "n2o":      273.0,
    # HFC compounds
    "hfc_134a": 1526.0,
    "hfc_410a": 2088.0,
    "hfc_32":   771.0,
    "hfc_125":  3740.0,
    "hfc_143a": 5810.0,
    "hfc_152a": 164.0,
    # PFC compounds
    "pfc_14":   7380.0,
    "pfc_116":  12400.0,
    # Other
    "sf6":      25200.0,
    "nf3":      17400.0,
}

GWP_LOOKUP = {
    GWPVersion.AR5: GWP_AR5,
    GWPVersion.AR6: GWP_AR6,
}

# Canonical gas keys used across emission factor columns and emission records
GAS_KEYS = ["co2", "ch4", "n2o", "hfc", "pfc", "sf6", "nf3"]

# Mapping from fuel_or_material values to their specific GWP compound key
# Used for per-compound GWP resolution on HFC and PFC records
COMPOUND_GWP_MAP = {
    # HFCs
    "HFC-134a":  "hfc_134a",
    "HFC-410A":  "hfc_410a",
    "HFC-32":    "hfc_32",
    "HFC-125":   "hfc_125",
    "HFC-143a":  "hfc_143a",
    "HFC-152a":  "hfc_152a",
    # PFCs
    "CF4":       "pfc_14",
    "C2F6":      "pfc_116",
    # SF6 — direct match
    "SF6":       "sf6",
    # NF3 — direct match
    "NF3":       "nf3",
}

# Fallback aggregate keys when compound is unknown
# flagged in emission record as factor_fallback_used=True
AGGREGATE_FALLBACK = {
    "hfc": {
        GWPVersion.AR5: GWP_AR5["hfc_410a"],
        GWPVersion.AR6: GWP_AR6["hfc_410a"],
    },
    "pfc": {
        GWPVersion.AR5: GWP_AR5["pfc_14"],
        GWPVersion.AR6: GWP_AR6["pfc_14"],
    },
}


def get_gwp(version: GWPVersion) -> dict:
    """Returns the full GWP dictionary for a given version."""
    return GWP_LOOKUP[version]


def get_gas_gwp(
    gas: str,
    version: GWPVersion,
    fuel_or_material: str | None = None,
) -> tuple[float, bool]:
    """
    Returns the GWP100 value for a specific gas under a given version.

    For HFC and PFC gases, attempts per-compound resolution using
    fuel_or_material to look up the specific compound GWP.
    Falls back to aggregate representative compound if not found,
    and signals this via the returned fallback flag.

    Args:
        gas:              one of the GAS_KEYS e.g. "hfc", "ch4"
        version:          GWPVersion.AR5 or GWPVersion.AR6
        fuel_or_material: the fuel/material string from the activity record
                          used to resolve per-compound GWP for HFCs/PFCs

    Returns:
        (gwp_value, compound_fallback_used)
        compound_fallback_used=True means aggregate was used instead
        of a per-compound value — caller should flag this on the record

    Raises:
        ValueError if gas key is not recognised
    """
    gwp_dict = get_gwp(version)

    # Direct lookup for non-aggregate gases
    if gas not in ("hfc", "pfc"):
        if gas not in gwp_dict:
            raise ValueError(
                f"Gas '{gas}' not found in GWP table for version {version}. "
                f"Valid keys: {list(gwp_dict.keys())}"
            )
        return gwp_dict[gas], False

    # Per-compound resolution for HFC and PFC
    if fuel_or_material and fuel_or_material in COMPOUND_GWP_MAP:
        compound_key = COMPOUND_GWP_MAP[fuel_or_material]
        if compound_key in gwp_dict:
            return gwp_dict[compound_key], False

    # Fallback to aggregate representative compound
    if gas in AGGREGATE_FALLBACK:
        return AGGREGATE_FALLBACK[gas][version], True

    raise ValueError(
        f"Gas '{gas}' could not be resolved for version {version}. "
        f"fuel_or_material='{fuel_or_material}'"
    )

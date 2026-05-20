"""
GWP (Global Warming Potential) constants for AR5 and AR6 (GWP100).

Source:
- AR5: IPCC Fifth Assessment Report (2013)
- AR6: IPCC Sixth Assessment Report (2021)

All values are GWP100 — 100-year warming potential relative to CO2.
CO2 is always 1.0 by definition.

Usage:
    from backend.core.calculations.gwp import get_gwp

    gwp = get_gwp("AR6")
    ch4_co2e = ch4_kg * gwp["ch4"]
"""

from backend.models.emission import GWPVersion

# AR5 GWP100 values (IPCC Fifth Assessment Report, 2013)
GWP_AR5 = {
    "co2":  1.0,
    "ch4":  28.0,
    "n2o":  265.0,
    "hfc_134a": 1300.0,
    "hfc_410a": 2088.0,
    "hfc_32":   677.0,
    "pfc_14":   6630.0,
    "pfc_116":  11100.0,
    "sf6":  23500.0,
    "nf3":  16100.0,
}

# AR6 GWP100 values (IPCC Sixth Assessment Report, 2021)
GWP_AR6 = {
    "co2":  1.0,
    "ch4":  27.9,
    "n2o":  273.0,
    "hfc_134a": 1526.0,
    "hfc_410a": 2088.0,
    "hfc_32":   771.0,
    "pfc_14":   7380.0,
    "pfc_116":  12400.0,
    "sf6":  25200.0,
    "nf3":  17400.0,
}

# Maps the enum value to the correct constants dictionary
GWP_LOOKUP = {
    GWPVersion.AR5: GWP_AR5,
    GWPVersion.AR6: GWP_AR6,
}

# These are the gas keys that map directly to emission factor columns
# and emission record columns throughout the platform
GAS_KEYS = ["co2", "ch4", "n2o", "hfc", "pfc", "sf6", "nf3"]

# GWP values to use for aggregate gases (HFC, PFC)
# where we store a combined factor rather than per-compound
# HFC-410A is the most common refrigerant in our factor library
AGGREGATE_GWP = {
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
    """
    Returns the full GWP dictionary for a given version.

    Args:
        version: GWPVersion.AR5 or GWPVersion.AR6

    Returns:
        Dictionary of gas keys to GWP100 values
    """
    return GWP_LOOKUP[version]


def get_gas_gwp(gas: str, version: GWPVersion) -> float:
    """
    Returns the GWP100 value for a specific gas under a given version.
    Handles aggregate gases (hfc, pfc) using representative compounds.

    Args:
        gas: one of "co2", "ch4", "n2o", "hfc", "pfc", "sf6", "nf3"
        version: GWPVersion.AR5 or GWPVersion.AR6

    Returns:
        GWP100 float value

    Raises:
        ValueError if gas key is not recognised
    """
    if gas in ("hfc", "pfc"):
        return AGGREGATE_GWP[gas][version]

    gwp_dict = get_gwp(version)
    key = gas if gas in gwp_dict else None

    if key is None:
        raise ValueError(
            f"Gas '{gas}' not found in GWP table for version {version}. "
            f"Valid keys: {list(gwp_dict.keys())}"
        )

    return gwp_dict[key]
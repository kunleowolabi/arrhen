"""
Tests for GWP constants and per-compound resolution.
"""
import pytest
from backend.core.calculations.gwp import get_gas_gwp, GWP_AR6, GWP_AR5
from backend.models.enums import GWPVersion


def test_co2_gwp_is_one():
    gwp, fallback = get_gas_gwp("co2", GWPVersion.AR6)
    assert gwp == 1.0
    assert fallback is False


def test_ch4_ar6():
    gwp, fallback = get_gas_gwp("ch4", GWPVersion.AR6)
    assert gwp == 27.9
    assert fallback is False


def test_ch4_ar5():
    gwp, fallback = get_gas_gwp("ch4", GWPVersion.AR5)
    assert gwp == 28.0
    assert fallback is False


def test_hfc_410a_per_compound():
    """HFC-410A should resolve to its specific GWP, not aggregate."""
    gwp, fallback = get_gas_gwp("hfc", GWPVersion.AR6, "HFC-410A")
    assert gwp == 2088.0
    assert fallback is False


def test_hfc_134a_per_compound():
    """HFC-134a has a different GWP than HFC-410A."""
    gwp, fallback = get_gas_gwp("hfc", GWPVersion.AR6, "HFC-134a")
    assert gwp == 1526.0
    assert fallback is False


def test_hfc_unknown_compound_uses_aggregate():
    """Unknown HFC compound falls back to aggregate and flags it."""
    gwp, fallback = get_gas_gwp("hfc", GWPVersion.AR6, "HFC-unknown")
    assert gwp == 2088.0  # HFC-410A aggregate
    assert fallback is True


def test_sf6_ar6():
    gwp, fallback = get_gas_gwp("sf6", GWPVersion.AR6)
    assert gwp == 25200.0
    assert fallback is False


def test_invalid_gas_raises():
    with pytest.raises(ValueError):
        get_gas_gwp("xyz", GWPVersion.AR6)

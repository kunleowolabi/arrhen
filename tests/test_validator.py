"""
Tests for the CSV ingestion validator.
"""
import pytest
from backend.core.pipelines.validator import (
    validate_row, check_duplicate, _sanitise_field
)

VALID_SITES = {"LAGOS-HQ", "PHC-FAC", "ABUJA-OPS", "KANO-HUB"}

VALID_ROW = {
    "site_code": "LAGOS-HQ",
    "scope": "1",
    "ghg_category": "stationary_combustion",
    "fuel_or_material": "diesel",
    "quantity": "1000",
    "unit": "litre",
    "period_year": "2024",
    "period_month": "1",
}


def test_valid_row_passes():
    result = validate_row(VALID_ROW, VALID_SITES)
    assert result.is_valid
    assert result.cleaned_data["quantity"] == 1000.0
    assert result.cleaned_data["scope"] == "scope_1"


def test_missing_required_field_fails():
    row = {**VALID_ROW}
    del row["quantity"]
    result = validate_row(row, VALID_SITES)
    assert not result.is_valid
    assert any("quantity" in e for e in result.errors)


def test_invalid_site_fails():
    row = {**VALID_ROW, "site_code": "UNKNOWN-SITE"}
    result = validate_row(row, VALID_SITES)
    assert not result.is_valid


def test_negative_quantity_fails():
    row = {**VALID_ROW, "quantity": "-100"}
    result = validate_row(row, VALID_SITES)
    assert not result.is_valid


def test_invalid_month_fails():
    row = {**VALID_ROW, "period_month": "13"}
    result = validate_row(row, VALID_SITES)
    assert not result.is_valid


def test_scope_normalisation():
    """Accepts '1', 'scope_1', 'Scope 1' etc."""
    for scope_val in ["1", "scope_1", "scope1", "Scope 1"]:
        row = {**VALID_ROW, "scope": scope_val}
        result = validate_row(row, VALID_SITES)
        assert result.is_valid, f"Failed for scope='{scope_val}'"
        assert result.cleaned_data["scope"] == "scope_1"


def test_unit_normalisation():
    row = {**VALID_ROW, "unit": "litres"}
    result = validate_row(row, VALID_SITES)
    assert result.is_valid
    assert result.cleaned_data["unit"] == "litre"


def test_duplicate_detection():
    key1 = ("LAGOS-HQ", "scope_1", "stationary_combustion", "diesel", 2024, 1)
    existing = {key1}
    row = {**VALID_ROW}
    result = validate_row(row, VALID_SITES)
    assert check_duplicate(result.cleaned_data, existing)


def test_csv_injection_sanitised():
    assert _sanitise_field("=CMD") == "CMD"
    assert _sanitise_field("+malicious") == "malicious"
    assert _sanitise_field("normal text") == "normal text"
    assert _sanitise_field("") == ""

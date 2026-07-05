"""
Tests for the emission calculation engine.
Uses the real database connection — requires DATABASE_URL in .env

Run with: python3 -m pytest tests/test_calculations.py -v
"""
import pytest
from datetime import date
from backend.db.database import SessionLocal
from backend.core.calculations.engine import calculate, CalculationError
from backend.models import Organisation, Site, ActivityRecord, DataLineage, EmissionFactor
from backend.models.enums import (
    ScopeType, DataSource, DataStatus, GWPVersion,
    IndustryType, FactorSource,
)
import uuid


@pytest.fixture(scope="function")
def db():
    """Real database session — rolls back after each test."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def test_org(db):
    org = Organisation(
        name=f"Test Org {uuid.uuid4().hex[:6]}",
        industry=IndustryType.energy_utilities,
        country="Nigeria",
    )
    db.add(org)
    db.flush()
    yield org
    db.delete(org)
    db.commit()


@pytest.fixture(scope="function")
def test_site(db, test_org):
    site = Site(
        name="Test Site",
        site_code=f"TEST-{uuid.uuid4().hex[:4].upper()}",
        country="Nigeria",
        region="South West",
        organisation_id=test_org.id,
    )
    db.add(site)
    db.flush()
    yield site


@pytest.fixture(scope="function")
def test_factor(db):
    factor = EmissionFactor(
        activity_type="stationary_combustion",
        fuel_or_material=f"test_fuel_{uuid.uuid4().hex[:6]}",
        region=None,
        co2_factor=2.68839,
        ch4_factor=0.00015,
        n2o_factor=0.00003,
        hfc_factor=0.0,
        pfc_factor=0.0,
        sf6_factor=0.0,
        nf3_factor=0.0,
        unit="litre",
        source=FactorSource.DEFRA,
        version="DEFRA 2023",
        valid_from=date(2023, 1, 1),
    )
    db.add(factor)
    db.flush()
    yield factor


@pytest.fixture(scope="function")
def test_lineage(db):
    lineage = DataLineage(
        source=DataSource.csv_upload,
        filename="test.csv",
    )
    db.add(lineage)
    db.flush()
    yield lineage


def test_diesel_co2e_calculation(db, test_site, test_factor, test_lineage):
    """
    1000 litres × DEFRA 2023 factors (AR6):
    CO2:  1000 × 2.68839           = 2688.39  kg
    CH4:  1000 × 0.00015 × 27.9   = 4.185    kg CO2e
    N2O:  1000 × 0.00003 × 273    = 8.19     kg CO2e
    Total ≈ 2700.765 kg = 2.700765 tCO2e
    """
    record = ActivityRecord(
        site_id=test_site.id,
        data_lineage_id=test_lineage.id,
        scope=ScopeType.scope_1,
        ghg_category="stationary_combustion",
        fuel_or_material=test_factor.fuel_or_material,
        quantity=1000.0,
        unit="litre",
        period_year=2024,
        period_month=1,
        status=DataStatus.validated,
    )
    db.add(record)
    db.flush()

    emission = calculate(db, record, GWPVersion.AR6)
    db.commit()

    assert abs(emission.co2_kg - 2688.39) < 0.01
    assert abs(emission.total_co2e_tonnes - 2.700765) < 0.001
    assert emission.gwp_version == GWPVersion.AR6
    assert record.status == DataStatus.calculated

    # Cleanup
    db.delete(emission)
    db.delete(record)
    db.commit()


def test_zero_quantity_raises(db, test_site, test_lineage):
    record = ActivityRecord(
        site_id=test_site.id,
        data_lineage_id=test_lineage.id,
        scope=ScopeType.scope_1,
        ghg_category="stationary_combustion",
        fuel_or_material="diesel",
        quantity=0.0,
        unit="litre",
        period_year=2024,
        status=DataStatus.validated,
    )
    db.add(record)
    db.flush()

    with pytest.raises(CalculationError, match="invalid quantity"):
        calculate(db, record, GWPVersion.AR6)

    db.delete(record)
    db.commit()



def test_missing_factor_raises(db, test_site, test_lineage):
    record = ActivityRecord(
        site_id=test_site.id,
        data_lineage_id=test_lineage.id,
        scope=ScopeType.scope_1,
        ghg_category="stationary_combustion",
        fuel_or_material="unobtanium_xyz_999",
        quantity=100.0,
        unit="litre",
        period_year=2024,
        status=DataStatus.validated,
    )
    db.add(record)
    db.flush()

    with pytest.raises(CalculationError):
        calculate(db, record, GWPVersion.AR6)

    db.delete(record)
    db.commit()

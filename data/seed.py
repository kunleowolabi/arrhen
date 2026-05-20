"""
Seed script — populates:
1. Emission factor library (DEFRA 2023 + IEA core factors)
2. Sample organisation and sites (Nigerian energy company)
3. Sample activity records across Scopes 1, 2, and 3
4. Sample reduction target

Run from project root with venv active:
    python3 data/seed.py
"""

import sys
import os
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../"))

from backend.db.database import SessionLocal
from backend.models import (
    Organisation, Site, IndustryType,
    EmissionFactor, FactorSource,
    ActivityRecord, DataLineage, ScopeType, DataSource, DataStatus,
    Target, ScopeCoverage, TargetType,
)
from geoalchemy2.elements import WKTElement


# ─── EMISSION FACTORS ─────────────────────────────────────────────────────────

EMISSION_FACTORS = [
    # Stationary combustion — diesel
    {
        "activity_type": "stationary_combustion",
        "fuel_or_material": "diesel",
        "region": None,
        "co2_factor": 2.68839,
        "ch4_factor": 0.00015,
        "n2o_factor": 0.00003,
        "unit": "litre",
        "source": FactorSource.DEFRA,
        "version": "DEFRA 2023",
        "valid_from": date(2023, 1, 1),
        "notes": "Diesel combustion in stationary equipment e.g. generators",
    },
    # Stationary combustion — petrol
    {
        "activity_type": "stationary_combustion",
        "fuel_or_material": "petrol",
        "region": None,
        "co2_factor": 2.31360,
        "ch4_factor": 0.00033,
        "n2o_factor": 0.00003,
        "unit": "litre",
        "source": FactorSource.DEFRA,
        "version": "DEFRA 2023",
        "valid_from": date(2023, 1, 1),
    },
    # Stationary combustion — natural gas
    {
        "activity_type": "stationary_combustion",
        "fuel_or_material": "natural_gas",
        "region": None,
        "co2_factor": 2.04270,
        "ch4_factor": 0.00005,
        "n2o_factor": 0.00001,
        "unit": "cubic_metre",
        "source": FactorSource.DEFRA,
        "version": "DEFRA 2023",
        "valid_from": date(2023, 1, 1),
    },
    # Mobile combustion — diesel
    {
        "activity_type": "company_vehicles",
        "fuel_or_material": "diesel",
        "region": None,
        "co2_factor": 2.68839,
        "ch4_factor": 0.00001,
        "n2o_factor": 0.00012,
        "unit": "litre",
        "source": FactorSource.DEFRA,
        "version": "DEFRA 2023",
        "valid_from": date(2023, 1, 1),
        "notes": "Diesel combustion in company-owned vehicles",
    },
    # Mobile combustion — petrol
    {
        "activity_type": "company_vehicles",
        "fuel_or_material": "petrol",
        "region": None,
        "co2_factor": 2.31360,
        "ch4_factor": 0.00005,
        "n2o_factor": 0.00022,
        "unit": "litre",
        "source": FactorSource.DEFRA,
        "version": "DEFRA 2023",
        "valid_from": date(2023, 1, 1),
    },
    # Purchased electricity — Nigeria grid (IEA)
    {
        "activity_type": "purchased_electricity",
        "fuel_or_material": "grid_electricity",
        "region": "NG",
        "co2_factor": 0.43200,
        "ch4_factor": 0.00001,
        "n2o_factor": 0.000004,
        "unit": "kWh",
        "source": FactorSource.IEA,
        "version": "IEA 2022",
        "valid_from": date(2022, 1, 1),
        "notes": "Nigeria grid emission factor. Used for location-based Scope 2.",
    },
    # Purchased electricity — global default (IEA)
    {
        "activity_type": "purchased_electricity",
        "fuel_or_material": "grid_electricity",
        "region": None,
        "co2_factor": 0.49300,
        "ch4_factor": 0.00001,
        "n2o_factor": 0.000005,
        "unit": "kWh",
        "source": FactorSource.IEA,
        "version": "IEA 2022",
        "valid_from": date(2022, 1, 1),
        "notes": "Global average grid emission factor. Fallback if no regional factor.",
    },
    # Fugitive — HFC-410A (refrigerant)
    {
        "activity_type": "fugitive_emissions",
        "fuel_or_material": "HFC-410A",
        "region": None,
        "co2_factor": 0.0,
        "ch4_factor": 0.0,
        "n2o_factor": 0.0,
        "hfc_factor": 1.0,
        "unit": "kg",
        "source": FactorSource.IPCC,
        "version": "IPCC AR6",
        "valid_from": date(2021, 1, 1),
        "notes": "GWP100 AR6 = 2088. 1kg HFC-410A = 2088 kg CO2e.",
    },
    # Fugitive — SF6
    {
        "activity_type": "fugitive_emissions",
        "fuel_or_material": "SF6",
        "region": None,
        "co2_factor": 0.0,
        "sf6_factor": 1.0,
        "unit": "kg",
        "source": FactorSource.IPCC,
        "version": "IPCC AR6",
        "valid_from": date(2021, 1, 1),
        "notes": "GWP100 AR6 = 25200. 1kg SF6 = 25200 kg CO2e.",
    },
    # Business travel — short haul flight
    {
        "activity_type": "business_travel",
        "fuel_or_material": "flight_short_haul",
        "region": None,
        "co2_factor": 0.25510,
        "ch4_factor": 0.00001,
        "n2o_factor": 0.00001,
        "unit": "passenger_km",
        "source": FactorSource.DEFRA,
        "version": "DEFRA 2023",
        "valid_from": date(2023, 1, 1),
        "notes": "Flights under 3700km e.g. Lagos to Abuja",
    },
    # Business travel — long haul flight
    {
        "activity_type": "business_travel",
        "fuel_or_material": "flight_long_haul",
        "region": None,
        "co2_factor": 0.19510,
        "ch4_factor": 0.000004,
        "n2o_factor": 0.000004,
        "unit": "passenger_km",
        "source": FactorSource.DEFRA,
        "version": "DEFRA 2023",
        "valid_from": date(2023, 1, 1),
        "notes": "Flights over 3700km e.g. Lagos to London",
    },
]


# ─── SAMPLE ORGANISATION ──────────────────────────────────────────────────────

SAMPLE_ORG = {
    "name": "Meridian Energy Nigeria Ltd",
    "industry": IndustryType.energy_utilities,
    "country": "Nigeria",
    "reporting_currency": "NGN",
    "fiscal_year_start_month": 1,
}

SAMPLE_SITES = [
    {
        "name": "Lagos Head Office",
        "site_code": "LAGOS-HQ",
        "region": "South West",
        "country": "Nigeria",
        "address": "Victoria Island, Lagos",
        "latitude": 6.4281,
        "longitude": 3.4219,
    },
    {
        "name": "Abuja Operations Centre",
        "site_code": "ABUJA-OPS",
        "region": "North Central",
        "country": "Nigeria",
        "address": "Central Business District, Abuja",
        "latitude": 9.0579,
        "longitude": 7.4951,
    },
    {
        "name": "Port Harcourt Facility",
        "site_code": "PHC-FAC",
        "region": "South South",
        "country": "Nigeria",
        "address": "Trans Amadi Industrial Layout, Port Harcourt",
        "latitude": 4.8156,
        "longitude": 7.0498,
    },
    {
        "name": "Kano Distribution Hub",
        "site_code": "KANO-HUB",
        "region": "North West",
        "country": "Nigeria",
        "address": "Bompai Industrial Area, Kano",
        "latitude": 12.0022,
        "longitude": 8.5920,
    },
]


# ─── SEED FUNCTIONS ───────────────────────────────────────────────────────────

def seed_emission_factors(db):
    print("\nSeeding emission factors...")
    count = 0
    for factor_data in EMISSION_FACTORS:
        existing = db.query(EmissionFactor).filter_by(
            activity_type=factor_data["activity_type"],
            fuel_or_material=factor_data["fuel_or_material"],
            version=factor_data["version"],
            region=factor_data.get("region"),
        ).first()

        if not existing:
            factor = EmissionFactor(
                activity_type=factor_data["activity_type"],
                fuel_or_material=factor_data["fuel_or_material"],
                region=factor_data.get("region"),
                co2_factor=factor_data.get("co2_factor", 0.0),
                ch4_factor=factor_data.get("ch4_factor", 0.0),
                n2o_factor=factor_data.get("n2o_factor", 0.0),
                hfc_factor=factor_data.get("hfc_factor", 0.0),
                pfc_factor=factor_data.get("pfc_factor", 0.0),
                sf6_factor=factor_data.get("sf6_factor", 0.0),
                nf3_factor=factor_data.get("nf3_factor", 0.0),
                unit=factor_data["unit"],
                source=factor_data["source"],
                version=factor_data["version"],
                valid_from=factor_data["valid_from"],
                valid_to=factor_data.get("valid_to"),
                notes=factor_data.get("notes"),
            )
            db.add(factor)
            count += 1

    db.commit()
    print(f"  ✓ {count} emission factors seeded")


def seed_organisation(db):
    print("\nSeeding sample organisation and sites...")

    existing = db.query(Organisation).filter_by(
        name=SAMPLE_ORG["name"]
    ).first()

    if existing:
        print("  ✓ Organisation already exists — skipping")
        return existing

    org = Organisation(**SAMPLE_ORG)
    db.add(org)
    db.flush()

    for site_data in SAMPLE_SITES:
        lat = site_data["latitude"]
        lon = site_data["longitude"]
        site = Site(
            name=site_data["name"],
            site_code=site_data["site_code"],
            region=site_data["region"],
            country=site_data["country"],
            address=site_data["address"],
            organisation_id=org.id,
            latitude=lat,
            longitude=lon,
            geom=WKTElement(f"POINT({lon} {lat})", srid=4326),
        )
        db.add(site)

    db.commit()
    print(f"  ✓ Organisation '{org.name}' with {len(SAMPLE_SITES)} sites seeded")
    return org


def seed_activity_records(db, org):
    print("\nSeeding sample activity records...")

    sites = db.query(Site).filter_by(organisation_id=org.id).all()
    site_map = {s.site_code: s for s in sites}

    existing = db.query(DataLineage).filter_by(
        filename="sample_seed_data"
    ).first()

    if existing:
        print("  ✓ Activity records already exist — skipping")
        return

    lineage = DataLineage(
        source=DataSource.csv_upload,
        filename="sample_seed_data",
        uploaded_by="system",
        record_count=8,
        valid_count=8,
        quarantine_count=0,
        notes="Initial seed data for development and testing",
    )
    db.add(lineage)
    db.flush()

    records = [
        # Scope 1 — Generator diesel (Lagos)
        ActivityRecord(
            site_id=site_map["LAGOS-HQ"].id,
            data_lineage_id=lineage.id,
            scope=ScopeType.scope_1,
            ghg_category="stationary_combustion",
            fuel_or_material="diesel",
            quantity=12500.0,
            unit="litre",
            period_year=2024,
            period_month=1,
            status=DataStatus.validated,
            activity_description="Main generator fuel consumption",
        ),
        # Scope 1 — Generator diesel (Port Harcourt)
        ActivityRecord(
            site_id=site_map["PHC-FAC"].id,
            data_lineage_id=lineage.id,
            scope=ScopeType.scope_1,
            ghg_category="stationary_combustion",
            fuel_or_material="diesel",
            quantity=28000.0,
            unit="litre",
            period_year=2024,
            period_month=1,
            status=DataStatus.validated,
            activity_description="Facility generator and process equipment",
        ),
        # Scope 1 — Company vehicles (Lagos)
        ActivityRecord(
            site_id=site_map["LAGOS-HQ"].id,
            data_lineage_id=lineage.id,
            scope=ScopeType.scope_1,
            ghg_category="company_vehicles",
            fuel_or_material="diesel",
            quantity=3200.0,
            unit="litre",
            period_year=2024,
            period_month=1,
            status=DataStatus.validated,
            activity_description="Company fleet fuel consumption",
        ),
        # Scope 1 — Fugitive HFC-410A (Port Harcourt)
        ActivityRecord(
            site_id=site_map["PHC-FAC"].id,
            data_lineage_id=lineage.id,
            scope=ScopeType.scope_1,
            ghg_category="fugitive_emissions",
            fuel_or_material="HFC-410A",
            quantity=5.0,
            unit="kg",
            period_year=2024,
            period_month=1,
            status=DataStatus.validated,
            activity_description="Air conditioning refrigerant leak",
        ),
        # Scope 2 — Grid electricity (Lagos)
        ActivityRecord(
            site_id=site_map["LAGOS-HQ"].id,
            data_lineage_id=lineage.id,
            scope=ScopeType.scope_2,
            ghg_category="purchased_electricity",
            fuel_or_material="grid_electricity",
            quantity=45000.0,
            unit="kWh",
            period_year=2024,
            period_month=1,
            status=DataStatus.validated,
            activity_description="Office electricity consumption",
        ),
        # Scope 2 — Grid electricity (Abuja)
        ActivityRecord(
            site_id=site_map["ABUJA-OPS"].id,
            data_lineage_id=lineage.id,
            scope=ScopeType.scope_2,
            ghg_category="purchased_electricity",
            fuel_or_material="grid_electricity",
            quantity=22000.0,
            unit="kWh",
            period_year=2024,
            period_month=1,
            status=DataStatus.validated,
            activity_description="Operations centre electricity consumption",
        ),
        # Scope 3 — Short haul flights (Lagos)
        ActivityRecord(
            site_id=site_map["LAGOS-HQ"].id,
            data_lineage_id=lineage.id,
            scope=ScopeType.scope_3,
            ghg_category="business_travel",
            fuel_or_material="flight_short_haul",
            quantity=8400.0,
            unit="passenger_km",
            period_year=2024,
            period_month=1,
            status=DataStatus.validated,
            activity_description="Domestic business flights Lagos-Abuja",
        ),
        # Scope 3 — Long haul flights (Lagos)
        ActivityRecord(
            site_id=site_map["LAGOS-HQ"].id,
            data_lineage_id=lineage.id,
            scope=ScopeType.scope_3,
            ghg_category="business_travel",
            fuel_or_material="flight_long_haul",
            quantity=15200.0,
            unit="passenger_km",
            period_year=2024,
            period_month=1,
            status=DataStatus.validated,
            activity_description="International business flights Lagos-London",
        ),
    ]

    for record in records:
        db.add(record)

    lineage.record_count = len(records)
    lineage.valid_count = len(records)
    db.commit()
    print(f"  ✓ {len(records)} activity records seeded")


def seed_target(db, org):
    print("\nSeeding reduction target...")

    existing = db.query(Target).filter_by(organisation_id=org.id).first()
    if existing:
        print("  ✓ Target already exists — skipping")
        return

    target = Target(
        organisation_id=org.id,
        name="50% Absolute Reduction by 2030",
        target_type=TargetType.absolute,
        scope_coverage=ScopeCoverage.scope_1_2,
        baseline_year=2023,
        target_year=2030,
        baseline_emissions_tco2e=1850.0,
        target_reduction_pct=50.0,
        target_emissions_tco2e=925.0,
        aligned_to="SBTi 1.5°C",
        notes="Baseline from 2023 annual inventory. Covers all Nigerian operations.",
    )
    db.add(target)
    db.commit()
    print(f"  ✓ Target '{target.name}' seeded")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Starting seed process...")
    db = SessionLocal()
    try:
        seed_emission_factors(db)
        org = seed_organisation(db)
        seed_activity_records(db, org)
        seed_target(db, org)
        print("\n✓ Seed complete\n")
    except Exception as e:
        print(f"\n✗ Seed failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


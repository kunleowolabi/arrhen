"""
KoboToolbox Connector — Arrhen Forms

Handles the three Arrhen-specific KoboToolbox forms:
  Form 1: Daily Site Operations Log    (aNogXjHodg7FY2J4KX5XD8)
  Form 2: Weekly Vehicle Fuel Log      (avMLnVLKT367QmnkUHhADQ)
  Form 3: Monthly Summary              (at3WKHFVYgx6LR22yJySFz)

Each form submission is split into multiple ActivityRecords
based on which fields contain non-zero values.

Usage:
    from backend.core.pipelines.kobo_connector import ArrhenKoboConnector

    connector = ArrhenKoboConnector(api_token="your-token")
    result = connector.import_form(
        db=db,
        form_number=1,
        organisation_id=org_id,
    )
"""

import os
from datetime import datetime, date
from uuid import UUID
from sqlalchemy.orm import Session
import httpx
import structlog

from backend.models import Site, ActivityRecord, DataLineage
from backend.models.enums import (
    DataSource, DataStatus, ScopeType, Scope2Method
)
from backend.core.pipelines.validator import check_duplicate
from backend.core.pipelines.csv_importer import _load_existing_keys

log = structlog.get_logger()

KOBO_BASE_URL = os.getenv("KOBO_BASE_URL", "https://kf.kobotoolbox.org")

FORM_UIDS = {
    1: os.getenv("KOBO_FORM_1_UID", "aNogXjHodg7FY2J4KX5XD8"),
    2: os.getenv("KOBO_FORM_2_UID", "avMLnVLKT367QmnkUHhADQ"),
    3: os.getenv("KOBO_FORM_3_UID", "at3WKHFVYgx6LR22yJySFz"),
}

MONTH_MAP = {
    "January": 1, "February": 2, "March": 3,
    "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9,
    "October": 10, "November": 11, "December": 12,
}


SITE_CODE_MAP = {
    "lagos_hq":  "LAGOS-HQ",
    "abuja_ops": "ABUJA-OPS",
    "phc_fac":   "PHC-FAC",
    "kano_hub":  "KANO-HUB",
}


def _normalise_site(raw: str) -> str:
    """Converts KoboToolbox site value to platform site_code."""
    return SITE_CODE_MAP.get(raw.lower().strip(), raw.upper())


def _flatten(submission: dict) -> dict:
    """
    Flattens KoboToolbox group-prefixed keys.
    'group_abc123/field_name' becomes 'field_name'.
    Top-level keys (no slash) are kept as-is.
    """
    flat = {}
    for key, value in submission.items():
        if '/' in key and not key.startswith('_') and not key.startswith('meta'):
            flat_key = key.split('/')[-1]
        else:
            flat_key = key
        flat[flat_key] = value
    return flat


def _parse_date(date_str: str) -> date | None:
    """Parses KoboToolbox date string YYYY-MM-DD to date object."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _safe_float(value, default=0.0) -> float:
    """Safely converts a value to float."""
    try:
        return float(value or 0)
    except (ValueError, TypeError):
        return default


def _safe_int(value, default=0) -> int:
    """Safely converts a value to int."""
    try:
        return int(value or 0)
    except (ValueError, TypeError):
        return default


def _extract_period_from_date(date_str: str) -> tuple[int, int]:
    """Extracts (year, month) from a YYYY-MM-DD date string."""
    d = _parse_date(date_str)
    if d:
        return d.year, d.month
    # Fallback to submission time
    now = datetime.utcnow()
    return now.year, now.month


def _split_form1(submission: dict) -> list[dict]:
    """
    Form 1: Daily Site Operations Log
    Splits one submission into up to 3 ActivityRecords:
      - Generator diesel (opening_tank - closing_tank)
      - Natural gas (PHC-FAC only)
      - Refrigerant top-up
    """
    submission = _flatten(submission)
    site = _normalise_site(submission.get("site", ""))
    activity_date = submission.get("activity_date", "")
    period_year, period_month = _extract_period_from_date(activity_date)
    description_base = f"Activity date: {activity_date}"

    records = []

    # Diesel consumption = opening - closing
    opening = _safe_float(submission.get("opening_tank"))
    closing = _safe_float(submission.get("closing_tank"))
    diesel_consumed = opening - closing

    if diesel_consumed > 0:
        records.append({
            "site_code": site,
            "scope": "scope_1",
            "ghg_category": "stationary_combustion",
            "fuel_or_material": "diesel",
            "quantity": diesel_consumed,
            "unit": "litre",
            "period_year": period_year,
            "period_month": period_month,
            "activity_description": (
                f"{description_base} | "
                f"Opening: {opening}L Closing: {closing}L"
            ),
        })

    # Natural gas — PHC-FAC only
    nat_gas = _safe_float(submission.get("natural_gas"))
    if nat_gas > 0 and site == "PHC-FAC":
        records.append({
            "site_code": site,
            "scope": "scope_1",
            "ghg_category": "stationary_combustion",
            "fuel_or_material": "natural_gas",
            "quantity": nat_gas,
            "unit": "cubic_metre",
            "period_year": period_year,
            "period_month": period_month,
            "activity_description": f"{description_base} | Natural gas",
        })

    # Refrigerant
    refrig_kg = _safe_float(submission.get("refrigerant_kg"))
    refrig_type = submission.get("refrigerant_type", "HFC-410A")
    if refrig_kg > 0:
        records.append({
            "site_code": site,
            "scope": "scope_1",
            "ghg_category": "fugitive_emissions",
            "fuel_or_material": refrig_type or "HFC-410A",
            "quantity": refrig_kg,
            "unit": "kg",
            "period_year": period_year,
            "period_month": period_month,
            "activity_description": (
                f"{description_base} | Refrigerant top-up"
            ),
        })

    return records


def _split_form2(submission: dict) -> list[dict]:
    """
    Form 2: Weekly Vehicle Fuel Log
    Splits into up to 4 ActivityRecords:
      - Light fleet diesel
      - Light fleet petrol
      - Heavy fleet diesel
      - Distribution diesel
    """
    submission = _flatten(submission)
    site = _normalise_site(submission.get("site", ""))
    week_ending = submission.get("week_ending", "")
    period_year, period_month = _extract_period_from_date(week_ending)
    description_base = f"Week ending: {week_ending}"

    records = []

    light_diesel = _safe_float(submission.get("light_diesel"))
    if light_diesel > 0:
        records.append({
            "site_code": site,
            "scope": "scope_1",
            "ghg_category": "company_vehicles",
            "fuel_or_material": "diesel",
            "quantity": light_diesel,
            "unit": "litre",
            "period_year": period_year,
            "period_month": period_month,
            "activity_description": (
                f"{description_base} | "
                f"Light fleet ({_safe_int(submission.get('light_count'))} vehicles)"
            ),
        })

    light_petrol = _safe_float(submission.get("light_petrol"))
    if light_petrol > 0:
        records.append({
            "site_code": site,
            "scope": "scope_1",
            "ghg_category": "company_vehicles",
            "fuel_or_material": "petrol",
            "quantity": light_petrol,
            "unit": "litre",
            "period_year": period_year,
            "period_month": period_month,
            "activity_description": (
                f"{description_base} | Light fleet petrol"
            ),
        })

    heavy_diesel = _safe_float(submission.get("heavy_diesel"))
    if heavy_diesel > 0:
        records.append({
            "site_code": site,
            "scope": "scope_1",
            "ghg_category": "company_vehicles",
            "fuel_or_material": "diesel",
            "quantity": heavy_diesel,
            "unit": "litre",
            "period_year": period_year,
            "period_month": period_month,
            "activity_description": (
                f"{description_base} | "
                f"Heavy fleet ({_safe_int(submission.get('heavy_count'))} vehicles)"
            ),
        })

    distrib_diesel = _safe_float(submission.get("distribution_diesel"))
    if distrib_diesel > 0:
        records.append({
            "site_code": site,
            "scope": "scope_1",
            "ghg_category": "company_vehicles",
            "fuel_or_material": "diesel",
            "quantity": distrib_diesel,
            "unit": "litre",
            "period_year": period_year,
            "period_month": period_month,
            "activity_description": (
                f"{description_base} | "
                f"Distribution ({_safe_int(submission.get('distribution_count'))} vehicles)"
            ),
        })

    return records


def _split_form3(submission: dict) -> list[dict]:
    """
    Form 3: Monthly Summary — Electricity and Business Travel
    Splits into up to 3 ActivityRecords:
      - Electricity (Scope 2, not PHC-FAC)
      - Domestic flights (Scope 3)
      - International flights (Scope 3)
    """
    submission = _flatten(submission)
    site = _normalise_site(submission.get("site", ""))

    # billing_month may be numeric string "1" or label "January"
    month_raw = submission.get("billing_month", "")
    try:
        period_month = int(month_raw)
    except (ValueError, TypeError):
        period_month = MONTH_MAP.get(month_raw, datetime.utcnow().month)

    period_year = _safe_int(
        submission.get("billing_year"),
        datetime.utcnow().year
    )

    billing_start = submission.get("billing_start", "")
    billing_end = submission.get("billing_end", "")

    records = []

    # Electricity — skip PHC-FAC
    electricity_kwh = _safe_float(submission.get("electricity_kwh"))
    if electricity_kwh > 0 and site != "PHC-FAC":
        scope2_method_raw = submission.get("scope2_method", "location_based")
        records.append({
            "site_code": site,
            "scope": "scope_2",
            "ghg_category": "purchased_electricity",
            "fuel_or_material": "grid_electricity",
            "quantity": electricity_kwh,
            "unit": "kWh",
            "period_year": period_year,
            "period_month": period_month,
            "scope_2_method": scope2_method_raw,
            "activity_description": (
                f"Billing period: {billing_start} to {billing_end}"
            ),
        })

    # Domestic flights
    domestic_pkm = _safe_float(submission.get("domestic_pkm"))
    if domestic_pkm > 0:
        domestic_trips = _safe_int(submission.get("domestic_trips"))
        records.append({
            "site_code": site,
            "scope": "scope_3",
            "ghg_category": "business_travel",
            "fuel_or_material": "flight_short_haul",
            "quantity": domestic_pkm,
            "unit": "passenger_km",
            "period_year": period_year,
            "period_month": period_month,
            "activity_description": (
                f"{domestic_trips} domestic trip(s) | "
                f"{period_month}/{period_year}"
            ),
        })

    # International flights (KoboToolbox uses intl_pkm / intl_trips)
    intl_pkm = _safe_float(
        submission.get("intl_pkm") or submission.get("international_pkm")
    )
    if intl_pkm > 0:
        intl_trips = _safe_int(
            submission.get("intl_trips") or submission.get("international_trips")
        )
        records.append({
            "site_code": site,
            "scope": "scope_3",
            "ghg_category": "business_travel",
            "fuel_or_material": "flight_long_haul",
            "quantity": intl_pkm,
            "unit": "passenger_km",
            "period_year": period_year,
            "period_month": period_month,
            "activity_description": (
                f"{intl_trips} international trip(s) | "
                f"{period_month}/{period_year}"
            ),
        })

    return records


FORM_SPLITTERS = {
    1: _split_form1,
    2: _split_form2,
    3: _split_form3,
}


class ArrhenKoboConnector:
    """
    KoboToolbox connector specific to the three Arrhen forms.
    Handles authentication, submission fetching, one-to-many
    record splitting, validation, and database ingestion.
    """

    def __init__(self, api_token: str | None = None):
        self.api_token = api_token or os.getenv("KOBO_API_TOKEN")
        if not self.api_token:
            raise ValueError(
                "KoboToolbox API token not provided. "
                "Set KOBO_API_TOKEN in .env or pass api_token."
            )

    def _fetch_submissions(self, form_uid: str) -> list[dict]:
        """Fetches all submissions from a KoboToolbox form."""
        url = f"{KOBO_BASE_URL}/api/v2/assets/{form_uid}/data/"
        headers = {"Authorization": f"Token {self.api_token}"}
        try:
            response = httpx.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json().get("results", [])
        except httpx.HTTPError as e:
            log.error("kobo_fetch_failed", form_uid=form_uid, error=str(e))
            raise RuntimeError(f"Failed to fetch form {form_uid}: {e}")

    def import_form(
        self,
        db: Session,
        form_number: int,
        organisation_id: UUID,
        uploaded_by: str = "kobo_connector",
    ) -> dict:
        """
        Fetches and imports submissions from one of the three Arrhen forms.

        Args:
            db:               SQLAlchemy session
            form_number:      1, 2, or 3
            organisation_id:  Organisation UUID
            uploaded_by:      Identifier for lineage tracking

        Returns:
            Summary dict with total, valid, quarantined, duplicate counts
        """
        if form_number not in FORM_UIDS:
            raise ValueError(f"form_number must be 1, 2, or 3. Got {form_number}")

        form_uid = FORM_UIDS[form_number]
        splitter = FORM_SPLITTERS[form_number]

        log.info("kobo_import_start", form=form_number, uid=form_uid)

        # Fetch submissions
        submissions = self._fetch_submissions(form_uid)

        if not submissions:
            return {
                "form": form_number,
                "total_submissions": 0,
                "total_records": 0,
                "valid": 0,
                "quarantined": 0,
                "duplicate": 0,
                "errors": [],
            }

        # Resolve sites
        sites = db.query(Site).filter_by(
            organisation_id=organisation_id,
            is_active=True,
        ).all()
        site_map = {s.site_code: s for s in sites}
        valid_site_codes = set(site_map.keys())

        # Create lineage record
        lineage = DataLineage(
            source=DataSource.odk_submission,
            odk_form_id=form_uid,
            uploaded_by=uploaded_by,
            uploaded_at=datetime.utcnow(),
            record_count=0,
            valid_count=0,
            quarantine_count=0,
            notes=f"KoboToolbox Form {form_number} import",
        )
        db.add(lineage)
        db.flush()

        existing_keys = _load_existing_keys(db, organisation_id)
        batch_keys = set()

        valid_count = 0
        quarantine_count = 0
        duplicate_count = 0
        error_log = []
        total_records = 0

        for sub_num, submission in enumerate(submissions, start=1):
            # Split submission into activity records
            try:
                record_dicts = splitter(submission)
            except Exception as e:
                error_log.append({
                    "submission": sub_num,
                    "error": f"Split failed: {e}",
                })
                continue

            for record_dict in record_dicts:
                total_records += 1
                site_code = record_dict.get("site_code", "")

                if site_code not in valid_site_codes:
                    quarantine_count += 1
                    error_log.append({
                        "submission": sub_num,
                        "error": f"Unknown site_code: {site_code}",
                    })
                    continue

                if record_dict.get("quantity", 0) <= 0:
                    continue  # Skip zero-value records silently

                site = site_map[site_code]

                dedup_key = (
                    site_code,
                    record_dict.get("scope"),
                    record_dict.get("ghg_category"),
                    record_dict.get("fuel_or_material"),
                    record_dict.get("period_year"),
                    record_dict.get("period_month"),
                )

                is_duplicate = dedup_key in existing_keys or dedup_key in batch_keys
                batch_keys.add(dedup_key)

                scope_2_method = None
                if record_dict.get("scope_2_method"):
                    try:
                        scope_2_method = Scope2Method(
                            record_dict["scope_2_method"]
                        )
                    except ValueError:
                        scope_2_method = Scope2Method.location_based

                record = ActivityRecord(
                    site_id=site.id,
                    data_lineage_id=lineage.id,
                    scope=ScopeType(record_dict["scope"]),
                    scope_2_method=scope_2_method,
                    ghg_category=record_dict["ghg_category"],
                    fuel_or_material=record_dict["fuel_or_material"],
                    quantity=float(record_dict["quantity"]),
                    unit=record_dict["unit"],
                    period_year=record_dict["period_year"],
                    period_month=record_dict.get("period_month"),
                    activity_description=record_dict.get(
                        "activity_description"
                    ),
                    status=DataStatus.validated,
                    is_flagged_duplicate=is_duplicate,
                    flag_reason=(
                        "Duplicate: same site/scope/category/fuel/period."
                        if is_duplicate else None
                    ),
                )
                db.add(record)

                if is_duplicate:
                    duplicate_count += 1
                else:
                    valid_count += 1
                    existing_keys.add(dedup_key)

        lineage.record_count = total_records
        lineage.valid_count = valid_count
        lineage.quarantine_count = quarantine_count
        lineage.notes = (
            f"KoboToolbox Form {form_number} | "
            f"{len(submissions)} submissions → {total_records} records | "
            f"{valid_count} valid | {quarantine_count} quarantined | "
            f"{duplicate_count} duplicates"
        )

        db.commit()

        log.info(
            "kobo_import_complete",
            form=form_number,
            submissions=len(submissions),
            records=total_records,
            valid=valid_count,
            quarantined=quarantine_count,
            duplicates=duplicate_count,
        )

        return {
            "form": form_number,
            "total_submissions": len(submissions),
            "total_records": total_records,
            "valid": valid_count,
            "quarantined": quarantine_count,
            "duplicate": duplicate_count,
            "errors": error_log,
        }

    def import_all_forms(
        self,
        db: Session,
        organisation_id: UUID,
        uploaded_by: str = "kobo_connector",
    ) -> dict:
        """
        Imports all three forms in sequence.
        Returns combined summary.
        """
        results = {}
        for form_number in [1, 2, 3]:
            try:
                results[f"form_{form_number}"] = self.import_form(
                    db=db,
                    form_number=form_number,
                    organisation_id=organisation_id,
                    uploaded_by=uploaded_by,
                )
            except Exception as e:
                results[f"form_{form_number}"] = {"error": str(e)}

        return results

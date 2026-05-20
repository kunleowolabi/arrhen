"""
CSV Importer Pipeline

Handles ingestion of activity data from CSV file uploads.

Expected CSV format (see data/sample_data/sample_upload_template.csv):
    site_code, scope, ghg_category, fuel_or_material, quantity, unit,
    period_year, period_month (optional), scope_2_method (optional),
    activity_description (optional), supplier_name (optional),
    supplier_tier (optional)

Process:
1. Parse CSV into row dictionaries
2. Resolve site codes to site IDs for the organisation
3. Validate each row
4. Check for duplicates within batch and against existing DB records
5. Write valid rows as ActivityRecords (status=validated)
6. Write invalid rows as ActivityRecords (status=quarantined)
7. Create DataLineage record for the entire batch
8. Return summary

Usage:
    from backend.core.pipelines.csv_importer import import_csv

    with open("upload.csv", "rb") as f:
        result = import_csv(
            db=db,
            file=f,
            organisation_id=org_id,
            uploaded_by="user@example.com",
        )
"""

import csv
import io
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from backend.models import (
    Organisation, Site, ActivityRecord,
    DataLineage,
)
from backend.models.enums import (
    DataSource, DataStatus, ScopeType, Scope2Method
)
from backend.core.pipelines.validator import (
    validate_row, check_duplicate
)
import structlog

log = structlog.get_logger()


class CSVImportError(Exception):
    """Raised when the CSV file cannot be parsed at all."""
    pass


def import_csv(
    db: Session,
    file: bytes | io.IOBase,
    organisation_id: uuid.UUID,
    uploaded_by: str = "system",
    filename: str = "upload.csv",
) -> dict:
    """
    Imports activity data from a CSV file for a given organisation.

    Args:
        db:               SQLAlchemy session
        file:             File-like object or bytes of the CSV
        organisation_id:  Organisation the data belongs to
        uploaded_by:      Identifier of the uploader (email or username)
        filename:         Original filename for lineage tracking

    Returns:
        {
            "lineage_id": str,
            "filename": str,
            "total": int,
            "valid": int,
            "quarantined": int,
            "duplicate": int,
            "errors": list of row-level error dicts,
            "warnings": list of row-level warning dicts,
        }
    """

    # ── Parse CSV ─────────────────────────────────────────────────────────────
    rows = _parse_csv(file)

    if not rows:
        raise CSVImportError(
            "CSV file is empty or contains only headers. "
            "No data rows found."
        )

    # ── Resolve sites for this organisation ───────────────────────────────────
    sites = db.query(Site).filter_by(
        organisation_id=organisation_id,
        is_active=True,
    ).all()

    if not sites:
        raise CSVImportError(
            f"No active sites found for organisation {organisation_id}. "
            f"Add sites before importing data."
        )

    site_map = {s.site_code: s for s in sites}
    valid_site_codes = set(site_map.keys())

    # ── Create DataLineage record ──────────────────────────────────────────────
    lineage = DataLineage(
        source=DataSource.csv_upload,
        filename=filename,
        uploaded_by=uploaded_by,
        uploaded_at=datetime.utcnow(),
        record_count=len(rows),
        valid_count=0,
        quarantine_count=0,
        notes=f"CSV upload: {len(rows)} rows",
    )
    db.add(lineage)
    db.flush()

    # ── Track seen keys for duplicate detection ────────────────────────────────
    # Pre-load existing records for this org to detect cross-upload duplicates
    existing_keys = _load_existing_keys(db, organisation_id)
    batch_keys = set()

    # ── Process each row ──────────────────────────────────────────────────────
    valid_count = 0
    quarantine_count = 0
    duplicate_count = 0
    error_log = []
    warning_log = []

    for row_num, row in enumerate(rows, start=2):
        # Row 1 is header, so data starts at row 2

        result = validate_row(row, valid_site_codes)

        if result.warnings:
            for warning in result.warnings:
                warning_log.append({
                    "row": row_num,
                    "warning": warning,
                })

        if not result.is_valid:
            # Quarantine the row with reasons
            _write_quarantined_row(
                db=db,
                row=row,
                site_map=site_map,
                lineage_id=lineage.id,
                errors=result.errors,
            )
            quarantine_count += 1
            error_log.append({
                "row": row_num,
                "data": row,
                "errors": result.errors,
            })
            continue

        cleaned = result.cleaned_data

        # ── Duplicate check ───────────────────────────────────────────────────
        is_duplicate = check_duplicate(cleaned, existing_keys | batch_keys)

        # Build the dedup key and add to batch tracker
        dedup_key = (
            cleaned.get("site_code"),
            cleaned.get("scope"),
            cleaned.get("ghg_category"),
            cleaned.get("fuel_or_material"),
            cleaned.get("period_year"),
            cleaned.get("period_month"),
        )
        batch_keys.add(dedup_key)

        if is_duplicate:
            duplicate_count += 1
            flag_reason = (
                f"Duplicate: same site/scope/category/fuel/period "
                f"already exists in database or this upload batch."
            )
        else:
            flag_reason = None

        # ── Write ActivityRecord ───────────────────────────────────────────────
        site = site_map[cleaned["site_code"]]

        scope_2_method = None
        if cleaned.get("scope_2_method"):
            scope_2_method = Scope2Method(cleaned["scope_2_method"])

        record = ActivityRecord(
            site_id=site.id,
            data_lineage_id=lineage.id,
            scope=ScopeType(cleaned["scope"]),
            scope_2_method=scope_2_method,
            ghg_category=cleaned["ghg_category"],
            fuel_or_material=cleaned["fuel_or_material"],
            quantity=cleaned["quantity"],
            unit=cleaned["unit"],
            period_year=cleaned["period_year"],
            period_month=cleaned["period_month"],
            activity_description=cleaned.get("activity_description"),
            supplier_name=cleaned.get("supplier_name"),
            supplier_tier=cleaned.get("supplier_tier"),
            status=DataStatus.validated,
            is_flagged_duplicate=is_duplicate,
            flag_reason=flag_reason,
        )
        db.add(record)
        valid_count += 1

        # Add to existing keys so subsequent rows in this
        # batch can detect duplicates against it
        existing_keys.add(dedup_key)

    # ── Update lineage counts ──────────────────────────────────────────────────
    lineage.valid_count = valid_count
    lineage.quarantine_count = quarantine_count
    lineage.notes = (
        f"CSV upload: {len(rows)} rows | "
        f"{valid_count} valid | "
        f"{quarantine_count} quarantined | "
        f"{duplicate_count} duplicates flagged"
    )

    db.commit()

    log.info(
        "csv_import_complete",
        filename=filename,
        total=len(rows),
        valid=valid_count,
        quarantined=quarantine_count,
        duplicates=duplicate_count,
    )

    return {
        "lineage_id": str(lineage.id),
        "filename": filename,
        "total": len(rows),
        "valid": valid_count,
        "quarantined": quarantine_count,
        "duplicate": duplicate_count,
        "errors": error_log,
        "warnings": warning_log,
    }


def _parse_csv(file: bytes | io.IOBase) -> list[dict]:
    """
    Parses a CSV file into a list of row dictionaries.
    Handles both bytes and file-like objects.
    Strips whitespace from all values.
    """
    if isinstance(file, bytes):
        content = file.decode("utf-8-sig")  # handles BOM from Excel exports
    else:
        raw = file.read()
        if isinstance(raw, bytes):
            content = raw.decode("utf-8-sig")
        else:
            content = raw

    reader = csv.DictReader(io.StringIO(content))

    rows = []
    for row in reader:
        # Strip whitespace from keys and values
        cleaned_row = {
            k.strip().lower(): v.strip() if isinstance(v, str) else v
            for k, v in row.items()
            if k is not None
        }
        rows.append(cleaned_row)

    return rows


def _load_existing_keys(
    db: Session,
    organisation_id: uuid.UUID,
) -> set[tuple]:
    """
    Loads deduplication keys for all existing ActivityRecords
    belonging to this organisation.
    Used to detect duplicates across uploads, not just within a batch.
    """
    existing_records = (
        db.query(
            ActivityRecord.site_id,
            ActivityRecord.scope,
            ActivityRecord.ghg_category,
            ActivityRecord.fuel_or_material,
            ActivityRecord.period_year,
            ActivityRecord.period_month,
            Site.site_code,
        )
        .join(Site, ActivityRecord.site_id == Site.id)
        .filter(Site.organisation_id == organisation_id)
        .all()
    )

    return {
        (
            rec.site_code,
            rec.scope.value,
            rec.ghg_category,
            rec.fuel_or_material,
            rec.period_year,
            rec.period_month,
        )
        for rec in existing_records
    }


def _write_quarantined_row(
    db: Session,
    row: dict,
    site_map: dict,
    lineage_id: uuid.UUID,
    errors: list[str],
) -> None:
    """
    Writes a failed row as a quarantined ActivityRecord.
    Uses placeholder values for required fields that failed validation.
    Preserves as much original data as possible for review.
    """
    # Try to resolve site — use first available if site_code invalid
    site_code = str(row.get("site_code", "")).strip().upper()
    site = site_map.get(site_code) or next(iter(site_map.values()))

    try:
        quantity = float(row.get("quantity", 0))
    except (ValueError, TypeError):
        quantity = 0.0

    try:
        period_year = int(row.get("period_year", 0))
    except (ValueError, TypeError):
        period_year = 0

    record = ActivityRecord(
        site_id=site.id,
        data_lineage_id=lineage_id,
        scope=ScopeType.scope_1,  # placeholder
        ghg_category=str(row.get("ghg_category", "unknown"))[:100],
        fuel_or_material=str(row.get("fuel_or_material", "unknown"))[:100],
        quantity=quantity,
        unit=str(row.get("unit", "unknown"))[:50],
        period_year=period_year if period_year > 0 else 1900,
        status=DataStatus.quarantined,
        is_flagged_duplicate=False,
        flag_reason=" | ".join(errors),
        activity_description=f"QUARANTINED: {row}",
    )
    db.add(record)
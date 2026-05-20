"""
Generic API Connector

A configurable connector for pulling activity data from external
REST APIs — utility company APIs, fleet telematics systems,
building management systems, ERP exports, etc.

Each external source is defined by a ConnectorConfig object that
specifies the endpoint, authentication, field mappings, and schedule.
No code changes needed to add a new source — just a new config.

Supported auth methods:
    - api_key:    Key passed as a header or query parameter
    - bearer:     Bearer token in Authorization header
    - basic:      HTTP Basic auth (username + password)

Usage:
    from backend.core.pipelines.api_connector import (
        APIConnector, ConnectorConfig
    )

    config = ConnectorConfig(
        name="Ikeja Electric API",
        base_url="https://api.ikejaelectric.com",
        endpoint="/v1/consumption",
        auth_method="api_key",
        auth_key="X-API-Key",
        auth_value="your-key-here",
        field_map={
            "meter_id": "site_code",
            "consumption_kwh": "quantity",
            "billing_month": "period_month",
            "billing_year": "period_year",
        },
        default_values={
            "scope": "scope_2",
            "ghg_category": "purchased_electricity",
            "fuel_or_material": "grid_electricity",
            "unit": "kWh",
        },
    )

    connector = APIConnector(config)
    result = connector.import_data(
        db=db,
        organisation_id=org_id,
        uploaded_by="system",
    )
"""

import uuid
from datetime import datetime
from dataclasses import dataclass, field
from sqlalchemy.orm import Session
import httpx
import structlog

from backend.models import Site, ActivityRecord, DataLineage
from backend.models.enums import (
    DataSource, DataStatus, ScopeType, Scope2Method
)
from backend.core.pipelines.validator import validate_row, check_duplicate
from backend.core.pipelines.csv_importer import (
    _load_existing_keys,
    _write_quarantined_row,
)

log = structlog.get_logger()


@dataclass
class ConnectorConfig:
    """
    Configuration for a single external API data source.

    Attributes:
        name:           Human-readable name e.g. "Ikeja Electric API"
        base_url:       Base URL e.g. "https://api.ikejaelectric.com"
        endpoint:       Path e.g. "/v1/consumption"
        auth_method:    "api_key", "bearer", or "basic"
        auth_key:       Header name for api_key auth e.g. "X-API-Key"
                        or query param name
        auth_value:     The key/token value
        auth_username:  Username for basic auth
        auth_password:  Password for basic auth
        field_map:      Maps API response fields to platform fields
        default_values: Static values applied to every record from
                        this source e.g. scope, ghg_category, unit
        params:         Additional query parameters for the request
        response_key:   Key in the JSON response containing the data array
                        e.g. "data", "results", "records"
                        If None, assumes response IS the array
        timeout:        Request timeout in seconds
    """
    name: str
    base_url: str
    endpoint: str
    auth_method: str = "api_key"
    auth_key: str | None = None
    auth_value: str | None = None
    auth_username: str | None = None
    auth_password: str | None = None
    field_map: dict = field(default_factory=dict)
    default_values: dict = field(default_factory=dict)
    params: dict = field(default_factory=dict)
    response_key: str | None = "results"
    timeout: int = 30


class APIConnectorError(Exception):
    """Raised when the external API call fails."""
    pass


class APIConnector:
    """
    Generic configurable API connector.
    Fetches data from an external REST API and imports it
    as ActivityRecords using the same validation pipeline
    as CSV and ODK imports.
    """

    def __init__(self, config: ConnectorConfig):
        self.config = config

    def import_data(
        self,
        db: Session,
        organisation_id: uuid.UUID,
        uploaded_by: str = "system",
    ) -> dict:
        """
        Fetches data from the configured API and imports as ActivityRecords.

        Args:
            db:               SQLAlchemy session
            organisation_id:  Organisation the data belongs to
            uploaded_by:      Identifier of who triggered the import

        Returns:
            Summary dict with total, valid, quarantined, duplicate counts
        """

        # ── Fetch data from API ────────────────────────────────────────────────
        raw_records = self._fetch()

        if not raw_records:
            log.info(
                "api_connector_no_data",
                source=self.config.name,
            )
            return {
                "lineage_id": None,
                "source": self.config.name,
                "total": 0,
                "valid": 0,
                "quarantined": 0,
                "duplicate": 0,
                "errors": [],
                "warnings": [],
            }

        # ── Apply field mapping and default values ─────────────────────────────
        mapped_rows = [
            self._apply_mapping(record)
            for record in raw_records
        ]

        # ── Resolve sites ──────────────────────────────────────────────────────
        sites = db.query(Site).filter_by(
            organisation_id=organisation_id,
            is_active=True,
        ).all()

        site_map = {s.site_code: s for s in sites}
        valid_site_codes = set(site_map.keys())

        # ── Create DataLineage record ──────────────────────────────────────────
        lineage = DataLineage(
            source=DataSource.api_connector,
            uploaded_by=uploaded_by,
            uploaded_at=datetime.utcnow(),
            record_count=len(mapped_rows),
            valid_count=0,
            quarantine_count=0,
            notes=f"API connector: {self.config.name} | {len(mapped_rows)} records",
        )
        db.add(lineage)
        db.flush()

        # ── Process rows ───────────────────────────────────────────────────────
        existing_keys = _load_existing_keys(db, organisation_id)
        batch_keys = set()

        valid_count = 0
        quarantine_count = 0
        duplicate_count = 0
        error_log = []
        warning_log = []

        for row_num, row in enumerate(mapped_rows, start=1):
            result = validate_row(row, valid_site_codes)

            if result.warnings:
                for warning in result.warnings:
                    warning_log.append({"row": row_num, "warning": warning})

            if not result.is_valid:
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
            is_duplicate = check_duplicate(cleaned, existing_keys | batch_keys)

            dedup_key = (
                cleaned.get("site_code"),
                cleaned.get("scope"),
                cleaned.get("ghg_category"),
                cleaned.get("fuel_or_material"),
                cleaned.get("period_year"),
                cleaned.get("period_month"),
            )
            batch_keys.add(dedup_key)

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
                flag_reason=(
                    "Duplicate: same site/scope/category/fuel/period exists."
                    if is_duplicate else None
                ),
            )
            db.add(record)

            if is_duplicate:
                duplicate_count += 1
            else:
                valid_count += 1

            existing_keys.add(dedup_key)

        # ── Update lineage ─────────────────────────────────────────────────────
        lineage.valid_count = valid_count
        lineage.quarantine_count = quarantine_count
        lineage.notes = (
            f"API connector: {self.config.name} | "
            f"{len(mapped_rows)} records | "
            f"{valid_count} valid | "
            f"{quarantine_count} quarantined | "
            f"{duplicate_count} duplicates"
        )

        db.commit()

        log.info(
            "api_connector_import_complete",
            source=self.config.name,
            total=len(mapped_rows),
            valid=valid_count,
            quarantined=quarantine_count,
            duplicates=duplicate_count,
        )

        return {
            "lineage_id": str(lineage.id),
            "source": self.config.name,
            "total": len(mapped_rows),
            "valid": valid_count,
            "quarantined": quarantine_count,
            "duplicate": duplicate_count,
            "errors": error_log,
            "warnings": warning_log,
        }

    def _fetch(self) -> list[dict]:
        """
        Makes the HTTP request to the external API.
        Returns a list of raw record dicts.
        """
        url = f"{self.config.base_url}{self.config.endpoint}"
        headers = self._build_headers()
        auth = self._build_auth()
        params = self.config.params.copy()

        try:
            response = httpx.get(
                url,
                headers=headers,
                auth=auth,
                params=params,
                timeout=self.config.timeout,
            )
            response.raise_for_status()
            data = response.json()

            # Extract array from response
            if self.config.response_key:
                records = data.get(self.config.response_key, [])
            else:
                records = data if isinstance(data, list) else [data]

            return records

        except httpx.HTTPError as e:
            raise APIConnectorError(
                f"API request failed for '{self.config.name}': {e}"
            )
        except ValueError as e:
            raise APIConnectorError(
                f"Invalid JSON response from '{self.config.name}': {e}"
            )

    def _build_headers(self) -> dict:
        """Builds request headers based on auth method."""
        headers = {"Accept": "application/json"}

        if self.config.auth_method == "api_key" and self.config.auth_key:
            headers[self.config.auth_key] = self.config.auth_value or ""

        if self.config.auth_method == "bearer":
            headers["Authorization"] = f"Bearer {self.config.auth_value}"

        return headers

    def _build_auth(self):
        """Builds httpx auth tuple for basic auth."""
        if self.config.auth_method == "basic":
            return (
                self.config.auth_username,
                self.config.auth_password,
            )
        return None

    def _apply_mapping(self, record: dict) -> dict:
        """
        Applies field_map and default_values to a raw API record.

        Field map translates API field names to platform field names.
        Default values fill in fields that are constant for this source
        e.g. scope, ghg_category, unit.
        """
        mapped = {}

        # Apply default values first
        mapped.update(self.config.default_values)

        # Apply field map — overrides defaults if same key
        for api_field, platform_field in self.config.field_map.items():
            if api_field in record:
                mapped[platform_field] = record[api_field]

        return mapped
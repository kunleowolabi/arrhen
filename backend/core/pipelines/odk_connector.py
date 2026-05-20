"""
ODK / KoboToolbox Connector

Connects to ODK Central or KoboToolbox and pulls form submissions
as ActivityRecords into the platform.

Supported platforms:
    "odk"  — ODK Central (self-hosted)
    "kobo" — KoboToolbox (cloud or self-hosted)

ODK Central API docs:  https://docs.getodk.org/central-api/
KoboToolbox API docs:  https://support.kobotoolbox.org/api.html

Authentication:
    ODK Central:  Email + password → session token
    KoboToolbox:  API token in Authorization header

Field mapping:
    ODK/Kobo form fields must match the expected field names below,
    or a custom field_map can be provided to translate form field
    names to platform field names.

    Required form fields (or mapped equivalents):
        site_code, scope, ghg_category, fuel_or_material,
        quantity, unit, period_year

    Optional:
        period_month, scope_2_method, activity_description,
        supplier_name, supplier_tier

Usage:
    from backend.core.pipelines.odk_connector import ODKConnector

    connector = ODKConnector(
        platform="kobo",
        base_url="https://kf.kobotoolbox.org",
        api_token="your-token-here",
    )

    result = connector.import_submissions(
        db=db,
        form_id="your-form-asset-id",
        organisation_id=org_id,
        uploaded_by="system",
    )
"""

import uuid
from datetime import datetime
from sqlalchemy.orm import Session
import httpx
import structlog

from backend.models import Site, ActivityRecord, DataLineage
from backend.models.enums import (
    DataSource, DataStatus, ScopeType, Scope2Method
)
from backend.core.pipelines.validator import validate_row, check_duplicate

log = structlog.get_logger()


# ── Default field mappings ─────────────────────────────────────────────────────
# Maps platform form field names to internal platform field names.
# Override by passing field_map to import_submissions().

ODK_DEFAULT_FIELD_MAP = {
    "site_code": "site_code",
    "scope": "scope",
    "ghg_category": "ghg_category",
    "fuel_or_material": "fuel_or_material",
    "quantity": "quantity",
    "unit": "unit",
    "period_year": "period_year",
    "period_month": "period_month",
    "scope_2_method": "scope_2_method",
    "activity_description": "activity_description",
    "supplier_name": "supplier_name",
    "supplier_tier": "supplier_tier",
}

KOBO_DEFAULT_FIELD_MAP = {
    "site_code": "site_code",
    "scope": "scope",
    "ghg_category": "ghg_category",
    "fuel_or_material": "fuel_or_material",
    "quantity": "quantity",
    "unit": "unit",
    "period_year": "period_year",
    "period_month": "period_month",
    "scope_2_method": "scope_2_method",
    "activity_description": "activity_description",
    "supplier_name": "supplier_name",
    "supplier_tier": "supplier_tier",
}


class ODKConnectionError(Exception):
    """Raised when connection to ODK/Kobo server fails."""
    pass


class ODKConnector:
    """
    Connector for ODK Central and KoboToolbox platforms.

    Handles authentication, submission fetching, field mapping,
    validation, and database ingestion.
    """

    def __init__(
        self,
        platform: str,
        base_url: str,
        api_token: str | None = None,
        email: str | None = None,
        password: str | None = None,
        timeout: int = 30,
    ):
        """
        Args:
            platform:   "odk" or "kobo"
            base_url:   Base URL of the server
                        ODK:  "https://odk.yourorg.com"
                        Kobo: "https://kf.kobotoolbox.org"
            api_token:  API token (KoboToolbox and ODK Central both support this)
            email:      Email for ODK Central session auth (alternative to token)
            password:   Password for ODK Central session auth
            timeout:    Request timeout in seconds
        """
        if platform not in ("odk", "kobo"):
            raise ValueError(
                f"Invalid platform '{platform}'. Must be 'odk' or 'kobo'."
            )

        self.platform = platform
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.email = email
        self.password = password
        self.timeout = timeout
        self._session_token = None

    def import_submissions(
        self,
        db: Session,
        form_id: str,
        organisation_id: uuid.UUID,
        uploaded_by: str = "system",
        field_map: dict | None = None,
        project_id: int | None = None,
    ) -> dict:
        """
        Fetches submissions from a form and imports them as ActivityRecords.

        Args:
            db:               SQLAlchemy session
            form_id:          ODK form ID or KoboToolbox asset UID
            organisation_id:  Organisation the data belongs to
            uploaded_by:      Identifier of who triggered the import
            field_map:        Custom field name mapping (form field → platform field)
                              If None, uses platform default mapping
            project_id:       ODK Central project ID (required for ODK only)

        Returns:
            Same summary dict as csv_importer.import_csv()
        """

        # ── Authenticate ───────────────────────────────────────────────────────
        headers = self._get_auth_headers()

        # ── Fetch submissions ──────────────────────────────────────────────────
        submissions = self._fetch_submissions(
            headers=headers,
            form_id=form_id,
            project_id=project_id,
        )

        if not submissions:
            log.info(
                "odk_no_submissions",
                platform=self.platform,
                form_id=form_id,
            )
            return {
                "lineage_id": None,
                "form_id": form_id,
                "total": 0,
                "valid": 0,
                "quarantined": 0,
                "duplicate": 0,
                "errors": [],
                "warnings": [],
            }

        # ── Resolve sites ──────────────────────────────────────────────────────
        sites = db.query(Site).filter_by(
            organisation_id=organisation_id,
            is_active=True,
        ).all()

        site_map = {s.site_code: s for s in sites}
        valid_site_codes = set(site_map.keys())

        # ── Apply field mapping ────────────────────────────────────────────────
        resolved_map = field_map or (
            KOBO_DEFAULT_FIELD_MAP
            if self.platform == "kobo"
            else ODK_DEFAULT_FIELD_MAP
        )

        mapped_rows = [
            _apply_field_map(submission, resolved_map)
            for submission in submissions
        ]

        # ── Create DataLineage record ──────────────────────────────────────────
        lineage = DataLineage(
            source=DataSource.odk_submission,
            odk_form_id=form_id,
            uploaded_by=uploaded_by,
            uploaded_at=datetime.utcnow(),
            record_count=len(mapped_rows),
            valid_count=0,
            quarantine_count=0,
            notes=f"{self.platform.upper()} import: form {form_id}",
        )
        db.add(lineage)
        db.flush()

        # ── Process rows — same logic as CSV importer ──────────────────────────
        from backend.core.pipelines.csv_importer import (
            _load_existing_keys,
            _write_quarantined_row,
        )

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

        lineage.valid_count = valid_count
        lineage.quarantine_count = quarantine_count
        lineage.notes = (
            f"{self.platform.upper()} import: {len(mapped_rows)} rows | "
            f"{valid_count} valid | "
            f"{quarantine_count} quarantined | "
            f"{duplicate_count} duplicates"
        )

        db.commit()

        log.info(
            "odk_import_complete",
            platform=self.platform,
            form_id=form_id,
            total=len(mapped_rows),
            valid=valid_count,
            quarantined=quarantine_count,
            duplicates=duplicate_count,
        )

        return {
            "lineage_id": str(lineage.id),
            "form_id": form_id,
            "total": len(mapped_rows),
            "valid": valid_count,
            "quarantined": quarantine_count,
            "duplicate": duplicate_count,
            "errors": error_log,
            "warnings": warning_log,
        }

    def _get_auth_headers(self) -> dict:
        """
        Returns authentication headers for the platform.
        ODK Central: Bearer token or session token from email/password
        KoboToolbox: Token header
        """
        if self.api_token:
            if self.platform == "kobo":
                return {"Authorization": f"Token {self.api_token}"}
            else:
                return {"Authorization": f"Bearer {self.api_token}"}

        if self.platform == "odk" and self.email and self.password:
            token = self._get_odk_session_token()
            return {"Authorization": f"Bearer {token}"}

        raise ODKConnectionError(
            "No authentication credentials provided. "
            "Supply api_token, or email+password for ODK Central."
        )

    def _get_odk_session_token(self) -> str:
        """
        Authenticates with ODK Central using email/password
        and returns a session token.
        """
        if self._session_token:
            return self._session_token

        url = f"{self.base_url}/v1/sessions"
        try:
            response = httpx.post(
                url,
                json={"email": self.email, "password": self.password},
                timeout=self.timeout,
            )
            response.raise_for_status()
            self._session_token = response.json()["token"]
            return self._session_token
        except httpx.HTTPError as e:
            raise ODKConnectionError(
                f"ODK Central authentication failed: {e}"
            )

    def _fetch_submissions(
        self,
        headers: dict,
        form_id: str,
        project_id: int | None = None,
    ) -> list[dict]:
        """
        Fetches all submissions from a form.
        Routes to platform-specific endpoint.
        """
        if self.platform == "kobo":
            return self._fetch_kobo_submissions(headers, form_id)
        else:
            return self._fetch_odk_submissions(headers, form_id, project_id)

    def _fetch_kobo_submissions(
        self,
        headers: dict,
        asset_uid: str,
    ) -> list[dict]:
        """
        Fetches submissions from KoboToolbox.
        Endpoint: GET /api/v2/assets/{asset_uid}/data/
        """
        url = f"{self.base_url}/api/v2/assets/{asset_uid}/data/"
        try:
            response = httpx.get(
                url,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        except httpx.HTTPError as e:
            raise ODKConnectionError(
                f"KoboToolbox fetch failed for asset '{asset_uid}': {e}"
            )

    def _fetch_odk_submissions(
        self,
        headers: dict,
        form_id: str,
        project_id: int | None,
    ) -> list[dict]:
        """
        Fetches submissions from ODK Central.
        Endpoint: GET /v1/projects/{projectId}/forms/{formId}.svc/Submissions
        """
        if not project_id:
            raise ODKConnectionError(
                "project_id is required for ODK Central submissions."
            )

        url = (
            f"{self.base_url}/v1/projects/{project_id}"
            f"/forms/{form_id}.svc/Submissions"
        )
        try:
            response = httpx.get(
                url,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("value", [])
        except httpx.HTTPError as e:
            raise ODKConnectionError(
                f"ODK Central fetch failed for form '{form_id}': {e}"
            )


def _apply_field_map(
    submission: dict,
    field_map: dict,
) -> dict:
    """
    Translates a raw submission dict using the field map.
    Maps form field names to internal platform field names.

    Example:
        submission = {"fuel_type": "diesel", "qty": 1000}
        field_map  = {"fuel_type": "fuel_or_material", "qty": "quantity"}
        result     = {"fuel_or_material": "diesel", "quantity": 1000}
    """
    mapped = {}
    for form_field, platform_field in field_map.items():
        if form_field in submission:
            mapped[platform_field] = submission[form_field]
    return mapped
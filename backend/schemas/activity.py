"""
Pydantic schemas for ActivityRecord and DataLineage endpoints.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from uuid import UUID
from backend.models.enums import (
    ScopeType, Scope2Method, DataSource, DataStatus
)


class ActivityRecordResponse(BaseModel):
    id: UUID
    site_id: UUID
    data_lineage_id: Optional[UUID]
    scope: ScopeType
    scope_2_method: Optional[Scope2Method]
    ghg_category: str
    activity_description: Optional[str]
    fuel_or_material: str
    quantity: float
    unit: str
    period_year: int
    period_month: Optional[int]
    status: DataStatus
    is_flagged_duplicate: bool
    flag_reason: Optional[str]
    supplier_name: Optional[str]
    supplier_tier: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


class ActivityRecordFilter(BaseModel):
    """Query parameters for filtering activity records."""
    site_id: Optional[UUID] = None
    scope: Optional[ScopeType] = None
    ghg_category: Optional[str] = None
    period_year: Optional[int] = None
    period_month: Optional[int] = None
    status: Optional[DataStatus] = None


class DataLineageResponse(BaseModel):
    id: UUID
    source: DataSource
    filename: Optional[str]
    odk_form_id: Optional[str]
    uploaded_by: Optional[str]
    uploaded_at: datetime
    record_count: int
    valid_count: int
    quarantine_count: int
    notes: Optional[str]

    model_config = {"from_attributes": True}


class CSVUploadResponse(BaseModel):
    """Response after a CSV upload."""
    lineage_id: str
    filename: str
    total: int
    valid: int
    quarantined: int
    duplicate: int
    errors: list[dict] = []
    warnings: list[dict] = []
"""
Pydantic schemas for Organisation and Site endpoints.

Request schemas: validate incoming data
Response schemas: shape outgoing data
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from uuid import UUID
from backend.models.enums import IndustryType, GWPVersion


# ── Site Schemas ───────────────────────────────────────────────────────────────

class SiteCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    site_code: Optional[str] = Field(None, max_length=50)
    region: Optional[str] = Field(None, max_length=100)
    country: str = Field(..., min_length=1, max_length=100)
    address: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    is_active: bool = True


class SiteResponse(BaseModel):
    id: UUID
    organisation_id: UUID
    name: str
    site_code: Optional[str]
    region: Optional[str]
    country: str
    address: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Organisation Schemas ───────────────────────────────────────────────────────

class OrganisationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    industry: IndustryType
    country: str = Field(..., min_length=1, max_length=100)
    reporting_currency: str = Field("USD", max_length=10)
    fiscal_year_start_month: int = Field(1, ge=1, le=12)
    default_gwp_version: GWPVersion = GWPVersion.AR6


class OrganisationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    industry: Optional[IndustryType] = None
    country: Optional[str] = Field(None, min_length=1, max_length=100)
    reporting_currency: Optional[str] = Field(None, max_length=10)
    fiscal_year_start_month: Optional[int] = Field(None, ge=1, le=12)
    default_gwp_version: Optional[GWPVersion] = None


class OrganisationResponse(BaseModel):
    id: UUID
    name: str
    industry: IndustryType
    country: str
    reporting_currency: str
    fiscal_year_start_month: int
    default_gwp_version: GWPVersion
    created_at: datetime
    updated_at: datetime
    sites: list[SiteResponse] = []

    model_config = {"from_attributes": True}


class OrganisationSummary(BaseModel):
    """Lightweight response without nested sites — for list endpoints."""
    id: UUID
    name: str
    industry: IndustryType
    country: str
    default_gwp_version: GWPVersion

    model_config = {"from_attributes": True}
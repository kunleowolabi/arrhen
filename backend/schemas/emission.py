"""
Pydantic schemas for EmissionFactor, EmissionRecord,
calculation requests and responses.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date
from uuid import UUID
from backend.models.enums import (
    FactorSource, GWPVersion, ScopeType
)


# ── Emission Factor Schemas ────────────────────────────────────────────────────

class EmissionFactorResponse(BaseModel):
    id: UUID
    activity_type: str
    fuel_or_material: str
    region: Optional[str]
    co2_factor: float
    ch4_factor: float
    n2o_factor: float
    hfc_factor: float
    pfc_factor: float
    sf6_factor: float
    nf3_factor: float
    unit: str
    source: FactorSource
    version: str
    valid_from: date
    valid_to: Optional[date]
    notes: Optional[str]

    model_config = {"from_attributes": True}


# ── Emission Record Schemas ────────────────────────────────────────────────────

class EmissionRecordResponse(BaseModel):
    id: UUID
    activity_record_id: UUID
    emission_factor_id: UUID
    co2_kg: float
    ch4_kg: float
    n2o_kg: float
    hfc_kg: float
    pfc_kg: float
    sf6_kg: float
    nf3_kg: float
    co2_co2e: float
    ch4_co2e: float
    n2o_co2e: float
    hfc_co2e: float
    pfc_co2e: float
    sf6_co2e: float
    nf3_co2e: float
    total_co2e_kg: float
    total_co2e_tonnes: float
    gwp_version: GWPVersion
    factor_fallback_used: bool
    calculated_at: datetime

    model_config = {"from_attributes": True}


# ── Calculation Request/Response ───────────────────────────────────────────────

class CalculationRequest(BaseModel):
    """Request body to trigger a batch calculation."""
    gwp_version: GWPVersion = GWPVersion.AR6
    period_year: Optional[int] = None
    period_month: Optional[int] = None
    site_id: Optional[UUID] = None
    organisation_id: Optional[UUID] = None
    scope: Optional[ScopeType] = None


class CalculationResponse(BaseModel):
    """Summary returned after a batch calculation run."""
    total: int
    success: int
    failed: int
    errors: list[str] = []
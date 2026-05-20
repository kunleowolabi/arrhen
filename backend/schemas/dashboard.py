"""
Pydantic schemas for dashboard and reporting endpoints.
"""

from pydantic import BaseModel
from typing import Optional
from uuid import UUID


class ScopeBreakdown(BaseModel):
    scope_1_tco2e: float
    scope_2_tco2e: float
    scope_3_tco2e: float
    total_tco2e: float


class SiteEmissionSummary(BaseModel):
    rank: int
    site_code: Optional[str]
    site_name: str
    region: Optional[str]
    total_co2e_tonnes: float
    record_count: int


class MaterialitySource(BaseModel):
    rank: int
    scope: str
    ghg_category: str
    fuel_or_material: str
    total_co2e_tonnes: float
    percentage_of_total: float
    is_material: bool
    fallback_used: bool
    record_count: int


class MaterialityScreenResult(BaseModel):
    organisation_id: str
    period_year: int
    threshold_pct: float
    total_co2e_tonnes: float
    material_source_count: int
    sources: list[MaterialitySource]


class TargetProgress(BaseModel):
    target_name: str
    baseline_year: int
    target_year: int
    baseline_emissions_tco2e: float
    target_emissions_tco2e: float
    target_reduction_pct: float
    current_emissions_tco2e: float
    current_reduction_pct: float
    on_track: bool
    aligned_to: Optional[str]


class DashboardOverview(BaseModel):
    organisation_id: str
    organisation_name: str
    period_year: int
    scope_breakdown: ScopeBreakdown
    top_sites: list[SiteEmissionSummary]
    top_sources: list[MaterialitySource]
    target_progress: list[TargetProgress]


class Scope2Summary(BaseModel):
    location_based_tco2e: float
    market_based_tco2e: float
    record_count: int


class TrendDataPoint(BaseModel):
    period_year: int
    period_month: Optional[int]
    scope_1_tco2e: float
    scope_2_tco2e: float
    scope_3_tco2e: float
    total_tco2e: float


class TrendResponse(BaseModel):
    organisation_id: str
    data_points: list[TrendDataPoint]
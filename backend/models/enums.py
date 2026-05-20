"""
Central enum definitions for the carbon platform.

All enums live here to avoid circular imports between model files.
Every model imports enums from this file rather than defining them locally.
"""

import enum


class IndustryType(str, enum.Enum):
    oil_and_gas = "oil_and_gas"
    manufacturing = "manufacturing"
    agriculture = "agriculture"
    financial_services = "financial_services"
    technology = "technology"
    retail = "retail"
    transportation = "transportation"
    construction = "construction"
    energy_utilities = "energy_utilities"
    other = "other"


class ScopeType(str, enum.Enum):
    scope_1 = "scope_1"
    scope_2 = "scope_2"
    scope_3 = "scope_3"


class Scope2Method(str, enum.Enum):
    location_based = "location_based"
    market_based = "market_based"


class DataSource(str, enum.Enum):
    csv_upload = "csv_upload"
    odk_submission = "odk_submission"
    api_connector = "api_connector"
    manual_entry = "manual_entry"


class DataStatus(str, enum.Enum):
    pending = "pending"
    validated = "validated"
    quarantined = "quarantined"
    calculated = "calculated"


class FactorSource(str, enum.Enum):
    DEFRA = "DEFRA"
    IPCC = "IPCC"
    EPA = "EPA"
    IEA = "IEA"
    custom = "custom"


class GWPVersion(str, enum.Enum):
    AR5 = "AR5"
    AR6 = "AR6"


class ScopeCoverage(str, enum.Enum):
    scope_1_only = "scope_1_only"
    scope_1_2 = "scope_1_2"
    scope_1_2_3 = "scope_1_2_3"


class TargetType(str, enum.Enum):
    absolute = "absolute"
    intensity = "intensity"
# Data Dictionary

This document defines every table and field in the Arrhen database. Intended for data analysts, verifiers, and developers working directly with the data.

---

## organisations

The top-level reporting entity.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `name` | String(255) | Organisation name |
| `industry` | Enum | See IndustryType below |
| `country` | String(100) | Country of headquarters |
| `reporting_currency` | String(10) | ISO currency code e.g. NGN, USD |
| `fiscal_year_start_month` | Integer | 1–12. Default: 1 (January) |
| `default_gwp_version` | Enum | AR5 or AR6. Default: AR6 |
| `created_at` | DateTime | Record creation timestamp |
| `updated_at` | DateTime | Last update timestamp |

**IndustryType values:**
`oil_and_gas`, `manufacturing`, `agriculture`, `financial_services`, `technology`, `retail`, `transportation`, `construction`, `energy_utilities`, `other`

---

## sites

A physical location belonging to an organisation.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `organisation_id` | UUID | FK → organisations.id |
| `name` | String(255) | Site display name |
| `site_code` | String(50) | Short identifier e.g. LAGOS-HQ |
| `region` | String(100) | Region or state |
| `country` | String(100) | Country |
| `address` | Text | Full address (optional) |
| `latitude` | Float | Decimal degrees, -90 to 90 |
| `longitude` | Float | Decimal degrees, -180 to 180 |
| `geom` | Geography(POINT) | PostGIS point for spatial queries |
| `is_active` | Boolean | False = decommissioned |
| `created_at` | DateTime | Record creation timestamp |

---

## data_lineage

An upload event record. One row per CSV upload, ODK sync, or API connector run.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `source` | Enum | See DataSource below |
| `filename` | String(255) | Original filename (CSV uploads) |
| `odk_form_id` | String(255) | ODK/Kobo form identifier |
| `odk_submission_id` | String(255) | Individual submission ID |
| `uploaded_by` | String(255) | Uploader identifier |
| `uploaded_at` | DateTime | Upload timestamp |
| `raw_payload` | JSONB | Original submission data |
| `record_count` | Integer | Total rows in upload |
| `valid_count` | Integer | Rows that passed validation |
| `quarantine_count` | Integer | Rows that failed validation |
| `notes` | Text | Summary note |

**DataSource values:**
`csv_upload`, `odk_submission`, `api_connector`, `manual_entry`

---

## activity_records

A single emission-generating activity. Raw input data — not yet calculated.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `site_id` | UUID | FK → sites.id |
| `data_lineage_id` | UUID | FK → data_lineage.id (nullable) |
| `scope` | Enum | scope_1, scope_2, scope_3 |
| `scope_2_method` | Enum | location_based or market_based (Scope 2 only) |
| `ghg_category` | String(100) | See GHG Category values below |
| `activity_description` | Text | Free text description (optional) |
| `fuel_or_material` | String(100) | e.g. diesel, grid_electricity, HFC-410A |
| `quantity` | Float | Amount of fuel/material consumed |
| `unit` | String(50) | See Unit values below |
| `period_year` | Integer | Reporting year e.g. 2024 |
| `period_month` | Integer | 1–12, nullable for annual records |
| `status` | Enum | See DataStatus below |
| `is_flagged_duplicate` | Boolean | True = potential duplicate |
| `flag_reason` | Text | Reason for quarantine or duplicate flag |
| `supplier_name` | String(255) | Scope 3 supplier name (optional) |
| `supplier_tier` | Integer | 1 = direct, 2+ = upstream (optional) |
| `created_at` | DateTime | Record creation timestamp |
| `updated_at` | DateTime | Last update timestamp |

**GHG Category values:**

*Scope 1:*
`stationary_combustion`, `mobile_combustion`, `company_vehicles`, `fugitive_emissions`

*Scope 2:*
`purchased_electricity`, `purchased_heat_steam`, `purchased_cooling`

*Scope 3:*
`purchased_goods_services`, `capital_goods`, `fuel_energy_activities`, `upstream_transportation`, `waste_operations`, `business_travel`, `employee_commuting`, `upstream_leased_assets`, `downstream_transportation`, `processing_sold_products`, `use_of_sold_products`, `end_of_life_treatment`, `downstream_leased_assets`, `franchises`, `investments`

**Unit values:**
`litre`, `kWh`, `MWh`, `km`, `kg`, `tonne`, `cubic_metre`, `passenger_km`

**DataStatus values:**
`pending`, `validated`, `quarantined`, `calculated`

---

## emission_factors

Versioned emission factor library. Each factor converts a unit of activity into raw gas masses.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `activity_type` | String(100) | Matches ghg_category in activity_records |
| `fuel_or_material` | String(100) | Matches fuel_or_material in activity_records |
| `region` | String(100) | ISO country code e.g. NG, GB. NULL = global default |
| `co2_factor` | Float | kg CO₂ per unit of activity |
| `ch4_factor` | Float | kg CH₄ per unit of activity |
| `n2o_factor` | Float | kg N₂O per unit of activity |
| `hfc_factor` | Float | kg HFC per unit of activity |
| `pfc_factor` | Float | kg PFC per unit of activity |
| `sf6_factor` | Float | kg SF₆ per unit of activity |
| `nf3_factor` | Float | kg NF₃ per unit of activity |
| `unit` | String(50) | Unit the factor applies per |
| `source` | Enum | DEFRA, IPCC, EPA, IEA, custom |
| `version` | String(50) | e.g. DEFRA 2023, IEA 2022 |
| `valid_from` | Date | Factor validity start date |
| `valid_to` | Date | Factor validity end date. NULL = currently active |
| `notes` | Text | Methodology notes (optional) |
| `created_at` | DateTime | Record creation timestamp |

---

## emission_records

Calculated output for a single activity record. One emission record per activity record.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `activity_record_id` | UUID | FK → activity_records.id (unique) |
| `emission_factor_id` | UUID | FK → emission_factors.id |
| `co2_kg` | Float | Raw CO₂ mass in kg |
| `ch4_kg` | Float | Raw CH₄ mass in kg |
| `n2o_kg` | Float | Raw N₂O mass in kg |
| `hfc_kg` | Float | Raw HFC mass in kg |
| `pfc_kg` | Float | Raw PFC mass in kg |
| `sf6_kg` | Float | Raw SF₆ mass in kg |
| `nf3_kg` | Float | Raw NF₃ mass in kg |
| `co2_co2e` | Float | CO₂ in CO₂e (kg × GWP) |
| `ch4_co2e` | Float | CH₄ in CO₂e (kg × GWP) |
| `n2o_co2e` | Float | N₂O in CO₂e (kg × GWP) |
| `hfc_co2e` | Float | HFC in CO₂e (kg × GWP) |
| `pfc_co2e` | Float | PFC in CO₂e (kg × GWP) |
| `sf6_co2e` | Float | SF₆ in CO₂e (kg × GWP) |
| `nf3_co2e` | Float | NF₃ in CO₂e (kg × GWP) |
| `total_co2e_kg` | Float | Sum of all gas CO₂e values in kg |
| `total_co2e_tonnes` | Float | total_co2e_kg / 1000 |
| `gwp_version` | Enum | AR5 or AR6 |
| `factor_fallback_used` | Boolean | True = global default factor applied |
| `calculated_at` | DateTime | Calculation timestamp |

---

## targets

An emission reduction commitment for an organisation.

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `organisation_id` | UUID | FK → organisations.id |
| `name` | String(255) | Target description |
| `target_type` | Enum | absolute or intensity |
| `scope_coverage` | Enum | scope_1_only, scope_1_2, scope_1_2_3 |
| `baseline_year` | Integer | Reference year for baseline |
| `target_year` | Integer | Year by which target must be met |
| `baseline_emissions_tco2e` | Float | Locked at target creation. Never updated. |
| `target_reduction_pct` | Float | e.g. 50.0 = 50% reduction |
| `target_emissions_tco2e` | Float | baseline × (1 − reduction_pct / 100) |
| `aligned_to` | String(100) | e.g. SBTi 1.5°C, Paris Agreement, internal |
| `notes` | Text | Additional context (optional) |
| `created_at` | DateTime | Record creation timestamp |

> **Important:** `baseline_emissions_tco2e` is locked at creation and should never be updated. Changing the baseline after a target is set undermines the integrity of progress reporting.

---

## Enum Reference

| Enum | Values |
|---|---|
| IndustryType | oil_and_gas, manufacturing, agriculture, financial_services, technology, retail, transportation, construction, energy_utilities, other |
| ScopeType | scope_1, scope_2, scope_3 |
| Scope2Method | location_based, market_based |
| DataSource | csv_upload, odk_submission, api_connector, manual_entry |
| DataStatus | pending, validated, quarantined, calculated |
| FactorSource | DEFRA, IPCC, EPA, IEA, custom |
| GWPVersion | AR5, AR6 |
| ScopeCoverage | scope_1_only, scope_1_2, scope_1_2_3 |
| TargetType | absolute, intensity |

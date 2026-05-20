# Methodology Statement

This document describes the greenhouse gas accounting methodology applied by the Arrhen platform. It is intended for sustainability professionals, third-party verifiers, and anyone evaluating the credibility of emission figures produced by the platform.

---

## Reporting Standard

Emissions are calculated in accordance with the **GHG Protocol Corporate Accounting and Reporting Standard** (World Resources Institute / World Business Council for Sustainable Development, revised edition).

The platform supports Scope 1, Scope 2, and Scope 3 reporting where activity data is available.

---

## Organisational Boundary

An **operational control** approach is used to define the organisational boundary. All sites over which the reporting organisation has full operational control are included in the inventory.

Sites can be added or deactivated without deleting historical data, preserving the integrity of prior reporting periods.

---

## Emission Scopes

### Scope 1 — Direct Emissions

Emissions from sources owned or directly controlled by the organisation. Includes:

- Stationary combustion (generators, boilers, furnaces)
- Mobile combustion (company-owned vehicles)
- Fugitive emissions (refrigerant leaks, gas pipeline losses)
- Process emissions where applicable

### Scope 2 — Indirect Energy Emissions

Emissions from the generation of purchased electricity, heat, steam, or cooling consumed by the organisation.

The platform supports both methodologies required by the GHG Protocol Scope 2 Guidance:

- **Location-based**: uses average grid emission factors for the country or region where energy is consumed
- **Market-based**: uses contractual instrument factors (RECs, PPAs, supplier-specific rates) where available

Where market-based data is not available, location-based figures are used and this is noted in the data quality statement.

### Scope 3 — Value Chain Emissions

Indirect emissions across the upstream and downstream value chain. The platform currently supports the following Scope 3 categories:

- Business travel (flights, road)
- Employee commuting
- Upstream transportation
- Purchased goods and services
- Waste operations

Scope 3 categories not listed above are not currently covered. Coverage will expand as additional emission factors are added to the library.

---

## Greenhouse Gases Tracked

The platform tracks all seven Kyoto Protocol greenhouse gases:

| Gas | Chemical Formula | Sources |
|---|---|---|
| Carbon dioxide | CO₂ | Combustion, industrial processes |
| Methane | CH₄ | Combustion, fugitive emissions, agriculture |
| Nitrous oxide | N₂O | Combustion, fertilisers |
| Hydrofluorocarbons | HFCs | Refrigerants, air conditioning |
| Perfluorocarbons | PFCs | Aluminium smelting, semiconductors |
| Sulphur hexafluoride | SF₆ | Electrical switchgear |
| Nitrogen trifluoride | NF₃ | Electronics manufacturing |

All gases are converted to carbon dioxide equivalent (CO₂e) using Global Warming Potential values.

---

## Global Warming Potential

The platform applies **GWP100** values from the **IPCC Sixth Assessment Report (AR6, 2021)** by default.

IPCC Fifth Assessment Report (AR5) values are also available and can be selected at the organisation level.

Key AR6 GWP100 values used:

| Gas | AR6 GWP100 | AR5 GWP100 |
|---|---|---|
| CO₂ | 1.0 | 1.0 |
| CH₄ | 27.9 | 28.0 |
| N₂O | 273.0 | 265.0 |
| HFC-410A | 2,088 | 2,088 |
| SF₆ | 25,200 | 23,500 |
| NF₃ | 17,400 | 16,100 |

The GWP version applied is stored on every emission record, enabling full recalculation under a different version without modifying source data.

---

## Emission Factor Library

Emission factors are sourced from the following authoritative references:

| Source | Version | Coverage |
|---|---|---|
| UK DEFRA | 2023 | Combustion fuels, vehicles, business travel |
| IEA | 2022 | Grid electricity by country |
| IPCC AR6 | 2021 | Refrigerants and industrial gases |

### Factor Selection Logic

For each activity record, the platform selects the most appropriate factor using the following priority order:

1. **Region-specific factor** — matches activity type, fuel, and country/region code
2. **Global default factor** — matches activity type and fuel, no region constraint

If a regional factor is unavailable and a global default is used, the emission record is flagged with `factor_fallback_used=true`. This flag is surfaced in the data quality statement of all reports.

### Adding Custom Factors

Organisations can add custom emission factors to the database with their own source attribution and validity dates. Custom factors follow the same selection logic and version tracking as the built-in library.

---

## Calculation Methodology

For each activity record the calculation proceeds as follows:

**Step 1 — Raw gas masses**

```
raw_gas_kg = activity_quantity × emission_factor_per_unit
```

Calculated separately for CO₂, CH₄, N₂O, HFCs, PFCs, SF₆, NF₃.

**Step 2 — CO₂e conversion**

```
gas_co2e = raw_gas_kg × GWP100_value
```

**Step 3 — Total**

```
total_co2e = sum of all gas_co2e values
total_co2e_tonnes = total_co2e_kg / 1000
```

Both raw gas masses (kg) and CO₂e values are stored separately on each emission record. This allows recalculation under a different GWP version without modifying source data.

---

## Materiality

Emission sources representing **1% or more** of total reported emissions are classified as material. Material sources are highlighted in the dashboard and reports.

The materiality threshold can be adjusted per screening run. Sources below the threshold are included in totals but may rely on estimation rather than direct measurement.

---

## Data Quality

### Duplicate Detection

The platform flags activity records as potential duplicates if the same combination of site, scope, category, fuel, year, and month appears more than once. Flagged duplicates are excluded from calculations unless manually reviewed and cleared.

### Quarantine

Records that fail validation (invalid field values, missing required fields, out-of-range quantities) are quarantined and excluded from calculations. Quarantine reasons are stored on the record and visible in the Flags & Quarantine page.

### Audit Trail

Every emission record carries:

- The source activity record ID
- The emission factor ID, source, version, and validity dates
- The GWP version applied
- A fallback flag if a global default factor was used
- The calculation timestamp

This audit trail is exportable as a JSON document from the Reports page.

---

## Limitations

- This platform does not replace third-party verification. Emission figures should be independently assured before use in public disclosures or regulatory submissions.
- Scope 3 coverage is partial. Categories not listed in this document are not currently supported.
- Emission factors are updated periodically. Figures calculated against older factor versions are not automatically recalculated when new versions are published. Recalculation must be triggered manually.
- The platform does not currently support carbon offset accounting or net emission figures.

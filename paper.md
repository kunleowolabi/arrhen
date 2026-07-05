---
title: 'Arrhen: An Open-Source Carbon Emission Tracking Platform for Emerging Markets'
tags:
  - carbon accounting
  - greenhouse gas emissions
  - GHG Protocol
  - sustainability
  - ODK
  - KoboToolbox
  - Python
  - FastAPI
  - React
authors:
  - name: [AUTHOR NAME]
    orcid: 0000-0000-0000-0000
    affiliation: 1
affiliations:
  - name: Independent Researcher
    index: 1
date: 2026
bibliography: paper.bib
---

# Summary

Arrhen is a self-hosted, open-source carbon emission tracking platform that
enables organisations to measure, calculate, and report greenhouse gas (GHG)
emissions in accordance with the GHG Protocol Corporate Accounting and Reporting
Standard [@ghgprotocol2004]. It implements a multi-scope (Scope 1, 2, and 3)
emission calculation engine using DEFRA 2023 and IEA 2022 emission factors, with
Global Warming Potential values sourced from the IPCC Sixth Assessment Report
[@ipcc2021]. The platform natively integrates with ODK [@anokwa2010] and
KoboToolbox, enabling field-collected activity data to flow directly into the
calculation engine — a pipeline with no equivalent in existing open-source carbon
accounting tools.

# Statement of Need

Corporate carbon accounting in Africa is primarily consultant-led, producing
annual sustainability reports that are expensive to commission, difficult to
audit, and provide no ongoing operational insight to the organisations they
describe [@seedling2026]. Enterprise carbon accounting software (Watershed,
Persefoni, IBM Envizi) operates at price points of $50,000–$200,000 per year
[@carbonmarketnetwork2026], inaccessible to the SMEs and mid-market companies
that constitute the majority of emitters across sub-Saharan Africa.

This gap is becoming critical under emerging regulation. Nigeria's Climate Change
Act 2021 mandates GHG reporting for qualifying private and public entities by
2027 and establishes the framework for a national Emissions Trading Scheme
[@cca2021]. Nigeria's National Carbon Market Activation Policy (NCMAP), launched
in 2025, targets $2.5 billion in carbon credit revenue by 2030 [@ncmap2025].
South Africa's mandatory carbon budgeting system commenced in January 2026 under
the Climate Change Act 2024 [@ens2025]. Participation in these markets requires
organisations to hold traceable, methodology-transparent emission inventories —
precisely what consultant-led annual reporting fails to provide.

Two secondary user groups face related data scarcity problems. Non-governmental
organisations working on climate programmes lack reliable emissions baselines
against which to measure intervention impact. Government agencies responsible
for national GHG inventories and carbon market oversight have limited access to
primary-source organisational data from private sector entities.

Arrhen addresses these problems by providing a free, self-hosted platform that
organisations can operate internally, with no per-seat pricing, no data transfer
to third parties, and a full audit trail for every emission record. The platform
is designed for the data infrastructure realities of emerging markets: activity
data is captured via ODK-compatible mobile forms that function offline, and the
calculation engine requires no specialist knowledge to operate.

# Related Software

Several open-source tools address adjacent problems:

**GHG Emissions Factor Libraries** (e.g., `pyfactor`, `ghgpy`) provide programmatic
access to emission factors but do not implement a full accounting workflow.

**CKAN-based data portals** enable open data publication but do not perform
calculations or provide operational dashboards.

**Commercial platforms** (Watershed, Persefoni, Greenly, Plan A) implement
comparable functionality but are closed-source, priced for enterprise markets,
and do not support field data collection integration.

Arrhen is the only open-source platform that combines a GHG Protocol-aligned
calculation engine with a native ODK/KoboToolbox ingestion pipeline and a
production-ready multi-tenant web interface.

# Technical Implementation

## Calculation Engine

The emission calculation engine converts activity records to CO₂e using the
following procedure:

$$\text{gas\_kg} = \text{quantity} \times \text{emission\_factor}$$

$$\text{gas\_co2e} = \text{gas\_kg} \times \text{GWP}_{100}$$

$$\text{total\_co2e} = \sum_{\text{gases}} \text{gas\_co2e}$$

All seven Kyoto Protocol gases (CO₂, CH₄, N₂O, HFCs, PFCs, SF₆, NF₃) are
tracked. For HFC and PFC compounds, per-compound GWP values are applied where
the specific compound is known (e.g., HFC-134a: 1,526; HFC-410A: 2,088 in AR6),
with a flagged aggregate fallback for unspecified compounds.

Emission factors are selected using a regional fallback hierarchy: a
region-specific factor is preferred; if unavailable, a global default factor is
applied and the record is flagged with `factor_fallback_used=true`. Every
emission record stores the factor ID, version, GWP version, fallback flag, and
calculation timestamp, providing a complete calculation audit trail.

Batch calculations flush per record to the database session and issue a single
commit at the end of the batch. Failed records are marked with an error status
and excluded from dashboard totals; the batch continues. This design ensures
partial batch failures are recoverable and do not corrupt inventory data.

## ODK/KoboToolbox Integration

The ODK connector fetches form submissions from KoboToolbox via the REST API
and applies a one-to-many splitting operation to transform a single form
submission into multiple `ActivityRecord` rows. For example, a daily site
operations form recording generator hours, diesel tank readings, and a
refrigerant top-up generates three separate activity records — one per emission
source. Group-prefixed field names (a KoboToolbox structural artifact) are
flattened before processing.

This integration reflects the operational reality of energy-sector field data
collection: a single daily log covers multiple emission-generating activities
across different GHG categories and scopes. ODK has been used at scale across
global health [@undp_odk], environmental monitoring [@techforwildlife2022], and
agricultural programmes [@odk_researchgate], and has established infrastructure
in many of the same organisations likely to adopt Arrhen for carbon monitoring.

## Data Model

The platform separates raw input (`activity_records`) from calculated output
(`emission_records`), enabling recalculation under a different GWP version
without modifying source data. Emission factors carry `valid_from` and `valid_to`
dates; factor selection respects the validity window of the reporting period, not
the current date, preventing retroactive changes to published figures.

## Architecture

The platform uses a FastAPI backend with SQLAlchemy 2.0 ORM and Supabase
(PostgreSQL + PostGIS) for persistence. The React frontend communicates with the
backend via a JWT-authenticated REST API. Supabase Row Level Security is enabled
on all tables, providing database-level data isolation between organisations.
GeoJSON endpoints power a Leaflet.js map showing emission intensity by site.

# Acknowledgements

We acknowledge the GHG Protocol Initiative for the methodological foundation on
which this platform is built.

# References


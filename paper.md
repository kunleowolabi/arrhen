---
title: 'Arrhen: A GHG Protocol-Aligned Calculation Engine with Native ODK Field-Data Integration'
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

Arrhen is an open-source implementation of the GHG Protocol Corporate
Accounting and Reporting Standard's emission calculation methodology
[@ghgprotocol2004], combining a per-gas, per-compound calculation engine
with a native data-ingestion pipeline from ODK-based field collection
tools [@anokwa2010]. The engine resolves emissions across all seven
Kyoto Protocol gases, applies IPCC Sixth Assessment Report Global
Warming Potential values with per-compound resolution for HFCs and
PFCs [@ipcc2021], and maintains a complete calculation audit trail —
factor version, GWP version, and fallback status — for every emission
record produced. Its distinguishing technical contribution is a
one-to-many ingestion pipeline that transforms a single ODK/KoboToolbox
form submission into multiple structured activity records spanning
different GHG categories and scopes, a transformation with no existing
open-source precedent connecting field-collected survey data directly
to a GHG Protocol-compliant calculation engine. A reference web
application built on top of the engine demonstrates the methodology in
a deployable, multi-tenant, audit-ready context.

# Statement of Need

Reproducible, methodology-transparent greenhouse gas accounting is a
prerequisite for any credible carbon market or regulatory reporting
regime, yet open, auditable reference implementations of the GHG
Protocol's calculation methodology remain scarce relative to the
standard's near-universal adoption. Existing open-source contributions
in this space are narrow in scope: `bonsai_ipcc` [@budzinski2024]
provides a Python package for national-level GHG inventory estimation
following IPCC guidelines, but targets country-level reporting rather
than corporate Scope 1/2/3 accounting and does not integrate a field
data-collection layer. `GES 1point5` [@ges1point5] is an open-source
web application for estimating the carbon footprint of academic
research institutions, published and peer-reviewed as research
software [@heiligenstein2022], demonstrating that web-based GHG
accounting tools are an accepted category of research software — but
its monetary emission-factor methodology and institutional scope do
not extend to multi-site corporate accounting or primary field-activity
ingestion. Lightweight CLI calculators such as `ghg-calculator`
[@starrybodies2026] embed emission factor databases for stateless,
single-scenario computation, but do not maintain a persistent data
model, lineage tracking, or multi-period audit trail.

Separately, ODK and its XLSForm standard are extensively used for
primary data collection in environmental monitoring, public health, and
agricultural research [@techforwildlife2022; @odk_researchgate], and
KoboToolbox — an ODK-compatible platform maintained as a nonprofit
initiative of the Harvard Humanitarian Initiative — is deployed by tens
of thousands of organisations globally [@kobo2026]. No published
open-source work, to our knowledge, connects ODK-collected field
activity data directly to a GHG Protocol-compliant calculation engine
with automatic decomposition of a single field submission into multiple
emission-source records. This is a non-trivial transformation: a single
daily operational log recording generator fuel consumption, refrigerant
top-up, and grid electricity use corresponds to at least three distinct
GHG categories and potentially two different emission scopes, each
requiring independent factor resolution and gas-specific GWP
application. Arrhen implements and demonstrates this transformation as
a reusable pipeline pattern, closing a gap between the field-data
collection tooling used throughout environmental and development
research and the calculation methodology required to convert that data
into standards-compliant emissions figures.

This gap has practical urgency in the regulatory environment motivating
this work. Nigeria's Climate Change Act 2021 mandates GHG reporting for
qualifying organisations by 2027 [@cca2021], Nigeria's National Carbon
Market Activation Policy targets $2.5 billion in carbon credit revenue
by 2030 [@ncmap2025], and South Africa's mandatory carbon budgeting
regime began its first commitment period in January 2026 [@ens2025].
Organisations entering these markets require calculation infrastructure
that is both methodologically correct and auditable by third parties —
properties that a closed-source or ad hoc spreadsheet-based approach
cannot readily provide.

# Related Software

**GHG calculation methodology software.** `bonsai_ipcc` [@budzinski2024]
is the closest published precedent for open-source, JOSS-reviewed GHG
calculation software; it targets national inventory compilation under
IPCC guidelines rather than corporate multi-scope accounting, and
includes no data-ingestion or web-interface layer. `GES 1point5`
[@ges1point5] demonstrates that a web-based GHG accounting tool is
acceptable as research software, but is scoped to research-institution
carbon footprinting using monetary emission factors, not corporate
GHG Protocol accounting with physical activity-based factors.
`ghg-calculator` [@starrybodies2026] embeds a large emission-factor
database for CLI-driven, stateless calculation without a persistent
audit trail.

**Commercial carbon accounting platforms.** Watershed, Persefoni, and
IBM Envizi implement comparable Scope 1/2/3 calculation functionality
with production-grade dashboards, but are closed-source, priced for
enterprise budgets, and expose no calculation methodology for
independent audit or academic citation.

**ODK-based field data collection.** ODK [@anokwa2010] and KoboToolbox
are mature, widely-deployed platforms for offline-capable field survey
collection, used extensively in environmental and public health
research [@techforwildlife2022]. Neither platform, nor any tool built
upon them that we are aware of, includes a GHG-specific calculation
engine or a defined transformation from survey submission structure to
multi-scope emission records.

Arrhen's contribution is the combination that none of the above provide
individually: a GHG Protocol-compliant, audit-tracked calculation engine
paired with a concrete, reusable ODK-to-emissions ingestion pattern.

# Technical Implementation

## Calculation Engine

The emission calculation engine converts activity records to CO₂e using
the following procedure:

$$\text{gas\_kg} = \text{quantity} \times \text{emission\_factor}$$

$$\text{gas\_co2e} = \text{gas\_kg} \times \text{GWP}_{100}$$

$$\text{total\_co2e} = \sum_{\text{gases}} \text{gas\_co2e}$$

All seven Kyoto Protocol gases (CO₂, CH₄, N₂O, HFCs, PFCs, SF₆, NF₃) are
tracked. For HFC and PFC compounds, per-compound GWP values are applied
where the specific compound is known (e.g., HFC-134a: 1,526; HFC-410A:
2,088 in AR6), with a flagged aggregate fallback for unspecified
compounds — a resolution granularity not present in the simpler
factor-lookup approach used by CLI-style calculators.

Emission factors are selected using a regional fallback hierarchy: a
region-specific factor is preferred; if unavailable, a global default
factor is applied and the record is flagged with
`factor_fallback_used=true`. Every emission record stores the factor
ID, version, GWP version, fallback flag, and calculation timestamp,
providing a complete calculation audit trail — the property required
for third-party verification that stateless calculators do not provide.

Batch calculations flush per record to the database session and issue a
single commit at the end of the batch. Failed records are marked with
an error status and excluded from dashboard totals; the batch
continues. This design ensures partial batch failures are recoverable
and do not corrupt inventory data.

## ODK/KoboToolbox Integration

The ODK connector fetches form submissions from KoboToolbox via the
REST API and applies a one-to-many splitting operation to transform a
single form submission into multiple `ActivityRecord` rows. A daily
site operations form recording generator hours, diesel tank readings,
and a refrigerant top-up generates three separate activity records —
one per emission source, each independently routed to the correct GHG
category and scope. Group-prefixed field names, a structural artifact
of KoboToolbox's form-group syntax, are flattened before processing;
site identifiers submitted in form-specific vocabulary (e.g.
`lagos_hq`) are normalised to the platform's canonical site coding
scheme prior to record creation.

This transformation pattern — decomposing a single structured
observation into multiple typed, independently-auditable calculation
inputs — is the paper's primary reusable technical contribution, and is
implemented as a standalone module (`kobo_connector.py`) independent of
the web application, making it directly adoptable by other GHG
accounting or research software that ingests ODK-family submissions.

## Data Model

The platform separates raw input (`activity_records`) from calculated
output (`emission_records`), enabling recalculation under a different
GWP version without modifying source data. Emission factors carry
`valid_from` and `valid_to` dates; factor selection respects the
validity window of the reporting period, not the current date,
preventing retroactive changes to published figures.

## Architecture

The reference implementation uses a FastAPI backend with SQLAlchemy 2.0
ORM and Supabase (PostgreSQL + PostGIS) for persistence. The React
frontend communicates with the backend via a JWT-authenticated REST
API. Row Level Security is enabled on all tables, providing
database-level data isolation between organisations in the multi-tenant
deployment model. GeoJSON endpoints power a map interface showing
emission intensity by site, demonstrating the engine's output in a
geospatial reporting context.

# Acknowledgements

We acknowledge the GHG Protocol Initiative for the methodological
foundation on which this work is built, and the ODK and KoboToolbox
communities for establishing the field-data collection standards this
work integrates with.

# References


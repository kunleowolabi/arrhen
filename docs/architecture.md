# Architecture

This document describes the technical design of the Arrhen platform — intended for developers, contributors, and technical reviewers.

---

## System Overview

Arrhen is a full-stack web application with a Python/FastAPI backend, a PostgreSQL database (Supabase), and a React frontend.

```
┌─────────────────┐         ┌──────────────────────┐
│ React Frontend  │◄───────►│  FastAPI Backend      │
│ (Vite, port     │  HTTP   │  (Uvicorn, port 8000) │
│  5173)          │  JSON   │                       │
└─────────────────┘         └──────────┬────────────┘
                                        │ SQLAlchemy
                                        ▼
                             ┌──────────────────────┐
                             │       Supabase        │
                             │  PostgreSQL + PostGIS │
                             └──────────────────────┘
```

---

## Backend

### Framework

FastAPI with Uvicorn as the ASGI server. Auto-generates OpenAPI documentation at `/docs`.

### Database Layer

SQLAlchemy 2.0 ORM with Alembic for schema migrations. Connects to Supabase via the connection pooler URL (session mode) for stability with Python connection pools.

### Core Modules

```
backend/core/
├── calculations/
│   ├── gwp.py              # GWP constants (AR5 + AR6)
│   ├── factor_selector.py  # Factor selection with fallback logic
│   ├── engine.py           # Calculation engine (single + batch)
│   └── scope2_handler.py   # Scope 2 dual methodology
├── pipelines/
│   ├── validator.py        # Shared row validation logic
│   ├── csv_importer.py     # CSV ingestion pipeline
│   ├── odk_connector.py    # ODK Central + KoboToolbox connector
│   └── api_connector.py    # Generic configurable API connector
├── materiality/
│   └── screener.py         # Materiality screening + breakdowns
└── reporting/
    └── report_generator.py # PDF + JSON report generation
```

### API Structure

All endpoints are prefixed `/api/v1/`.

```
/organisations    CRUD for organisations and sites
/activity         Upload, list, lineage tracking
/calculations     Trigger engine, pending status
/factors          Emission factor library
/dashboard        Aggregated data for frontend charts
/geo              GeoJSON endpoints for Leaflet
/reports          PDF, JSON, audit trail downloads
```

### Data Flow — Upload to Dashboard

```
User uploads CSV
        ↓
csv_importer.py
  Parses rows
  Validates each row (validator.py)
  Flags duplicates
  Writes ActivityRecords (status=validated)
  Writes DataLineage record
        ↓
User clicks Process Pending Records
        ↓
engine.calculate_batch()
  Queries all validated ActivityRecords
  For each: factor_selector → gwp → calculate
  Writes EmissionRecords
  Updates ActivityRecord status → calculated
        ↓
Dashboard endpoints query EmissionRecords
  Aggregated by scope, site, category
  Returned as JSON to frontend
        ↓
React renders charts and tables
```

---

## Database Schema

### Core Tables

| Table | Purpose |
|---|---|
| `organisations` | Reporting entities |
| `sites` | Physical locations with PostGIS coordinates |
| `data_lineage` | Upload event audit trail |
| `activity_records` | Raw activity data (input) |
| `emission_factors` | Versioned factor library |
| `emission_records` | Calculated emissions (output) |
| `targets` | Reduction commitments |

### Key Design Decisions

**Separate activity and emission records**

Activity records store raw data. Emission records store calculated outputs. This separation means raw data is never modified by calculations — recalculation under a different GWP version creates a new emission record, it does not overwrite the original.

**Versioned emission factors**

Each factor has `valid_from` and `valid_to` dates. The factor selector finds the factor valid at the time the activity occurred, not the most recently added factor. This prevents retroactive changes to published figures.

**PostGIS on sites**

Each site stores both plain float coordinates (latitude, longitude) and a PostGIS Geography point. The float coordinates are used for simple display; the Geography column enables spatial queries (regional aggregation, distance calculations, emission intensity mapping).

**Data lineage on every record**

Every ActivityRecord links back to a DataLineage entry recording the upload source, filename, uploader, and timestamp. This is the foundation of the audit trail.

---

## Frontend

### Stack

React 18, Vite, Tailwind CSS v4, React Router v6.

### Design System

CSS custom properties defined in `src/index.css`. All colours, typography, and spacing reference these tokens. No hardcoded values in components.

### Page Structure

```
src/
├── api/
│   └── client.js           # Axios instance + all API functions
├── components/
│   └── layout/
│       ├── Layout.jsx       # Shell with sidebar + outlet
│       └── Sidebar.jsx      # Navigation + org name
└── pages/
    ├── Overview.jsx         # KPIs, target banner, scope charts
    ├── Trends.jsx           # Year-on-year line + area charts
    ├── Sites.jsx            # Map + site table + comparison chart
    ├── Factors.jsx          # Factor library browser
    ├── DataManagement.jsx   # CSV upload + calculations
    ├── Flags.jsx            # Quarantine + duplicate review
    └── Reports.jsx          # PDF + JSON + audit trail export
```

### Responsive Design

The sidebar collapses to a bottom tab bar on screens narrower than 768px (`md` breakpoint). Content grids use `auto-fit` columns that reflow on small screens. Tables have horizontal scroll on mobile.

---

## Geospatial Layer

PostGIS is enabled on the Supabase project. The `sites` table includes a `Geography(POINT, 4326)` column populated when a site is created with coordinates.

The `/geo/emission-intensity` endpoint joins site coordinates with emission totals and returns a GeoJSON FeatureCollection. Each feature includes an `intensity_score` (0.0–1.0) used by Leaflet to colour-code map markers.

---

## Reporting

### PDF

Generated server-side using ReportLab. No browser rendering required. Contains: cover page, methodology statement, scope summary, site breakdown, materiality analysis, data quality statement, reduction targets.

### JSON Inventory

Full structured export of all emission records for a period, including factor provenance and methodology metadata. Suitable for regulatory portal submission or parent company consolidation.

### Audit Trail

Record-level export showing every emission record alongside its source activity, factor applied, GWP version, fallback flag, and calculation timestamp. Designed for third-party verification.

---

## Extension Points

The architecture is deliberately extensible at several points:

**New emission factors**

Insert rows into `emission_factors` with the correct `activity_type`, `fuel_or_material`, `region`, and validity dates. No code changes required.

**New data sources**

Implement a connector following the pattern in `pipelines/api_connector.py`. Define a `ConnectorConfig` with the source URL, auth method, and field mapping.

**New report formats**

Add a generator function in `reporting/report_generator.py` and a corresponding endpoint in `api/reports.py`.

**Async processing**

The calculation engine is designed to run as a Celery task. Wire `calculate_batch` to a Celery worker and add a job status endpoint for frontend polling.

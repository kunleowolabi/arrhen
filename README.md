# Arrhen — Carbon Emission Tracking Platform

A sustainability data management platform for tracking, calculating, and reporting greenhouse gas emissions. Built on the GHG Protocol Corporate Standard.

---

## What It Does

Arrhen helps organisations measure and manage their carbon footprint across all three emission scopes:

- **Data ingestion** — upload activity data via CSV or connect field data collection tools (ODK, KoboToolbox)
- **Emission calculations** — automatic conversion of activity data to CO₂e using versioned emission factor libraries
- **Dashboard** — real-time emission summaries, scope breakdowns, site comparisons, and target tracking
- **Geospatial mapping** — emission intensity visualised across sites on an interactive map
- **Reporting** — PDF emission reports, JSON inventory exports, and full audit trail downloads

---

## Tech Stack

| Layer | Technology |
|---|---|
| Database | Supabase (PostgreSQL + PostGIS) |
| Backend | Python 3.14, FastAPI, SQLAlchemy 2.0 |
| Migrations | Alembic |
| Frontend | React, Vite, Tailwind CSS v4 |
| Charts | Recharts |
| Maps | Leaflet.js + react-leaflet |
| PDF Reports | ReportLab |
| Data pipelines | Pandas |

---

## Project Structure

```
arrhen/
├── backend/
│   ├── api/                    # FastAPI route handlers
│   ├── core/
│   │   ├── calculations/       # Emission factor engine, GWP conversion
│   │   ├── pipelines/          # CSV + ODK data ingestion
│   │   ├── materiality/        # Materiality screening
│   │   └── reporting/          # PDF + JSON report generation
│   ├── models/                 # SQLAlchemy models
│   ├── schemas/                # Pydantic request/response schemas
│   └── db/                     # Database connection + Alembic migrations
├── data/
│   ├── emission_factors/       # Factor library reference data
│   ├── sample_data/            # Sample CSV templates
│   └── seed.py                 # Database seed script
├── docs/                       # Methodology, architecture, data dictionary
├── frontend/                   # React application
├── tests/                      # Test suite
├── .env.example                # Environment variable template
└── requirements.txt            # Python dependencies
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- A Supabase project with PostGIS enabled

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/arrhen.git
cd arrhen
```

### 2. Set up the Python environment

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in:

```
DATABASE_URL=postgresql://postgres.yourref:password@aws-0-region.pooler.supabase.com:5432/postgres
SUPABASE_URL=https://yourref.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SECRET_KEY=your-secret-key
DEFAULT_GWP_VERSION=AR6
```

Generate a secret key:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Run database migrations

```bash
alembic upgrade head
```

### 5. Seed the database

```bash
python3 data/seed.py
```

### 6. Start the backend

```bash
uvicorn backend.main:app --reload --port 8000
```

API documentation available at `http://localhost:8000/docs`

### 7. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Application available at `http://localhost:5173`

---

## Data Upload

Arrhen accepts activity data via CSV upload. Download the template from the Data Management page or use the format below:

```
site_code, scope, ghg_category, fuel_or_material, quantity, unit,
period_year, period_month, scope_2_method, activity_description
```

After uploading, click **Process Pending Records** on the Data Management page to run calculations.

See `docs/data_dictionary.md` for valid field values.

---

## API Reference

Full interactive API documentation is available at `http://localhost:8000/docs` when the backend is running.

Key endpoint groups:

| Prefix | Purpose |
|---|---|
| `/api/v1/organisations` | Organisation and site management |
| `/api/v1/activity` | Activity record upload and retrieval |
| `/api/v1/calculations` | Trigger calculations, view results |
| `/api/v1/factors` | Emission factor library |
| `/api/v1/dashboard` | Aggregated data for frontend |
| `/api/v1/geo` | GeoJSON endpoints for map |
| `/api/v1/reports` | PDF and JSON report generation |

---

## Licence

Licensed under the Business Source Licence 1.1. Free for internal, research, and non-commercial use. See `COMMERCIAL.md` for commercial licensing.

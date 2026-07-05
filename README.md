# Arrhen

Open-source carbon emission tracking platform built for organisations in emerging markets.

[![License: BUSL-1.1](https://img.shields.io/badge/License-BUSL--1.1-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.14+-green.svg)](https://python.org)
[![DOI](https://joss.theoj.org/papers/placeholder/status.svg)](https://joss.theoj.org)

---

## Statement of Need

Corporate carbon accounting in Africa is primarily outsourced to sustainability consultants who publish an annual report on their client's behalf. This creates data exposure risk, introduces inaccuracy through secondhand data collection, and leaves organisations with no internal capacity to engage with their own emissions data. At the same time, enterprise carbon accounting platforms (Watershed, Persefoni, IBM Envizi) are priced between $50,000–$200,000 per year — inaccessible to the SMEs and mid-market companies that constitute the majority of emitters in emerging economies.

This gap is sharpening under new regulation. Nigeria's Climate Change Act 2021 mandates GHG reporting for qualifying organisations by 2027 and establishes the National Council on Climate Change (NCCC) as regulator of a nascent Emissions Trading Scheme. South Africa's mandatory carbon budgeting system began its first commitment period in January 2026. Across the continent, the African Carbon Markets Initiative (ACMI) targets 300 million carbon credits annually by 2030. Companies without traceable, methodology-transparent emission records are excluded from these markets.

Arrhen addresses this by providing a free, self-hosted, GHG Protocol-aligned carbon accounting platform that organisations can operate internally — with no per-seat pricing, no data exposure to third parties, and full audit trail transparency. Its core differentiator is a native integration with ODK/KoboToolbox, the standard mobile data collection framework used by WHO, USAID, and the Red Cross for field data collection in low-connectivity environments. This integration allows field technicians to log daily operational activity directly into structured forms that feed automatically into the emission calculation engine — eliminating the manual data extraction step that makes consultant-led accounting inaccurate and expensive.

---

## Functionality

- **Scope 1, 2, and 3 emission tracking** aligned with the GHG Protocol Corporate Standard
- **Emission calculation engine** applying DEFRA 2023 and IEA 2022 factors with IPCC AR6 GWP100 values; AR5 also supported
- **Per-compound GWP resolution** for HFCs and PFCs (HFC-134a, HFC-410A, etc.)
- **ODK/KoboToolbox connector** — field form submissions split into validated activity records automatically
- **CSV ingestion pipeline** with duplicate detection, quarantine, and full data lineage
- **Multi-site, multi-scope dashboard** with target tracking, trend analysis, and geospatial emission intensity mapping
- **PDF and JSON report generation** with audit trail export suitable for third-party verification
- **Role-based access control** — admin, analyst, and viewer roles per organisation
- **Multi-tenant architecture** — multiple organisations on shared infrastructure with row-level data isolation

---

## Installation

### Prerequisites

- Python 3.14+
- Node.js 18+
- Supabase project with PostGIS enabled

### Backend

```bash
git clone https://github.com/[AUTHOR]/arrhen.git
cd arrhen

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Fill in DATABASE_URL, SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_JWT_SECRET

alembic upgrade head
python3 data/seed.py

uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Application runs at `http://localhost:5173`. API documentation at `http://localhost:8000/docs`.

### Environment Variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | Supabase pooler connection string (session mode) |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anonymous key |
| `SUPABASE_JWT_SECRET` | JWT secret for token verification |
| `DEFAULT_GWP_VERSION` | `AR6` or `AR5` |
| `ALLOWED_ORIGINS` | Comma-separated list of allowed CORS origins |
| `KOBO_API_TOKEN` | KoboToolbox API token (optional) |

See `.env.example` for the full list.

---

## Data Upload

Activity data is ingested via:

1. **CSV upload** — download the template from the Data Management page, populate with activity data, and upload. Run calculations after each upload.
2. **KoboToolbox integration** — connect field data collection forms; submissions are fetched and split into activity records automatically.

See `docs/data_dictionary.md` for valid field values.

---

## Testing

```bash
python3 -m pytest tests/ -v
```

Tests cover GWP constant correctness, per-compound HFC/PFC resolution, CSV validation and injection protection, and emission calculation accuracy against manually verified reference values.

---

## Documentation

| Document | Contents |
|---|---|
| [`docs/methodology.md`](docs/methodology.md) | GHG Protocol alignment, factor sources, GWP values, scope coverage, limitations |
| [`docs/architecture.md`](docs/architecture.md) | System design, data flow, API structure, extension points |
| [`docs/data_dictionary.md`](docs/data_dictionary.md) | Every table, field, valid values, units, relationships |

---

## Licence

Source-available under the [Business Source Licence 1.1](LICENSE) (BUSL-1.1). Free for internal, research, educational, and non-commercial use. Converts to Apache 2.0 on 20 May 2029. See [COMMERCIAL.md](COMMERCIAL.md) for commercial licensing.


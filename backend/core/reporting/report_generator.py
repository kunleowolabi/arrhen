"""
Report Generator

Produces two output formats:

1. JSON — full structured emission inventory with lineage
2. PDF  — clean structured report using ReportLab
           Cover page, methodology, scope summary, site breakdown,
           materiality analysis, data quality statement

Both formats are audit-ready and methodology-transparent.
"""

from datetime import datetime
from sqlalchemy.orm import Session
from uuid import UUID

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, HRFlowable, PageBreak,
)
from reportlab.lib import colors

from backend.models import (
    Organisation, Site, ActivityRecord,
    EmissionRecord, EmissionFactor, Target,
)
from backend.models.enums import ScopeType
from backend.core.materiality.screener import (
    get_scope_breakdown,
    get_site_breakdown,
    run_materiality_screen,
)


# ── Colour palette ─────────────────────────────────────────────────────────────
BLACK = colors.HexColor('#0A0A0A')
DARK_GREY = colors.HexColor('#525252')
MID_GREY = colors.HexColor('#A3A3A3')
LIGHT_GREY = colors.HexColor('#F4F4F4')
BORDER_GREY = colors.HexColor('#E5E5E5')
WHITE = colors.white


# ── JSON Report ────────────────────────────────────────────────────────────────

def generate_json_report(
    db: Session,
    organisation_id: UUID,
    period_year: int,
) -> dict:
    """
    Generates a complete structured JSON emission inventory.
    Includes all emission records with full lineage and factor provenance.
    """
    org = db.query(Organisation).filter_by(id=organisation_id).first()
    if not org:
        return {"error": "Organisation not found"}

    scope_data = get_scope_breakdown(db, organisation_id, period_year)
    site_data = get_site_breakdown(db, organisation_id, period_year)
    materiality = run_materiality_screen(db, organisation_id, period_year)

    # Fetch all emission records with activity and factor detail
    rows = (
        db.query(ActivityRecord, EmissionRecord, EmissionFactor, Site)
        .join(
            EmissionRecord,
            ActivityRecord.id == EmissionRecord.activity_record_id,
        )
        .join(
            EmissionFactor,
            EmissionRecord.emission_factor_id == EmissionFactor.id,
        )
        .join(Site, ActivityRecord.site_id == Site.id)
        .filter(
            Site.organisation_id == organisation_id,
            ActivityRecord.period_year == period_year,
        )
        .all()
    )

    records = []
    for activity, emission, factor, site in rows:
        records.append({
            "record_id": str(emission.id),
            "activity_record_id": str(activity.id),
            "site": {
                "id": str(site.id),
                "code": site.site_code,
                "name": site.name,
                "region": site.region,
                "country": site.country,
            },
            "activity": {
                "scope": activity.scope.value,
                "ghg_category": activity.ghg_category,
                "fuel_or_material": activity.fuel_or_material,
                "quantity": activity.quantity,
                "unit": activity.unit,
                "period_year": activity.period_year,
                "period_month": activity.period_month,
                "description": activity.activity_description,
                "is_duplicate": activity.is_flagged_duplicate,
            },
            "emission_factor": {
                "id": str(factor.id),
                "source": factor.source.value,
                "version": factor.version,
                "region": factor.region,
                "fallback_used": emission.factor_fallback_used,
            },
            "emissions": {
                "gwp_version": emission.gwp_version.value,
                "co2_kg": emission.co2_kg,
                "ch4_kg": emission.ch4_kg,
                "n2o_kg": emission.n2o_kg,
                "hfc_kg": emission.hfc_kg,
                "sf6_kg": emission.sf6_kg,
                "co2_co2e": emission.co2_co2e,
                "ch4_co2e": emission.ch4_co2e,
                "n2o_co2e": emission.n2o_co2e,
                "hfc_co2e": emission.hfc_co2e,
                "sf6_co2e": emission.sf6_co2e,
                "total_co2e_kg": emission.total_co2e_kg,
                "total_co2e_tonnes": emission.total_co2e_tonnes,
                "calculated_at": emission.calculated_at.isoformat(),
            },
        })

    return {
        "report_metadata": {
            "generated_at": datetime.utcnow().isoformat(),
            "organisation": {
                "id": str(org.id),
                "name": org.name,
                "industry": org.industry.value,
                "country": org.country,
            },
            "period_year": period_year,
            "methodology": {
                "standard": "GHG Protocol Corporate Standard",
                "emission_factor_sources": ["DEFRA 2023", "IEA 2022", "IPCC AR6"],
                "gwp_standard": "IPCC AR6 GWP100",
                "scope_2_method": "Location-based (market-based where available)",
            },
            "data_quality": {
                "total_records": len(records),
                "fallback_factor_records": sum(
                    1 for r in records
                    if r["emission_factor"]["fallback_used"]
                ),
                "coverage_note": (
                    "Records using global default factors are flagged "
                    "as fallback_used=true. Regional factors preferred "
                    "where available."
                ),
            },
        },
        "summary": {
            "scope_breakdown": scope_data,
            "site_breakdown": site_data,
            "materiality": {
                "threshold_pct": materiality["threshold_pct"],
                "material_source_count": materiality["material_source_count"],
                "sources": materiality["sources"],
            },
        },
        "emission_records": records,
    }


# ── PDF Report ─────────────────────────────────────────────────────────────────

def generate_pdf_report(
    db: Session,
    organisation: Organisation,
    period_year: int,
) -> bytes:
    """
    Generates a structured PDF emission report using ReportLab.
    Returns raw PDF bytes for streaming to the client.
    """
    import io
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    org_id = organisation.id
    story = []

    # ── Styles ─────────────────────────────────────────────
    styles = _build_styles()

    # ── Cover page ─────────────────────────────────────────
    story += _cover_page(organisation, period_year, styles)
    story.append(PageBreak())

    # ── Methodology statement ──────────────────────────────
    story += _methodology_section(styles)
    story.append(PageBreak())

    # ── Emission summary ───────────────────────────────────
    scope_data = get_scope_breakdown(db, org_id, period_year)
    story += _scope_summary_section(scope_data, period_year, styles)
    story.append(Spacer(1, 8 * mm))

    # ── Site breakdown ─────────────────────────────────────
    site_data = get_site_breakdown(db, org_id, period_year)
    story += _site_breakdown_section(site_data, styles)
    story.append(Spacer(1, 8 * mm))

    # ── Materiality analysis ───────────────────────────────
    materiality = run_materiality_screen(db, org_id, period_year)
    story += _materiality_section(materiality, styles)
    story.append(PageBreak())

    # ── Data quality statement ─────────────────────────────
    story += _data_quality_section(db, org_id, period_year, styles)
    story.append(Spacer(1, 8 * mm))

    # ── Target progress ────────────────────────────────────
    targets = db.query(Target).filter_by(
        organisation_id=org_id
    ).all()
    if targets:
        story += _targets_section(targets, scope_data, styles)

    # ── Build PDF ──────────────────────────────────────────
    doc.build(
        story,
        onFirstPage=_page_footer,
        onLaterPages=_page_footer,
    )

    buffer.seek(0)
    return buffer.read()


# ── Style builder ──────────────────────────────────────────────────────────────

def _build_styles():
    base = getSampleStyleSheet()

    styles = {
        "cover_org": ParagraphStyle(
            "cover_org",
            fontName="Helvetica-Bold",
            fontSize=22,
            textColor=BLACK,
            leading=28,
            spaceAfter=4 * mm,
        ),
        "cover_title": ParagraphStyle(
            "cover_title",
            fontName="Helvetica",
            fontSize=14,
            textColor=DARK_GREY,
            leading=20,
            spaceAfter=2 * mm,
        ),
        "cover_meta": ParagraphStyle(
            "cover_meta",
            fontName="Helvetica",
            fontSize=10,
            textColor=MID_GREY,
            leading=14,
            spaceAfter=1 * mm,
        ),
        "section_header": ParagraphStyle(
            "section_header",
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=BLACK,
            leading=18,
            spaceBefore=6 * mm,
            spaceAfter=3 * mm,
        ),
        "subsection_header": ParagraphStyle(
            "subsection_header",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=DARK_GREY,
            leading=14,
            spaceBefore=4 * mm,
            spaceAfter=2 * mm,
        ),
        "body": ParagraphStyle(
            "body",
            fontName="Helvetica",
            fontSize=9,
            textColor=DARK_GREY,
            leading=14,
            spaceAfter=2 * mm,
        ),
        "label": ParagraphStyle(
            "label",
            fontName="Helvetica",
            fontSize=8,
            textColor=MID_GREY,
            leading=12,
        ),
        "kpi_value": ParagraphStyle(
            "kpi_value",
            fontName="Helvetica-Bold",
            fontSize=18,
            textColor=BLACK,
            leading=22,
        ),
        "kpi_label": ParagraphStyle(
            "kpi_label",
            fontName="Helvetica",
            fontSize=8,
            textColor=MID_GREY,
            leading=12,
        ),
        "footer": ParagraphStyle(
            "footer",
            fontName="Helvetica",
            fontSize=7,
            textColor=MID_GREY,
            leading=10,
            alignment=TA_CENTER,
        ),
        "table_header": ParagraphStyle(
            "table_header",
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=DARK_GREY,
            leading=12,
        ),
        "table_cell": ParagraphStyle(
            "table_cell",
            fontName="Helvetica",
            fontSize=8,
            textColor=DARK_GREY,
            leading=12,
        ),
    }

    return styles


# ── Section builders ───────────────────────────────────────────────────────────

def _cover_page(org, period_year, styles):
    content = []

    content.append(Spacer(1, 40 * mm))
    content.append(HRFlowable(
        width="100%",
        thickness=2,
        color=BLACK,
        spaceAfter=8 * mm,
    ))
    content.append(Paragraph(org.name, styles["cover_org"]))
    content.append(Paragraph(
        f"Greenhouse Gas Emission Report · {period_year}",
        styles["cover_title"],
    ))
    content.append(Spacer(1, 6 * mm))
    content.append(HRFlowable(
        width="100%",
        thickness=0.5,
        color=BORDER_GREY,
        spaceAfter=8 * mm,
    ))
    content.append(Spacer(1, 6 * mm))

    meta = [
        ("Industry", org.industry.value.replace("_", " ").title()),
        ("Country", org.country),
        ("Reporting Period", str(period_year)),
        ("Report Generated", datetime.utcnow().strftime("%d %B %Y")),
        ("Standard", "GHG Protocol Corporate Standard"),
        ("GWP Reference", "IPCC Sixth Assessment Report (AR6) GWP100"),
    ]

    for label, value in meta:
        content.append(Paragraph(
            f"<b>{label}:</b> {value}",
            styles["cover_meta"],
        ))

    content.append(Spacer(1, 40 * mm))
    content.append(Paragraph(
        "This report has not been subject to third-party verification. "
        "Data quality notes and lineage information are available in the "
        "accompanying audit trail export.",
        styles["body"],
    ))

    return content


def _methodology_section(styles):
    content = []

    content.append(Paragraph("Methodology Statement", styles["section_header"]))
    content.append(HRFlowable(
        width="100%", thickness=0.5,
        color=BORDER_GREY, spaceAfter=4 * mm,
    ))

    sections = [
        (
            "Reporting Standard",
            "Emissions have been calculated in accordance with the GHG Protocol "
            "Corporate Accounting and Reporting Standard (revised edition). Scope 1, "
            "Scope 2, and Scope 3 categories are reported where data is available "
            "and material.",
        ),
        (
            "Emission Factors",
            "Emission factors are sourced from the UK Department for Environment, "
            "Food and Rural Affairs (DEFRA) 2023 conversion factors and the "
            "International Energy Agency (IEA) 2022 grid emission factors. "
            "Where a region-specific factor is unavailable, a global default "
            "factor is applied and flagged in the data quality statement.",
        ),
        (
            "Global Warming Potential",
            "All greenhouse gases are converted to carbon dioxide equivalent (CO₂e) "
            "using Global Warming Potential values from the IPCC Sixth Assessment "
            "Report (AR6), 100-year time horizon (GWP100). Gases reported include "
            "CO₂, CH₄, N₂O, HFCs, PFCs, SF₆, and NF₃.",
        ),
        (
            "Scope 2 Methodology",
            "Scope 2 emissions are reported on a location-based basis using average "
            "grid emission factors for the country of operation. Where contractual "
            "instruments (RECs, PPAs) are specified, market-based figures are "
            "presented alongside location-based figures.",
        ),
        (
            "Organisational Boundary",
            "An operational control approach is used to define the organisational "
            "boundary. All sites over which the organisation has full operational "
            "control are included in the inventory.",
        ),
        (
            "Materiality",
            "Emission sources representing 1% or more of total reported emissions "
            "are considered material and are presented in the materiality analysis "
            "section. Sources below this threshold are included in totals but may "
            "rely on spend-based or activity-based estimation.",
        ),
    ]

    for title, body in sections:
        content.append(Paragraph(title, styles["subsection_header"]))
        content.append(Paragraph(body, styles["body"]))

    return content


def _scope_summary_section(scope_data, period_year, styles):
    content = []

    content.append(Paragraph(
        "Emission Summary", styles["section_header"]
    ))
    content.append(HRFlowable(
        width="100%", thickness=0.5,
        color=BORDER_GREY, spaceAfter=4 * mm,
    ))

    # KPI table — 4 columns
    kpi_data = [
        [
            _kpi_cell("Total CO₂e", f"{scope_data['total_tco2e']:,.3f} t", styles),
            _kpi_cell("Scope 1", f"{scope_data['scope_1_tco2e']:,.3f} t", styles),
            _kpi_cell("Scope 2", f"{scope_data['scope_2_tco2e']:,.3f} t", styles),
            _kpi_cell("Scope 3", f"{scope_data['scope_3_tco2e']:,.3f} t", styles),
        ]
    ]

    kpi_table = Table(kpi_data, colWidths=["25%", "25%", "25%", "25%"])
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT_GREY]),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER_GREY),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_GREY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))

    content.append(kpi_table)
    content.append(Spacer(1, 4 * mm))

    # Scope percentages
    total = scope_data["total_tco2e"]
    if total > 0:
        rows = [
            ["Scope", "tCO₂e", "% of Total", "Description"],
            [
                "Scope 1",
                f"{scope_data['scope_1_tco2e']:,.3f}",
                f"{scope_data['scope_1_tco2e'] / total * 100:.1f}%",
                "Direct emissions from owned sources",
            ],
            [
                "Scope 2",
                f"{scope_data['scope_2_tco2e']:,.3f}",
                f"{scope_data['scope_2_tco2e'] / total * 100:.1f}%",
                "Indirect emissions from purchased energy",
            ],
            [
                "Scope 3",
                f"{scope_data['scope_3_tco2e']:,.3f}",
                f"{scope_data['scope_3_tco2e'] / total * 100:.1f}%",
                "Indirect emissions from value chain",
            ],
        ]
        content.append(_build_table(rows, styles))

    return content


def _site_breakdown_section(site_data, styles):
    content = []

    content.append(Paragraph("Site Breakdown", styles["section_header"]))
    content.append(HRFlowable(
        width="100%", thickness=0.5,
        color=BORDER_GREY, spaceAfter=4 * mm,
    ))

    if not site_data:
        content.append(Paragraph(
            "No site-level data available for this period.",
            styles["body"],
        ))
        return content

    rows = [["Rank", "Site Code", "Site Name", "Region", "tCO₂e", "Records"]]
    for site in site_data:
        rows.append([
            str(site["rank"]),
            site["site_code"] or "—",
            site["site_name"],
            site["region"] or "—",
            f"{site['total_co2e_tonnes']:,.3f}",
            str(site["record_count"]),
        ])

    content.append(_build_table(rows, styles))
    return content


def _materiality_section(materiality, styles):
    content = []

    content.append(Paragraph(
        "Materiality Analysis", styles["section_header"]
    ))
    content.append(HRFlowable(
        width="100%", thickness=0.5,
        color=BORDER_GREY, spaceAfter=4 * mm,
    ))
    content.append(Paragraph(
        f"Sources representing ≥{materiality['threshold_pct']}% of total emissions "
        f"are classified as material. {materiality['material_source_count']} of "
        f"{len(materiality['sources'])} identified sources are material.",
        styles["body"],
    ))

    if not materiality["sources"]:
        content.append(Paragraph(
            "No emission sources identified for this period.",
            styles["body"],
        ))
        return content

    rows = [[
        "Rank", "Scope", "Category",
        "Fuel / Material", "tCO₂e", "% Total", "Material",
    ]]

    for source in materiality["sources"]:
        rows.append([
            str(source["rank"]),
            source["scope"].replace("_", " ").title(),
            source["ghg_category"].replace("_", " "),
            source["fuel_or_material"],
            f"{source['total_co2e_tonnes']:,.3f}",
            f"{source['percentage_of_total']:.1f}%",
            "Yes" if source["is_material"] else "No",
        ])

    content.append(_build_table(rows, styles))
    return content


def _data_quality_section(db, org_id, period_year, styles):
    content = []

    content.append(Paragraph(
        "Data Quality Statement", styles["section_header"]
    ))
    content.append(HRFlowable(
        width="100%", thickness=0.5,
        color=BORDER_GREY, spaceAfter=4 * mm,
    ))

    # Count records and quality flags
    from backend.models import Site
    total_records = (
        db.query(ActivityRecord)
        .join(Site, ActivityRecord.site_id == Site.id)
        .filter(
            Site.organisation_id == org_id,
            ActivityRecord.period_year == period_year,
        )
        .count()
    )

    quarantined = (
        db.query(ActivityRecord)
        .join(Site, ActivityRecord.site_id == Site.id)
        .filter(
            Site.organisation_id == org_id,
            ActivityRecord.period_year == period_year,
            ActivityRecord.status == "quarantined",
        )
        .count()
    )

    duplicates = (
        db.query(ActivityRecord)
        .join(Site, ActivityRecord.site_id == Site.id)
        .filter(
            Site.organisation_id == org_id,
            ActivityRecord.period_year == period_year,
            ActivityRecord.is_flagged_duplicate == True,
        )
        .count()
    )

    fallback_records = (
        db.query(EmissionRecord)
        .join(
            ActivityRecord,
            EmissionRecord.activity_record_id == ActivityRecord.id,
        )
        .join(Site, ActivityRecord.site_id == Site.id)
        .filter(
            Site.organisation_id == org_id,
            ActivityRecord.period_year == period_year,
            EmissionRecord.factor_fallback_used == True,
        )
        .count()
    )

    # Factor versions used
    factors_used = (
        db.query(EmissionFactor.source, EmissionFactor.version)
        .join(
            EmissionRecord,
            EmissionFactor.id == EmissionRecord.emission_factor_id,
        )
        .join(
            ActivityRecord,
            EmissionRecord.activity_record_id == ActivityRecord.id,
        )
        .join(Site, ActivityRecord.site_id == Site.id)
        .filter(
            Site.organisation_id == org_id,
            ActivityRecord.period_year == period_year,
        )
        .distinct()
        .all()
    )

    rows = [
        ["Metric", "Value", "Note"],
        [
            "Total activity records",
            str(total_records),
            "All records for the reporting period",
        ],
        [
            "Quarantined records",
            str(quarantined),
            "Failed validation — excluded from calculations",
        ],
        [
            "Duplicate records",
            str(duplicates),
            "Flagged as potential duplicates — excluded",
        ],
        [
            "Records using fallback factors",
            str(fallback_records),
            "Global default used — no regional factor available",
        ],
    ]

    content.append(_build_table(rows, styles))
    content.append(Spacer(1, 4 * mm))

    content.append(Paragraph(
        "Emission Factor Versions Applied", styles["subsection_header"]
    ))

    factor_rows = [["Source", "Version"]]
    for source, version in factors_used:
        factor_rows.append([source.value, version])

    content.append(_build_table(factor_rows, styles))

    return content


def _targets_section(targets, scope_data, styles):
    content = []

    content.append(Paragraph(
        "Reduction Targets", styles["section_header"]
    ))
    content.append(HRFlowable(
        width="100%", thickness=0.5,
        color=BORDER_GREY, spaceAfter=4 * mm,
    ))

    total = scope_data["total_tco2e"]

    rows = [[
        "Target", "Baseline", "Target",
        "Current", "Reduction", "Status",
    ]]

    for target in targets:
        baseline = target.baseline_emissions_tco2e
        reduction_pct = (
            ((baseline - total) / baseline * 100)
            if baseline > 0 else 0.0
        )
        on_track = total <= target.target_emissions_tco2e

        rows.append([
            target.name,
            f"{baseline:,.0f} t",
            f"{target.target_emissions_tco2e:,.0f} t",
            f"{total:,.2f} t",
            f"{reduction_pct:.1f}%",
            "On Track" if on_track else "Off Track",
        ])

    content.append(_build_table(rows, styles))
    return content


# ── Table builder ──────────────────────────────────────────────────────────────

def _build_table(rows, styles):
    """Builds a styled ReportLab table from a list of row lists."""
    formatted = []
    for i, row in enumerate(rows):
        formatted_row = []
        for cell in row:
            style = styles["table_header"] if i == 0 else styles["table_cell"]
            formatted_row.append(Paragraph(str(cell), style))
        formatted.append(formatted_row)

    col_count = len(rows[0])
    col_width = 170 * mm / col_count

    table = Table(formatted, colWidths=[col_width] * col_count)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_GREY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GREY]),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER_GREY),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_GREY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))

    return table


def _kpi_cell(label, value, styles):
    """Builds a KPI cell for the summary table."""
    return [
        Paragraph(value, styles["kpi_value"]),
        Paragraph(label, styles["kpi_label"]),
    ]


# ── Page footer ────────────────────────────────────────────────────────────────

def _page_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MID_GREY)
    canvas.drawCentredString(
        A4[0] / 2,
        12 * mm,
        f"Carbon Emission Tracking Platform · Confidential · "
        f"Page {doc.page}",
    )
    canvas.restoreState()
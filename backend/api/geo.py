"""
Geospatial endpoints — GeoJSON responses for Leaflet map.

GET    /geo/sites                        — all sites as GeoJSON
GET    /geo/emission-intensity           — sites with emission data
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional

from backend.db.database import get_db
from backend.models import Site, ActivityRecord, EmissionRecord
from backend.core.materiality.screener import get_site_breakdown
from backend.api.auth import get_current_user, validate_org_access
from backend.models.user import User

router = APIRouter()


@router.get("/sites")
def get_sites_geojson(
    organisation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    validate_org_access(organisation_id, current_user, db)
    """
    Returns all sites as a GeoJSON FeatureCollection.
    Used by Leaflet to render site markers on the map.
    """
    sites = db.query(Site).filter_by(
        organisation_id=organisation_id,
        is_active=True,
    ).all()

    features = []
    for site in sites:
        if site.latitude is None or site.longitude is None:
            continue
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [site.longitude, site.latitude],
            },
            "properties": {
                "id": str(site.id),
                "name": site.name,
                "site_code": site.site_code,
                "region": site.region,
                "country": site.country,
                "is_active": site.is_active,
            },
        })

    return {
        "type": "FeatureCollection",
        "features": features,
    }


@router.get("/emission-intensity")
def get_emission_intensity_geojson(
    organisation_id: UUID,
    period_year: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    validate_org_access(organisation_id, current_user, db)
    """
    Returns sites as GeoJSON with emission intensity data.
    Properties include total_co2e_tonnes and intensity_rank
    so Leaflet can colour-code markers by emission level.
    """
    site_emissions = get_site_breakdown(db, organisation_id, period_year)
    emission_map = {s["site_code"]: s for s in site_emissions}

    sites = db.query(Site).filter_by(
        organisation_id=organisation_id,
        is_active=True,
    ).all()

    max_emissions = max(
        (s["total_co2e_tonnes"] for s in site_emissions),
        default=1.0,
    )

    features = []
    for site in sites:
        if site.latitude is None or site.longitude is None:
            continue

        emission_data = emission_map.get(site.site_code, {})
        total_co2e = emission_data.get("total_co2e_tonnes", 0.0)

        # Intensity score 0.0 to 1.0 for colour scaling in frontend
        intensity = total_co2e / max_emissions if max_emissions > 0 else 0.0

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [site.longitude, site.latitude],
            },
            "properties": {
                "id": str(site.id),
                "name": site.name,
                "site_code": site.site_code,
                "region": site.region,
                "total_co2e_tonnes": total_co2e,
                "intensity_score": round(intensity, 4),
                "rank": emission_data.get("rank", None),
                "record_count": emission_data.get("record_count", 0),
            },
        })

    # Sort by emission intensity descending
    features.sort(
        key=lambda f: f["properties"]["total_co2e_tonnes"],
        reverse=True,
    )

    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "period_year": period_year,
            "total_sites": len(features),
            "max_co2e_tonnes": max_emissions,
        },
    }
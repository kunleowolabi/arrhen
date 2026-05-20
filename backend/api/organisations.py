"""
Organisation and Site endpoints.

GET    /organisations                    — list all organisations
POST   /organisations                    — create organisation
GET    /organisations/{id}               — get organisation with sites
PATCH  /organisations/{id}               — update organisation
GET    /organisations/{id}/sites         — list sites
POST   /organisations/{id}/sites         — add site
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from backend.db.database import get_db
from backend.models import Organisation, Site
from backend.schemas.organisation import (
    OrganisationCreate, OrganisationUpdate,
    OrganisationResponse, OrganisationSummary,
    SiteCreate, SiteResponse,
)
from geoalchemy2.elements import WKTElement

router = APIRouter()


@router.get("", response_model=list[OrganisationSummary])
def list_organisations(db: Session = Depends(get_db)):
    return db.query(Organisation).all()


@router.post(
    "",
    response_model=OrganisationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_organisation(
    payload: OrganisationCreate,
    db: Session = Depends(get_db),
):
    org = Organisation(**payload.model_dump())
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


@router.get("/{org_id}", response_model=OrganisationResponse)
def get_organisation(org_id: UUID, db: Session = Depends(get_db)):
    org = db.query(Organisation).filter_by(id=org_id).first()
    if not org:
        raise HTTPException(
            status_code=404,
            detail=f"Organisation {org_id} not found",
        )
    return org


@router.patch("/{org_id}", response_model=OrganisationResponse)
def update_organisation(
    org_id: UUID,
    payload: OrganisationUpdate,
    db: Session = Depends(get_db),
):
    org = db.query(Organisation).filter_by(id=org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organisation not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(org, field, value)

    db.commit()
    db.refresh(org)
    return org


@router.get("/{org_id}/sites", response_model=list[SiteResponse])
def list_sites(org_id: UUID, db: Session = Depends(get_db)):
    return db.query(Site).filter_by(organisation_id=org_id).all()


@router.post(
    "/{org_id}/sites",
    response_model=SiteResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_site(
    org_id: UUID,
    payload: SiteCreate,
    db: Session = Depends(get_db),
):
    org = db.query(Organisation).filter_by(id=org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organisation not found")

    site_data = payload.model_dump()
    lat = site_data.get("latitude")
    lon = site_data.get("longitude")

    site = Site(
        **site_data,
        organisation_id=org_id,
        geom=(
            WKTElement(f"POINT({lon} {lat})", srid=4326)
            if lat and lon else None
        ),
    )
    db.add(site)
    db.commit()
    db.refresh(site)
    return site
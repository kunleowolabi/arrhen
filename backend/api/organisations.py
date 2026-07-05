"""
Organisation and Site endpoints.
All endpoints scoped to the authenticated user's organisations.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from backend.db.database import get_db
from backend.models import Organisation, Site
from backend.models.user import User, OrganisationMembership
from backend.schemas.organisation import (
    OrganisationCreate, OrganisationUpdate,
    OrganisationResponse, OrganisationSummary,
    SiteCreate, SiteResponse,
)
from backend.api.auth import get_current_user, validate_org_access
from geoalchemy2.elements import WKTElement

router = APIRouter()


def _user_org_ids(current_user: User, db: Session) -> list:
    memberships = db.query(OrganisationMembership).filter_by(
        user_id=current_user.id
    ).all()
    return [m.organisation_id for m in memberships]


@router.get("", response_model=list[OrganisationSummary])
def list_organisations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns only organisations the current user belongs to."""
    org_ids = _user_org_ids(current_user, db)
    return db.query(Organisation).filter(Organisation.id.in_(org_ids)).all()


@router.post("", response_model=OrganisationResponse, status_code=status.HTTP_201_CREATED)
def create_organisation(
    payload: OrganisationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Creates a new organisation and automatically assigns
    the creating user as admin.
    """
    org = Organisation(**payload.model_dump())
    db.add(org)
    db.flush()

    # Auto-assign creator as admin
    membership = OrganisationMembership(
        user_id=current_user.id,
        organisation_id=org.id,
        role="admin",
    )
    db.add(membership)
    db.commit()
    db.refresh(org)
    return org


@router.get("/{org_id}", response_model=OrganisationResponse)
def get_organisation(
    org_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    validate_org_access(org_id, current_user, db)
    org = db.query(Organisation).filter_by(id=org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organisation not found")
    return org


@router.patch("/{org_id}", response_model=OrganisationResponse)
def update_organisation(
    org_id: UUID,
    payload: OrganisationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    validate_org_access(org_id, current_user, db)
    org = db.query(Organisation).filter_by(id=org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organisation not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(org, field, value)
    db.commit()
    db.refresh(org)
    return org


@router.get("/{org_id}/sites", response_model=list[SiteResponse])
def list_sites(
    org_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    validate_org_access(org_id, current_user, db)
    return db.query(Site).filter_by(organisation_id=org_id).all()


@router.post("/{org_id}/sites", response_model=SiteResponse, status_code=status.HTTP_201_CREATED)
def create_site(
    org_id: UUID,
    payload: SiteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    validate_org_access(org_id, current_user, db)
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

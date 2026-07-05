"""
Auth endpoints — user info and organisation membership management.

GET    /auth/me                          — current user info + memberships
POST   /auth/memberships                 — add user to organisation (admin only)
PATCH  /auth/memberships/{id}            — change user role (admin only)
DELETE /auth/memberships/{id}            — remove user from organisation (admin only)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from backend.db.database import get_db
from backend.api.auth import get_current_user, require_role
from backend.models.user import User, OrganisationMembership, UserRole
from backend.models import Organisation

router = APIRouter()


@router.get("/me")
def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Returns current user profile and all organisation memberships."""
    memberships = (
        db.query(OrganisationMembership)
        .filter_by(user_id=current_user.id)
        .all()
    )
    org_ids = [str(m.organisation_id) for m in memberships]
    orgs = db.query(Organisation).filter(
        Organisation.id.in_([m.organisation_id for m in memberships])
    ).all()
    org_map = {str(o.id): o.name for o in orgs}

    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "organisations": [
            {
                "organisation_id": str(m.organisation_id),
                "organisation_name": org_map.get(str(m.organisation_id)),
                "role": m.role.value,
                "membership_id": str(m.id),
            }
            for m in memberships
        ],
    }


@router.post("/memberships", status_code=status.HTTP_201_CREATED)
def add_membership(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    """
    Adds a user to an organisation with a specified role.
    Requires admin role. Creates the User record if not yet registered.
    """
    required = ["email", "organisation_id", "role"]
    missing = [f for f in required if not payload.get(f)]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required fields: {', '.join(missing)}",
        )

    try:
        role = UserRole(payload["role"])
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {[r.value for r in UserRole]}",
        )

    org_id = UUID(payload["organisation_id"])
    org = db.query(Organisation).filter_by(id=org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organisation not found")

    # Find or create user by email
    target_user = db.query(User).filter_by(email=payload["email"]).first()
    if not target_user:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No user found with email {payload['email']}. "
                "They must sign up first."
            ),
        )

    # Check not already a member
    existing = db.query(OrganisationMembership).filter_by(
        user_id=target_user.id,
        organisation_id=org_id,
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="User is already a member of this organisation.",
        )

    membership = OrganisationMembership(
        user_id=target_user.id,
        organisation_id=org_id,
        role=role,
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)

    return {
        "membership_id": str(membership.id),
        "user_email": target_user.email,
        "organisation_id": str(org_id),
        "role": role.value,
    }


@router.patch("/memberships/{membership_id}")
def update_membership_role(
    membership_id: UUID,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    """Changes a user's role within an organisation. Admin only."""
    membership = db.query(OrganisationMembership).filter_by(
        id=membership_id
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")

    try:
        membership.role = UserRole(payload["role"])
    except (ValueError, KeyError):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {[r.value for r in UserRole]}",
        )

    db.commit()
    return {"membership_id": str(membership_id), "role": membership.role.value}


@router.delete("/memberships/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_membership(
    membership_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.admin)),
):
    """Removes a user from an organisation. Admin only."""
    membership = db.query(OrganisationMembership).filter_by(
        id=membership_id
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")

    db.delete(membership)
    db.commit()

"""
User and OrganisationMembership models.

Users mirror Supabase Auth — the id field matches auth.users.id
so we can join platform data to auth identity.

OrganisationMembership links users to organisations with a role.
One user can belong to multiple organisations.
"""

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from backend.models.base import Base


class UserRole(str, enum.Enum):
    admin   = "admin"    # full access — manage users, sites, targets, all data
    analyst = "analyst"  # read all + upload CSV + run calculations
    viewer  = "viewer"   # read-only — dashboard and reports only


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
        # Populated from Supabase auth.users.id — not auto-generated here
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    memberships: Mapped[list["OrganisationMembership"]] = relationship(
        "OrganisationMembership", back_populates="user"
    )

    def __repr__(self):
        return f"<User {self.email}>"


class OrganisationMembership(Base):
    __tablename__ = "organisation_memberships"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organisations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole), nullable=False, default=UserRole.viewer
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    user: Mapped["User"] = relationship("User", back_populates="memberships")
    organisation: Mapped["Organisation"] = relationship("Organisation")

    def __repr__(self):
        return f"<Membership {self.user_id} → {self.organisation_id} [{self.role}]>"


from backend.models.organisation import Organisation  # noqa: E402

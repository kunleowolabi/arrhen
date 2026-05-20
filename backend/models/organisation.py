import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Text, Integer, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from geoalchemy2 import Geography

from backend.models.base import Base
from backend.models.enums import IndustryType, GWPVersion


class Organisation(Base):
    __tablename__ = "organisations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    industry: Mapped[IndustryType] = mapped_column(
        SAEnum(IndustryType), nullable=False
    )
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    reporting_currency: Mapped[str] = mapped_column(String(10), default="USD")
    fiscal_year_start_month: Mapped[int] = mapped_column(Integer, default=1)
    default_gwp_version: Mapped[GWPVersion] = mapped_column(
        SAEnum(GWPVersion), default=GWPVersion.AR6
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    sites: Mapped[list["Site"]] = relationship("Site", back_populates="organisation")
    targets: Mapped[list["Target"]] = relationship("Target", back_populates="organisation")

    def __repr__(self):
        return f"<Organisation {self.name}>"


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    site_code: Mapped[str] = mapped_column(String(50), nullable=True)
    region: Mapped[str] = mapped_column(String(100), nullable=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=True)
    latitude: Mapped[float] = mapped_column(nullable=True)
    longitude: Mapped[float] = mapped_column(nullable=True)

    geom: Mapped[object] = mapped_column(
        Geography(geometry_type="POINT", srid=4326), nullable=True
    )

    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    organisation: Mapped["Organisation"] = relationship(
        "Organisation", back_populates="sites"
    )
    activity_records: Mapped[list["ActivityRecord"]] = relationship(
        "ActivityRecord", back_populates="site"
    )

    def __repr__(self):
        return f"<Site {self.site_code or self.name}>"


from backend.models.activity import ActivityRecord  # noqa: E402
from backend.models.target import Target  # noqa: E402
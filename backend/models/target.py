import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Float, Integer, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from backend.models.base import Base
from backend.models.enums import ScopeCoverage, TargetType


class Target(Base):
    __tablename__ = "targets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organisation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organisations.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_type: Mapped[TargetType] = mapped_column(
        SAEnum(TargetType), nullable=False
    )
    scope_coverage: Mapped[ScopeCoverage] = mapped_column(
        SAEnum(ScopeCoverage), nullable=False
    )
    baseline_year: Mapped[int] = mapped_column(Integer, nullable=False)
    target_year: Mapped[int] = mapped_column(Integer, nullable=False)
    baseline_emissions_tco2e: Mapped[float] = mapped_column(Float, nullable=False)
    target_reduction_pct: Mapped[float] = mapped_column(Float, nullable=False)
    target_emissions_tco2e: Mapped[float] = mapped_column(Float, nullable=False)
    aligned_to: Mapped[str] = mapped_column(String(100), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    organisation: Mapped["Organisation"] = relationship(
        "Organisation", back_populates="targets"
    )

    def __repr__(self):
        return f"<Target {self.name} | {self.baseline_year}→{self.target_year}>"


from backend.models.organisation import Organisation  # noqa: E402
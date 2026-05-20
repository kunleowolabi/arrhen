import uuid
from datetime import datetime
from sqlalchemy import (
    String, DateTime, ForeignKey, Float, Text,
    Integer, Enum as SAEnum, Boolean
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from backend.models.base import Base
from backend.models.enums import (
    ScopeType, Scope2Method, DataSource, DataStatus
)


class DataLineage(Base):
    __tablename__ = "data_lineage"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source: Mapped[DataSource] = mapped_column(
        SAEnum(DataSource), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=True)
    odk_form_id: Mapped[str] = mapped_column(String(255), nullable=True)
    odk_submission_id: Mapped[str] = mapped_column(String(255), nullable=True)
    uploaded_by: Mapped[str] = mapped_column(String(255), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    raw_payload: Mapped[dict] = mapped_column(JSONB, nullable=True)
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    valid_count: Mapped[int] = mapped_column(Integer, default=0)
    quarantine_count: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str] = mapped_column(Text, nullable=True)

    activity_records: Mapped[list["ActivityRecord"]] = relationship(
        "ActivityRecord", back_populates="lineage"
    )

    def __repr__(self):
        return f"<DataLineage {self.source} @ {self.uploaded_at}>"


class ActivityRecord(Base):
    __tablename__ = "activity_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False
    )
    data_lineage_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_lineage.id"), nullable=True
    )

    scope: Mapped[ScopeType] = mapped_column(SAEnum(ScopeType), nullable=False)
    scope_2_method: Mapped[Scope2Method] = mapped_column(
        SAEnum(Scope2Method), nullable=True
    )
    ghg_category: Mapped[str] = mapped_column(String(100), nullable=False)
    activity_description: Mapped[str] = mapped_column(Text, nullable=True)

    fuel_or_material: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)

    period_year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_month: Mapped[int] = mapped_column(Integer, nullable=True)

    status: Mapped[DataStatus] = mapped_column(
        SAEnum(DataStatus), default=DataStatus.pending
    )
    is_flagged_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    flag_reason: Mapped[str] = mapped_column(Text, nullable=True)

    supplier_name: Mapped[str] = mapped_column(String(255), nullable=True)
    supplier_tier: Mapped[int] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    site: Mapped["Site"] = relationship("Site", back_populates="activity_records")
    lineage: Mapped["DataLineage"] = relationship(
        "DataLineage", back_populates="activity_records"
    )
    emission_record: Mapped["EmissionRecord"] = relationship(
        "EmissionRecord", back_populates="activity_record", uselist=False
    )

    def __repr__(self):
        return (
            f"<ActivityRecord {self.ghg_category} | "
            f"{self.quantity}{self.unit} | {self.period_year}>"
        )


from backend.models.emission import EmissionRecord  # noqa: E402
from backend.models.organisation import Site  # noqa: E402
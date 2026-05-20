import uuid
from datetime import datetime, date
from sqlalchemy import String, DateTime, ForeignKey, Float, Text, Date, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from backend.models.base import Base
from backend.models.enums import FactorSource, GWPVersion


class EmissionFactor(Base):
    __tablename__ = "emission_factors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    activity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    fuel_or_material: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[str] = mapped_column(String(100), nullable=True)

    co2_factor: Mapped[float] = mapped_column(Float, nullable=False)
    ch4_factor: Mapped[float] = mapped_column(Float, default=0.0)
    n2o_factor: Mapped[float] = mapped_column(Float, default=0.0)
    hfc_factor: Mapped[float] = mapped_column(Float, default=0.0)
    pfc_factor: Mapped[float] = mapped_column(Float, default=0.0)
    sf6_factor: Mapped[float] = mapped_column(Float, default=0.0)
    nf3_factor: Mapped[float] = mapped_column(Float, default=0.0)

    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    source: Mapped[FactorSource] = mapped_column(SAEnum(FactorSource), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[date] = mapped_column(Date, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    emission_records: Mapped[list["EmissionRecord"]] = relationship(
        "EmissionRecord", back_populates="emission_factor"
    )

    def __repr__(self):
        return f"<EmissionFactor {self.fuel_or_material} | {self.source} {self.version}>"


class EmissionRecord(Base):
    __tablename__ = "emission_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    activity_record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("activity_records.id"),
        nullable=False, unique=True
    )
    emission_factor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("emission_factors.id"), nullable=False
    )

    co2_kg: Mapped[float] = mapped_column(Float, default=0.0)
    ch4_kg: Mapped[float] = mapped_column(Float, default=0.0)
    n2o_kg: Mapped[float] = mapped_column(Float, default=0.0)
    hfc_kg: Mapped[float] = mapped_column(Float, default=0.0)
    pfc_kg: Mapped[float] = mapped_column(Float, default=0.0)
    sf6_kg: Mapped[float] = mapped_column(Float, default=0.0)
    nf3_kg: Mapped[float] = mapped_column(Float, default=0.0)

    co2_co2e: Mapped[float] = mapped_column(Float, default=0.0)
    ch4_co2e: Mapped[float] = mapped_column(Float, default=0.0)
    n2o_co2e: Mapped[float] = mapped_column(Float, default=0.0)
    hfc_co2e: Mapped[float] = mapped_column(Float, default=0.0)
    pfc_co2e: Mapped[float] = mapped_column(Float, default=0.0)
    sf6_co2e: Mapped[float] = mapped_column(Float, default=0.0)
    nf3_co2e: Mapped[float] = mapped_column(Float, default=0.0)

    total_co2e_kg: Mapped[float] = mapped_column(Float, nullable=False)
    total_co2e_tonnes: Mapped[float] = mapped_column(Float, nullable=False)

    gwp_version: Mapped[GWPVersion] = mapped_column(SAEnum(GWPVersion), nullable=False)
    factor_fallback_used: Mapped[bool] = mapped_column(default=False)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    activity_record: Mapped["ActivityRecord"] = relationship(
        "ActivityRecord", back_populates="emission_record"
    )
    emission_factor: Mapped["EmissionFactor"] = relationship(
        "EmissionFactor", back_populates="emission_records"
    )

    def __repr__(self):
        return (
            f"<EmissionRecord {self.total_co2e_tonnes:.3f} tCO2e "
            f"| {self.gwp_version}>"
        )


from backend.models.activity import ActivityRecord  # noqa: E402
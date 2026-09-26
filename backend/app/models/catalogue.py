"""Clinical catalogue: tests, units, ranges and limits. Seeded from data/catalogue/*.csv."""

from datetime import date
from decimal import Decimal

from sqlalchemy import (
    ARRAY,
    REAL,
    Boolean,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import INT4RANGE, Range
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, pg_enum
from app.models.enums import Sex


class OrganSystem(Base):
    __tablename__ = "organ_system"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(Text, unique=True)
    name_en: Mapped[str] = mapped_column(Text)
    name_hi: Mapped[str] = mapped_column(Text)
    name_or: Mapped[str] = mapped_column(Text)
    mesh_ids: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    translations_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)


class LabTest(Base):
    __tablename__ = "lab_test"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(Text, unique=True)  # stable slug used by seeds and code
    loinc_code: Mapped[str] = mapped_column(Text, unique=True)
    canonical_name: Mapped[str] = mapped_column(Text)
    short_name: Mapped[str] = mapped_column(Text)
    panel: Mapped[str] = mapped_column(Text, index=True)
    aliases: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    organ_system_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("organ_system.id"), index=True)
    canonical_unit: Mapped[str] = mapped_column(Text)
    decimals: Mapped[int] = mapped_column(SmallInteger, default=1)
    plausible_min: Mapped[Decimal] = mapped_column(Numeric)
    plausible_max: Mapped[Decimal] = mapped_column(Numeric)
    cv_within_subject: Mapped[float | None] = mapped_column(REAL)
    cv_analytical: Mapped[float | None] = mapped_column(REAL)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class UnitConversion(Base):
    __tablename__ = "unit_conversion"
    __table_args__ = (UniqueConstraint("test_id", "from_unit", name="uq_unit_conversion_test_from"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    test_id: Mapped[int] = mapped_column(Integer, ForeignKey("lab_test.id", ondelete="CASCADE"), index=True)
    from_unit: Mapped[str] = mapped_column(Text)  # normalised unit key, see app.catalogue.units
    factor: Mapped[Decimal] = mapped_column(Numeric)
    offset: Mapped[Decimal] = mapped_column(Numeric, default=0)


class ReferenceRange(Base):
    """Default ranges used only when a report prints none (ref_source = 'catalogue')."""

    __tablename__ = "reference_range"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    test_id: Mapped[int] = mapped_column(Integer, ForeignKey("lab_test.id", ondelete="CASCADE"), index=True)
    sex: Mapped[Sex] = mapped_column(pg_enum(Sex, "sex"), default=Sex.UNKNOWN)  # unknown = applies to all
    age_min: Mapped[int] = mapped_column(SmallInteger, default=18)
    age_max: Mapped[int] = mapped_column(SmallInteger, default=120)
    low: Mapped[Decimal | None] = mapped_column(Numeric)
    high: Mapped[Decimal | None] = mapped_column(Numeric)
    source: Mapped[str] = mapped_column(Text)


class CriticalLimit(Base):
    __tablename__ = "critical_limit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    test_id: Mapped[int] = mapped_column(Integer, ForeignKey("lab_test.id", ondelete="CASCADE"), unique=True)
    low: Mapped[Decimal | None] = mapped_column(Numeric)
    high: Mapped[Decimal | None] = mapped_column(Numeric)
    message_key: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text)
    reviewed_by: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[date | None] = mapped_column(Date)


class PopulationPercentile(Base):
    __tablename__ = "population_percentile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    test_id: Mapped[int] = mapped_column(Integer, ForeignKey("lab_test.id", ondelete="CASCADE"), index=True)
    sex: Mapped[Sex] = mapped_column(pg_enum(Sex, "sex"))
    age_band: Mapped[Range[int]] = mapped_column(INT4RANGE)
    p05: Mapped[Decimal] = mapped_column(Numeric)
    p25: Mapped[Decimal] = mapped_column(Numeric)
    p50: Mapped[Decimal] = mapped_column(Numeric)
    p75: Mapped[Decimal] = mapped_column(Numeric)
    p95: Mapped[Decimal] = mapped_column(Numeric)
    n: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(Text)

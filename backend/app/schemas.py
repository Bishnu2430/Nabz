"""API request and response models."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Lang, Relationship, ReportStatus, Sex


class ProfileIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)
    sex: Sex = Sex.UNKNOWN
    date_of_birth: date | None = None
    relationship: Relationship = Relationship.SELF
    preferred_language: Lang = Lang.EN
    consent_processing: bool = Field(description="Consent to read and store this person's reports")


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    display_name: str
    sex: Sex
    date_of_birth: date | None
    relationship: Relationship
    preferred_language: Lang
    reports: int = 0
    latest_report_at: datetime | None = None


class Box(BaseModel):
    page: int
    x0: float
    top: float
    x1: float
    bottom: float


class ObservationOut(BaseModel):
    id: uuid.UUID
    raw_name: str | None
    raw_value: str | None
    raw_unit: str | None
    raw_range: str | None
    raw_flag: str | None
    section: str | None
    test_code: str | None
    test_name: str | None
    value: Decimal | None = Field(description="Value in the test's canonical unit")
    unit: str | None
    ref_low: Decimal | None
    ref_high: Decimal | None
    ref_source: str
    confidence: float
    needs_attention: bool = Field(description="Below the confidence threshold or not mapped to a test")
    match_method: str | None
    candidates: list[tuple[str, str, float]] = Field(default_factory=list, description="[code, name, score]")
    bbox: Box | None
    edited: bool


class PageOut(BaseModel):
    page_no: int
    width: int
    height: int
    source: str
    quality: float | None


class ReportOut(BaseModel):
    id: uuid.UUID
    profile_id: uuid.UUID
    status: ReportStatus
    lab_name: str | None
    collected_at: date | None
    created_at: datetime
    pages: list[PageOut]
    observations: list[ObservationOut]
    needs_attention: int
    unmapped: int = Field(description="Rows without a test or a number; confirming is refused while this is above 0")
    confidence_threshold: float


class ReportSummary(BaseModel):
    id: uuid.UUID
    status: ReportStatus
    lab_name: str | None
    collected_at: date | None
    created_at: datetime
    rows: int


class Accepted(BaseModel):
    report_id: uuid.UUID
    status: ReportStatus


class ObservationPatch(BaseModel):
    raw_name: str | None = Field(default=None, max_length=120)
    raw_value: str | None = Field(default=None, max_length=30)
    raw_unit: str | None = Field(default=None, max_length=30)
    raw_range: str | None = Field(default=None, max_length=60)
    test_code: str | None = Field(default=None, description="Map the row to this catalogue test")


class ObservationNew(BaseModel):
    test_code: str
    raw_value: str = Field(min_length=1, max_length=30)
    raw_unit: str | None = Field(default=None, max_length=30)
    raw_range: str | None = Field(default=None, max_length=60)


class ConfirmIn(BaseModel):
    collected_at: date | None = Field(default=None, description="Sample collection date, if the user corrects it")


class CatalogueTest(BaseModel):
    code: str
    name: str
    short_name: str
    panel: str
    unit: str
    organ: str

"""API request and response models."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ConsentPurpose, Lang, ObsStatus, Relationship, ReportStatus, Sex


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


# --- Analysis (Sprint 4) ---------------------------------------------------------------------------------------


class PreviousOut(BaseModel):
    value: float
    date: date
    report_id: uuid.UUID


class ChangeOut(BaseModel):
    fraction: float | None = Field(description="current / previous − 1")
    direction: str
    significant: bool | None = Field(description="Beyond the reference change value; None when the test has no RCV")
    rcv_down: float | None
    rcv_up: float | None


class ProjectionOut(BaseModel):
    kind: str = Field(description="leave: heading out of range; enter: heading back into range")
    limit: str
    value: float
    on: date


class TrendOut(BaseModel):
    n: int
    first: date
    last: date
    slope_per_year: float
    intercept: float
    slope_low: float | None
    slope_high: float | None
    p_value: float
    change_fraction: float | None
    direction: str
    confirmed: bool
    reason: str = Field(description="Why it isn't confirmed: too_few, short_span, not_significant, "
                                    "no_variation_data, within_variation; empty when confirmed")
    projection: ProjectionOut | None


class PercentileOut(BaseModel):
    value: float
    side: str = Field(description="below (under the 5th), within, above (over the 95th)")
    population: str
    sex: str
    age_band: list[int]


class ResultOut(BaseModel):
    """One confirmed result with its analysis as of the report's date."""

    observation_id: uuid.UUID
    report_id: uuid.UUID
    date: date
    test_code: str
    test_name: str
    short_name: str
    organ: str
    value: Decimal
    unit: str | None
    decimals: int
    ref_low: Decimal | None
    ref_high: Decimal | None
    ref_source: str
    status: ObsStatus
    critical: bool
    flag_disagrees: bool = False
    previous: PreviousOut | None = None
    change: ChangeOut | None = None
    trend: TrendOut | None = None
    percentile: PercentileOut | None = None


class OrganOut(BaseModel):
    code: str
    names: dict[str, str] = Field(description="Display name by language code (en, hi, or)")
    status: ObsStatus = Field(description="Worst status among its tests")
    results: list[ResultOut]


class PersonOut(BaseModel):
    id: uuid.UUID
    display_name: str
    sex: Sex
    age: int | None


class InsightsOut(BaseModel):
    report: ReportSummary
    person: PersonOut
    analysed: bool = Field(description="False until the analysis stage has run")
    critical: list[ResultOut] = Field(description="Results beyond a critical limit; shown before anything else")
    organs: list[OrganOut] = Field(description="Worst organ first")
    explanation: dict | None = None


class TestInfoOut(BaseModel):
    code: str
    name: str
    short_name: str
    unit: str
    decimals: int
    organ: str
    rcv_down: float | None
    rcv_up: float | None


class TestHistoryOut(BaseModel):
    test: TestInfoOut
    person: PersonOut
    results: list[ResultOut] = Field(description="Oldest first")


class WatchOut(BaseModel):
    """A test worth a look on the profile page: a confirmed trend or a significant change."""

    test_code: str
    test_name: str
    organ: str
    n_points: int
    direction: str | None
    confirmed: bool
    rcv_significant: bool | None
    projected_crossing: date | None
    percentile: float | None
    latest: ResultOut


# --- Consent and explanations (Sprint 5) -------------------------------------------------------------------------


class ConsentIn(BaseModel):
    granted: bool


class ConsentOut(BaseModel):
    purpose: ConsentPurpose
    granted: bool
    granted_at: datetime | None


class TestExplanationOut(BaseModel):
    test_code: str
    status: str
    what_it_measures: str
    what_this_result_means: str
    citations: list[str]


class SourceOut(BaseModel):
    label: str
    title: str
    url: str | None
    organisation: str
    license: str


class ExplanationOut(BaseModel):
    id: uuid.UUID
    language: Lang
    source: str = Field(description="model: generated and checked; template: built only from computed values")
    reason: str | None = Field(description="Why the template was used: critical, no_consent, no_model, "
                                           "no_knowledge, validation, provider_error")
    summary: str
    per_test: list[TestExplanationOut]
    doctor_questions: list[str]
    disclaimer_key: str
    sources: list[SourceOut]
    has_audio: bool
    created_at: datetime


class ExplanationState(BaseModel):
    state: str = Field(description="ready, pending (being written) or none")
    explanation: ExplanationOut | None = None


class ExplainIn(BaseModel):
    language: Lang
    regenerate: bool = Field(default=False, description="Write it again, e.g. after consent to external AI is given")


class AudioOut(BaseModel):
    url: str


class FeedbackIn(BaseModel):
    helpful: bool
    comment: str | None = Field(default=None, max_length=1000)

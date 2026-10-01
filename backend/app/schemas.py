"""API request and response models."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ConsentPurpose, Lang, ObsStatus, RecordKind, Relationship, ReportStatus, Sex


class ProfileIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)
    sex: Sex = Sex.UNKNOWN
    date_of_birth: date | None = None
    relationship: Relationship = Relationship.SELF
    preferred_language: Lang = Lang.EN
    consent_processing: bool = Field(description="Consent to read and store this person's reports")


class ResultBrief(BaseModel):
    """One result in a line: enough to say "Creatinine 1.62 mg/dL, above 0.60–1.30" anywhere in the app."""

    test_code: str
    test_name: str
    short_name: str
    value: Decimal
    unit: str | None
    decimals: int
    status: ObsStatus
    ref_low: Decimal | None
    ref_high: Decimal | None
    date: date
    report_id: uuid.UUID


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
    last_tested: date | None = Field(default=None, description="Date of the latest confirmed report")
    attention: list[ResultBrief] = Field(default_factory=list,
                                         description="Tests whose latest result is outside its range, worst first")


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
    note: str | None = None
    out_of_range: list[ResultBrief] = Field(default_factory=list,
                                            description="Confirmed results outside their range, worst first")


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


# --- Accounts (Sprint 6) -----------------------------------------------------------------------------------------


class RegisterIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=200)
    preferred_language: Lang = Lang.EN


class LoginIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=200)
    totp_code: str | None = Field(default=None, max_length=10)


class TokenIn(BaseModel):
    token: str = Field(max_length=200)


class ResetIn(BaseModel):
    token: str = Field(max_length=200)
    password: str = Field(max_length=200)


class EmailIn(BaseModel):
    email: str = Field(max_length=254)


class ChangePasswordIn(BaseModel):
    current_password: str = Field(max_length=200)
    new_password: str = Field(max_length=200)


class CodeIn(BaseModel):
    code: str = Field(max_length=10)


class PasswordIn(BaseModel):
    password: str = Field(max_length=200)


class MeOut(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    preferred_language: Lang
    email_verified: bool
    totp_enabled: bool
    totp_required: bool = Field(description="Staff must turn on two-step sign-in before anything else")
    csrf_token: str = Field(description="Send as the X-CSRF-Token header on every POST, PUT, PATCH and DELETE")


class MePatch(BaseModel):
    preferred_language: Lang


class TotpSetupOut(BaseModel):
    secret: str
    uri: str
    qr_svg: str = Field(description="The otpauth URI as an SVG QR code (data URI)")


# --- Body map (Sprint 6) ------------------------------------------------------------------------------------------


class BodyMapOrgan(BaseModel):
    code: str
    status: ObsStatus = Field(description="Worst status among the organ system's tests in this report")
    out_of_range: int
    results: int
    tests: list[ResultBrief] = Field(description="Every result of this system in the report, worst first")


class BodyMapFrame(BaseModel):
    """One analysed report as the body map shows it; the timeline replays these in date order (FR-29)."""

    report_id: uuid.UUID
    date: date
    lab_name: str | None
    organs: list[BodyMapOrgan]


# --- Other health records (Sprint 7) --------------------------------------------------------------------------------


class RecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    profile_id: uuid.UUID
    kind: RecordKind
    title: str
    record_date: date | None
    facility: str | None
    notes: str | None
    mime_type: str
    size_bytes: int
    created_at: datetime
    has_image: bool = False
    study_title: str | None = None
    findings: list[str] = Field(default_factory=list, description="As written in the report, not interpreted")
    impression: list[str] = Field(default_factory=list)
    image_credit: str | None = Field(default=None, description="The image's author and licence, shown with it")


class RecordPatch(BaseModel):
    kind: RecordKind | None = None
    title: str | None = Field(default=None, min_length=1, max_length=120)
    record_date: date | None = None
    facility: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=1000)


class ReportNoteIn(BaseModel):
    note: str | None = Field(default=None, max_length=500, description="The person's own note; empty clears it")



class OrganTestHistory(BaseModel):
    test: TestInfoOut
    results: list[ResultOut] = Field(description="Oldest first")


class OrganHistoryOut(BaseModel):
    """One organ system over time: every test with each result's as-of analysis (the body map's organ panel)."""

    code: str
    names: dict[str, str]
    person: PersonOut
    tests: list[OrganTestHistory] = Field(description="Worst latest status first, then catalogue order")


# --- Sharing with a doctor (FR-34) ----------------------------------------------------------------------------------


class ShareIn(BaseModel):
    days: int = Field(default=7, ge=1, le=30, description="How long the link works")
    label: str | None = Field(default=None, max_length=80, description="Who it is for; only the owner sees this")


class ShareOut(BaseModel):
    id: uuid.UUID
    label: str | None
    created_at: datetime
    expires_at: datetime
    revoked: bool
    active: bool
    views: int
    last_viewed_at: datetime | None


class ShareCreated(ShareOut):
    url: str = Field(description="Shown once: only the token's hash is stored")
    qr_svg: str


class SharedPerson(BaseModel):
    display_name: str
    sex: Sex
    age: int | None


class SharedReportOut(BaseModel):
    """What someone holding the link sees: one report, read-only, with no account and no identifiers beyond the
    person's name, age and sex."""

    person: SharedPerson
    lab_name: str | None
    collected_at: date | None
    note: str | None
    critical: list[ResultOut]
    organs: list[OrganOut]
    questions: list[str]
    expires_at: datetime

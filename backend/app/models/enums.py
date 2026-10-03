"""Enumerations shared by the ORM and the API. See docs/04-data-design.md §4."""

from enum import StrEnum


class ReportStatus(StrEnum):
    UPLOADED = "uploaded"
    REJECTED = "rejected"
    QUEUED = "queued"
    PROCESSING = "processing"
    NEEDS_REVIEW = "needs_review"
    VERIFIED = "verified"
    ANALYSING = "analysing"
    EXPLAINING = "explaining"
    EXPLAINED = "explained"
    FAILED = "failed"
    DELETED = "deleted"


class JobStage(StrEnum):
    EXTRACT = "extract"
    ANALYSE = "analyse"
    EXPLAIN = "explain"
    NARRATE = "narrate"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ObsStatus(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL_LOW = "critical_low"
    CRITICAL_HIGH = "critical_high"
    UNKNOWN = "unknown"


class ConsentPurpose(StrEnum):
    PROCESSING = "processing"
    EXTERNAL_AI = "external_ai"
    VOICE = "voice"
    RESEARCH = "research"


class SafetyStatus(StrEnum):
    PASSED = "passed"
    FALLBACK = "fallback"
    BLOCKED = "blocked"


class Sex(StrEnum):
    FEMALE = "female"
    MALE = "male"
    OTHER = "other"
    UNKNOWN = "unknown"


class Lang(StrEnum):
    EN = "en"
    HI = "hi"
    ODIA = "or"


class UserRole(StrEnum):
    USER = "user"  # member: manages their family's reports
    CLINICIAN = "clinician"
    REVIEWER = "reviewer"  # clinical reviewer: safety queue, sign-offs
    ADMIN = "admin"


STAFF_ROLES = frozenset({UserRole.REVIEWER, UserRole.ADMIN})  # TOTP required, 1-day sessions


class TokenPurpose(StrEnum):
    VERIFY_EMAIL = "verify_email"
    RESET_PASSWORD = "reset_password"  # noqa: S105 - a token purpose, not a password


class RecordKind(StrEnum):
    """Other health records a person keeps with their lab reports; stored and shown, not analysed."""

    IMAGING = "imaging"  # X-ray, MRI, CT, ultrasound reports
    PRESCRIPTION = "prescription"
    DISCHARGE = "discharge"  # discharge summaries
    VACCINATION = "vaccination"
    OTHER = "other"


class ReadingKind(StrEnum):
    """Readings a person takes at home. Shown and charted against their own target; never interpreted by Nabz."""

    BP = "bp"  # value = systolic, value2 = diastolic, mmHg
    GLUCOSE = "glucose"  # mg/dL
    WEIGHT = "weight"  # kg
    PULSE = "pulse"  # beats per minute
    TEMPERATURE = "temperature"  # °C
    SPO2 = "spo2"  # %


class Relationship(StrEnum):
    SELF = "self"
    PARENT = "parent"
    CHILD = "child"
    SPOUSE = "spouse"
    OTHER = "other"

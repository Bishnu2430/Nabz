"""ORM models. Importing this package registers every table on Base.metadata."""

from app.models.base import Base
from app.models.care import HomeReading, Reminder
from app.models.catalogue import (
    CriticalLimit,
    LabTest,
    OrganSystem,
    PopulationPercentile,
    ReferenceRange,
    UnitConversion,
)
from app.models.clinical import Clinician, ClinicianNote, ReportGrant
from app.models.governance import AuditLog, Feedback, SafetyReview, ShareLink
from app.models.identity import AppUser, AuthToken, Consent, Profile, UserSession
from app.models.knowledge import (
    Explanation,
    ExplanationCitation,
    KbChunk,
    KbDocument,
    ReportQuestion,
    TrendInsight,
)
from app.models.reports import HealthRecord, Observation, ProcessingJob, Report, ReportFile, ReportPage

__all__ = [
    "AppUser", "AuditLog", "AuthToken", "Base", "Clinician", "ClinicianNote", "Consent", "CriticalLimit",
    "Explanation", "ExplanationCitation", "Feedback", "HealthRecord", "HomeReading", "KbChunk", "KbDocument",
    "LabTest", "Observation", "OrganSystem", "PopulationPercentile", "ProcessingJob", "Profile", "ReferenceRange",
    "Reminder", "Report", "ReportFile", "ReportGrant", "ReportPage", "ReportQuestion", "SafetyReview", "ShareLink",
    "TrendInsight", "UnitConversion", "UserSession",
]

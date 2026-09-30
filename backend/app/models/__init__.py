"""ORM models. Importing this package registers every table on Base.metadata."""

from app.models.base import Base
from app.models.catalogue import (
    CriticalLimit,
    LabTest,
    OrganSystem,
    PopulationPercentile,
    ReferenceRange,
    UnitConversion,
)
from app.models.governance import AuditLog, Feedback, ShareLink
from app.models.identity import AppUser, AuthToken, Consent, Profile, UserSession
from app.models.knowledge import Explanation, ExplanationCitation, KbChunk, KbDocument, TrendInsight
from app.models.reports import Observation, ProcessingJob, Report, ReportFile, ReportPage

__all__ = [
    "AppUser", "AuditLog", "AuthToken", "Base", "Consent", "CriticalLimit", "Explanation", "ExplanationCitation",
    "Feedback", "KbChunk", "KbDocument", "LabTest", "Observation", "OrganSystem", "PopulationPercentile",
    "ProcessingJob", "Profile", "ReferenceRange", "Report", "ReportFile", "ReportPage", "ShareLink",
    "TrendInsight", "UnitConversion", "UserSession",
]

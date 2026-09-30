"""Small helpers that create users, profiles and consents for tests."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.security import UNUSABLE_PASSWORD_HASH
from app.models import AppUser, Consent, Observation, Profile, Report
from app.models.enums import ConsentPurpose, ReportStatus
from app.services.interpretation import lab_test_ids


def make_profile(s: Session, consent: bool = True, email: str = "test@nabz.local") -> Profile:
    user = AppUser(email=email, password_hash=UNUSABLE_PASSWORD_HASH)
    s.add(user)
    s.flush()
    profile = Profile(owner_user_id=user.id, display_name="Test person")
    s.add(profile)
    s.flush()
    if consent:
        s.add(Consent(user_id=user.id, profile_id=profile.id, purpose=ConsentPurpose.PROCESSING,
                      policy_version="test"))
        s.flush()
    return profile


def add_report(s: Session, profile_id: uuid.UUID, uploaded_by: uuid.UUID, when: date,
               values: dict[str, tuple[float, float | None, float | None]]) -> Report:
    ids = lab_test_ids(s)
    report = Report(profile_id=profile_id, uploaded_by=uploaded_by, collected_at=when, status=ReportStatus.VERIFIED,
                    source_sha256=uuid.uuid4().hex)
    s.add(report)
    s.flush()
    for code, (value, low, high) in values.items():
        s.add(Observation(
            report_id=report.id, test_id=ids[code], raw_name=code, raw_value=str(value), value_num=Decimal(str(value)),
            ref_low=None if low is None else Decimal(str(low)), ref_high=None if high is None else Decimal(str(high)),
            ref_source="report", confidence=1.0, verified_at=datetime.now(UTC),
        ))
    s.flush()
    return report

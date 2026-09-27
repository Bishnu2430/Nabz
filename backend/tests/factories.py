"""Small helpers that create users, profiles and consents for tests."""

from sqlalchemy.orm import Session

from app.core.security import UNUSABLE_PASSWORD_HASH
from app.models import AppUser, Consent, Profile
from app.models.enums import ConsentPurpose


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

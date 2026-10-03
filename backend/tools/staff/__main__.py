"""Create (or reset) a staff account for the safety and admin console:

    python -m tools.staff --email reviewer@nabz.local --role reviewer
    python -m tools.staff --email admin@nabz.local --role admin
    python -m tools.staff --email doctor@nabz.local --role clinician --name "Dr. Anjali Rath" --verified \
        --registration "OCMR 40213" --council "Odisha Council of Medical Registration" --specialty "General medicine"

The account is confirmed and its two-step sign-in is on from the start, so it can sign in straight away. The tool
prints a new password and the authenticator key once (add the key, or the otpauth:// link as a QR code, to an
authenticator app); nothing is written to disk. Running it again for the same email issues a new password and key
and signs out every session.

For a clinician, `--name`, `--registration` and `--council` record their medical-council registration, and
`--verified` marks it as checked, as an admin does on the console's Doctors tab after looking it up in the council's
register. Use invented names and numbers for a demo doctor.
"""

from __future__ import annotations

import argparse
import secrets
import sys
from datetime import UTC, datetime

from sqlalchemy import select

from app.core import security
from app.db import SessionLocal
from app.models import AppUser, Clinician
from app.models.enums import UserRole
from app.services.auth import normalise_email, revoke_all


def main() -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.staff")
    ap.add_argument("--email", required=True)
    ap.add_argument("--role", required=True, choices=[r.value for r in UserRole if r is not UserRole.USER])
    ap.add_argument("--name", help="clinician: full name as registered")
    ap.add_argument("--registration", help="clinician: registration number")
    ap.add_argument("--council", help="clinician: the medical council that issued it")
    ap.add_argument("--specialty")
    ap.add_argument("--verified", action="store_true", help="clinician: mark the registration as checked")
    a = ap.parse_args()
    if a.role == UserRole.CLINICIAN.value and a.name and not (a.registration and a.council):
        ap.error("--name needs --registration and --council")

    email = normalise_email(a.email)
    password = secrets.token_urlsafe(12)
    secret = security.new_totp_secret()
    now = datetime.now(UTC)
    with SessionLocal.begin() as s:
        user = s.scalar(select(AppUser).where(AppUser.email == email))
        if user is None:
            user = AppUser(email=email, password_hash="")
            s.add(user)
        user.role = UserRole(a.role)
        user.password_hash = security.hash_password(password)
        user.email_verified_at = user.email_verified_at or now
        user.totp_secret_enc = security.encrypt(secret)
        user.totp_enabled_at = now
        user.failed_logins, user.locked_until, user.deleted_at = 0, None, None
        s.flush()
        revoke_all(s, user.id)
        if a.role == UserRole.CLINICIAN.value and a.name:
            reg = s.get(Clinician, user.id) or Clinician(user_id=user.id)
            reg.full_name, reg.registration_no, reg.council = a.name, a.registration, a.council
            reg.specialty, reg.verified_at = a.specialty, now if a.verified else None
            s.add(reg)
    print(f"{email} now has the {a.role} role.")
    if a.role == UserRole.CLINICIAN.value and a.name:
        state = "checked" if a.verified else "not checked"
        print(f"registration:      {a.name}, {a.council} {a.registration} ({state})")
    print(f"password:          {password}")
    print(f"authenticator key: {secret}")
    print(f"otpauth link:      {security.totp_uri(secret, email)}")
    print("These are shown once; run the tool again to issue new ones.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

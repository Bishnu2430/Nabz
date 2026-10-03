"""Create (or reset) a staff account for the safety and admin console:

    python -m tools.staff --email reviewer@nabz.local --role reviewer
    python -m tools.staff --email admin@nabz.local --role admin

The account is confirmed and its two-step sign-in is on from the start, so it can sign in straight away. The tool
prints a new password and the authenticator key once (add the key, or the otpauth:// link as a QR code, to an
authenticator app); nothing is written to disk. Running it again for the same email issues a new password and key
and signs out every session.
"""

from __future__ import annotations

import argparse
import secrets
import sys
from datetime import UTC, datetime

from sqlalchemy import select

from app.core import security
from app.db import SessionLocal
from app.models import AppUser
from app.models.enums import UserRole
from app.services.auth import normalise_email, revoke_all


def main() -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.staff")
    ap.add_argument("--email", required=True)
    ap.add_argument("--role", required=True, choices=[r.value for r in UserRole if r is not UserRole.USER])
    a = ap.parse_args()

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
    print(f"{email} now has the {a.role} role.")
    print(f"password:          {password}")
    print(f"authenticator key: {secret}")
    print(f"otpauth link:      {security.totp_uri(secret, email)}")
    print("These are shown once; run the tool again to issue new ones.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

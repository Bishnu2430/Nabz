"""Password hashing, random tokens, TOTP and encryption of TOTP secrets (docs/12 §3, docs/10 §4)."""

from __future__ import annotations

import base64
import hashlib
import secrets
from functools import lru_cache
from pathlib import Path

import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from cryptography.exceptions import InvalidTag
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.core.config import settings

# A stored hash that no password can match: accounts created without a password (tests, imports) can't sign in.
UNUSABLE_PASSWORD_HASH = "!"  # noqa: S105 - deliberately not a valid hash

MIN_PASSWORD_LENGTH = 10
_hasher = PasswordHasher()  # Argon2id with the library's current recommended parameters


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(stored: str, password: str) -> bool:
    try:
        return _hasher.verify(stored, password)
    except (VerificationError, InvalidHashError):
        return False


def needs_rehash(stored: str) -> bool:
    try:
        return _hasher.check_needs_rehash(stored)
    except InvalidHashError:
        return False


@lru_cache(maxsize=1)
def common_passwords() -> frozenset[str]:
    """Passwords of 10 or more characters from the NCSC's 100,000 most used (data/security, ASVS 5.0 6.2.4)."""
    path = Path(settings.data_dir) / "security" / "common-passwords.txt"
    return frozenset(path.read_text(encoding="utf-8").split()) if path.exists() else frozenset()


def password_problem(password: str, email: str = "") -> str | None:
    """A reason the password is too weak, or None. Length first (NIST SP 800-63B), then the obvious, then the list
    of passwords people use most."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Use at least {MIN_PASSWORD_LENGTH} characters."
    if len(set(password)) < 4:
        return "Use a less repetitive password."
    if email and email.split("@")[0].lower() in password.lower():
        return "Don't include your email address in your password."
    if password.lower() in common_passwords():
        return COMMON
    return None


COMMON = "This password is one of the most used. Choose another."


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


GCM_PREFIX = "g1:"  # AES-256-GCM; anything else is an older Fernet (AES-CBC with HMAC) value


def _fernet() -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode()).digest())
    return Fernet(key)


def _gcm() -> AESGCM:
    key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"nabz secret-at-rest v1").derive(
        settings.secret_key.encode())
    return AESGCM(key)


def encrypt(text: str) -> str:
    """Authenticated encryption for secrets at rest, such as TOTP keys (ASVS 5.0 11.3.2: AES-GCM)."""
    nonce = secrets.token_bytes(12)
    return GCM_PREFIX + base64.urlsafe_b64encode(nonce + _gcm().encrypt(nonce, text.encode(), None)).decode()


def decrypt(blob: str) -> str | None:
    """The text, or None if the value was tampered with or encrypted under another key. Reads older Fernet values."""
    if blob.startswith(GCM_PREFIX):
        try:
            raw = base64.urlsafe_b64decode(blob[len(GCM_PREFIX):])
            return _gcm().decrypt(raw[:12], raw[12:], None).decode()
        except (InvalidTag, ValueError):
            return None
    try:
        return _fernet().decrypt(blob.encode()).decode()
    except InvalidToken:
        return None


def new_totp_secret() -> str:
    return pyotp.random_base32()


def totp_uri(secret: str, email: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name="Nabz")


def verify_totp(secret: str, code: str) -> bool:
    code = code.strip().replace(" ", "")
    return code.isdigit() and pyotp.TOTP(secret).verify(code, valid_window=1)

# A stored hash that no password can match: used for development and test accounts that
# must never be able to sign in. Real hashing (Argon2id) arrives with accounts in Sprint 6.
UNUSABLE_PASSWORD_HASH = "!"  # noqa: S105 - deliberately not a valid hash

# 13 · Security self-assessment (OWASP ASVS 5.0, Level 1)

| | |
|---|---|
| **Document ID** | NBZ-DOC-13 |
| **Version** | 1.0 |
| **Standard** | [OWASP Application Security Verification Standard 5.0.0](https://github.com/OWASP/ASVS/tree/master/5.0), Level 1 (CC BY-SA 4.0) |
| **Verifies** | NFR-09 ([02 §5](02-software-requirements-specification.md#5-non-functional-requirements)) |
| **Assessed** | 2026-10-03, against branch `feat/finish-requirements` |

## 1. Scope and method

**In scope:** the API (`backend/app`), the worker, the web app (`frontend/src`) and the Docker Compose deployment as run for the demonstration: one machine, the web app and API on `localhost`.

**Method:** every Level 1 requirement in ASVS 5.0 (70) was read against the code, and each verdict cites the code or the automated test that shows it. Where a requirement was not met, it was fixed when the fix was small, and the fix is listed in §3. Requirement texts below are shortened; the standard has the full wording.

**Verdicts:** *Met*; *Partial* (met only in some configurations, or with a stated exception); *Not met*; *N/A* (the application has no such feature).

## 2. Summary

| Verdict | Requirements |
|---|---|
| Met | 50 |
| Partial | 4 (3.3.1, 3.4.1, 6.4.1, 14.2.1) |
| Not met | 3 (12.1.1, 12.2.1, 12.2.2) |
| N/A | 13 (no rich-text input, XML, WebSockets, self-contained tokens or OAuth) |

**All 7 open items come from one fact: the demonstration serves HTTP on `localhost`.** The application is ready for HTTPS. Setting `COOKIE_SECURE=true` behind a TLS-terminating proxy:
- renames the cookie to `__Host-nabz_session` and marks it `Secure`;
- turns on HSTS.

That closes 3.3.1 and 3.4.1. The proxy itself closes 12.1.1, 12.2.1 and 12.2.2. §5 lists what remains.

## 3. Fixed during the assessment

| Requirement | Finding | Fix | Evidence |
|---|---|---|---|
| 3.2.1, 3.4.1, 4.1.1 | API responses had no security headers; JSON had no charset | Every response: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Cross-Origin-Resource-Policy: same-origin`. JSON: `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'` and `charset=utf-8`. HSTS (1 year) behind HTTPS | `app/main.py` `SecurityHeaders`; `test_auth.py::test_every_response_carries_the_security_headers` |
| 3.2.1, 14.2.1 | The web pages had no security headers; a share link's token could leak as a referrer | The web server sends `nosniff`, `DENY`, `no-referrer` and a permissions policy on every page | `frontend/vite.config.ts` |
| 3.3.1 | Cookie had no name prefix | `__Host-nabz_session` when `COOKIE_SECURE=true` | `app/api/deps.py` |
| 6.2.4 | No check against common passwords | The 9,113 passwords of 10+ characters from the NCSC's 100,000 most used are refused, in any case (`data/security/common-passwords.txt`, MIT, from SecLists) | `test_auth.py::test_one_of_the_most_used_passwords_is_refused_in_any_case` |
| 7.2.4 | Signing in left the browser's previous session valid on the server | Sign-in revokes the presented session before issuing a new one | `test_auth.py::test_signing_in_again_ends_the_session_the_browser_had` |
| 11.3.2 | TOTP secrets used Fernet (AES-CBC with HMAC), legacy in ASVS Appendix C | New secrets use AES-256-GCM with an HKDF-derived key; older values are still read | `test_auth.py::test_secrets_at_rest_use_aes_gcm_and_older_values_still_read` |

## 4. Third-party components (15.1.1)

**Remediation time frames**, from the day a vulnerability in a dependency is published:
- critical or high severity: fixed or mitigated within 7 days;
- medium: within 30 days;
- low: at the next planned update.

**Updates.** Dependencies are reviewed at the start of every sprint and before each release, with `npm audit` for the web app and the OSV database for the Python lock file.

**Result on 2026-10-03 (15.2.1):**
- `npm audit`: 0 vulnerabilities, production and development dependencies.
- 83 locked Python packages (`backend/uv.lock`) queried against [OSV](https://osv.dev): 0 known vulnerabilities.

## 5. Open items

| Item | Requirements | What closes it |
|---|---|---|
| HTTPS | 3.3.1, 3.4.1, 12.1.1, 12.2.1, 12.2.2 | Put a TLS-terminating reverse proxy (for example Caddy) in front of the web app with a publicly trusted certificate, TLS 1.2 and 1.3 only, and set `COOKIE_SECURE=true`. Calls to Groq, ElevenLabs and MedlinePlus already use TLS. |
| Initial staff passwords | 6.4.1 | `tools.staff` prints a random 16-character password that doesn't expire. Add "must change at first sign-in" or an expiry. Two-step sign-in is already required before a staff account can do anything. |
| Capability links | 14.2.1 | By design, share links and emailed links carry a token in the URL. Each token is 256 random bits, stored only as a SHA-256 hash, expires, and can be withdrawn or is single-use. Pages send no referrer. Accepted as an exception. |

## 6. Requirement by requirement

### V1 Encoding and sanitization

| ID | Requirement (short) | Verdict | Evidence |
|---|---|---|---|
| 1.2.1 | Output encoding for the context | Met | React renders every value as text; the API returns JSON only; emails are plain text; the share QR code is drawn by Segno from a URL the server builds |
| 1.2.2 | Encode untrusted data in URLs; only safe protocols | Met | `encodeURIComponent` for every path or query part built in the web app; knowledge-document URLs must match `^https?://` (`KbDocumentIn`) |
| 1.2.3 | Encoding when building JavaScript or JSON | Met | JSON is produced by FastAPI and Pydantic serialisers and `JSON.stringify`; nothing is built by string concatenation |
| 1.2.4 | Parameterised database queries | Met | SQLAlchemy ORM with bound parameters throughout; the only `text()` SQL is constant (`select 1`, index predicates) |
| 1.2.5 | No OS command injection | Met | The application runs no OS commands (no `subprocess` or `os.system` in `backend/app`) |
| 1.3.1 | Sanitise rich-text (WYSIWYG) input | N/A | No rich-text input: every field is plain text, shown as text |
| 1.3.2 | No `eval()` or dynamic code execution | Met | None in the API or the web app (no `eval`, `new Function` or `dangerouslySetInnerHTML`) |
| 1.5.1 | Safe XML parser configuration | N/A | No XML from users is parsed; PDFs go to PDFium and images to OpenCV and Pillow |

### V2 Validation and business logic

| ID | Requirement (short) | Verdict | Evidence |
|---|---|---|---|
| 2.1.1 | Input validation rules documented | Met | Types, lengths, patterns and enums in `app/schemas.py`; plausibility bounds per test in the catalogue ([04](04-data-design.md)); upload rules in [12 §3](12-ux-and-access-design.md) |
| 2.2.1 | Input checked against business expectations | Met | Enum allow-lists; plausible-value checks on results and home readings (`test_care.py::test_home_readings_are_checked_charted_against_the_persons_own_target`) |
| 2.2.2 | Validation at a trusted service layer | Met | Every rule is enforced by the API; the web app's checks only give earlier feedback |
| 2.3.1 | Business flows in order, without skipping steps | Met | A report moves upload → review → confirm → analyse → explain on the server; values are locked after confirmation (`test_api.py::test_upload_review_confirm`); a critical-limit change applies only after review (`test_catalogue_admin.py::test_a_critical_limit_applies_only_after_clinical_review`) |

### V3 Web frontend security

| ID | Requirement (short) | Verdict | Evidence |
|---|---|---|---|
| 3.2.1 | Browsers must not render responses in the wrong context | Met | `nosniff` on every response; uploaded files are served inline only with their sniffed type (PDF, JPEG or PNG) through authorised routes; JSON carries `default-src 'none'` |
| 3.2.2 | Text rendered with safe functions | Met | React text nodes everywhere |
| 3.3.1 | Cookies `Secure` with a `__Host-`/`__Secure-` prefix | Partial | `Secure` and `__Host-nabz_session` behind HTTPS (`COOKIE_SECURE=true`); off on the local HTTP demonstration. Always `HttpOnly`, `SameSite=Strict`, path `/` |
| 3.4.1 | HSTS of at least one year | Partial | Sent behind HTTPS (`max-age=31536000; includeSubDomains`); not on local HTTP |
| 3.4.2 | CORS origin fixed or allow-listed | Met | No CORS headers at all: the web app and the API share one origin, so the browser refuses cross-origin reads |
| 3.5.1 | Cross-origin requests to sensitive functions are refused | Met | Every non-GET request needs the session's CSRF token in a header (`app/api/deps.py`), and the cookie is `SameSite=Strict` (`test_auth.py::test_sign_up_verify_sign_in_and_csrf`) |
| 3.5.2 | Preflight cannot be bypassed | N/A | Protection doesn't rely on CORS preflight (3.5.1) |
| 3.5.3 | Sensitive functions use non-safe HTTP methods | Met | Every change is `POST`, `PUT`, `PATCH` or `DELETE`; email links open a page that `POST`s the token |

### V4 API and web service

| ID | Requirement (short) | Verdict | Evidence |
|---|---|---|---|
| 4.1.1 | Content-Type with a charset on every body | Met | `application/json; charset=utf-8` on JSON and problem details; files carry their own type |
| 4.4.1 | WebSockets over TLS | N/A | No WebSockets; progress uses Server-Sent Events on the same origin |

### V5 File handling

| ID | Requirement (short) | Verdict | Evidence |
|---|---|---|---|
| 5.2.1 | Only files of a size the app can process | Met | Reports up to 10 MB, other records up to 20 MB (`test_worker.py::test_ingest_rules`) |
| 5.2.2 | File type checked by content, not just extension | Met | The type is sniffed from the first bytes (PDF, JPEG, PNG) and anything else is refused; the stored extension comes from the sniffed type (`app/services/ingest.py`) |
| 5.3.1 | Uploads never executed from a public folder | Met | Files live in a private store outside any web root and are served only through authorised API routes |
| 5.3.2 | File paths built from trusted data | Met | Storage keys are generated from UUIDs; user file names are never used |

### V6 Authentication

| ID | Requirement (short) | Verdict | Evidence |
|---|---|---|---|
| 6.1.1 | Anti-automation controls documented | Met | [12 §3](12-ux-and-access-design.md) and [10 §4](10-safety-privacy-compliance.md): 20 account requests a minute per IP; a 15-minute lockout after 5 failures, ended early by a password reset so it can't be used to keep someone out |
| 6.2.1 | Passwords of at least 8 characters | Met | At least 10 (`MIN_PASSWORD_LENGTH`) |
| 6.2.2 | Users can change their password | Met | Settings → Password |
| 6.2.3 | Change needs the current password | Met | `current_password` checked (`test_auth.py`) |
| 6.2.4 | Checked against at least the top 3,000 common passwords | Met | 9,113 refused (§3) |
| 6.2.5 | No composition rules | Met | Length, a minimal variety check and "not your email" only |
| 6.2.6 | `type=password` fields | Met | All password inputs |
| 6.2.7 | Paste and password managers allowed | Met | Nothing blocks paste; `autocomplete` is `current-password` or `new-password` |
| 6.2.8 | Password verified exactly as entered | Met | No trimming or case change before Argon2id verification |
| 6.3.1 | Credential-stuffing and brute-force controls as documented | Met | `test_auth.py::test_wrong_passwords_lock_the_account_and_errors_stay_generic` |
| 6.3.2 | No default accounts | Met | No built-in accounts; staff accounts are created by `tools.staff` with a random password and two-step sign-in |
| 6.4.1 | Initial secrets random, policy-compliant and short-lived | Partial | Email-verification (24 h) and reset (30 min) tokens are random and single-use; a staff account's first password is random but doesn't expire (§5) |
| 6.4.2 | No password hints or secret questions | Met | None |

### V7 Session management

| ID | Requirement (short) | Verdict | Evidence |
|---|---|---|---|
| 7.2.1 | Session tokens verified by a trusted backend | Met | Every request looks the session up on the server (`session_user`) |
| 7.2.2 | Dynamically generated session tokens | Met | One reference token per session; no static keys |
| 7.2.3 | Reference tokens from a CSPRNG, at least 128 bits | Met | `secrets.token_urlsafe(32)` (256 bits), stored only as a SHA-256 hash |
| 7.2.4 | New token on sign-in; the old one ended | Met | §3 |
| 7.4.1 | Terminated sessions can't be used again | Met | Sign-out revokes the row on the server (`test_auth.py::test_sign_out_and_sign_out_everywhere`) |
| 7.4.2 | All sessions end when an account is disabled or deleted | Met | Deleting an account deletes its sessions; an admin can sign a user out everywhere (`test_console.py::test_the_admin_manages_roles_sessions_and_failed_jobs`) |

### V8 Authorization

| ID | Requirement (short) | Verdict | Evidence |
|---|---|---|---|
| 8.1.1 | Authorization rules documented | Met | [12 §2](12-ux-and-access-design.md#2-roles-and-permissions) roles and permissions |
| 8.2.1 | Function-level access needs explicit permission | Met | `require_roles` on every staff and clinician route (`test_console.py::test_members_cannot_open_the_console`, `test_clinicians.py`) |
| 8.2.2 | Data-level access (no IDOR) | Met | Every profile, report, record, grant and note is checked against the account; another account's item answers 404 (`test_api.py::test_other_peoples_data_is_invisible`, `test_clinicians.py`) |
| 8.3.1 | Authorization enforced on the server | Met | The web app's role checks only choose what to show |

### V9 Self-contained tokens and V10 OAuth and OIDC

| ID | Verdict | Reason |
|---|---|---|
| 9.1.1, 9.1.2, 9.1.3, 9.2.1 | N/A | No self-contained tokens (such as JWTs); sessions and links use opaque reference tokens |
| 10.4.1 – 10.4.5 | N/A | Nabz is not an OAuth authorization server and uses no OAuth or OIDC |

### V11 Cryptography

| ID | Requirement (short) | Verdict | Evidence |
|---|---|---|---|
| 11.3.1 | No ECB or PKCS#1 v1.5 | Met | Neither is used |
| 11.3.2 | Approved ciphers and modes such as AES-GCM | Met | AES-256-GCM for secrets at rest (§3); legacy values are only read |
| 11.4.1 | Approved hash functions only | Met | SHA-256 for tokens and checksums, Argon2id for passwords. MD5 appears only in a test-only embedder that buckets words, not for security |

### V12 Secure communication

| ID | Requirement (short) | Verdict | Evidence |
|---|---|---|---|
| 12.1.1 | Only TLS 1.2 and 1.3 | Not met | The demonstration serves HTTP on `localhost`; outbound calls use TLS (§5) |
| 12.2.1 | TLS for all client connections | Not met | As above |
| 12.2.2 | Publicly trusted certificates | Not met | As above |

### V13 Configuration

| ID | Requirement (short) | Verdict | Evidence |
|---|---|---|---|
| 13.4.1 | No source-control metadata deployed | Met | The API image and container hold `backend/` only, and the web container mounts `frontend/` only; `.git` is in neither |

### V14 Data protection

| ID | Requirement (short) | Verdict | Evidence |
|---|---|---|---|
| 14.2.1 | No sensitive data in URLs | Partial | Session and CSRF tokens and API keys never appear in URLs; share-link and emailed tokens do, by design (§5) |
| 14.3.1 | Authenticated data cleared from the client at sign-out | Met | Sign-out clears the query cache; browser storage holds only language, theme, text size and the body-map view |

### V15 Secure coding and architecture

| ID | Requirement (short) | Verdict | Evidence |
|---|---|---|---|
| 15.1.1 | Remediation time frames for components documented | Met | §4 |
| 15.2.1 | No components past those time frames | Met | §4: 0 known vulnerabilities |
| 15.3.1 | Only the needed fields returned | Met | Every route has a Pydantic response model; staff views hold no names, values or reports (`test_console.py`) |

## Revision history

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-10-03 | First assessment: 70 Level 1 requirements; 6 findings fixed; open items for HTTPS, staff first passwords and capability links |

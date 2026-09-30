# 12 · UX and access design

| | |
|---|---|
| **Document ID** | NBZ-DOC-12 |
| **Version** | 0.1 · decisions agreed 2026-09-27 |
| **Related** | [SRS](02-software-requirements-specification.md) · [Data design](04-data-design.md) · [Safety & privacy](10-safety-privacy-compliance.md) |

## 1. Decisions

| # | Decision | Choice |
|---|---|---|
| D1 | Visual theme | **Sumi-e scroll** (ink on washi paper) for light mode; **urushi lacquer** (black lacquer and gold) for dark mode and for the 3D stage |
| D2 | Roles | Member · Clinician · Clinical reviewer · Admin |
| D3 | Sign-in | Email and password only; authenticator-app codes (TOTP) for staff; no social login |
| D4 | Doctors | Real clinician accounts; the seeded accounts use fictional doctors |
| D5 | Seeded data | Seeded profiles use open-source synthetic patients (Synthea) plus the Nabz report generator; no real people |
| D6 | Build order | Unchanged from the [project plan](07-project-plan.md); accounts are built in Sprint 6 |

## 2. Roles and permissions

| Capability | Member | Clinician | Clinical reviewer | Admin |
|---|---|---|---|---|
| Own account, family profiles, consents | ✓ | ✓ (own) | ✓ (own) | ✓ (own) |
| Upload, review, explanations, trends for own profiles | ✓ | — | — | — |
| Share a report with a doctor (link or clinician account) | ✓ | — | — | — |
| View reports shared with them; add notes | — | ✓ | — | — |
| Safety queue: template fallbacks, flagged feedback (de-identified) | — | — | ✓ | — |
| Sign off critical limits and explanation templates | — | — | ✓ | — |
| Users, roles, clinician verification | — | — | — | ✓ |
| Catalogue, knowledge base, jobs, audit log, system health | — | — | view | ✓ |
| Read identifiable health data | own only | shared only | never | **break-glass only**: reason required, audited, owner notified |

Clinicians are verified by an admin against a medical-council registration number before they can receive shared reports. The admin role runs the system without routine access to health data. That is a deliberate privacy property and a jury talking point.

## 3. Authentication

- **Accounts:** email and password; Argon2id hashes; email verification before first upload; forgot and reset password by an emailed single-use token (hashed at rest, 30-minute expiry).
- **Email in development and the demo:** a **Mailpit** container captures every outgoing email and shows it in a web inbox, so no real mail server or credentials are needed.
- **Sessions:** server-side sessions in PostgreSQL behind an `HttpOnly`, `Secure`, `SameSite=Strict` cookie, plus a CSRF token for state-changing requests. Sessions are revocable ("sign out everywhere"), with a 14-day idle expiry and 1 day for staff.
- **Second factor:** TOTP is **required** for admin and clinical reviewer, and optional for members and clinicians.
- **Abuse protection:** per-IP and per-account rate limits; a 15-minute lockout after 5 failed attempts; generic error messages that don't reveal whether an email is registered.
- **No social login** (D3), which keeps the scope small and avoids sending data to a third-party identity provider.

**Schema additions (Sprint 6 migration `20260930_accounts_sessions_tokens`, details in [04 §5.7](04-data-design.md#57-accounts-and-sessions-sprint-6)):**
- `user_role` gains `clinician` and `reviewer`.
- New tables: `user_session` (token hash, CSRF token, last seen, revoked) and `auth_token` (confirm-email and reset tokens, hashed, single use).
- `app_user` gains `email_verified_at`, `totp_secret_enc`, `totp_enabled_at`, `failed_logins` and `locked_until`. The TOTP secret is encrypted in the application with Fernet, keyed from `SECRET_KEY`, rather than with `pgcrypto`: the key then never reaches the database or its logs.
- Deferred with the clinician features (Should): `clinician_verification`, `profile_member`, `clinician_note`.

**As built (Sprint 6).**
- **Rate limits:** 20 account requests per minute per IP address (sign-up, sign-in, resend, forgot password), held in memory in the API process; this is enough for one API instance and moves to PostgreSQL if the API is scaled out.
- **Same answer for every email:** sign-up and forgot-password answer 202 with the same words whether or not the email has an account. An existing owner gets an email saying someone tried to sign up. Sign-in with an unknown email still runs Argon2 on a dummy hash, so timing doesn't reveal it either.
- **One-click confirmation:** the emailed link opens a page with a button; nothing is confirmed on page load, so a mail scanner that opens links cannot use up the token.
- **Session rules:** a password reset signs out every device; a password change signs out the other devices; a new session is issued at every sign-in.
- **Staff:** a reviewer or admin without two-step sign-in can reach only its set-up (API 403 with `"setup": "totp"`; the web app redirects to Settings), and cannot turn it off.
- **Deletion (FR-33):** deleting a report, a person or the account removes the rows, the uploaded files and the narration audio at once; account deletion needs the password.

## 4. Seeded data

- **Clinicians:** 2–3 fictional doctor accounts with fictional names and registration numbers. No real doctor's name or identity is used.
- **Members and profiles:** fictional families (the "Priya and Ramesh" persona and a few others).
- **Lab histories:** Synthea, an open-source synthetic patient generator, produces multi-year records with LOINC-coded lab observations. Nabz imports them by matching `lab_test.loinc_code`, and the Nabz generator renders some of those histories as printable reports for uploading. All of it is synthetic; no real person's data is used.

## 5. Visual design

### 5.1 Palette

| Token | Light: sumi-e | Dark: urushi | Use |
|---|---|---|---|
| `surface` | `#F4EFE6` washi paper | `#16120F` black lacquer | Page |
| `surface-raised` | `#FBF8F2` | `#211B16` | Cards, sheets |
| `ink` | `#1F1D1B` | `#EDE3D1` | Body text |
| `ink-muted` | `#6B645B` | `#A89A82` | Secondary text |
| `hairline` | `#D9CFBF` | `#3A3029` | Borders, dividers |
| `accent` | `#B8412E` vermilion (seal) | `#C9A55A` gold | Primary action, seal stamp, focus |
| `link` | `#2E4A62` indigo | `#8FA9C4` | Links, info |
| `status-normal` | `#486A4D` jade | `#8FB093` | Normal |
| `status-borderline` | `#825A1D` ochre | `#D8A94E` | Borderline / change to watch; rows to check |
| `status-abnormal` | `#A33A28` deep vermilion | `#E07A62` | High or low |
| `status-critical` | `#8E1F1B` crimson | `#F0907E` | Critical (always with seal icon and text) |
| `gold` | `#9A7A36` | `#C9A55A` | Kintsugi seams on improving trends |

Every status is shown as **colour + icon + word**, never by colour alone. All text pairs must pass WCAG 2.2 AA.

**Contrast check (Sprint 3, `frontend/src/index.css`).**
- Status and body text colours pass AA (≥ 4.5 : 1) on `surface`, `surface-raised` and the darker `surface-sunken`, in both themes.
- Jade, ochre and gold were darkened from the first draft to get there. The first-draft jade and ochre measured 4.3–4.4 : 1 on `surface-sunken`, and gold measured 2.7 : 1.
- Abnormal was separated from the seal vermilion, so an abnormal value never looks like the brand colour.
- The vermilion `accent` is used for button backgrounds (button text 5.2 : 1), focus rings and the seal, never for small text on the sunken surface (4.3 : 1).
- In dark mode, every pair measures at least 5.8 : 1.

### 5.2 Type

| Role | Latin | Hindi | Odia |
|---|---|---|---|
| Display (headings, organ names) | Shippori Mincho | Noto Serif Devanagari | Noto Sans Oriya |
| Body (16–18 px minimum) | Noto Sans | Noto Sans Devanagari | Noto Sans Oriya |
| Numbers in tables | Noto Sans, tabular figures | same | same |

Brush lettering is decorative only and never carries information.

### 5.3 Motifs, each tied to a feature

| Motif | Where |
|---|---|
| **Hanko seal** | Stamps onto the report when the user confirms the values (the human-review gate) |
| **Ensō brush circle** | Loading and progress ring while a report is processed |
| **Hanging scroll** | The explanation unrolls section by section |
| **Handscroll** | The multi-year timeline scrolls horizontally |
| **Kintsugi** | Gold seam on a trend line where a value moved back into range |
| **Rice-paper body** | 3D body with ink contour lines and pigment-tinted organs on the lacquer stage. As built: a translucent figure whose shader draws a gold rim and faint contour lines every 5 cm; organ systems use the dark-theme status colours whatever the page theme, and abnormal ones breathe slowly (not with reduced motion). The flat SVG body, used when WebGL 2 is missing and on the landing page, is drawn with the same organ IDs |

### 5.4 What to avoid

- **Chinese or Japanese characters as decoration.** They read as nonsense or wrong meanings to native readers and mean nothing to most users.
- **Pseudo-"oriental" fonts and clichés** (dragons, lanterns, bamboo borders).
- **Arbitrary mixing of Chinese and Japanese motifs.** The design borrows principles (ma, asymmetry, paper, ink, seal) rather than costume.
- **Low contrast for decoration's sake:** many users are older.

## 6. Pages

| Area | Route | Page | Roles | Priority |
|---|---|---|---|---|
| Public | `/` | Landing: ink-body hero, how it works, privacy promise, language switch | all | Must |
| | `/login` `/signup` `/verify-email` `/forgot-password` `/reset-password` | Sign-in flows | all | Must |
| | `/privacy` `/safety` | Privacy notice; what Nabz is and is not | all | Must |
| | `/terms` `/about` | Terms; licences and attributions | all | Should |
| | `/s/:token` | Shared summary for a doctor, no login | anyone with link | Should |
| Member | `/welcome` | Onboarding: language → consents → first profile | member | Must |
| | `/home` | Family dashboard: card per person, alerts, recent reports, upload | member | Must |
| | `/p/:id` | One person: latest body map, report timeline, key trends | member | Must |
| | `/p/:id/upload` | Upload, quality check, live progress (ensō) | member | Must |
| | `/r/:id/review` | Values beside the image, weakest first, confirm with the seal | member | Must |
| | `/r/:id` | Insights: 3D body, organ cards, explanation (language + audio), doctor questions, sources | member | Must |
| | `/p/:id/tests/:code` | One test over time: change significance, projection, percentile | member | Must |
| | `/r/:id/print` | Printable summary and doctor questions | member | Should |
| | `/p/:id/share` | Share links and clinician access | member | Should |
| | `/settings` | Account, security (TOTP), language, consents, profiles, export, delete | all signed-in | Must |
| | `/help` | Frequently asked questions | all | Could |
| Clinician | `/clinician` · `/clinician/p/:id` | Shared with me · read-only view with notes | clinician | Should |
| Reviewer | `/review` | Safety queue and sign-offs | reviewer | Should |
| Admin | `/admin/users` | Users, roles, clinician verification | admin | Must |
| | `/admin` `/admin/catalogue` `/admin/knowledge` `/admin/jobs` `/admin/audit` | Health, catalogue, knowledge base, job monitor, audit log | admin | Should |
| System | — | 404, error boundary, offline banner | all | Must |

**Built by the end of Sprint 6:** the public pages (`/`, the sign-in flows, `/privacy`, `/safety`), `/home`, `/p/:id` (with the body-map timeline), `/p/:id/upload`, `/r/:id/review`, `/r/:id` (with the body map), `/p/:id/tests/:code` and `/settings` (which also holds each person's export and deletion). Not yet: `/welcome`, `/r/:id/print`, `/p/:id/share`, `/s/:token`, `/terms`, `/about`, `/help`, and the clinician, reviewer and admin areas.

## Revision history

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-09-27 | Decisions D1–D6, roles, authentication, visual design and page map |
| 0.2 | 2026-09-27 | §5.1 light-theme status colours adjusted to pass WCAG AA; contrast results |
| 0.3 | 2026-09-30 | §3 accounts as built in Sprint 6 (schema, rate limits, enumeration resistance, session rules, staff, deletion); §5.3 rice-paper body as built; §6 build status |

"""Get a demo account ready to run with no internet (FR-38), and check that it is.

    python -m tools.offline check   --email dev@nabz.local
    python -m tools.offline prepare --email dev@nabz.local --people "Ramesh Mohanty" --languages en,hi [--narrate --yes]

`check` lists, for each person's latest report, which languages have an explanation and which have narration, and
whether Groq and ElevenLabs can be reached from here. Offline, Nabz still shows every stored explanation and plays
every stored narration; anything new falls back (explanations and answers built from the values) or waits (audio).

`prepare` writes the missing explanations for the people and languages given (with the model when it can be reached
and the person has consented, otherwise from the values), and with `--narrate` makes the missing narration. Narration
uses ElevenLabs characters, so the tool first says how many it needs and only goes ahead with `--yes`. It records the
account holder's consent to voice processing for those people, as pressing "Allow and listen" would.
"""

from __future__ import annotations

import argparse
import sys

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.explanations import get_tts
from app.api.routes.profiles import POLICY_VERSION
from app.core.config import settings
from app.db import SessionLocal
from app.explain.llm import GroqProvider
from app.explain.tts import TTSError, narration_text
from app.knowledge.embed import default_embedder
from app.models import AppUser, Consent, Explanation, Profile, Report
from app.models.enums import ConsentPurpose, Lang, ReportStatus
from app.services.explanation import explain_report
from app.services.ingest import has_consent
from app.storage import default_storage

SERVICES = {"Groq (explanations)": "https://api.groq.com", "ElevenLabs (narration)": "https://api.elevenlabs.io"}
EXPLAINED = (ReportStatus.EXPLAINING, ReportStatus.EXPLAINED)


def reachable(url: str) -> bool:
    try:
        httpx.head(url, timeout=3.0)
        return True
    except httpx.HTTPError:
        return False


def latest_reports(s: Session, email: str, people: list[str] | None) -> list[tuple[Profile, Report]]:
    user = s.scalar(select(AppUser).where(AppUser.email == email.lower()))
    if user is None:
        sys.exit(f"{email}: no such account")
    out = []
    for p in s.scalars(select(Profile).where(Profile.owner_user_id == user.id, Profile.deleted_at.is_(None))
                       .order_by(Profile.created_at)):
        if people and p.display_name not in people:
            continue
        report = s.scalar(select(Report).where(Report.profile_id == p.id, Report.status.in_(EXPLAINED))
                          .order_by(Report.collected_at.desc().nulls_last()).limit(1))
        if report is not None:
            out.append((p, report))
    return out


def check(email: str) -> int:
    online = {name: reachable(url) for name, url in SERVICES.items()}
    with SessionLocal() as s:
        rows = latest_reports(s, email, None)
        print(f"{'Person':<22} {'Latest report':<14} {'Explained in':<14} {'Narrated in'}")
        missing_audio = 0
        for p, r in rows:
            exps = s.scalars(select(Explanation).where(Explanation.report_id == r.id)).all()
            langs = sorted(e.language.value for e in exps)
            audio = sorted(e.language.value for e in exps if e.audio_key)
            missing_audio += len(langs) - len(audio)
            when = r.collected_at.isoformat() if r.collected_at else "undated"
            print(f"{p.display_name:<22} {when:<14} {', '.join(langs) or '—':<14} {', '.join(audio) or '—'}")
    print()
    for name, ok in online.items():
        print(f"{name}: {'reachable' if ok else 'not reachable (offline)'}")
    print("\nOffline, every explanation above is shown and every narration above plays. New explanations and answers"
          "\nare built from the values; narration that doesn't exist yet can't be made.")
    if missing_audio:
        print(f"{missing_audio} explanation(s) have no narration; `prepare --narrate` makes them while online.")
    return 0


def prepare(email: str, people: list[str], languages: list[str], narrate: bool, yes: bool) -> int:
    provider = GroqProvider(settings.groq_api_key, settings.llm_model) if settings.groq_api_key else None
    embedder = default_embedder()
    with SessionLocal() as s:
        rows = latest_reports(s, email, people)
        if not rows:
            sys.exit("No explained report for those people.")
        for p, r in rows:
            have = {e.language.value for e in s.scalars(select(Explanation).where(Explanation.report_id == r.id))}
            for lang in languages:
                if lang not in have:
                    out = explain_report(s, r, lang, provider, embedder)
                    s.commit()
                    print(f"{p.display_name}: wrote the {lang} explanation ({out.source}"
                          f"{f', {out.reason}' if out.reason else ''})")
        if not narrate:
            return 0
        todo = [(p, e) for p, r in rows for e in s.scalars(select(Explanation).where(
            Explanation.report_id == r.id, Explanation.language.in_([Lang(x) for x in languages]),
            Explanation.audio_key.is_(None)))]
        chars = sum(len(narration_text(e.content, e.language.value)) for _, e in todo)
        print(f"Narration for {len(todo)} explanation(s): about {chars:,} ElevenLabs characters.")
        if not todo or not yes:
            if todo:
                print("Run again with --yes to make them.")
            return 0
        tts = get_tts()
        if tts is None:
            sys.exit("ELEVENLABS_API_KEY isn't set.")
        storage = default_storage()
        for p, e in todo:
            if not has_consent(s, p.id, ConsentPurpose.VOICE):
                s.add(Consent(user_id=p.owner_user_id, profile_id=p.id, purpose=ConsentPurpose.VOICE,
                              policy_version=POLICY_VERSION))
            try:
                audio = tts.synthesize(narration_text(e.content, e.language.value), e.language.value)
            except TTSError as exc:
                print(f"{p.display_name} ({e.language.value}): narration failed: {exc}")
                continue
            key = f"audio/{e.report_id}/{e.id}.mp3"
            storage.put(key, audio)
            e.audio_key = key
            s.commit()
            print(f"{p.display_name} ({e.language.value}): narration ready, {len(audio) // 1024} KB")
    return 0


def rehearse() -> int:
    """TC-21: a whole report, start to finish, on a throwaway account, then gone. Run it with the stack offline
    (compose.offline.yaml) to see what the demo does without internet."""
    import time
    import uuid
    from datetime import UTC, datetime

    from fastapi.testclient import TestClient

    from app.api import deps
    from app.core.security import UNUSABLE_PASSWORD_HASH
    from app.main import app

    for name, url in SERVICES.items():
        print(f"{name}: {'reachable' if reachable(url) else 'not reachable (offline)'}")
    email = f"rehearsal-{uuid.uuid4().hex[:8]}@nabz.local"
    with SessionLocal.begin() as s:
        user = AppUser(email=email, password_hash=UNUSABLE_PASSWORD_HASH, email_verified_at=datetime.now(UTC))
        s.add(user)
    app.dependency_overrides[deps.current_user] = lambda: user
    ok = True
    started = time.monotonic()

    def wait_for(c: TestClient, rid: str, states: set[str], limit: float) -> str:
        end = time.monotonic() + limit
        while time.monotonic() < end:
            state = c.get(f"/v1/reports/{rid}").json()["status"]
            if state in states or state in ("failed", "rejected"):
                return state
            time.sleep(1)
        return "timed out"

    try:
        with TestClient(app) as c:
            pid = c.post("/v1/profiles", json={"display_name": "Rehearsal", "sex": "female",
                                               "date_of_birth": "1985-02-11", "relationship": "self",
                                               "consent_processing": True}).json()["id"]
            # with consent to the AI service, so the model is tried and, offline, its absence is handled
            c.put(f"/v1/profiles/{pid}/consents/external_ai", json={"granted": True})
            rid = c.post(f"/v1/profiles/{pid}/sample-report").json()["report_id"]
            state = wait_for(c, rid, {"needs_review"}, 180)
            rows = len(c.get(f"/v1/reports/{rid}").json()["observations"])
            print(f"read the sample report: {state}, {rows} values ({time.monotonic() - started:.0f} s)")
            ok &= state == "needs_review"
            c.post(f"/v1/reports/{rid}/confirm", json={})
            state = wait_for(c, rid, {"explaining", "explained"}, 180)
            state = wait_for(c, rid, {"explained"}, 120) if state == "explaining" else state
            print(f"analysed and explained: {state} ({time.monotonic() - started:.0f} s)")
            ok &= state == "explained"
            e = c.get(f"/v1/reports/{rid}/explanation?lang=en").json()["explanation"] or {}
            print(f"explanation: {e.get('source')} ({e.get('reason') or 'model'})")
            organs = len(c.get(f"/v1/reports/{rid}/insights").json()["organs"])
            print(f"results page: {organs} organ systems")
            for q in ("Which results are outside the range?", "Do I have diabetes?"):
                a = c.post(f"/v1/reports/{rid}/ask", json={"question": q}).json()
                print(f"asked {q!r}: {a.get('mode')}{f' ({a['refusal']})' if a.get('refusal') else ''}")
                ok &= a.get("mode") in ("knowledge", "refusal", "model")
            c.delete(f"/v1/profiles/{pid}")
    finally:
        app.dependency_overrides.clear()
        with SessionLocal.begin() as s:
            s.delete(s.get(AppUser, user.id))
    print(f"\n{'Passed' if ok else 'Failed'} in {time.monotonic() - started:.0f} s; the rehearsal account is deleted.")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.offline")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("rehearse", help="run one report end to end on a throwaway account (TC-21)")
    c = sub.add_parser("check")
    c.add_argument("--email", required=True)
    pr = sub.add_parser("prepare")
    pr.add_argument("--email", required=True)
    pr.add_argument("--people", nargs="+", required=True, help="display names, e.g. \"Ramesh Mohanty\"")
    pr.add_argument("--languages", default="en", help="comma-separated: en,hi,or")
    pr.add_argument("--narrate", action="store_true", help="also make the narration (uses ElevenLabs characters)")
    pr.add_argument("--yes", action="store_true", help="go ahead with the narration")
    a = ap.parse_args()
    if a.cmd == "rehearse":
        return rehearse()
    if a.cmd == "check":
        return check(a.email)
    return prepare(a.email, a.people, [x.strip() for x in a.languages.split(",") if x.strip()], a.narrate, a.yes)


if __name__ == "__main__":
    raise SystemExit(main())

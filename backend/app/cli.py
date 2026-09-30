"""Management commands.

    python -m app.cli seed-catalogue [--dir PATH]
    python -m app.cli ingest FILE [--email dev@nabz.local] [--profile "Dev profile"]
    python -m app.cli show-report REPORT_ID
"""

import argparse
import sys
import uuid
from pathlib import Path

from sqlalchemy import select

from app.catalogue import CatalogueError, read_catalogue
from app.catalogue.seed import seed_catalogue
from app.core.config import settings
from app.core.security import UNUSABLE_PASSWORD_HASH
from app.db import SessionLocal
from app.models import AppUser, Consent, Observation, Profile, Report
from app.models.enums import ConsentPurpose
from app.services.ingest import IngestError, ingest_report
from app.storage import default_storage


def cmd_seed_catalogue(args: argparse.Namespace) -> int:
    directory = Path(args.dir or Path(settings.data_dir) / "catalogue")
    try:
        data = read_catalogue(directory)
    except CatalogueError as exc:
        print(exc, file=sys.stderr)
        return 1
    with SessionLocal.begin() as session:
        result = seed_catalogue(session, data)
    print(f"seeded {result.organs} organ systems, {result.tests} tests, {result.conversions} unit conversions, "
          f"{result.ranges} reference ranges, {result.limits} critical limits, "
          f"{result.percentiles} population percentile cells")
    return 0


def cmd_load_knowledge(args: argparse.Namespace) -> int:
    from app.knowledge.embed import default_embedder
    from app.knowledge.store import load_knowledge

    embedder = default_embedder()
    if embedder is None:
        print("embedding model not found in data/external/models (see data/external.md)", file=sys.stderr)
        return 1
    path = Path(args.file or Path(settings.data_dir) / "knowledge" / "chunks.jsonl")
    with SessionLocal.begin() as session:
        result = load_knowledge(session, embedder, path)
    print(f"loaded {result.documents} documents, {result.chunks} passages ({embedder.name})")
    return 0


def cmd_create_user(args: argparse.Namespace) -> int:
    """Create a verified account (e.g. staff or seeded clinicians). Members normally sign up in the app."""
    from datetime import UTC, datetime

    from app.core.security import hash_password, password_problem
    from app.models.enums import UserRole

    if problem := password_problem(args.password, args.email):
        print(problem, file=sys.stderr)
        return 1
    with SessionLocal.begin() as s:
        if s.scalar(select(AppUser).where(AppUser.email == args.email.lower())):
            print(f"{args.email} already has an account", file=sys.stderr)
            return 1
        s.add(AppUser(email=args.email.lower(), password_hash=hash_password(args.password), role=UserRole(args.role),
                      email_verified_at=datetime.now(UTC)))
    print(f"created {args.role} {args.email}")
    return 0


def cmd_set_password(args: argparse.Namespace) -> int:
    """Set a password (and confirm the email) for an existing account, e.g. the pre-Sprint-6 development account."""
    from datetime import UTC, datetime

    from app.core.security import hash_password, password_problem

    if problem := password_problem(args.password, args.email):
        print(problem, file=sys.stderr)
        return 1
    with SessionLocal.begin() as s:
        user = s.scalar(select(AppUser).where(AppUser.email == args.email.lower()))
        if user is None:
            print(f"no account for {args.email}", file=sys.stderr)
            return 1
        user.password_hash = hash_password(args.password)
        user.email_verified_at = user.email_verified_at or datetime.now(UTC)
        user.failed_logins, user.locked_until = 0, None
    print(f"password set for {args.email}")
    return 0


def cmd_extract_imaging(args: argparse.Namespace) -> int:
    """Take the study image and report text out of imaging records stored before the viewer existed."""
    from app.api.routes.records import attach_study
    from app.models import HealthRecord
    from app.models.enums import RecordKind

    storage = default_storage()
    done = 0
    with SessionLocal.begin() as s:
        for record in s.scalars(select(HealthRecord).where(HealthRecord.kind == RecordKind.IMAGING,
                                                           HealthRecord.image_key.is_(None))):
            attach_study(record, storage.get(record.storage_key), storage)
            done += record.image_key is not None
    print(f"study images taken from {done} imaging records")
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    """Development helper until the upload API exists: queue a file for a local dev profile."""
    data = Path(args.file).read_bytes()
    with SessionLocal.begin() as s:
        user = s.scalar(select(AppUser).where(AppUser.email == args.email))
        if user is None:
            user = AppUser(email=args.email, password_hash=UNUSABLE_PASSWORD_HASH)
            s.add(user)
            s.flush()
        profile = s.scalar(select(Profile).where(Profile.owner_user_id == user.id,
                                                 Profile.display_name == args.profile))
        if profile is None:
            profile = Profile(owner_user_id=user.id, display_name=args.profile)
            s.add(profile)
            s.flush()
            s.add(Consent(user_id=user.id, profile_id=profile.id, purpose=ConsentPurpose.PROCESSING,
                          policy_version="dev"))
            s.flush()
        try:
            report = ingest_report(s, default_storage(), profile_id=profile.id, uploaded_by=user.id, data=data)
        except IngestError as exc:
            print(exc, file=sys.stderr)
            return 1
        print(f"queued report {report.id} for profile '{profile.display_name}'")
    return 0


def cmd_show_report(args: argparse.Namespace) -> int:
    with SessionLocal() as s:
        report = s.get(Report, uuid.UUID(args.report_id))
        if report is None:
            print("no such report", file=sys.stderr)
            return 1
        rows = s.scalars(select(Observation).where(Observation.report_id == report.id)
                         .order_by(Observation.bbox["page"].as_integer(), Observation.bbox["top"].as_float())).all()
        print(f"report {report.id}  status={report.status.value}  lab={report.lab_name!r}  rows={len(rows)}")
        for o in rows:
            print(f"  {o.section or '-':<12} {o.raw_name:<42} {o.raw_value:>9} {o.raw_flag or '':<2} "
                  f"{o.raw_unit or '':<12} {o.raw_range or '':<18} conf={o.confidence:.2f}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("seed-catalogue", help="load data/catalogue/*.csv into the database")
    p.add_argument("--dir", help="catalogue directory (default: $DATA_DIR/catalogue)")
    p.set_defaults(func=cmd_seed_catalogue)
    p = sub.add_parser("load-knowledge", help="embed data/knowledge/chunks.jsonl into the knowledge base")
    p.add_argument("--file")
    p.set_defaults(func=cmd_load_knowledge)
    p = sub.add_parser("create-user", help="create a verified account (staff, seeded clinicians)")
    p.add_argument("--email", required=True)
    p.add_argument("--password", required=True)
    p.add_argument("--role", default="user", choices=["user", "clinician", "reviewer", "admin"])
    p.set_defaults(func=cmd_create_user)
    p = sub.add_parser("set-password", help="set the password of an existing account and confirm its email")
    p.add_argument("--email", required=True)
    p.add_argument("--password", required=True)
    p.set_defaults(func=cmd_set_password)
    p = sub.add_parser("extract-imaging", help="take study images and report text out of older imaging records")
    p.set_defaults(func=cmd_extract_imaging)
    p = sub.add_parser("ingest", help="queue a report file for a local development profile")
    p.add_argument("file")
    p.add_argument("--email", default="dev@nabz.local")
    p.add_argument("--profile", default="Dev profile")
    p.set_defaults(func=cmd_ingest)
    p = sub.add_parser("show-report", help="print a report's status and extracted rows")
    p.add_argument("report_id")
    p.set_defaults(func=cmd_show_report)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

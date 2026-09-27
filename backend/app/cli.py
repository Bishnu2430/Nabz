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
          f"{result.ranges} reference ranges, {result.limits} critical limits")
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

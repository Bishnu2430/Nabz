"""Management commands.

    python -m app.cli seed-catalogue [--dir PATH]
"""

import argparse
import sys
from pathlib import Path

from app.catalogue import CatalogueError, read_catalogue
from app.catalogue.seed import seed_catalogue
from app.core.config import settings
from app.db import SessionLocal


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("seed-catalogue", help="load data/catalogue/*.csv into the database")
    p.add_argument("--dir", help="catalogue directory (default: $DATA_DIR/catalogue)")
    p.set_defaults(func=cmd_seed_catalogue)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

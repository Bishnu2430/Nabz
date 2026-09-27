import argparse
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import URL, Engine, create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.catalogue import CatalogueData, read_catalogue
from app.catalogue.seed import seed_catalogue
from app.core.config import settings

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def catalogue_dir() -> Path:
    return Path(settings.data_dir) / "catalogue"


@pytest.fixture(scope="session")
def catalogue(catalogue_dir: Path) -> CatalogueData:
    return read_catalogue(catalogue_dir)


def alembic_config(url: URL) -> Config:
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    cfg.cmd_opts = argparse.Namespace(x=[f"url={url.render_as_string(hide_password=False)}"])
    return cfg


@pytest.fixture(scope="session")
def pg_admin() -> Iterator[Engine]:
    base = create_engine(settings.database_url).url
    admin = create_engine(base.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        admin.connect().close()
    except OperationalError:
        pytest.skip("PostgreSQL is not reachable (set DATABASE_URL)")
    yield admin
    admin.dispose()


def create_test_database(admin: Engine) -> URL:
    name = f"nabz_test_{uuid.uuid4().hex[:8]}"
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    return admin.url.set(database=name)


def drop_test_database(admin: Engine, url: URL) -> None:
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE "{url.database}" WITH (FORCE)'))


@pytest.fixture(scope="session")
def migrated_engine(pg_admin: Engine, catalogue: CatalogueData) -> Iterator[Engine]:
    """A migrated database with the catalogue seeded, shared by the tests that need one."""
    url = create_test_database(pg_admin)
    command.upgrade(alembic_config(url), "head")
    engine = create_engine(url)
    with Session(engine) as s, s.begin():
        seed_catalogue(s, catalogue)
    yield engine
    engine.dispose()
    drop_test_database(pg_admin, url)


@pytest.fixture
def sessions(migrated_engine: Engine) -> Iterator[sessionmaker[Session]]:
    """Session factory; user data is wiped after each test (the catalogue stays)."""
    yield sessionmaker(bind=migrated_engine, expire_on_commit=False)
    with migrated_engine.begin() as conn:
        conn.execute(text("TRUNCATE app_user, processing_job, audit_log RESTART IDENTITY CASCADE"))

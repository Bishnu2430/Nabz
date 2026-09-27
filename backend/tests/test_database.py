"""Migrations and catalogue seeding against a real, throwaway PostgreSQL database."""

from collections.abc import Iterator

import pytest
from alembic import command
from sqlalchemy import URL, Engine, create_engine, func, inspect, select, text
from sqlalchemy.orm import Session

from app.catalogue import CatalogueData
from app.catalogue.seed import seed_catalogue
from app.models import Base, CriticalLimit, LabTest, OrganSystem, UnitConversion
from tests.conftest import alembic_config, create_test_database, drop_test_database

pytestmark = pytest.mark.db


@pytest.fixture(scope="module")
def db_url(pg_admin: Engine) -> Iterator[URL]:
    url = create_test_database(pg_admin)
    yield url
    drop_test_database(pg_admin, url)


def test_migrations_create_every_model_table(db_url: URL) -> None:
    command.upgrade(alembic_config(db_url), "head")
    tables = set(inspect(create_engine(db_url)).get_table_names())
    assert set(Base.metadata.tables) <= tables


def test_seed_is_idempotent(db_url: URL, catalogue: CatalogueData) -> None:
    engine = create_engine(db_url)
    for _ in range(2):
        with Session(engine) as s, s.begin():
            seed_catalogue(s, catalogue)
    with Session(engine) as s:
        assert s.scalar(select(func.count()).select_from(OrganSystem)) == len(catalogue.organs)
        assert s.scalar(select(func.count()).select_from(LabTest)) == len(catalogue.tests)
        assert s.scalar(select(func.count()).select_from(UnitConversion)) == len(catalogue.conversions)
        assert s.scalar(select(func.count()).select_from(CriticalLimit)) == len(catalogue.limits)
        hba1c = s.scalars(select(LabTest).where(LabTest.code == "hba1c")).one()
        assert hba1c.loinc_code == "4548-4" and "Glycated Haemoglobin" in hba1c.aliases


def test_downgrade_removes_everything(db_url: URL) -> None:
    cfg = alembic_config(db_url)
    command.downgrade(cfg, "base")
    engine = create_engine(db_url)
    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
    with engine.connect() as conn:
        types = conn.execute(text("SELECT count(*) FROM pg_type WHERE typname = 'report_status'")).scalar()
    assert types == 0
    command.upgrade(cfg, "head")

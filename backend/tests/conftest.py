from pathlib import Path

import pytest

from app.catalogue import CatalogueData, read_catalogue
from app.core.config import settings


@pytest.fixture(scope="session")
def catalogue_dir() -> Path:
    return Path(settings.data_dir) / "catalogue"


@pytest.fixture(scope="session")
def catalogue(catalogue_dir: Path) -> CatalogueData:
    return read_catalogue(catalogue_dir)

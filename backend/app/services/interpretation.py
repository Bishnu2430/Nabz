"""Shared helpers for turning raw observations into interpreted ones (worker and API)."""

from __future__ import annotations

import threading
from datetime import date
from functools import lru_cache
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalogue import read_catalogue
from app.catalogue.convert import UnitConverter
from app.catalogue.data import CatalogueData
from app.catalogue.db import catalogue_from_db, revision
from app.catalogue.matcher import CatalogueMatcher
from app.core.config import settings
from app.extraction.interpret import ConfidenceModel, Interpreted, Interpreter, RawRow
from app.models import LabTest, Observation, Profile

MODEL_PATH = "models/confidence-v1.json"


def build_interpreter(catalogue: CatalogueData, model: ConfidenceModel | None = None) -> Interpreter:
    converter = UnitConverter(catalogue)
    return Interpreter(catalogue, CatalogueMatcher(catalogue, converter), converter,
                       model or ConfidenceModel.load(Path(settings.data_dir) / MODEL_PATH))


@lru_cache(maxsize=1)
def default_interpreter() -> Interpreter:
    """The interpreter for the catalogue as shipped in data/catalogue; `current_interpreter` is the one in use."""
    return build_interpreter(read_catalogue(Path(settings.data_dir) / "catalogue"))


@lru_cache(maxsize=1)
def _confidence_model() -> ConfidenceModel:
    return ConfidenceModel.load(Path(settings.data_dir) / MODEL_PATH)


class LiveCatalogue:
    """The catalogue as administrators have left it (FR-35), and an interpreter built from it. Each use costs one
    small query for the revision number; the copy is rebuilt only when an edit has raised it."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._built: tuple[int, CatalogueData, Interpreter] | None = None

    def get(self, session: Session) -> tuple[CatalogueData, Interpreter]:
        rev = revision(session)
        built = self._built
        if built is None or built[0] != rev:
            with self._lock:
                if self._built is None or self._built[0] != rev:
                    data = catalogue_from_db(session)
                    if data is None:  # not seeded: the shipped catalogue
                        data = read_catalogue(Path(settings.data_dir) / "catalogue")
                    self._built = (rev, data, build_interpreter(data, _confidence_model()))
                built = self._built
        return built[1], built[2]


live_catalogue = LiveCatalogue()


def current_interpreter(session: Session) -> Interpreter:
    return live_catalogue.get(session)[1]


def age_on(profile: Profile, when: date | None) -> int | None:
    if profile.date_of_birth is None:
        return None
    on = when or date.today()
    dob = profile.date_of_birth
    return on.year - dob.year - ((on.month, on.day) < (dob.month, dob.day))


def lab_test_ids(session: Session) -> dict[str, int]:
    return {code: id_ for code, id_ in session.execute(select(LabTest.code, LabTest.id))}


def raw_row_of(obs: Observation, source: str) -> RawRow:
    """Rebuild the interpreter input from a stored row; `source` is 'manual' after a user edit."""
    conf = 1.0 if source == "manual" or obs.ocr_confidence is None else float(obs.ocr_confidence)
    return RawRow(obs.raw_name or "", obs.raw_value or "", obs.raw_unit, obs.raw_range, obs.raw_flag, obs.section,
                  conf, source)


def apply(obs: Observation, it: Interpreted, ids: dict[str, int]) -> None:
    """Copy an interpretation onto an observation row."""
    obs.test_id = ids.get(it.test_code) if it.test_code else None
    obs.value_num = it.value_num
    obs.unit = it.unit
    obs.ref_low, obs.ref_high = it.ref_low, it.ref_high
    obs.ref_source = it.ref_source
    obs.confidence = it.confidence
    obs.match_score = round(it.match.score, 4)
    obs.match_method = it.match.method
    obs.match_candidates = [[c, round(s, 4)] for c, s in it.match.candidates] or None

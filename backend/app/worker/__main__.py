"""Run the pipeline worker:  python -m app.worker"""

import logging
import signal
import threading
from pathlib import Path

from app.catalogue import read_catalogue
from app.core.config import settings
from app.db import SessionLocal
from app.storage import default_storage
from app.worker.runner import Worker
from app.worker.stages import AnalysisStage, ExtractionStage


def main() -> None:
    logging.basicConfig(level=settings.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    catalogue = read_catalogue(Path(settings.data_dir) / "catalogue")
    worker = Worker(SessionLocal, [ExtractionStage(default_storage(), catalogue), AnalysisStage()])
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    worker.run_forever(stop)


if __name__ == "__main__":
    main()

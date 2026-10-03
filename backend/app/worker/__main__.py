"""Run the pipeline worker:  python -m app.worker"""

import logging
import signal
import threading

from app.core.config import settings
from app.db import SessionLocal
from app.explain.llm import GroqProvider
from app.knowledge.embed import default_embedder
from app.storage import default_storage
from app.worker.runner import Worker
from app.worker.stages import AnalysisStage, ExplanationStage, ExtractionStage


def main() -> None:
    logging.basicConfig(level=settings.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    # Without a key or the embedding model, explanations use the template built from computed values.
    provider = GroqProvider(settings.groq_api_key, settings.llm_model) if settings.groq_api_key else None
    stages = [ExtractionStage(default_storage()), AnalysisStage(),
              ExplanationStage(provider, default_embedder())]
    worker = Worker(SessionLocal, stages)
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    worker.run_forever(stop)


if __name__ == "__main__":
    main()

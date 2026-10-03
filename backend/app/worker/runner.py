"""The worker loop: claim a job, run its stage handler, record the outcome."""

from __future__ import annotations

import logging
import socket
import threading
import time
import uuid

from sqlalchemy.orm import Session, sessionmaker

from app.models import Report
from app.models.enums import JobStage, ReportStatus
from app.services import reminders
from app.worker import queue
from app.worker.stages import StageHandler

log = logging.getLogger("nabz.worker")

RUNNING_STATUS = {JobStage.EXTRACT: ReportStatus.PROCESSING, JobStage.ANALYSE: ReportStatus.ANALYSING,
                  JobStage.EXPLAIN: ReportStatus.EXPLAINING}
RETRY_STATUS = {JobStage.EXTRACT: ReportStatus.QUEUED, JobStage.ANALYSE: ReportStatus.VERIFIED,
                JobStage.EXPLAIN: ReportStatus.ANALYSING}


class Worker:
    def __init__(self, sessions: sessionmaker[Session], handlers: list[StageHandler], poll_interval: float = 1.0,
                 worker_id: str | None = None):
        self.sessions = sessions
        self.handlers = {h.stage: h for h in handlers}
        self.poll_interval = poll_interval
        self.worker_id = worker_id or f"{socket.gethostname()}-{uuid.uuid4().hex[:6]}"

    def run_once(self) -> bool:
        """Process at most one job. Returns True if a job was claimed."""
        with self.sessions.begin() as s:
            job = queue.claim(s, self.worker_id, list(self.handlers))
            if job is None:
                return False
            if (status := RUNNING_STATUS.get(job.stage)) and (report := s.get(Report, job.report_id)):
                report.status = status
        started = time.perf_counter()
        try:
            handler = self.handlers[job.stage]
            with self.sessions.begin() as s:
                handler.handle(job, s)
                queue.complete(s, job.id)
            log.info("job %s %s report=%s done in %.1fs", job.id, job.stage.value, job.report_id,
                     time.perf_counter() - started)
        except Exception as exc:  # noqa: BLE001 - every failure is recorded on the job
            error = f"{type(exc).__name__}: {exc}"
            with self.sessions.begin() as s:
                retry = queue.fail(s, job.id, error)
                if report := s.get(Report, job.report_id):
                    report.status = RETRY_STATUS.get(job.stage, report.status) if retry else ReportStatus.FAILED
            log.warning("job %s %s attempt %s failed (%s): %s", job.id, job.stage.value, job.attempts,
                        "will retry" if retry else "giving up", error)
        return True

    def run_forever(self, stop: threading.Event) -> None:
        log.info("worker %s started (stages: %s)", self.worker_id, ", ".join(s.value for s in self.handlers))
        last_recovery = 0.0
        while not stop.is_set():
            if time.monotonic() - last_recovery > 60:
                with self.sessions.begin() as s:
                    if n := queue.recover_stale(s):
                        log.warning("requeued %d stale job(s)", n)
                with self.sessions.begin() as s:  # once a minute is often enough for reminders with a date
                    if n := reminders.send_due(s):
                        log.info("sent %d reminder email(s)", n)
                last_recovery = time.monotonic()
            if not self.run_once():
                stop.wait(self.poll_interval)
        log.info("worker %s stopped", self.worker_id)

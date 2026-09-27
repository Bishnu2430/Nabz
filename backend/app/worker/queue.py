"""Durable job queue on PostgreSQL (ADR-0002).

Jobs are claimed with `FOR UPDATE SKIP LOCKED`, so any number of workers can
poll the same table without double-processing. Enqueueing happens in the same
transaction as the report change that caused it, so jobs are never lost.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import ProcessingJob
from app.models.enums import JobStage

MAX_ATTEMPTS = 3
BACKOFF_BASE = timedelta(seconds=10)
STALE_AFTER = timedelta(minutes=10)


@dataclass(frozen=True)
class Job:
    id: int
    report_id: uuid.UUID
    stage: JobStage
    attempts: int


def enqueue(session: Session, report_id: uuid.UUID, stage: JobStage, delay: timedelta = timedelta(0)) -> None:
    job = ProcessingJob(report_id=report_id, stage=stage)
    session.add(job)
    session.flush()
    if delay:
        session.execute(text("UPDATE processing_job SET run_after = now() + :d WHERE id = :id"),
                        {"d": delay, "id": job.id})
    session.execute(text("SELECT pg_notify('nabz_jobs', :stage)"), {"stage": stage.value})


_CLAIM = text("""
    UPDATE processing_job
       SET status = 'running', locked_at = now(), locked_by = :worker, attempts = attempts + 1
     WHERE id = (SELECT id FROM processing_job
                  WHERE status = 'queued' AND run_after <= now()
                  ORDER BY id
                  FOR UPDATE SKIP LOCKED
                  LIMIT 1)
 RETURNING id, report_id, stage, attempts
""")


def claim(session: Session, worker_id: str) -> Job | None:
    row = session.execute(_CLAIM, {"worker": worker_id}).first()
    return Job(row.id, row.report_id, JobStage(row.stage), row.attempts) if row else None


def complete(session: Session, job_id: int) -> None:
    session.execute(text("UPDATE processing_job SET status = 'succeeded', finished_at = now(), error = NULL "
                         "WHERE id = :id"), {"id": job_id})


def fail(session: Session, job_id: int, error: str) -> bool:
    """Record a failure. Returns True if the job will be retried, False if it is now permanently failed."""
    row = session.execute(text("""
        UPDATE processing_job
           SET status = CASE WHEN attempts < :max THEN 'queued' ELSE 'failed' END::job_status,
               run_after = now() + (:base * power(2, attempts - 1)),
               finished_at = CASE WHEN attempts < :max THEN NULL ELSE now() END,
               locked_at = NULL, locked_by = NULL, error = :error
         WHERE id = :id
     RETURNING status
    """), {"id": job_id, "max": MAX_ATTEMPTS, "base": BACKOFF_BASE, "error": error[:500]}).first()
    return row is not None and row.status == "queued"


def recover_stale(session: Session, older_than: timedelta = STALE_AFTER) -> int:
    """Requeue jobs whose worker died mid-way (locked longer than `older_than`)."""
    result = session.execute(text("""
        UPDATE processing_job SET status = 'queued', locked_at = NULL, locked_by = NULL
         WHERE status = 'running' AND locked_at < now() - :age
    """), {"age": older_than})
    return result.rowcount or 0

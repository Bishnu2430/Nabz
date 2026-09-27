from datetime import timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker

from app.models import ProcessingJob, Report
from app.models.enums import JobStage, JobStatus
from app.worker import queue
from tests.factories import make_profile

pytestmark = pytest.mark.db


def _reports(sessions: sessionmaker[Session], n: int) -> list:
    with sessions.begin() as s:
        profile = make_profile(s)
        reports = [Report(profile_id=profile.id, uploaded_by=profile.owner_user_id, source_sha256=f"h{i}")
                   for i in range(n)]
        s.add_all(reports)
        s.flush()
        for r in reports:
            queue.enqueue(s, r.id, JobStage.EXTRACT)
        return [r.id for r in reports]


def test_claim_complete(sessions: sessionmaker[Session]) -> None:
    (report_id,) = _reports(sessions, 1)
    with sessions.begin() as s:
        job = queue.claim(s, "w1")
        assert job is not None and job.report_id == report_id and job.attempts == 1
    with sessions.begin() as s:
        assert queue.claim(s, "w1") is None  # nothing else is ready
        queue.complete(s, job.id)
    with sessions() as s:
        row = s.get(ProcessingJob, job.id)
        assert row.status == JobStatus.SUCCEEDED and row.finished_at is not None


def test_two_workers_never_get_the_same_job(sessions: sessionmaker[Session]) -> None:
    ids = _reports(sessions, 2)
    s1, s2 = sessions(), sessions()
    try:
        s1.begin()
        s2.begin()
        j1 = queue.claim(s1, "w1")  # row stays locked until s1 commits
        j2 = queue.claim(s2, "w2")  # SKIP LOCKED moves on to the next job instead of waiting
        assert j1 is not None and j2 is not None
        assert {j1.report_id, j2.report_id} == set(ids)
        assert queue.claim(s2, "w2") is None
    finally:
        s1.rollback()
        s2.rollback()
        s1.close()
        s2.close()


def test_failures_back_off_then_give_up(sessions: sessionmaker[Session]) -> None:
    _reports(sessions, 1)
    for attempt in range(1, queue.MAX_ATTEMPTS + 1):
        with sessions.begin() as s:
            s.execute(text("UPDATE processing_job SET run_after = now()"))  # skip the back-off wait
            job = queue.claim(s, "w1")
            assert job is not None and job.attempts == attempt
            retry = queue.fail(s, job.id, "RuntimeError: boom")
        assert retry is (attempt < queue.MAX_ATTEMPTS)
        if retry:
            with sessions.begin() as s:
                assert queue.claim(s, "w1") is None  # back-off: not ready yet
    with sessions() as s:
        row = s.scalars(select(ProcessingJob)).one()
        assert row.status == JobStatus.FAILED and row.error == "RuntimeError: boom"


def test_stale_jobs_are_recovered(sessions: sessionmaker[Session]) -> None:
    _reports(sessions, 1)
    with sessions.begin() as s:
        job = queue.claim(s, "dead-worker")
        s.execute(text("UPDATE processing_job SET locked_at = now() - interval '1 hour'"))
    with sessions.begin() as s:
        assert queue.recover_stale(s, timedelta(minutes=10)) == 1
    with sessions.begin() as s:
        again = queue.claim(s, "w2")
        assert again is not None and again.id == job.id

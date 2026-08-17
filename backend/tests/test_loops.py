"""
Tests for loops — the saved-campaign feature.

The behaviours that matter: a loop is due only when its cadence has elapsed,
a posting is announced as new exactly once, and jobs below the loop's
threshold are not recorded at all.
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.models.loop import JobLoop, LoopMatch
from app.models.user import Resume
from app.schemas.job import NormalizedJob
from app.services import loop_service
from app.services.loop_service import is_due, run_loop

# asyncio_mode=auto in pytest.ini handles the async tests; the due-logic tests
# below are deliberately synchronous.


def _loop(**overrides) -> JobLoop:
    base = dict(
        user_id="user-123",
        name="DevOps roles",
        keywords=["DevOps Engineer"],
        location=None,
        remote_only=True,
        cadence_hours=24,
        min_score=50,
        active=True,
    )
    base.update(overrides)
    return JobLoop(**base)


def _normalized(source_job_id: str, title: str, skills: list[str], company: str = "Acme") -> NormalizedJob:
    return NormalizedJob(
        source="remotive",
        source_job_id=source_job_id,
        title=title,
        company=company,
        location="Worldwide",
        remote=True,
        description=" ".join(skills),
        skills=skills,
        job_url="https://example.com",
        apply_url="https://example.com",
    )


# --------------------------------------------------------------- due logic

def test_never_run_loop_is_due():
    assert is_due(_loop(last_run_at=None)) is True


def test_recently_run_loop_is_not_due():
    loop = _loop(last_run_at=datetime.utcnow() - timedelta(hours=2), cadence_hours=24)
    assert is_due(loop) is False


def test_loop_past_its_cadence_is_due():
    loop = _loop(last_run_at=datetime.utcnow() - timedelta(hours=25), cadence_hours=24)
    assert is_due(loop) is True


def test_inactive_loop_is_never_due():
    assert is_due(_loop(active=False, last_run_at=None)) is False


# ------------------------------------------------------------------- runs

@pytest.fixture
def fake_sources(monkeypatch):
    """Replace the upstream fetch so tests never touch the network."""
    queue: list[list[NormalizedJob]] = []

    async def fake_fetch(queries, locations, remote, page=1, **kwargs):
        return queue.pop(0) if queue else []

    monkeypatch.setattr(loop_service.source_manager, "fetch_for_queries", fake_fetch)
    return queue


async def _seed(db, skills=("Docker", "Kubernetes", "Terraform", "AWS", "Python")):
    db.add(Resume(
        user_id="user-123",
        file_name="resume.pdf",
        raw_text="DevOps engineer with cloud automation experience.",
        extracted_skills=list(skills),
        summary="DevOps engineer.",
        experience_years=5,
    ))
    loop = _loop()
    db.add(loop)
    await db.commit()
    await db.refresh(loop)
    return loop


async def test_run_records_matching_jobs(session_factory, fake_sources):
    async with session_factory() as db:
        loop = await _seed(db)
        fake_sources.append([
            _normalized("1", "DevOps Engineer", ["Docker", "Kubernetes", "AWS"]),
        ])

        result = await run_loop(db, loop)

        assert result.status == "ok"
        assert result.new_matches == 1
        assert await db.scalar(select(func.count()).select_from(LoopMatch)) == 1


async def test_same_job_is_not_announced_twice(session_factory, fake_sources):
    """Two runs, same posting — it must count as new only the first time."""
    async with session_factory() as db:
        loop = await _seed(db)
        job = _normalized("1", "DevOps Engineer", ["Docker", "Kubernetes", "AWS"])

        fake_sources.append([job])
        first = await run_loop(db, loop)

        fake_sources.append([job])
        second = await run_loop(db, loop)

        assert first.new_matches == 1
        assert second.new_matches == 0
        assert await db.scalar(select(func.count()).select_from(LoopMatch)) == 1


async def test_jobs_below_threshold_are_not_recorded(session_factory, fake_sources):
    async with session_factory() as db:
        loop = await _seed(db)
        fake_sources.append([
            _normalized("2", "Pastry Chef", ["Baking", "Cake Decorating"], company="Bakery"),
        ])

        result = await run_loop(db, loop)

        assert result.new_matches == 0
        assert result.below_threshold == 1
        assert await db.scalar(select(func.count()).select_from(LoopMatch)) == 0


async def test_run_without_a_resume_is_skipped_not_faked(session_factory, fake_sources):
    """No resume means nothing to score against — say so, do not invent scores."""
    async with session_factory() as db:
        loop = _loop()
        db.add(loop)
        await db.commit()
        await db.refresh(loop)

        result = await run_loop(db, loop)

        assert result.status == "skipped"
        assert result.error and "resume" in result.error.lower()
        assert loop.last_run_status == "skipped"


async def test_failure_is_recorded_on_the_loop(session_factory, monkeypatch):
    async def exploding_fetch(queries, locations, remote, page=1, **kwargs):
        raise RuntimeError("upstream is down")

    monkeypatch.setattr(loop_service.source_manager, "fetch_for_queries", exploding_fetch)

    async with session_factory() as db:
        loop = await _seed(db)

        result = await run_loop(db, loop)

        assert result.status == "error"
        assert "upstream is down" in (result.error or "")
        assert loop.last_run_status == "error"


async def test_run_updates_last_run_timestamp(session_factory, fake_sources):
    async with session_factory() as db:
        loop = await _seed(db)
        assert loop.last_run_at is None

        fake_sources.append([])
        await run_loop(db, loop)

        assert loop.last_run_at is not None
        assert is_due(loop) is False

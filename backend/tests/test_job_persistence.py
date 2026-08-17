"""
Persistence regression tests.

Root cause of the constant-42 score: save_normalized_jobs() built the Job row
but never touched nj.skills, so `job_skills` stayed empty forever and every
match request went out with no skills to match against.
"""

import pytest
from sqlalchemy import func, select

from app.models.job import Job, JobSourceRecord, Skill
from app.schemas.job import NormalizedJob
from app.services.job_service import save_normalized_jobs

pytestmark = pytest.mark.asyncio


def _job(**overrides) -> NormalizedJob:
    base = dict(
        source="remotive",
        source_job_id="1",
        title="DevOps Engineer",
        company="Acme Corp",
        location="Worldwide",
        remote=True,
        employment_type="full_time",
        description="We use Docker, Kubernetes and Terraform on AWS.",
        posted_at=None,
        job_url="https://example.com/1",
        apply_url="https://example.com/1",
        skills=["Docker", "Kubernetes"],
    )
    base.update(overrides)
    return NormalizedJob(**base)


async def test_skills_are_persisted(session_factory):
    """The bug: this table was always empty."""
    saved = await save_normalized_jobs([_job()])

    assert len(saved) == 1
    assert {s.name for s in saved[0].skills} >= {"Docker", "Kubernetes"}

    async with session_factory() as db:
        count = await db.scalar(select(func.count()).select_from(Skill))
        assert count > 0, "skills table is empty — the original bug"


async def test_skills_are_mined_from_description_when_source_sends_none(session_factory):
    """Adzuna sends no tags; the description must still yield real skills."""
    saved = await save_normalized_jobs([
        _job(
            source="adzuna",
            source_job_id="a1",
            skills=[],
            description="Seeking an engineer with strong Python, PostgreSQL and Kafka experience.",
        )
    ])

    names = {s.name for s in saved[0].skills}
    assert {"Python", "PostgreSQL", "Kafka"} <= names


async def test_shared_skill_is_reused_not_duplicated(session_factory):
    """`skills.name` is unique — two jobs with Docker must share one row."""
    await save_normalized_jobs([
        _job(source_job_id="1", company="Acme Corp"),
        _job(source_job_id="2", company="Globex", title="Platform Engineer"),
    ])

    async with session_factory() as db:
        docker_rows = await db.scalar(
            select(func.count()).select_from(Skill).where(Skill.name == "Docker")
        )
        assert docker_rows == 1


async def test_same_source_job_is_not_duplicated(session_factory):
    await save_normalized_jobs([_job()])
    await save_normalized_jobs([_job()])

    async with session_factory() as db:
        assert await db.scalar(select(func.count()).select_from(Job)) == 1


async def test_same_posting_from_two_sources_collapses_to_one_job(session_factory):
    """Cross-source dedup: one canonical job, two source records."""
    await save_normalized_jobs([
        _job(source="remotive", source_job_id="r1", title="Senior DevOps Engineer"),
        _job(source="adzuna", source_job_id="a1", title="DevOps Engineer (Remote)",
             company="Acme Corp Inc.", salary_min=100000, salary_max=150000, currency="USD"),
    ])

    async with session_factory() as db:
        assert await db.scalar(select(func.count()).select_from(Job)) == 1
        assert await db.scalar(select(func.count()).select_from(JobSourceRecord)) == 2

        job = (await db.execute(select(Job))).scalars().first()
        # The second source contributed salary the first one lacked.
        assert job.salary_min == 100000


async def test_genuinely_different_jobs_are_kept_apart(session_factory):
    """A false merge hides a real job, so dedup must stay conservative."""
    await save_normalized_jobs([
        _job(source_job_id="1", company="Acme Corp", title="DevOps Engineer"),
        _job(source_job_id="2", company="Globex", title="DevOps Engineer"),
        _job(source_job_id="3", company="Acme Corp", title="Data Scientist"),
    ])

    async with session_factory() as db:
        assert await db.scalar(select(func.count()).select_from(Job)) == 3


async def test_one_bad_job_does_not_discard_the_batch(session_factory, monkeypatch):
    """
    A savepoint per job: one posting that blows up must not take its
    neighbours down with it, and must not force a commit per job either.
    """
    import app.services.job_service as job_service

    real_fingerprint = job_service.job_fingerprint

    def exploding_fingerprint(company, title, location, remote):
        if title == "Poison Pill":
            raise ValueError("simulated failure while processing this job")
        return real_fingerprint(company, title, location, remote)

    monkeypatch.setattr(job_service, "job_fingerprint", exploding_fingerprint)

    saved = await save_normalized_jobs([
        _job(source_job_id="ok1", company="Acme Corp"),
        _job(source_job_id="bad", title="Poison Pill"),
        _job(source_job_id="ok2", company="Globex", title="SRE"),
    ])

    assert len(saved) == 2
    async with session_factory() as db:
        assert await db.scalar(select(func.count()).select_from(Job)) == 2

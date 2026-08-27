from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import Dict, List
import logging

from app.models.job import Job, JobSourceRecord, Skill
from app.schemas.job import NormalizedJob
from app.core.database import AsyncSessionLocal
from app.services.job_identity import job_fingerprint
from app.services.skill_extractor import normalize_skills

logger = logging.getLogger("jobpulse.jobs")


async def _resolve_skills(db: AsyncSession, names: List[str], cache: Dict[str, Skill]) -> List[Skill]:
    """
    Get-or-create Skill rows for the given names.

    `skills.name` is unique, so the same skill seen on twenty jobs in one batch
    must resolve to one row. The cache keeps that to a single lookup per batch
    and also prevents adding two pending Skill objects with the same name
    inside one flush, which would raise a uniqueness error.
    """
    resolved: List[Skill] = []

    for name in names:
        key = name.lower()
        if key in cache:
            resolved.append(cache[key])
            continue

        stmt = select(Skill).where(Skill.name == name)
        existing = (await db.execute(stmt)).scalars().first()

        if existing is None:
            existing = Skill(name=name)
            db.add(existing)
            # Flush so the row exists before it is referenced by the
            # association table on the next job in this batch.
            await db.flush()

        cache[key] = existing
        resolved.append(existing)

    return resolved


async def _load_full(db: AsyncSession, job_id: str) -> Job | None:
    """
    Re-read a job with relations eagerly loaded.

    Required before the object crosses into Pydantic serialization: lazy loads
    on an async session raise MissingGreenlet outside the awaited context.
    """
    stmt = (
        select(Job)
        .options(selectinload(Job.source_records), selectinload(Job.skills))
        .where(Job.id == job_id)
    )
    return (await db.execute(stmt)).scalars().first()


async def save_normalized_jobs(jobs: List[NormalizedJob]) -> List[Job]:
    """
    Persist normalized jobs, deduplicating both within a source and across
    sources, and attach their skills.

    Manages its own session so it is safe to call from a background task.
    Returns deeply loaded ORM objects.
    """
    saved_ids: List[str] = []
    skill_cache: Dict[str, Skill] = {}

    async with AsyncSessionLocal() as db:
        for nj in jobs:
            try:
                # A savepoint per job: one malformed posting rolls back only
                # itself, instead of discarding the whole batch or forcing a
                # round-trip commit for every single job.
                async with db.begin_nested():
                    # 1. Exact match on this source's own id -> already stored.
                    stmt = select(JobSourceRecord).where(
                        JobSourceRecord.source == nj.source,
                        JobSourceRecord.source_job_id == nj.source_job_id,
                    )
                    existing_record = (await db.execute(stmt)).scalars().first()

                    if existing_record:
                        if existing_record.job_id not in saved_ids:
                            saved_ids.append(existing_record.job_id)
                        continue

                    skills = normalize_skills(nj.skills, nj.description, nj.title)
                    fingerprint = job_fingerprint(nj.company, nj.title, nj.location, nj.remote)

                    # 2. Same posting from a different board -> attach as an
                    #    extra source record on the canonical job.
                    canonical_stmt = (
                        select(Job)
                        .options(selectinload(Job.skills))
                        .where(Job.fingerprint == fingerprint)
                    )
                    canonical = (await db.execute(canonical_stmt)).scalars().first()

                    if canonical is None:
                        # Skills must be resolved and handed to the constructor.
                        # Appending to `canonical.skills` after the flush below
                        # would lazy-load the collection, which raises
                        # MissingGreenlet on an async session.
                        skill_objs = await _resolve_skills(db, skills, skill_cache)
                        canonical = Job(
                            skills=skill_objs,
                            fingerprint=fingerprint,
                            title=nj.title,
                            company=nj.company,
                            location=nj.location,
                            remote=nj.remote,
                            employment_type=nj.employment_type,
                            experience_min=nj.experience_min,
                            experience_max=nj.experience_max,
                            description=nj.description,
                            salary_min=nj.salary_min,
                            salary_max=nj.salary_max,
                            currency=nj.currency,
                            posted_at=nj.posted_at,
                        )
                        db.add(canonical)
                        await db.flush()  # assign canonical.id
                        merge_skills = False
                    else:
                        merge_skills = True
                        # A second source often carries data the first lacked
                        # (Adzuna has salary, Remotive does not). Fill gaps
                        # without overwriting what is already known.
                        if canonical.salary_min is None and nj.salary_min is not None:
                            canonical.salary_min = nj.salary_min
                            canonical.salary_max = nj.salary_max
                            canonical.currency = nj.currency
                        if canonical.posted_at is None and nj.posted_at is not None:
                            canonical.posted_at = nj.posted_at
                        if canonical.experience_min is None and nj.experience_min is not None:
                            canonical.experience_min = nj.experience_min
                            canonical.experience_max = nj.experience_max
                        if nj.description and len(nj.description) > len(canonical.description or ""):
                            canonical.description = nj.description

                    # 3. Skills — for an existing canonical job, union in
                    #    whatever this source contributed that is not already
                    #    attached. (New jobs got theirs at construction.)
                    #    `canonical.skills` is safe to read here because the
                    #    lookup above eager-loaded it.
                    if merge_skills:
                        already = {s.name.lower() for s in canonical.skills}
                        new_names = [s for s in skills if s.lower() not in already]
                        for skill in await _resolve_skills(db, new_names, skill_cache):
                            canonical.skills.append(skill)

                    db.add(
                        JobSourceRecord(
                            job_id=canonical.id,
                            source=nj.source,
                            source_job_id=nj.source_job_id,
                            job_url=nj.job_url,
                            apply_url=nj.apply_url,
                        )
                    )

                    if canonical.id not in saved_ids:
                        saved_ids.append(canonical.id)

            except Exception as exc:
                # begin_nested() already rolled this job's savepoint back.
                logger.warning("Skipped job %r from %s: %s", nj.title, nj.source, exc)

        try:
            await db.commit()
        except Exception as exc:
            await db.rollback()
            logger.error("Failed to commit job batch: %s", exc)
            return []

        # Re-read once, after commit, with relations loaded for serialization.
        return [job for job_id in saved_ids if (job := await _load_full(db, job_id)) is not None]

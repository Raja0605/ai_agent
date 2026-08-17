"""
Loop execution — running a saved search campaign and recording what is new.

One run is: fetch from every source for the loop's keywords, persist and
deduplicate the results, score each job against the loop's resume, and record
matches that clear the loop's threshold and have not been recorded before.

Scoring here is deterministic rather than model-backed. A run scores every job
it fetched, unattended, on a schedule — putting an LLM call in that path would
make a background loop cost real money per posting for a number whose job is
to rank a list. The full AI evaluation runs when a person opens a job.
"""

import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.job import Job
from app.models.loop import JobLoop, LoopMatch
from app.models.user import Resume
from app.schemas.ai import JobMatchRequest, ResumeProfile
from app.schemas.loop import LoopRunResult
from app.services.ai.heuristic import heuristic_match
from app.services.job_service import save_normalized_jobs
from app.services.sources.manager import SourceManager

logger = logging.getLogger("jobpulse.loops")

source_manager = SourceManager()


async def _resume_profile(db: AsyncSession, loop: JobLoop) -> Optional[ResumeProfile]:
    """
    Load the resume a loop scores against — the one it was pinned to, else the
    user's most recent. Without a resume there is nothing to score against, so
    the run is skipped rather than producing meaningless numbers.
    """
    stmt = select(Resume).where(Resume.user_id == loop.user_id)
    if loop.resume_id:
        stmt = stmt.where(Resume.id == loop.resume_id)
    stmt = stmt.order_by(Resume.created_at.desc()).limit(1)

    resume = (await db.execute(stmt)).scalars().first()
    if resume is None:
        return None

    return ResumeProfile(
        full_name="Candidate",
        target_role=loop.keywords[0] if loop.keywords else "Engineer",
        summary=resume.summary or "",
        skills=list(resume.extracted_skills or []),
        experience_years=resume.experience_years or 0,
        raw_text=resume.raw_text,
    )


async def run_loop(db: AsyncSession, loop: JobLoop) -> LoopRunResult:
    """Execute one loop and record its new matches. Never raises."""
    # Captured up front: after a rollback the instance is expired, and reading
    # any attribute off it would trigger a lazy refresh in the error handler.
    loop_id = loop.id

    try:
        profile = await _resume_profile(db, loop)
        if profile is None:
            loop.last_run_at = datetime.utcnow()
            loop.last_run_status = "skipped"
            loop.last_run_error = "No resume available to score against."
            await db.commit()
            return LoopRunResult(
                loop_id=loop.id,
                status="skipped",
                jobs_fetched=0,
                new_matches=0,
                below_threshold=0,
                error=loop.last_run_error,
            )

        normalized = await source_manager.fetch_for_queries(
            queries=list(loop.keywords or []),
            locations=[loop.location] if loop.location else [],
            remote=loop.remote_only,
            india_only=settings.INDIA_ONLY,
        )
        jobs = await save_normalized_jobs(normalized)

        # Jobs already recorded for this loop, so a posting is announced once.
        seen_stmt = select(LoopMatch.job_id).where(LoopMatch.loop_id == loop.id)
        already_matched = set((await db.execute(seen_stmt)).scalars().all())

        new_matches = 0
        below_threshold = 0

        for job in jobs:
            if job.id in already_matched:
                continue

            result = heuristic_match(
                JobMatchRequest(
                    job_id=job.id,
                    job_title=job.title,
                    job_description=job.description or "",
                    job_skills=[s.name for s in job.skills],
                    company=job.company,
                    resume=profile,
                )
            )

            if result.score < loop.min_score:
                below_threshold += 1
                continue

            db.add(
                LoopMatch(
                    loop_id=loop.id,
                    job_id=job.id,
                    score=result.score,
                    score_method=result.method,
                    matched_skills=result.matched_skills,
                    missing_skills=result.missing_skills,
                    seen=False,
                )
            )
            already_matched.add(job.id)
            new_matches += 1

        loop.last_run_at = datetime.utcnow()
        loop.last_run_status = "ok"
        loop.last_run_error = None
        await db.commit()

        logger.info(
            "Loop %r: fetched %d, %d new matches, %d below threshold.",
            loop.name, len(jobs), new_matches, below_threshold,
        )

        return LoopRunResult(
            loop_id=loop.id,
            status="ok",
            jobs_fetched=len(jobs),
            new_matches=new_matches,
            below_threshold=below_threshold,
        )

    except Exception as exc:
        await db.rollback()
        logger.exception("Loop %s failed.", loop_id)
        # Record the failure on the loop so it is visible in the UI rather
        # than only in the server log. Re-fetch first: the rollback above
        # expired the instance we were handed.
        try:
            fresh = await db.get(JobLoop, loop_id)
            if fresh is not None:
                fresh.last_run_at = datetime.utcnow()
                fresh.last_run_status = "error"
                fresh.last_run_error = str(exc)[:500]
                await db.commit()
        except Exception:
            await db.rollback()
            logger.exception("Could not record the failure on loop %s.", loop_id)

        return LoopRunResult(
            loop_id=loop_id,
            status="error",
            jobs_fetched=0,
            new_matches=0,
            below_threshold=0,
            error=str(exc)[:500],
        )


def is_due(loop: JobLoop, now: Optional[datetime] = None) -> bool:
    """A loop is due if it is active and its cadence has elapsed."""
    if not loop.active:
        return False
    if loop.last_run_at is None:
        return True
    now = now or datetime.utcnow()
    elapsed_hours = (now - loop.last_run_at).total_seconds() / 3600
    return elapsed_hours >= (loop.cadence_hours or 24)


async def due_loops(db: AsyncSession) -> List[JobLoop]:
    stmt = select(JobLoop).where(JobLoop.active.is_(True))
    loops = (await db.execute(stmt)).scalars().all()
    return [loop for loop in loops if is_due(loop)]


async def loop_counts(db: AsyncSession, loop_id: str) -> tuple[int, int]:
    """(total matches, unseen matches) for one loop."""
    total = await db.scalar(
        select(func.count()).select_from(LoopMatch).where(LoopMatch.loop_id == loop_id)
    )
    unseen = await db.scalar(
        select(func.count())
        .select_from(LoopMatch)
        .where(LoopMatch.loop_id == loop_id, LoopMatch.seen.is_(False))
    )
    return int(total or 0), int(unseen or 0)


async def load_matches(
    db: AsyncSession, loop_id: str, unseen_only: bool = False, limit: int = 100
) -> List[LoopMatch]:
    stmt = (
        select(LoopMatch)
        .options(
            selectinload(LoopMatch.job).selectinload(Job.skills),
            selectinload(LoopMatch.job).selectinload(Job.source_records),
        )
        .where(LoopMatch.loop_id == loop_id)
        .order_by(LoopMatch.score.desc(), LoopMatch.created_at.desc())
        .limit(limit)
    )
    if unseen_only:
        stmt = stmt.where(LoopMatch.seen.is_(False))
    return list((await db.execute(stmt)).scalars().all())

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.loop import JobLoop, LoopMatch
from app.schemas.loop import (
    LoopCreate,
    LoopMatchJob,
    LoopMatchResponse,
    LoopResponse,
    LoopRunResult,
    LoopUpdate,
)
from app.services.loop_service import load_matches, loop_counts, run_loop

router = APIRouter()


async def _to_response(db: AsyncSession, loop: JobLoop) -> LoopResponse:
    total, unseen = await loop_counts(db, loop.id)
    return LoopResponse(
        id=loop.id,
        name=loop.name,
        keywords=list(loop.keywords or []),
        location=loop.location,
        remote_only=loop.remote_only,
        resume_id=loop.resume_id,
        cadence_hours=loop.cadence_hours,
        min_score=loop.min_score,
        active=loop.active,
        last_run_at=loop.last_run_at,
        last_run_status=loop.last_run_status,
        last_run_error=loop.last_run_error,
        created_at=loop.created_at,
        total_matches=total,
        new_matches=unseen,
    )


async def _get_owned_loop(db: AsyncSession, loop_id: str, user_id: str) -> JobLoop:
    stmt = select(JobLoop).where(JobLoop.id == loop_id, JobLoop.user_id == user_id)
    loop = (await db.execute(stmt)).scalars().first()
    if loop is None:
        raise HTTPException(status_code=404, detail="Loop not found")
    return loop


@router.get("/", response_model=List[LoopResponse])
async def list_loops(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    stmt = select(JobLoop).where(JobLoop.user_id == current_user_id).order_by(JobLoop.created_at.desc())
    loops = (await db.execute(stmt)).scalars().all()
    return [await _to_response(db, loop) for loop in loops]


@router.post("/", response_model=LoopResponse, status_code=status.HTTP_201_CREATED)
async def create_loop(
    loop_in: LoopCreate,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    loop = JobLoop(user_id=current_user_id, **loop_in.model_dump())
    db.add(loop)
    await db.commit()
    await db.refresh(loop)
    return await _to_response(db, loop)


@router.patch("/{loop_id}", response_model=LoopResponse)
async def update_loop(
    loop_id: str,
    loop_update: LoopUpdate,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    loop = await _get_owned_loop(db, loop_id, current_user_id)
    for key, value in loop_update.model_dump(exclude_unset=True).items():
        setattr(loop, key, value)
    await db.commit()
    await db.refresh(loop)
    return await _to_response(db, loop)


@router.delete("/{loop_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_loop(
    loop_id: str,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    loop = await _get_owned_loop(db, loop_id, current_user_id)
    await db.delete(loop)
    await db.commit()


@router.post("/{loop_id}/run", response_model=LoopRunResult)
async def run_loop_now(
    loop_id: str,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    """
    Run a loop immediately, ignoring its cadence.

    Awaited rather than backgrounded: the user pressed a button and the result
    (how many new matches) is the point of pressing it.
    """
    loop = await _get_owned_loop(db, loop_id, current_user_id)
    return await run_loop(db, loop)


@router.get("/{loop_id}/matches", response_model=List[LoopMatchResponse])
async def get_loop_matches(
    loop_id: str,
    unseen_only: bool = Query(False, description="Only matches not yet reviewed"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    await _get_owned_loop(db, loop_id, current_user_id)
    matches = await load_matches(db, loop_id, unseen_only=unseen_only, limit=limit)

    responses: List[LoopMatchResponse] = []
    for match in matches:
        job = match.job
        if job is None:
            continue
        primary = job.source_records[0] if job.source_records else None
        responses.append(
            LoopMatchResponse(
                id=match.id,
                loop_id=match.loop_id,
                score=match.score,
                score_method=match.score_method or "heuristic",
                matched_skills=list(match.matched_skills or []),
                missing_skills=list(match.missing_skills or []),
                seen=match.seen,
                created_at=match.created_at,
                job=LoopMatchJob(
                    id=job.id,
                    title=job.title,
                    company=job.company,
                    location=job.location,
                    remote=job.remote,
                    employment_type=job.employment_type,
                    description=job.description or "",
                    salary_min=job.salary_min,
                    salary_max=job.salary_max,
                    currency=job.currency,
                    posted_at=job.posted_at,
                    skills=[s.name for s in job.skills],
                    sources=[r.source for r in job.source_records],
                    apply_url=(primary.apply_url or primary.job_url) if primary else None,
                ),
            )
        )
    return responses


@router.post("/{loop_id}/matches/seen", status_code=status.HTTP_204_NO_CONTENT)
async def mark_matches_seen(
    loop_id: str,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    """Clear the 'new' badge once the user has reviewed a loop's matches."""
    await _get_owned_loop(db, loop_id, current_user_id)
    stmt = select(LoopMatch).where(LoopMatch.loop_id == loop_id, LoopMatch.seen.is_(False))
    for match in (await db.execute(stmt)).scalars().all():
        match.seen = True
    await db.commit()

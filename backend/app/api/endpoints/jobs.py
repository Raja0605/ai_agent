from fastapi import APIRouter, Query, BackgroundTasks, Depends, HTTPException
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, desc
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.schemas.job import NormalizedJob, JobResponse
from app.models.job import Job, Skill
from app.services.sources.manager import SourceManager
from app.services.job_service import save_normalized_jobs
from app.services.job_filter import SearchCriteria
from app.services.locations import (
    is_indian_location,
    location_aliases,
    matches_location_query,
)
from app.services.role_matcher import matches_role
from app.core.database import get_db

router = APIRouter()
source_manager = SourceManager()

#: How many stored jobs to consider before filtering and paginating. Large
#: enough that paging through a normal result set is complete, small enough
#: that the table is never loaded wholesale.
CANDIDATE_POOL_SIZE = 500

@router.get("/", response_model=List[JobResponse])
async def get_jobs(
    keyword: Optional[str] = Query(None, description="Job title, skill or company"),
    location: Optional[str] = Query(None, description="Location"),
    remote: Optional[bool] = Query(None, description="Filter for remote jobs"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Fetch jobs from the local normalized database.
    """
    stmt = select(Job).options(selectinload(Job.source_records), selectinload(Job.skills)).order_by(desc(Job.created_at))

    if keyword:
        # A per-word OR, not a match on the whole phrase. Requiring the
        # literal string meant "data engineer" missed "Staff Data Privacy
        # Engineer" — the words are both there but not adjacent. This is
        # deliberately a wide net: it only has to be a superset of what the
        # role matcher accepts below, which is what does the real work.
        #
        # Skills are included because the box accepts "Kubernetes", which is
        # rarely in a title and almost always in the extracted skills.
        word_clauses = [
            clause
            for word in keyword.split()
            if word
            for clause in (
                Job.title.ilike(f"%{word}%"),
                Job.company.ilike(f"%{word}%"),
                Job.skills.any(Skill.name.ilike(f"%{word}%")),
            )
        ]
        if word_clauses:
            stmt = stmt.where(or_(*word_clauses))
    if location:
        # A plain LIKE on the query missed every alias: searching "Bangalore"
        # returned nothing for the rows stored as "Bengaluru, Karnataka".
        # Remote roles are included because they are reachable from any city.
        clauses = [Job.location.ilike(f"%{alias}%") for alias in location_aliases(location)]
        if clauses:
            stmt = stmt.where(or_(*clauses, Job.remote.is_(True)))
    if remote is not None:
        stmt = stmt.where(Job.remote == remote)

    # Read a bounded pool of the most recent candidates, apply the same role
    # rules the live search uses, then paginate the filtered result. SQL can
    # narrow by substring but cannot tell that "Data Analyst" is a different
    # job from "Data Engineer"; that judgement lives in one place.
    #
    # Paginating before filtering would be simpler and wrong — pages would
    # come back short and inconsistently sized. The pool is capped so a large
    # table cannot be dragged into memory; past that, older matches are not
    # reachable by paging, which is the accepted trade for a search that
    # returns honest pages.
    result = await db.execute(stmt.limit(CANDIDATE_POOL_SIZE))
    rows = result.scalars().all()

    if keyword:
        rows = [
            job for job in rows
            if matches_role(keyword, job.title, [s.name for s in job.skills], job.company)
        ]

    if location:
        # The SQL above widened the net to include remote roles, since a
        # remote job is reachable from any city. That let remote postings from
        # other countries through, so the alias-aware check has to run here
        # too — the LIKE clauses are a prefilter, not the decision.
        rows = [
            job for job in rows
            if matches_location_query(job.location, location, job.remote)
        ]

    if settings.INDIA_ONLY:
        rows = [job for job in rows if is_indian_location(job.location, job.remote)]

    return rows[(page - 1) * page_size : page * page_size]

@router.post("/sync")
async def sync_jobs(
    background_tasks: BackgroundTasks,
    keyword: str = Query(..., description="Job title or keywords"),
    location: Optional[str] = Query(None, description="Location to search in"),
    remote: bool = Query(False, description="Filter for remote jobs"),
    india_only: bool = Query(None, description="Restrict to jobs reachable from India"),
):
    """
    Trigger background aggregation from all sources.
    """
    scope = settings.INDIA_ONLY if india_only is None else india_only

    async def fetch_and_save():
        jobs = await source_manager.fetch_all(
            keyword=keyword, location=location, remote=remote, india_only=scope
        )
        await save_normalized_jobs(jobs)

    background_tasks.add_task(fetch_and_save)
    return {"message": "Job synchronization started in the background."}

from app.api.deps import get_current_user
from app.models.user import UserProfile

@router.get("/search", response_model=List[JobResponse])
async def search_jobs(
    keyword: Optional[str] = Query(None, description="Job title or keywords"),
    location: Optional[str] = Query(None, description="Location to search in"),
    remote: bool = Query(False, description="Filter for remote jobs"),
    use_resume: bool = Query(False, description="Use user resume to generate queries"),
    india_only: bool = Query(None, description="Restrict to jobs reachable from India"),
    page: int = Query(1, ge=1),
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user)
):
    """
    On-demand job aggregation search based on manual query or user resume profile.
    """
    queries = []
    locations = []

    # Extract search profile from resume if requested
    if use_resume:
        stmt = select(UserProfile).where(UserProfile.user_id == current_user_id)
        res = await db.execute(stmt)
        profile = res.scalars().first()

        if profile:
            if profile.target_roles:
                queries.extend(profile.target_roles)
            if profile.preferred_locations:
                locations.extend(profile.preferred_locations)

    # Always include manual entries as priority
    if keyword and keyword not in queries:
        queries.insert(0, keyword)
    if location and location not in locations:
        locations.insert(0, location)

    # Fallback default if absolutely nothing provided
    if not queries:
        queries = ["Software Engineer"]

    criteria = SearchCriteria.build(
        keywords=queries,
        locations=locations,
        remote=remote,
        india_only=settings.INDIA_ONLY if india_only is None else india_only,
    )

    # `fetch` returns only the postings that answer `criteria`, best match
    # first. Everything from here on is already filtered.
    jobs = await source_manager.fetch(criteria, page=page)

    # Explicitly await db save/commit BEFORE sending results to frontend.
    saved_jobs = await save_normalized_jobs(jobs)

    # The database can hold a job that an earlier, wider search stored, and
    # `save_normalized_jobs` merges by fingerprint — so re-check the result
    # rather than assume every saved row came from this search. Previously
    # this endpoint returned whatever got saved, which is why searches came
    # back carrying roles and cities nobody asked for.
    return [
        job for job in saved_jobs
        if not criteria.keywords
        or any(
            matches_role(k, job.title, [s.name for s in job.skills], job.company)
            for k in criteria.keywords
        )
    ]

@router.get("/{job_id}", response_model=JobResponse)
async def get_job_by_id(
    job_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific job by its ID.
    """
    stmt = select(Job).options(selectinload(Job.source_records), selectinload(Job.skills)).where(Job.id == job_id)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job

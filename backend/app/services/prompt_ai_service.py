"""Prompt AI orchestration: interpret, search existing sources, match, rank.

Does not replace /api/jobs/search, LinkedIn MCP, or JobSpy MCP. It calls them.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator, Callable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.mcp import MCPServer
from app.models.user import Resume
from app.schemas.ai import JobMatchRequest, ResumeProfile
from app.schemas.job import NormalizedJob
from app.schemas.jobspy import JobSpySearchRequest
from app.schemas.prompt_ai import (
    InterpretedPrompt,
    PromptAIJobResult,
    PromptAISearchResponse,
    SourceStatus,
)
from app.services.ai.heuristic import heuristic_match
from app.services.job_filter import SearchCriteria, apply
from app.services.job_service import save_normalized_jobs
from app.services.jobspy_mcp_client import JobSpyMCPError
from app.services.jobspy_service import JobSpyService
from app.services.locations import matches_location_query
from app.services.prompt_interpreter import interpret_prompt
from app.sources.manager import SourceManager
from mcp_agent.job_search import MCPJobSearch
from mcp_agent.models import MCPServerConfig

logger = logging.getLogger("jobpulse.prompt_ai")

ProgressFn = Callable[[str], None]


class PromptAIService:
    def __init__(
        self,
        source_manager: SourceManager | None = None,
        jobspy: JobSpyService | None = None,
    ):
        self.source_manager = source_manager or SourceManager()
        self.jobspy = jobspy or JobSpyService()

    async def search(
        self,
        prompt: str,
        resume: Resume,
        db: AsyncSession,
        on_progress: Optional[Callable[[str], Any]] = None,
    ) -> PromptAISearchResponse:
        progress: list[str] = []

        async def emit(message: str) -> None:
            progress.append(message)
            if on_progress:
                result = on_progress(message)
                if asyncio.iscoroutine(result):
                    await result

        await emit("Loading selected resume...")
        await emit("Understanding your job requirements...")
        interpreted = interpret_prompt(prompt)

        keywords = list(interpreted.keywords) or [prompt]
        location = interpreted.locations[0] if interpreted.locations else None
        filters = {
            "remote": interpreted.remote if interpreted.remote is not None else False,
            "experience_min": interpreted.experience_min,
            "experience_max": interpreted.experience_max,
            "salary_min": interpreted.salary_min,
            "posted_after": interpreted.posted_after,
            "india_only": settings.INDIA_ONLY if interpreted.country in (None, "india") else False,
            "limit": 25,
        }

        jobs: list[NormalizedJob] = []
        source_status: dict[str, SourceStatus] = {}
        search_tasks: list[tuple[str, Any]] = []

        if settings.REMOTIVE_ENABLED or settings.ADZUNA_ENABLED:
            labels = []
            if settings.REMOTIVE_ENABLED:
                labels.append("Remotive")
            if settings.ADZUNA_ENABLED:
                labels.append("Adzuna")
            for label in labels:
                await emit(f"Searching {label}...")
            search_tasks.append(("direct", self._search_direct(keywords, location, filters)))

        mcp_rows = (await db.execute(select(MCPServer).where(MCPServer.enabled.is_(True)))).scalars().all()
        for server in mcp_rows:
            await emit(f"Searching {server.name}...")
            search_tasks.append((f"mcp:{server.id}", self._search_mcp(server, keywords, location, interpreted, filters)))

        jobspy_sites: list[str] = []
        if settings.JOBSPY_ENABLED:
            try:
                info = await self.jobspy.discover()
                jobspy_sites = list(info.get("sites") or [])
            except Exception:
                jobspy_sites = []
                source_status["jobspy"] = SourceStatus(
                    status="failed", count=0, message="Job Spy temporarily unavailable."
                )
            if jobspy_sites:
                for site in jobspy_sites:
                    await emit(f"Searching {site.replace('_', ' ').title()}...")
                search_tasks.append(
                    ("jobspy", self._search_jobspy(keywords, location, interpreted, jobspy_sites))
                )

        gathered = await asyncio.gather(*(task for _, task in search_tasks), return_exceptions=True)
        for (key, _), result in zip(search_tasks, gathered):
            if isinstance(result, Exception):
                logger.warning("Prompt AI source failed", extra={"source": key, "error": str(result)})
                self._mark_failed(source_status, key, result)
                continue
            batch, statuses = result
            jobs.extend(batch)
            source_status.update(statuses)

        await emit("Normalizing jobs...")
        criteria = SearchCriteria.build(
            keywords=keywords,
            locations=interpreted.locations,
            remote=interpreted.remote is True,
            india_only=filters["india_only"],
            min_experience=interpreted.experience_min,
            max_experience=interpreted.experience_max,
        )
        filtered = apply(jobs, criteria) if jobs else []
        await emit("Removing duplicates...")
        saved = await save_normalized_jobs(filtered) if filtered else []

        await emit("Matching jobs against your resume...")
        profile = _resume_profile(resume)
        matched: list[PromptAIJobResult] = []
        for job in saved:
            job_skills = [skill.name for skill in (job.skills or [])]
            match = heuristic_match(
                JobMatchRequest(
                    job_id=job.id,
                    job_title=job.title,
                    job_description=job.description or "",
                    job_skills=job_skills,
                    company=job.company or "",
                    resume=profile,
                    location=job.location,
                    remote=bool(job.remote),
                    experience_min=job.experience_min,
                    experience_max=job.experience_max,
                )
            )
            match = _enrich_match(match, interpreted, job, profile)
            payload = _job_payload(job)
            payload["match"] = match.model_dump()
            matched.append(PromptAIJobResult.model_validate(payload))

        await emit("Ranking results...")
        matched.sort(key=lambda item: item.match.score, reverse=True)

        return PromptAISearchResponse(
            interpreted=interpreted,
            results=matched,
            source_status=source_status,
            progress=progress,
            total=len(matched),
            resume_id=resume.id,
            resume_file_name=resume.file_name,
        )

    async def stream(
        self, prompt: str, resume: Resume, db: AsyncSession
    ) -> AsyncIterator[str]:
        queue: asyncio.Queue[str | None] = asyncio.Queue()

        def on_progress(message: str) -> None:
            queue.put_nowait(message)

        async def run() -> None:
            try:
                result = await self.search(prompt, resume, db, on_progress=on_progress)
                queue.put_nowait(json.dumps({"event": "complete", "data": result.model_dump(mode="json")}))
            except Exception as exc:
                logger.exception("Prompt AI search failed")
                queue.put_nowait(json.dumps({"event": "error", "message": str(exc) or "Prompt AI search failed"}))
            finally:
                queue.put_nowait(None)

        task = asyncio.create_task(run())
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                if item.startswith("{"):
                    yield f"data: {item}\n\n"
                else:
                    yield f"data: {json.dumps({'event': 'progress', 'message': item})}\n\n"
        finally:
            await task

    async def _search_direct(
        self, keywords: list[str], location: Optional[str], filters: dict[str, Any]
    ) -> tuple[list[NormalizedJob], dict[str, SourceStatus]]:
        jobs, statuses = await self.source_manager.search(keywords, location, filters)
        mapped: dict[str, SourceStatus] = {}
        for name, info in statuses.items():
            status = info.get("status") if isinstance(info, dict) else None
            count = info.get("result_count", 0) if isinstance(info, dict) else 0
            if status == "error":
                mapped[name] = SourceStatus(
                    status="failed", count=0, message=f"{name.title()} temporarily unavailable."
                )
            else:
                mapped[name] = SourceStatus(status="success", count=count)
        return jobs, mapped

    async def _search_mcp(
        self,
        server: MCPServer,
        keywords: list[str],
        location: Optional[str],
        interpreted: InterpretedPrompt,
        filters: dict[str, Any],
    ) -> tuple[list[NormalizedJob], dict[str, SourceStatus]]:
        key = f"{server.name.lower()}-mcp"
        try:
            searcher = MCPJobSearch(
                MCPServerConfig(server.name, server.transport, server.endpoint, server.enabled)
            )
            jobs, _tool = await searcher.search(
                keywords,
                location,
                interpreted.remote,
                filters={
                    "experience_min": interpreted.experience_min,
                    "experience_max": interpreted.experience_max,
                    "posted_after": interpreted.posted_after,
                    "limit": 25,
                },
            )
            return jobs, {key: SourceStatus(status="success", count=len(jobs))}
        except Exception:
            return [], {
                key: SourceStatus(
                    status="failed",
                    count=0,
                    message=f"{server.name} temporarily unavailable.",
                )
            }

    async def _search_jobspy(
        self,
        keywords: list[str],
        location: Optional[str],
        interpreted: InterpretedPrompt,
        sites: list[str],
    ) -> tuple[list[NormalizedJob], dict[str, SourceStatus]]:
        request = JobSpySearchRequest(
            search_term=" ".join(keywords)[:200],
            location=location,
            site_name=sites,
            results_wanted=20,
            job_type=interpreted.job_type,
            is_remote=True if interpreted.remote is True else None,
            hours_old=interpreted.hours_old,
            country_indeed=interpreted.country or "india",
        )
        try:
            jobs, meta = await self.jobspy.search(request)
        except (JobSpyMCPError, ValueError, Exception):
            failed = {
                site: SourceStatus(status="failed", count=0, message=f"{site} temporarily unavailable.")
                for site in sites
            }
            return [], failed
        mapped: dict[str, SourceStatus] = {}
        for site, info in (meta.get("portal_status") or {}).items():
            if info.get("status") == "failed":
                mapped[site] = SourceStatus(
                    status="failed",
                    count=0,
                    message=f"{site.replace('_', ' ').title()} temporarily unavailable.",
                )
            else:
                mapped[site] = SourceStatus(status="success", count=int(info.get("count") or 0))
        return jobs, mapped

    @staticmethod
    def _mark_failed(source_status: dict[str, SourceStatus], key: str, error: Exception) -> None:
        label = key.split(":", 1)[-1]
        source_status[label] = SourceStatus(
            status="failed",
            count=0,
            message="temporarily unavailable.",
        )


def _job_payload(job) -> dict:
    return {
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "remote": bool(job.remote),
        "employment_type": job.employment_type,
        "experience_min": job.experience_min,
        "experience_max": job.experience_max,
        "description": job.description or "",
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "currency": job.currency,
        "posted_at": job.posted_at,
        "created_at": job.created_at,
        "skills": [{"name": skill.name} for skill in (job.skills or [])],
        "source_records": [
            {
                "source": record.source,
                "source_job_id": record.source_job_id,
                "job_url": record.job_url,
                "apply_url": record.apply_url,
            }
            for record in (job.source_records or [])
        ],
    }


def _resume_profile(resume: Resume) -> ResumeProfile:
    return ResumeProfile(
        full_name="",
        target_role=resume.target_role or "",
        summary=resume.summary or "",
        skills=list(resume.extracted_skills or []),
        experience_years=resume.experience_years or 0,
        raw_text=resume.raw_text or "",
    )
    return ResumeProfile(
        full_name="",
        target_role=resume.target_role or "",
        summary=resume.summary or "",
        skills=list(resume.extracted_skills or []),
        experience_years=resume.experience_years or 0,
        raw_text=resume.raw_text or "",
    )


def _enrich_match(match, interpreted: InterpretedPrompt, job, profile: ResumeProfile):
    reasons = list(match.match_reasons)
    gaps = list(match.gaps)

    if interpreted.locations:
        if any(matches_location_query(job.location, loc, bool(job.remote)) for loc in interpreted.locations):
            reasons.append("Location matches")
        elif job.remote:
            reasons.append("Remote role is reachable from the requested location")
        else:
            gaps.append("Location does not match the prompt")

    if interpreted.remote is True and job.remote:
        reasons.append("Remote preference matches")
    if interpreted.hybrid and job.remote:
        reasons.append("Remote/hybrid preference is compatible")

    years = profile.experience_years or 0
    job_min = job.experience_min
    if job_min is not None and years >= job_min:
        reasons.append("Experience requirement matches")

    match.match_reasons = reasons
    match.gaps = gaps
    match.recommendations = gaps
    return match

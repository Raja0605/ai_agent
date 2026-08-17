from fastapi import APIRouter

from app.schemas.ai import (
    AtsCheckRequest,
    AtsCheckResult,
    BatchMatchItem,
    BatchMatchRequest,
    BatchMatchResponse,
    CoverLetterRequest,
    CoverLetterResult,
    JobMatchRequest,
    MatchResult,
    TailorResumeRequest,
    TailorResumeResult,
)
from app.services.ai.base import BaseAIService
from app.services.ai.gemini import GeminiProvider
from app.services.ai.heuristic import heuristic_match
from app.services.ai.openai_provider import OpenAIProvider
from app.core.config import settings

router = APIRouter()


def get_llm_provider() -> BaseAIService:
    if settings.LLM_PROVIDER.lower() == "openai":
        return OpenAIProvider(api_key=settings.OPENAI_API_KEY or "", model=settings.OPENAI_MODEL)
    return GeminiProvider(api_key=settings.GOOGLE_API_KEY or "", model=settings.GEMINI_MODEL)


@router.get("/config")
async def get_ai_config():
    """
    Report the AI configuration actually in force.

    The frontend used to display a model name from a hardcoded client-side
    default, which had drifted away from what the backend really calls. This
    is the single source of truth for that badge.
    """
    provider = get_llm_provider()
    return {
        "provider": settings.LLM_PROVIDER.lower(),
        "provider_name": provider.name,
        "model": provider.model,
        "configured": provider.is_configured,
        "active_method": "ai" if provider.is_configured else "heuristic",
    }


@router.post("/match", response_model=MatchResult)
async def match_job(request: JobMatchRequest):
    """Evaluate one resume against one job, using AI when it is available."""
    return await get_llm_provider().match_job(request)


@router.post("/match/batch", response_model=BatchMatchResponse)
async def match_jobs_batch(request: BatchMatchRequest):
    """
    Score a whole result page against one resume.

    Deliberately deterministic-only: a search returns dozens of jobs, and one
    model call each would be slow and expensive for a number that exists to
    rank a list. The detail view runs the full AI evaluation on the single job
    the user actually opened. Results are labelled `method: heuristic` so the
    UI never presents these as AI judgements.
    """
    items = [
        BatchMatchItem(
            job_id=job.job_id,
            result=heuristic_match(
                JobMatchRequest(
                    job_id=job.job_id,
                    job_title=job.job_title,
                    job_description=job.job_description,
                    job_skills=job.job_skills,
                    company=job.company,
                    resume=request.resume,
                )
            ),
        )
        for job in request.jobs
    ]
    return BatchMatchResponse(items=items)


@router.post("/cover-letter", response_model=CoverLetterResult)
async def generate_cover_letter(request: CoverLetterRequest):
    """Generate a personalized cover note, falling back to a labelled template."""
    return await get_llm_provider().generate_cover_letter(request)


@router.post("/tailor", response_model=TailorResumeResult)
async def tailor_resume(request: TailorResumeRequest):
    """Rewrite the resume's headline content toward one specific posting."""
    return await get_llm_provider().tailor_resume(request)


@router.post("/ats-check", response_model=AtsCheckResult)
async def check_ats(request: AtsCheckRequest):
    """Check whether the resume is structurally parseable by an ATS."""
    return await get_llm_provider().check_ats(request)

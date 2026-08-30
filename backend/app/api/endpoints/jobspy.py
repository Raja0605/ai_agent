from fastapi import APIRouter, HTTPException

from app.schemas.job import JobResponse
from app.schemas.jobspy import JobSpySearchRequest
from app.services.job_service import save_normalized_jobs
from app.services.jobspy_mcp_client import JobSpyMCPError
from app.services.jobspy_service import JobSpyService

router = APIRouter()
service = JobSpyService()


@router.get("/health")
async def health():
    return await service.health()


@router.get("/tools")
async def tools():
    try:
        return await service.tools()
    except JobSpyMCPError as exc:
        raise HTTPException(503, "Job Spy MCP is unavailable") from exc
    except Exception as exc:
        raise HTTPException(503, "Job Spy MCP is unavailable") from exc


@router.post("/test")
async def test():
    result = await service.health()
    if result.get("status") != "connected":
        raise HTTPException(503, "Job Spy MCP is unavailable")
    try:
        details = await service.tools()
    except Exception as exc:
        raise HTTPException(503, "Job Spy MCP is unavailable") from exc
    result.update({"tools": details.get("tools", []), "sites": details.get("sites", [])})
    return result


@router.post("/search")
async def search(payload: JobSpySearchRequest):
    try:
        jobs, meta = await service.search(payload)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except JobSpyMCPError as exc:
        raise HTTPException(503, "Job Spy MCP search is unavailable") from exc
    except Exception as exc:
        raise HTTPException(503, "Job Spy MCP search is unavailable") from exc
    saved = await save_normalized_jobs(jobs)
    counts: dict[str, int] = {}
    for job in jobs:
        counts[job.source] = counts.get(job.source, 0) + 1
    return {
        "results": [JobResponse.model_validate(job) for job in saved],
        "sources": counts,
        **meta,
    }

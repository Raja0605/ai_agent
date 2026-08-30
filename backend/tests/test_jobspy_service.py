"""Unit tests for Job Spy MCP argument mapping, parsing, and partial failure."""
from datetime import datetime

import pytest
from sqlalchemy import func, select

from app.models.job import Job, JobSourceRecord
from app.schemas.job import NormalizedJob
from app.schemas.jobspy import JobSpySearchRequest
from app.services.job_service import save_normalized_jobs
from app.services.jobspy_service import JobSpyService

SCHEMA = {
    "type": "object",
    "properties": {
        "search_term": {"type": "string"},
        "location": {"type": "string"},
        "site_name": {
            "type": "array",
            "items": {"type": "string"},
            "description": "linkedin, indeed, glassdoor, zip_recruiter, google, bayt, naukri, bdjobs",
        },
        "results_wanted": {"type": "integer"},
        "job_type": {"type": "string", "enum": ["fulltime", "parttime", "internship", "contract"]},
        "is_remote": {"type": "boolean"},
        "hours_old": {"type": "integer"},
        "country_indeed": {"type": "string", "default": "usa"},
        "proxies": {"type": "array"},
    },
    "required": ["search_term"],
}

SAMPLE_TEXT = """Found 2 jobs:

**DevOps Engineer**
Company: ABC Technologies
Location: Chennai, Tamil Nadu
Site: indeed
Type: fulltime
Posted: 2026-08-28
URL: https://example.com/indeed/1
Description: Kubernetes and AWS...

================================================================================

**DevOps Engineer**
Company: ABC Technologies
Location: Chennai
Site: naukri
URL: https://example.com/naukri/1
Description: Kubernetes...

================================================================================
"""


def test_arguments_follow_schema_and_default_to_india():
    request = JobSpySearchRequest(
        search_term="DevOps Engineer",
        location="Chennai",
        site_name=["indeed"],
        results_wanted=20,
        country_indeed="India",
    )
    args = JobSpyService.build_arguments(SCHEMA, request, ["indeed"])
    assert args["search_term"] == "DevOps Engineer"
    assert args["location"] == "Chennai"
    assert args["site_name"] == ["indeed"]
    assert args["country_indeed"] == "india"
    assert "proxies" not in args
    assert "is_remote" not in args


def test_arguments_omit_fields_the_schema_does_not_declare():
    request = JobSpySearchRequest(search_term="SRE", location="Chennai")
    args = JobSpyService.build_arguments({"properties": {"query": {"type": "string"}}}, request, ["indeed"])
    assert args == {"query": "SRE"}


def test_text_results_are_parsed_without_inventing_fields():
    jobs = JobSpyService.parse_text_results(SAMPLE_TEXT)
    assert len(jobs) == 2
    assert jobs[0]["title"] == "DevOps Engineer"
    assert jobs[0]["site"] == "indeed"
    assert jobs[1]["site"] == "naukri"


def test_normalize_uses_jobspy_source_prefix():
    jobs = JobSpyService.normalize(SAMPLE_TEXT, "indeed")
    assert [job.source for job in jobs] == ["jobspy:indeed", "jobspy:naukri"]
    assert jobs[0].posted_at == datetime(2026, 8, 28)
    assert jobs[0].currency is None or jobs[0].salary_min is None


def test_empty_and_error_text_are_not_jobs():
    assert JobSpyService.normalize("No jobs found matching your criteria.", "indeed") == []
    assert JobSpyService.normalize("Error searching for jobs: blocked", "glassdoor") == []


@pytest.mark.asyncio
async def test_partial_portal_failure_keeps_successful_results(monkeypatch):
    service = JobSpyService()

    async def fake_discover():
        return {
            "search_tool": {"name": "search_jobs", "inputSchema": SCHEMA},
            "sites": ["indeed", "naukri", "linkedin", "glassdoor"],
            "schema": SCHEMA,
            "tools": [{"name": "search_jobs"}],
        }

    async def fake_search_site(tool_name, schema, request, site, timeout):
        if site == "glassdoor":
            return site, [], "temporarily unavailable"
        job = NormalizedJob(
            source=f"jobspy:{site}",
            source_job_id=site,
            title="DevOps Engineer",
            company="ABC Technologies",
            location="Chennai",
            description="",
            job_url=f"https://example.com/{site}",
            apply_url=f"https://example.com/{site}",
            currency=None,
        )
        return site, [job], None

    monkeypatch.setattr(service, "discover", fake_discover)
    monkeypatch.setattr(service, "_search_site", fake_search_site)

    jobs, meta = await service.search(JobSpySearchRequest(
        search_term="DevOps Engineer",
        location="Chennai",
        site_name=["indeed", "naukri", "linkedin", "glassdoor"],
    ))
    assert len(jobs) == 3
    assert meta["portal_status"]["glassdoor"]["status"] == "failed"
    assert meta["portal_status"]["indeed"]["status"] == "success"
    assert meta["total"] == 3


@pytest.mark.asyncio
async def test_unknown_board_is_rejected(monkeypatch):
    service = JobSpyService()

    async def fake_discover():
        return {
            "search_tool": {"name": "search_jobs", "inputSchema": SCHEMA},
            "sites": ["indeed", "naukri"],
            "schema": SCHEMA,
            "tools": [{"name": "search_jobs"}],
        }

    monkeypatch.setattr(service, "discover", fake_discover)
    with pytest.raises(ValueError, match="Unsupported"):
        await service.search(JobSpySearchRequest(search_term="DevOps", site_name=["not_a_board"]))


async def test_jobspy_sources_reuse_canonical_dedup(session_factory):
    jobs = [
        NormalizedJob(
            source=f"jobspy:{site}",
            source_job_id=site,
            title="DevOps Engineer",
            company="ABC Technologies",
            location="Chennai",
            description="Kubernetes",
            job_url=f"https://example.com/{site}",
            apply_url=f"https://example.com/{site}",
            currency=None,
        )
        for site in ("indeed", "naukri", "linkedin")
    ]
    saved = await save_normalized_jobs(jobs)
    assert len(saved) == 1
    async with session_factory() as db:
        assert await db.scalar(select(func.count()).select_from(Job)) == 1
        assert await db.scalar(select(func.count()).select_from(JobSourceRecord)) == 3

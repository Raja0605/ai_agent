"""Job Spy search through the independent JobSpy HTTP server.

Uses HTTP API instead of MCP for simpler integration.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from datetime import datetime
from typing import Any, Optional

import httpx
from app.core.config import settings
from app.schemas.job import NormalizedJob
from app.schemas.jobspy import JobSpySearchRequest

logger = logging.getLogger("jobpulse.jobspy")

# Display names only.
SITE_LABELS = {
    "indeed": "Indeed",
    "linkedin": "LinkedIn",
    "naukri": "Naukri",
    "glassdoor": "Glassdoor",
    "google": "Google Jobs",
    "zip_recruiter": "ZipRecruiter",
    "bayt": "Bayt",
    "bdjobs": "BDJobs",
}

_SITE_ALIASES = {
    "google jobs": "google",
    "google_jobs": "google",
    "ziprecruiter": "zip_recruiter",
    "zip recruiter": "zip_recruiter",
}


class JobSpyService:
    def _base_url(self) -> str:
        return f"http://{settings.JOBSPY_HOST}:{settings.JOBSPY_PORT}"

    async def health(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self._base_url()}/health")
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "status": "connected",
                        "server": "jobspy_http",
                        "host": settings.JOBSPY_HOST,
                        "port": settings.JOBSPY_PORT,
                    }
        except Exception as e:
            logger.warning("JobSpy health check failed", extra={"error": str(e)})
        return {
            "status": "disconnected",
            "server": "jobspy_http",
            "host": settings.JOBSPY_HOST,
            "port": settings.JOBSPY_PORT,
        }

    async def tools(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(f"{self._base_url()}/tools")
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "status": "connected",
                        "server": "jobspy_http",
                        "host": settings.JOBSPY_HOST,
                        "port": settings.JOBSPY_PORT,
                        "tools": data.get("tools", []),
                        "sites": data.get("sites", []),
                        "job_search_tool": "search_jobs",
                    }
        except Exception as e:
            logger.warning("JobSpy tools discovery failed", extra={"error": str(e)})
        return {
            "status": "disconnected",
            "server": "jobspy_http",
            "host": settings.JOBSPY_HOST,
            "port": settings.JOBSPY_PORT,
            "tools": [],
            "sites": [],
            "job_search_tool": None,
        }

    async def discover(self) -> dict[str, Any]:
        """Discover available tools and sites from HTTP API"""
        tools_data = await self.tools()
        return {
            "tools": tools_data.get("tools", []),
            "search_tool": {"name": "search_jobs"},
            "sites": tools_data.get("sites", []),
        }

    async def search(self, request: JobSpySearchRequest) -> tuple[list[NormalizedJob], dict[str, Any]]:
        """Search for jobs using HTTP API"""
        info = await self.discover()
        supported = info["sites"]
        requested = [self.canonical_site(name) for name in (request.site_name or supported)]
        unknown = [name for name in requested if name not in supported]
        if unknown:
            raise ValueError(f"Unsupported job boards: {', '.join(unknown)}")
        if not requested:
            raise ValueError("Select at least one supported job board")

        timeout = settings.JOBSPY_SITE_TIMEOUT_SECONDS
        tasks = [
            self._search_site(request, site, timeout)
            for site in requested
        ]
        completed = await asyncio.gather(*tasks)

        jobs: list[NormalizedJob] = []
        portal_status: dict[str, Any] = {}
        for site, site_jobs, error in completed:
            if error:
                portal_status[site] = {
                    "status": "failed",
                    "count": 0,
                    "message": "temporarily unavailable",
                }
            else:
                jobs.extend(site_jobs)
                portal_status[site] = {"status": "success", "count": len(site_jobs)}

        return jobs, {
            "sites": requested,
            "portal_status": portal_status,
            "total": len(jobs),
        }

    async def _search_site(
        self,
        request: JobSpySearchRequest,
        site: str,
        timeout: float,
    ) -> tuple[str, list[NormalizedJob], str | None]:
        """Search a single job board via HTTP API"""
        try:
            payload = {
                "search_term": request.search_term,
                "location": request.location,
                "site_name": [site],
                "results_wanted": request.results_wanted,
                "job_type": request.job_type,
                "is_remote": request.is_remote,
                "distance": request.distance,
                "hours_old": request.hours_old,
                "country_indeed": self._india_country(request.country_indeed),
            }
            
            async with httpx.AsyncClient(timeout=timeout + 5) as client:
                response = await client.post(
                    f"{self._base_url()}/search",
                    json=payload,
                    timeout=timeout
                )
                if response.status_code != 200:
                    return site, [], f"HTTP {response.status_code}"
                
                data = response.json()
                results = data.get("results", [])
                jobs = [self._normalize_item(item, site) for item in results]
                jobs = [j for j in jobs if j is not None]
                return site, jobs, None
                
        except Exception as exc:
            logger.warning("JobSpy portal failed", extra={"site": site, "error": str(exc)})
            return site, [], "temporarily unavailable"

    @classmethod
    def canonical_site(cls, value: str) -> str:
        raw = (value or "").strip().lower()
        return _SITE_ALIASES.get(raw, raw.replace(" ", "_"))

    @staticmethod
    def _india_country(value: str | None) -> str:
        raw = (value or "india").strip().lower()
        if raw in {"in", "ind", "india"}:
            return "india"
        return raw or "india"

    @classmethod
    def _normalize_item(cls, item: dict[str, Any], fallback_site: str) -> NormalizedJob | None:
        title = item.get("title")
        url = item.get("job_url")
        if not title or not url or str(url).upper() == "N/A":
            return None
        site = cls.canonical_site(str(item.get("site") or fallback_site))
        posted = cls._parse_datetime(item.get("date_posted"))
        salary_min, salary_max, currency = cls._salary(item)
        remote = item.get("is_remote")
        if remote is None:
            blob = f"{item.get('location') or ''} {item.get('description') or ''}".lower()
            remote = "remote" in blob
        description = item.get("description")
        company = item.get("company")
        location = item.get("location")
        employment = item.get("job_type")
        source_id = str(item.get("id") or hashlib.sha256(str(url).encode()).hexdigest())
        return NormalizedJob(
            source=f"jobspy:{site}",
            source_job_id=source_id,
            title=str(title),
            company=str(company) if company else "Unknown company",
            location=str(location) if location else None,
            remote=bool(remote),
            employment_type=str(employment) if employment else None,
            description=str(description) if description else "",
            salary_min=salary_min,
            salary_max=salary_max,
            currency=currency,
            posted_at=posted,
            job_url=str(url),
            apply_url=str(url),
        )

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        text = str(value).strip()
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(text[:19], fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None

    @staticmethod
    def _salary(item: dict[str, Any]) -> tuple[int | None, int | None, str | None]:
        salary_str = item.get("salary")
        if not salary_str:
            return None, None, None
        
        # Parse salary string like "$50,000 - $80,000 (yearly)"
        numbers = re.findall(r"[\d,]+", str(salary_str))
        parsed = [int(num.replace(",", "")) for num in numbers if num.replace(",", "").isdigit()]
        
        if len(parsed) >= 2:
            return parsed[0], parsed[1], "USD"
        elif parsed:
            return parsed[0], None, "USD"
        
        return None, None, None

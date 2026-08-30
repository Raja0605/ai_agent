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

# Sites that are permanently blocked upstream (bot-detection, reCAPTCHA, etc.)
# and should never be included in the default search pool. Explicit user
# selections still go through so the UI can report UNAVAILABLE accurately.
_BLOCKED_SITES = {"naukri"}

# Glassdoor requires more specific location strings than other sites.
# Map common bare city names to their full region strings.
_GLASSDOOR_LOCATION_MAP = {
    "chennai": "Chennai, Tamil Nadu, India",
    "bangalore": "Bangalore, Karnataka, India",
    "bengaluru": "Bangalore, Karnataka, India",
    "mumbai": "Mumbai, Maharashtra, India",
    "delhi": "New Delhi, Delhi, India",
    "new delhi": "New Delhi, Delhi, India",
    "hyderabad": "Hyderabad, Telangana, India",
    "pune": "Pune, Maharashtra, India",
    "kolkata": "Kolkata, West Bengal, India",
    "ahmedabad": "Ahmedabad, Gujarat, India",
    "noida": "Noida, Uttar Pradesh, India",
    "gurgaon": "Gurgaon, Haryana, India",
    "gurugram": "Gurgaon, Haryana, India",
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
        if request.site_name:
            # User explicitly chose sites — honour their choice, just canonicalise.
            requested = [self.canonical_site(name) for name in request.site_name]
        else:
            # Default: all supported sites except permanently-blocked ones.
            requested = [
                s for s in supported if s not in _BLOCKED_SITES
            ]
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
        for site, site_jobs, error, mcp_status in completed:
            label = SITE_LABELS.get(site, site)
            if mcp_status == "verification_required":
                portal_status[site] = {
                    "status": "verification_required",
                    "count": 0,
                    "message": error or f"{label} requires verification. Open the official {label} page and complete the CAPTCHA manually before continuing.",
                }
            elif mcp_status in ("blocked", "unavailable"):
                portal_status[site] = {
                    "status": "unavailable",
                    "count": 0,
                    "message": error or f"{label} is currently unavailable (blocked by provider)",
                }
            elif mcp_status in ("error", "failed") or (error and mcp_status != "no_results"):
                portal_status[site] = {
                    "status": "failed",
                    "count": 0,
                    "message": error or "temporarily unavailable",
                }
            elif site_jobs:
                jobs.extend(site_jobs)
                portal_status[site] = {"status": "success", "count": len(site_jobs)}
            else:
                portal_status[site] = {
                    "status": "no_results",
                    "count": 0,
                    "message": "No results found for this query",
                }

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
    ) -> tuple[str, list[NormalizedJob], str | None, str | None]:
        """Search a single job board via HTTP API.

        Returns (site, jobs, error_message, mcp_status).
        mcp_status is one of: success | no_results | blocked | unavailable | verification_required | error | None
        """
        try:
            location = self._normalize_location(request.location, site)
            payload = {
                "search_term": request.search_term,
                "location": location,
                "site_name": [site],
                "results_wanted": request.results_wanted,
                "job_type": request.job_type,
                "is_remote": request.is_remote,
                "distance": request.distance,
                "hours_old": request.hours_old,
                "country_indeed": self._india_country(request.country_indeed),
            }
            if site == "google":
                loc_bit = f" near {location}" if location else ""
                payload["google_search_term"] = f"{request.search_term} jobs{loc_bit}"

            async with httpx.AsyncClient(timeout=timeout + 5) as client:
                response = await client.post(
                    f"{self._base_url()}/search",
                    json=payload,
                    timeout=timeout
                )
                if response.status_code != 200:
                    return site, [], f"HTTP {response.status_code}", "failed"

                data = response.json()
                mcp_status = data.get("status", "success")
                error = data.get("error")
                logger.info(
                    "JobSpy site %s status=%s count=%s error=%s",
                    site,
                    mcp_status,
                    data.get("count"),
                    error,
                )

                if mcp_status in ("blocked", "unavailable", "verification_required", "error", "failed"):
                    return site, [], error or f"{site} {mcp_status}", mcp_status

                results = data.get("results") or []
                jobs = [job for item in results if (job := self._normalize_item(item, site)) is not None]
                dropped = len(results) - len(jobs)
                if dropped:
                    logger.warning("JobSpy site %s dropped %s of %s results during normalize", site, dropped, len(results))
                if results and not jobs:
                    return site, [], "results dropped during normalize (missing title or URL)", "error"
                if mcp_status == "no_results" or not jobs:
                    return site, [], None, "no_results"
                return site, jobs, None, "success"

        except Exception as exc:
            logger.warning("JobSpy portal failed", extra={"site": site, "error": str(exc)})
            return site, [], "temporarily unavailable", "error"


    @classmethod
    def canonical_site(cls, value: str) -> str:
        raw = (value or "").strip().lower()
        return _SITE_ALIASES.get(raw, raw.replace(" ", "_"))

    @staticmethod
    def _normalize_location(location: str | None, site: str) -> str | None:
        """Expand bare Indian city names for Glassdoor's location lookup.

        JobSpy interpolates the location into Glassdoor's findPopularLocationAjax
        query. A fuller "City, State, India" string is what the lookup expects
        when the endpoint is reachable; a 403 from Glassdoor is a separate issue.
        """
        if not location or site != "glassdoor":
            return location
        key = location.strip().lower()
        return _GLASSDOOR_LOCATION_MAP.get(key, location)

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
        min_amount = item.get("min_amount")
        max_amount = item.get("max_amount")
        currency = item.get("currency")
        if isinstance(currency, str) and currency.strip():
            currency_code = currency.strip().upper()
        else:
            currency_code = None
        if min_amount is not None or max_amount is not None:
            try:
                salary_min = int(min_amount) if min_amount is not None else None
            except (TypeError, ValueError):
                salary_min = None
            try:
                salary_max = int(max_amount) if max_amount is not None else None
            except (TypeError, ValueError):
                salary_max = None
            return salary_min, salary_max, currency_code

        if not salary_str:
            return None, None, None
        
        # Parse salary string like "$50,000 - $80,000 (yearly)"
        numbers = re.findall(r"[\d,]+", str(salary_str))
        parsed = [int(num.replace(",", "")) for num in numbers if num.replace(",", "").isdigit()]
        
        if len(parsed) >= 2:
            return parsed[0], parsed[1], currency_code or "USD"
        elif parsed:
            return parsed[0], None, currency_code or "USD"
        
        return None, None, None

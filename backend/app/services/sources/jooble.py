"""
Jooble — a job aggregator with a free API key and an Indian index.

Jooble runs a country-specific index at `in.jooble.org` that pulls from the
Indian portals and company sites, and hands out API keys on request with no
partner review. Like Careerjet it is a legitimate second-hand route to
listings this app cannot fetch first-hand.

Its `source` field names the site a posting was indexed from, so results keep
the identity of the original portal — a Naukri listing arrives tagged
`naukri`, not `jooble`.

Set JOOBLE_API_KEY to enable; without it the adapter is a no-op.
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, List, Optional

import httpx

from app.core.config import settings
from app.schemas.job import NormalizedJob
from app.services.locations import is_indian_location
from app.services.salary_parser import parse_indian_salary
from app.services.skill_extractor import normalize_skills, strip_html
from app.services.sources.base import JobSource
from app.services.sources.publishers import publisher_slug

logger = logging.getLogger("jobpulse.sources")


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return parsed.astimezone(timezone.utc).replace(tzinfo=None) if parsed.tzinfo else parsed


class JoobleAdapter(JobSource):
    source_name = "jooble"

    async def search(
        self,
        keyword: str,
        location: Optional[str] = None,
        remote: bool = False,
        page: int = 1,
    ) -> List[NormalizedJob]:
        api_key = settings.JOOBLE_API_KEY
        if not api_key:
            logger.info("[jooble] No JOOBLE_API_KEY set — skipping.")
            return []

        body = {
            "keywords": keyword,
            "location": location or "India",
            "page": str(max(1, page)),
            "ResultOnPage": "50",
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    # The key is part of the path, not a header.
                    f"https://{settings.JOOBLE_API_HOST}/api/{api_key}",
                    json=body,
                    timeout=20.0,
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPStatusError as exc:
            logger.warning("[jooble] HTTP %s", exc.response.status_code)
            return []
        except Exception as exc:
            logger.warning("[jooble] fetch failed: %s", exc)
            return []

        return self._parse(payload)

    def _parse(self, payload: Any) -> List[NormalizedJob]:
        jobs: List[NormalizedJob] = []

        for item in payload.get("jobs") or []:
            link = item.get("link")
            if not link:
                continue

            location = item.get("location") or "India"
            title = (item.get("title") or "Untitled role").strip()
            # Jooble returns a snippet with the query terms wrapped in <b>.
            description = strip_html(item.get("snippet") or "").strip()
            is_remote = "remote" in f"{location} {title}".lower()

            if not is_indian_location(location, is_remote):
                continue

            # Salary arrives as free text ("₹8,00,000 - ₹12,00,000 per year"),
            # which the Indian salary parser already understands.
            parsed_salary = parse_indian_salary(item.get("salary"))

            job_id = item.get("id")
            jobs.append(
                NormalizedJob(
                    source=publisher_slug(item.get("source"), self.source_name),
                    source_job_id=str(job_id)
                    if job_id
                    else hashlib.sha1(link.encode("utf-8")).hexdigest(),
                    title=title,
                    company=(item.get("company") or "Unknown Company").strip(),
                    location=location,
                    remote=is_remote,
                    employment_type=(item.get("type") or "").lower() or None,
                    description=description,
                    salary_min=parsed_salary.min_amount if parsed_salary else None,
                    salary_max=parsed_salary.max_amount if parsed_salary else None,
                    currency=parsed_salary.currency if parsed_salary else None,
                    posted_at=_parse_datetime(item.get("updated")),
                    job_url=link,
                    apply_url=link,
                    skills=normalize_skills([], description, title),
                )
            )

        return jobs

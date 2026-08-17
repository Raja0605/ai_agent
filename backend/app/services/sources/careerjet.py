"""
Careerjet — a job-search index with a genuinely open partner API.

Careerjet crawls Indian portals and company sites under its own publisher
agreements and exposes the result through a documented API with an India
locale (`en_IN`). It is the cheapest legitimate way to widen coverage beyond
the company career boards: a free affiliate key, no partner review, and no
terms-of-service problem, because redistributing these listings is the product
Careerjet sells.

Set CAREERJET_API_KEY to enable; without it the adapter is a no-op.
"""

import hashlib
import logging
from datetime import datetime
from typing import Any, List, Optional

import httpx

from app.core.config import settings
from app.schemas.job import NormalizedJob
from app.services.locations import is_indian_location
from app.services.skill_extractor import normalize_skills, strip_html
from app.services.sources.base import JobSource

logger = logging.getLogger("jobpulse.sources")

_ENDPOINT = "https://search.api.careerjet.net/v4/query"

# Careerjet reports the pay period as a single letter.
_ANNUALIZE = {"Y": 1, "M": 12, "W": 52, "D": 260, "H": 2080}

# Date formats seen on the India locale.
_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%a, %d %b %Y", "%d %b %Y")


def _parse_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    return None


def _annualize(amount: Any, period: Optional[str]) -> Optional[int]:
    try:
        value = float(amount)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    return int(value * _ANNUALIZE.get((period or "Y").upper(), 1))


class CareerjetAdapter(JobSource):
    source_name = "careerjet"

    async def search(
        self,
        keyword: str,
        location: Optional[str] = None,
        remote: bool = False,
        page: int = 1,
    ) -> List[NormalizedJob]:
        api_key = settings.CAREERJET_API_KEY
        if not api_key:
            logger.info("[careerjet] No CAREERJET_API_KEY set — skipping.")
            return []

        params = {
            "keywords": keyword,
            "location": location or "India",
            "locale_code": settings.CAREERJET_LOCALE,
            "sort": "date",
            "page": str(max(1, min(page, 10))),  # the API caps pages at 10
            "page_size": "50",
            # Both are required by the API. It uses them for its own
            # fraud/abuse accounting, and rejects the call without them.
            "user_ip": settings.CAREERJET_USER_IP,
            "user_agent": "JobPulse/1.0",
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    _ENDPOINT,
                    params=params,
                    # The key is the basic-auth username with an empty password.
                    auth=(api_key, ""),
                    timeout=20.0,
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPStatusError as exc:
            logger.warning("[careerjet] HTTP %s", exc.response.status_code)
            return []
        except Exception as exc:
            logger.warning("[careerjet] fetch failed: %s", exc)
            return []

        return self._parse(payload)

    def _parse(self, payload: Any) -> List[NormalizedJob]:
        jobs: List[NormalizedJob] = []

        for item in payload.get("jobs") or []:
            url = item.get("url")
            if not url:
                continue

            location = item.get("locations") or "India"
            title = (item.get("title") or "Untitled role").strip()
            description = strip_html(item.get("description") or "").strip()
            is_remote = "remote" in f"{location} {title}".lower()

            if not is_indian_location(location, is_remote):
                continue

            period = item.get("salary_type")

            jobs.append(
                NormalizedJob(
                    source=self.source_name,
                    # Careerjet returns no stable id, so derive one from the
                    # posting URL — it is the only field guaranteed unique.
                    source_job_id=hashlib.sha1(url.encode("utf-8")).hexdigest(),
                    title=title,
                    company=(item.get("company") or "Unknown Company").strip(),
                    location=location,
                    remote=is_remote,
                    employment_type=None,
                    description=description,
                    salary_min=_annualize(item.get("salary_min"), period),
                    salary_max=_annualize(item.get("salary_max"), period),
                    currency=item.get("salary_currency_code"),
                    posted_at=_parse_date(item.get("date")),
                    job_url=url,
                    apply_url=url,
                    skills=normalize_skills([], description, title),
                )
            )

        return jobs

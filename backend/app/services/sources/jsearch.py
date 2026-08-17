"""
Naukri, LinkedIn and Indeed postings, reached through Google for Jobs.

None of the three can be queried directly:

* **Naukri** publishes no public API at all, and its terms forbid scraping.
* **Indeed** retired the Publisher API and its XML feed; what remains is an
  enterprise data partnership (NDA, sales-gated) and an iframe search widget
  that returns no data.
* **LinkedIn** gates job data behind Talent Solutions partnership, and is the
  most litigious of the three about scraping.

What all three *do* is publish their postings into Google for Jobs, which is
indexed and resold by licensed aggregators. This adapter talks to one of them
(JSearch, on RapidAPI by default), so the postings arrive through a channel
the portals opted into rather than one that violates their terms.

The important consequence for the UI: a result keeps the identity of the
portal it came from. `job_publisher` says "Naukri" or "LinkedIn", and that is
what lands in `NormalizedJob.source`, so the source badge and the source
filter show the real portals instead of a single opaque "aggregator" entry.

Set JSEARCH_API_KEY to enable. Without it the adapter is a no-op, exactly like
Adzuna — a missing key costs you this source, not the search.
"""

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

# Salary period -> multiplier to reach an annual figure. Indian postings quote
# monthly pay far more often than Western ones, so getting this wrong turns a
# ₹80,000/month role into a ₹80,000/year one.
_ANNUALIZE = {"YEAR": 1, "MONTH": 12, "WEEK": 52, "DAY": 260, "HOUR": 2080}


def _annual_salary(amount: Any, period: Optional[str]) -> Optional[int]:
    try:
        value = float(amount)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    return int(value * _ANNUALIZE.get((period or "YEAR").upper(), 1))


def _items(payload: Any) -> List[dict]:
    """
    The job list, whichever envelope the API used.

    `/search-v2` returns `{"data": {"jobs": [...], "cursor": ...}}`; the older
    `/search` returned `{"data": [...]}`. Accepting both means a future move
    back or forward does not silently yield zero results — which is exactly
    how the wrong endpoint went unnoticed until a live key was tried.
    """
    if not isinstance(payload, dict):
        return []

    data = payload.get("data")
    if isinstance(data, dict):
        return data.get("jobs") or []
    if isinstance(data, list):
        return data
    return []


def _salary(item: dict) -> tuple[Optional[int], Optional[int], Optional[str]]:
    """
    Annual salary, from whichever of the several salary fields is populated.

    This endpoint carries no currency field. Most postings give no figures at
    all; where they do, the free-text `job_salary_string` is the only place a
    currency appears, so the Indian parser is tried first and the numeric
    fields are used as a fallback.
    """
    parsed = parse_indian_salary(item.get("job_salary_string") or item.get("job_salary"))
    if parsed is not None:
        return parsed.min_amount, parsed.max_amount, parsed.currency

    period = item.get("job_salary_period")
    minimum = _annual_salary(item.get("job_min_salary"), period)
    maximum = _annual_salary(item.get("job_max_salary"), period)
    if minimum is None and maximum is None:
        return None, None, None

    # Figures with no stated currency, on a posting the India gate has already
    # accepted, are rupees. Labelling them USD would be a worse guess.
    return minimum, maximum, "INR"


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    # The column is naive UTC.
    return parsed.astimezone(timezone.utc).replace(tzinfo=None) if parsed.tzinfo else parsed


class JSearchAdapter(JobSource):
    #: Only a fallback label — each job is stored under its own publisher.
    source_name = "jsearch"

    async def search(
        self,
        keyword: str,
        location: Optional[str] = None,
        remote: bool = False,
        page: int = 1,
    ) -> List[NormalizedJob]:
        api_key = settings.JSEARCH_API_KEY
        if not api_key:
            logger.info("[jsearch] No JSEARCH_API_KEY set — skipping.")
            return []

        # This endpoint paginates by opaque cursor rather than page number,
        # and there is no cursor to hand on a fresh search. Rather than burn
        # a quota call re-fetching page 1 under a different name, later pages
        # return nothing; `num_pages` widens the first call instead.
        if page > 1:
            return []

        # The API takes one natural-language string rather than separate role
        # and location fields, and reads the location out of it.
        query = f"{keyword} in {location}" if location else f"{keyword} in India"

        params = {
            "query": query,
            "num_pages": str(settings.JSEARCH_NUM_PAGES),
            "country": settings.JSEARCH_COUNTRY,
            "date_posted": settings.JSEARCH_DATE_POSTED,
        }
        if remote:
            params["work_from_home"] = "true"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://{settings.JSEARCH_API_HOST}{settings.JSEARCH_ENDPOINT}",
                    params=params,
                    headers={
                        "X-RapidAPI-Key": api_key,
                        "X-RapidAPI-Host": settings.JSEARCH_API_HOST,
                    },
                    timeout=20.0,
                )
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPStatusError as exc:
            # 429 on the free RapidAPI tier is routine, and worth naming
            # explicitly so it is not mistaken for a broken integration.
            if exc.response.status_code == 429:
                logger.warning("[jsearch] Rate limited — quota exhausted for this key.")
            else:
                logger.warning("[jsearch] HTTP %s", exc.response.status_code)
            return []
        except Exception as exc:
            logger.warning("[jsearch] fetch failed: %s", exc)
            return []

        return self._parse(payload)

    def _parse(self, payload: Any) -> List[NormalizedJob]:
        allowed = settings.jsearch_publisher_list
        jobs: List[NormalizedJob] = []

        for item in _items(payload):
            source = publisher_slug(item.get("job_publisher"), self.source_name)
            if allowed and source not in allowed:
                continue

            job_id = item.get("job_id")
            if not job_id:
                continue

            is_remote = bool(item.get("job_is_remote"))
            location = ", ".join(
                part
                for part in (item.get("job_city"), item.get("job_state"))
                if part
            ) or item.get("job_location") or ("Remote" if is_remote else "India")

            # The country filter is a hint to the aggregator, not a guarantee;
            # US postings still come back on an India query.
            if not is_indian_location(location, is_remote):
                continue

            description = strip_html(item.get("job_description") or "").strip()
            title = (item.get("job_title") or "Untitled role").strip()
            salary_min, salary_max, currency = _salary(item)

            # `job_employment_types` is the machine-readable list; the singular
            # field is display text and arrives with an en-dash ("Full–time").
            employment_types = item.get("job_employment_types") or []
            employment_type = (
                employment_types[0]
                if employment_types
                else item.get("job_employment_type") or ""
            )

            jobs.append(
                NormalizedJob(
                    source=source,
                    source_job_id=str(job_id),
                    title=title,
                    company=item.get("employer_name") or "Unknown Company",
                    location=location,
                    remote=is_remote,
                    employment_type=employment_type.lower().replace("–", "-") or None,
                    description=description,
                    salary_min=salary_min,
                    salary_max=salary_max,
                    currency=currency,
                    posted_at=_parse_datetime(item.get("job_posted_at_datetime_utc")),
                    job_url=item.get("job_apply_link"),
                    apply_url=item.get("job_apply_link"),
                    # This endpoint sends no skill list, so they are mined from
                    # the description.
                    skills=normalize_skills([], description, title),
                )
            )

        return jobs

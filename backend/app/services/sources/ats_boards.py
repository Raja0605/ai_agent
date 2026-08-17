"""
Company career boards published by the major ATS platforms.

Greenhouse, Lever and Ashby each expose a company's open roles as a public
JSON endpoint — the same one the company's own careers page calls. No
credentials, no scraping, no terms-of-service problem: this is the interface
companies publish for exactly this purpose.

For the Indian market this is the strongest source available. Naukri, Indeed,
LinkedIn and Foundit have no usable public API and forbid scraping, while most
Indian product companies and funded startups run their hiring on one of these
three platforms. A probe of 55 candidate companies found 10 live boards
carrying 181 India-located postings, all first-party and current.

Postings come straight from the employer, so unlike an aggregator there is no
staleness lag, no duplicate reposting, and the apply link is the real one.
"""

import asyncio
import html as html_lib
import logging
import time
from abc import abstractmethod
from datetime import datetime, timezone
from typing import Any, List, Optional

import httpx

from app.core.config import settings
from app.schemas.job import NormalizedJob
from app.services.locations import is_indian_location
from app.services.salary_parser import parse_indian_salary
from app.services.skill_extractor import normalize_skills, strip_html
from app.services.sources.base import JobSource

logger = logging.getLogger("jobpulse.sources")

# A board's full posting list is the same regardless of what the user searched
# for, and one search fans out over several keywords. Without caching, a
# three-keyword search would refetch every board three times.
_CACHE_TTL_SECONDS = 900
_cache: dict[str, tuple[float, List[dict]]] = {}


def _clean_text(raw: str) -> str:
    """ATS descriptions arrive as HTML, sometimes double-escaped."""
    if not raw:
        return ""
    # Greenhouse returns content with entities escaped twice (&lt;div&gt;).
    text = html_lib.unescape(html_lib.unescape(raw))
    text = strip_html(text)
    return " ".join(text.split())


class AtsBoardSource(JobSource):
    """
    Shared behaviour for the three ATS platforms.

    Each board is fetched whole and filtered locally, because none of these
    endpoints accept a search query — they return the company's full open
    list, which is small (5-107 roles in practice).
    """

    #: Where the company slug goes in the request URL.
    url_template: str

    #: These endpoints take no query parameters at all, so there is nothing to
    #: pass a location to — `SourceManager` asks once and the shared filter
    #: narrows the result.
    uses_location_param = False

    def __init__(self, companies: List[str]):
        self.companies = companies

    @abstractmethod
    def parse(self, company: str, payload: Any) -> List[NormalizedJob]:
        """Map one board's response onto NormalizedJob objects."""

    async def _fetch_board(self, client: httpx.AsyncClient, company: str) -> List[NormalizedJob]:
        cache_key = f"{self.source_name}:{company}"
        cached = _cache.get(cache_key)
        now = time.monotonic()

        if cached and now - cached[0] < _CACHE_TTL_SECONDS:
            payload = cached[1]
        else:
            url = self.url_template.format(company=company)
            try:
                response = await client.get(url, timeout=20.0)
                response.raise_for_status()
                payload = response.json()
            except httpx.HTTPStatusError as exc:
                # 404 means the slug is wrong or the board was taken down —
                # normal for a configured list that drifts over time.
                if exc.response.status_code != 404:
                    logger.warning("[%s/%s] HTTP %s", self.source_name, company, exc.response.status_code)
                return []
            except Exception as exc:
                logger.warning("[%s/%s] fetch failed: %s", self.source_name, company, exc)
                return []

            _cache[cache_key] = (now, payload)

        try:
            return self.parse(company, payload)
        except Exception as exc:
            logger.warning("[%s/%s] parse failed: %s", self.source_name, company, exc)
            return []

    async def search(
        self,
        keyword: str,
        location: Optional[str] = None,
        remote: bool = False,
        page: int = 1,
    ) -> List[NormalizedJob]:
        if not self.companies:
            return []

        # One connection pool across every board in this source.
        async with httpx.AsyncClient(
            headers={"User-Agent": "JobPulse/1.0"}, follow_redirects=True
        ) as client:
            results = await asyncio.gather(
                *(self._fetch_board(client, company) for company in self.companies),
                return_exceptions=True,
            )

        jobs: List[NormalizedJob] = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning("[%s] board task failed: %s", self.source_name, result)
                continue
            jobs.extend(result)

        # No filtering here. These boards are small and already India-gated at
        # parse time; deciding which postings answer the search is the shared
        # filter's job, so this source is held to the same standard as the
        # aggregators instead of its own looser one.
        return jobs


def _salary_from(description: str) -> tuple[Optional[int], Optional[int], Optional[str]]:
    parsed = parse_indian_salary(description)
    if parsed is None:
        return None, None, None
    return parsed.min_amount, parsed.max_amount, parsed.currency


class GreenhouseSource(AtsBoardSource):
    source_name = "greenhouse"
    url_template = "https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true"

    def parse(self, company: str, payload: Any) -> List[NormalizedJob]:
        jobs: List[NormalizedJob] = []

        for item in payload.get("jobs", []) or []:
            location = (item.get("location") or {}).get("name") or ""
            description = _clean_text(item.get("content") or "")
            title = html_lib.unescape(item.get("title") or "Untitled role")
            remote = "remote" in f"{location} {title}".lower()

            if not is_indian_location(location, remote):
                continue

            posted = _parse_iso(item.get("first_published") or item.get("updated_at"))
            salary_min, salary_max, currency = _salary_from(description)

            jobs.append(
                NormalizedJob(
                    source=self.source_name,
                    source_job_id=str(item.get("id")),
                    title=title,
                    company=item.get("company_name") or company,
                    location=location or "India",
                    remote=remote,
                    employment_type=None,
                    description=description,
                    salary_min=salary_min,
                    salary_max=salary_max,
                    currency=currency,
                    posted_at=posted,
                    job_url=item.get("absolute_url"),
                    apply_url=item.get("absolute_url"),
                    skills=normalize_skills([], description, title),
                )
            )

        return jobs


class LeverSource(AtsBoardSource):
    source_name = "lever"
    url_template = "https://api.lever.co/v0/postings/{company}?mode=json"

    def parse(self, company: str, payload: Any) -> List[NormalizedJob]:
        jobs: List[NormalizedJob] = []

        for item in payload or []:
            categories = item.get("categories") or {}
            location = categories.get("location") or ""
            workplace = (item.get("workplaceType") or "").lower()
            remote = workplace == "remote" or "remote" in location.lower()

            if not is_indian_location(location, remote):
                continue

            # Lever splits the body across several fields; the plain-text
            # variants avoid another HTML strip.
            description = " ".join(
                filter(
                    None,
                    [
                        item.get("descriptionPlain") or "",
                        item.get("additionalPlain") or "",
                    ],
                )
            ).strip()
            if not description:
                description = _clean_text(item.get("description") or "")

            title = item.get("text") or "Untitled role"
            salary_min, salary_max, currency = _salary_from(description)

            jobs.append(
                NormalizedJob(
                    source=self.source_name,
                    source_job_id=str(item.get("id")),
                    title=title,
                    company=company.replace("-", " ").title(),
                    location=location or "India",
                    remote=remote,
                    employment_type=categories.get("commitment"),
                    description=description,
                    salary_min=salary_min,
                    salary_max=salary_max,
                    currency=currency,
                    # Lever timestamps are epoch milliseconds.
                    posted_at=_parse_epoch_ms(item.get("createdAt")),
                    job_url=item.get("hostedUrl"),
                    apply_url=item.get("applyUrl") or item.get("hostedUrl"),
                    skills=normalize_skills([], description, title),
                )
            )

        return jobs


class AshbySource(AtsBoardSource):
    source_name = "ashby"
    url_template = "https://api.ashbyhq.com/posting-api/job-board/{company}?includeCompensation=true"

    def parse(self, company: str, payload: Any) -> List[NormalizedJob]:
        jobs: List[NormalizedJob] = []

        for item in payload.get("jobs", []) or []:
            if item.get("isListed") is False:
                continue

            location = item.get("location") or ""
            remote = bool(item.get("isRemote")) or "remote" in location.lower()

            if not is_indian_location(location, remote):
                continue

            description = item.get("descriptionPlain") or _clean_text(item.get("descriptionHtml") or "")
            title = item.get("title") or "Untitled role"
            salary_min, salary_max, currency = _salary_from(
                f"{description} {item.get('compensation') or ''}"
            )

            jobs.append(
                NormalizedJob(
                    source=self.source_name,
                    source_job_id=str(item.get("id")),
                    title=title,
                    company=company.replace("-", " ").title(),
                    location=location or "India",
                    remote=remote,
                    employment_type=item.get("employmentType"),
                    description=description,
                    salary_min=salary_min,
                    salary_max=salary_max,
                    currency=currency,
                    posted_at=_parse_iso(item.get("publishedAt")),
                    job_url=item.get("jobUrl"),
                    apply_url=item.get("applyUrl") or item.get("jobUrl"),
                    skills=normalize_skills([], description, title),
                )
            )

        return jobs


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    # Stored in a naive UTC column, so drop the offset after converting.
    return parsed.astimezone(timezone.utc).replace(tzinfo=None) if parsed.tzinfo else parsed


def _parse_epoch_ms(value: Any) -> Optional[datetime]:
    try:
        return datetime.utcfromtimestamp(int(value) / 1000)
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def build_ats_sources() -> List[AtsBoardSource]:
    """
    Instantiate one source per ATS from the configured board list.

    Configured as `ats:company` pairs so a new employer is a config change
    rather than a code change — see ATS_BOARDS in core/config.py.
    """
    by_platform: dict[str, List[str]] = {"greenhouse": [], "lever": [], "ashby": []}

    for entry in settings.ats_board_list:
        platform, _, company = entry.partition(":")
        platform = platform.strip().lower()
        company = company.strip()
        if platform in by_platform and company:
            by_platform[platform].append(company)
        else:
            logger.warning("Ignoring malformed ATS_BOARDS entry: %r", entry)

    sources: List[AtsBoardSource] = []
    if by_platform["greenhouse"]:
        sources.append(GreenhouseSource(by_platform["greenhouse"]))
    if by_platform["lever"]:
        sources.append(LeverSource(by_platform["lever"]))
    if by_platform["ashby"]:
        sources.append(AshbySource(by_platform["ashby"]))

    return sources

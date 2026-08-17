import asyncio
import logging
from typing import List, Optional, Sequence

from app.schemas.job import NormalizedJob
from app.services import job_filter
from app.services.job_filter import SearchCriteria
from app.services.sources.base import JobSource

# Import adapters
from app.services.sources.adzuna import AdzunaAdapter
from app.services.sources.ats_boards import build_ats_sources
from app.services.sources.careerjet import CareerjetAdapter
from app.services.sources.jooble import JoobleAdapter
from app.services.sources.jsearch import JSearchAdapter
from app.services.sources.remotive import RemotiveAdapter

logger = logging.getLogger("jobpulse.sources")

#: Upper bound on in-flight source requests. A three-role, three-city search
#: across every adapter plans well over fifty calls; firing them all at once
#: is what gets a free API tier to return 429 for the rest of the minute.
MAX_CONCURRENT_REQUESTS = 12


def default_sources() -> List[JobSource]:
    """
    Every adapter, in no particular order — results are aggregated, scored and
    deduplicated downstream, so no source takes precedence over another.

    Each adapter that needs credentials returns nothing when they are absent,
    so an unconfigured key costs that one source rather than the search.
    """
    return [
        # Aggregators that index the Indian portals. This is how Naukri,
        # LinkedIn and Indeed postings reach the app: none can be queried
        # directly, but all three syndicate into these indexes, and each
        # posting keeps the name of the portal it came from.
        JSearchAdapter(),
        CareerjetAdapter(),
        JoobleAdapter(),
        # Country-scoped aggregator, strong in India. Needs credentials.
        AdzunaAdapter(),
        # Remote-first and global, no credentials.
        RemotiveAdapter(),
        # Company career boards — first-party postings straight from the
        # employer, with no aggregator lag and a real apply link.
        *build_ats_sources(),
    ]


class SourceManager:
    def __init__(self, sources: Optional[Sequence[JobSource]] = None):
        self.sources: List[JobSource] = (
            list(sources) if sources is not None else default_sources()
        )

    async def fetch(self, criteria: SearchCriteria, page: int = 1) -> List[NormalizedJob]:
        """
        Query every source for every requested role and city, then keep only
        what actually answers the search.

        Sources are asked for what they can filter server-side; the final say
        on whether a posting matches belongs to `job_filter`, so all of them
        are held to one standard.
        """
        plan = self._plan(criteria)
        if not plan:
            return []

        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

        async def run(source: JobSource, keyword: str, location: Optional[str]):
            async with semaphore:
                return await source.search(
                    keyword=keyword,
                    location=location,
                    remote=criteria.remote,
                    page=page,
                )

        results = await asyncio.gather(
            *(run(*step) for step in plan), return_exceptions=True
        )

        aggregated: List[NormalizedJob] = []
        seen: set[str] = set()

        for step, result in zip(plan, results):
            if isinstance(result, Exception):
                logger.warning("[%s] search failed: %s", step[0].source_name, result)
                continue
            for job in result:
                # The same posting comes back for several keywords and cities.
                identifier = f"{job.source}-{job.source_job_id}"
                if identifier not in seen:
                    seen.add(identifier)
                    aggregated.append(job)

        matched = job_filter.apply(aggregated, criteria)
        logger.info(
            "Search %r: %d fetched, %d matched the criteria",
            criteria.keywords,
            len(aggregated),
            len(matched),
        )
        return matched

    def _plan(self, criteria: SearchCriteria) -> List[tuple]:
        """
        The (source, keyword, location) calls to make.

        Sources that filter a whole board locally are asked once per keyword
        rather than once per city: their endpoints take no location parameter,
        so repeating the call per city would refetch the same list and throw
        away the extra copies.
        """
        keywords = criteria.keywords or ("",)
        locations: tuple[Optional[str], ...] = criteria.locations or (None,)

        plan = []
        for source in self.sources:
            source_locations = (
                locations if getattr(source, "uses_location_param", True) else (None,)
            )
            for keyword in keywords:
                for location in source_locations:
                    plan.append((source, keyword, location))
        return plan

    async def fetch_for_queries(
        self,
        queries: List[str],
        locations: List[str],
        remote: bool,
        page: int = 1,
        india_only: bool = True,
    ) -> List[NormalizedJob]:
        """Search several roles and cities at once."""
        return await self.fetch(
            SearchCriteria.build(
                keywords=queries,
                locations=locations,
                remote=remote,
                india_only=india_only,
            ),
            page=page,
        )

    async def fetch_all(
        self,
        keyword: str,
        location: Optional[str] = None,
        remote: bool = False,
        page: int = 1,
        india_only: bool = True,
    ) -> List[NormalizedJob]:
        """Search a single role and city."""
        return await self.fetch(
            SearchCriteria.build(
                keywords=[keyword],
                locations=[location],
                remote=remote,
                india_only=india_only,
            ),
            page=page,
        )

import asyncio
from app.core.config import settings
from app.sources.remotive import RemotiveSource
from app.sources.adzuna import AdzunaSource


class SourceManager:
    """Concurrent, approved direct-source aggregation only."""

    async def fetch_all(self, keyword: str, location: str = None, remote: bool = False, india_only: bool = False):
        """Fetch jobs from all configured sources.
        Currently returns an empty list as a stub.
        """
        return await self.search([keyword], location, {"remote": remote, "india_only": india_only})[0]

    async def fetch(self, criteria, page: int = 1):
        """Fetch jobs based on SearchCriteria.
        Stub implementation returns empty list.
        """
        keywords = list(getattr(criteria, "keywords", [])) or ["Software Engineer"]
        locations = list(getattr(criteria, "locations", []))
        jobs, _ = await self.search(keywords, locations[0] if locations else None,
                                    {"remote": getattr(criteria, "remote", False)})
        return jobs

    async def search(self, keywords, location=None, filters=None, sources=None):
        providers = {"remotive": RemotiveSource(), "adzuna": AdzunaSource()}
        enabled = set(sources or providers.keys())
        selected = []
        if settings.REMOTIVE_ENABLED and "remotive" in enabled: selected.append(providers["remotive"])
        if settings.ADZUNA_ENABLED and "adzuna" in enabled: selected.append(providers["adzuna"])
        results = await asyncio.gather(*(p.search_jobs(keywords, location, filters) for p in selected), return_exceptions=True)
        jobs, statuses = [], {}
        for provider, result in zip(selected, results):
            if isinstance(result, Exception):
                statuses[provider.name] = {"status": "error", "result_count": 0}
            else:
                jobs.extend(result); statuses[provider.name] = {"status": "success", "result_count": len(result)}
        return jobs, statuses

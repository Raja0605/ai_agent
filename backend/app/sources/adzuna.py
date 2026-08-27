from datetime import datetime
from typing import List, Optional
import httpx

from app.core.config import settings
from app.schemas.job import NormalizedJob
from app.sources.base import JobSource


class AdzunaSource(JobSource):
    name = "adzuna"

    async def search_jobs(self, keywords: List[str], location: Optional[str] = None,
                          filters: Optional[dict] = None) -> List[NormalizedJob]:
        if not settings.ADZUNA_APP_ID or not settings.ADZUNA_APP_KEY:
            return []
        path = f"https://api.adzuna.com/v1/api/jobs/{settings.ADZUNA_COUNTRY}/search/1"
        params = {"app_id": settings.ADZUNA_APP_ID, "app_key": settings.ADZUNA_APP_KEY,
                  "what": " ".join(keywords), "results_per_page": 25}
        if location:
            params["where"] = location
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.get(path, params=params)
            response.raise_for_status()
        jobs = []
        for item in response.json().get("results", []):
            created = item.get("created")
            try:
                posted_at = datetime.fromisoformat(created.replace("Z", "+00:00")) if created else None
            except ValueError:
                posted_at = None
            jobs.append(NormalizedJob(source=self.name, source_job_id=str(item.get("id")), title=item.get("title", "Untitled role"),
                company=(item.get("company") or {}).get("display_name", "Unknown company"), location=(item.get("location") or {}).get("display_name"),
                remote="remote" in item.get("title", "").lower(), description=item.get("description") or "", salary_min=item.get("salary_min"),
                salary_max=item.get("salary_max"), currency="INR" if settings.ADZUNA_COUNTRY == "in" else None,
                posted_at=posted_at, job_url=item.get("redirect_url"), apply_url=item.get("redirect_url")))
        return jobs

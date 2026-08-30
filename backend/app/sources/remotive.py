from datetime import datetime
from typing import List, Optional
import httpx

from app.schemas.job import NormalizedJob
from app.sources.base import JobSource
from app.services.job_filter import extract_experience_range


class RemotiveSource(JobSource):
    name = "remotive"

    async def search_jobs(self, keywords: List[str], location: Optional[str] = None,
                          filters: Optional[dict] = None, **kwargs) -> List[NormalizedJob]:
        query = " ".join(keywords)
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.get("https://remotive.com/api/remote-jobs", params={"search": query})
            response.raise_for_status()
        jobs = []
        for item in response.json().get("jobs", []):
            published = item.get("publication_date")
            try:
                posted_at = datetime.fromisoformat(published.replace("Z", "+00:00")) if published else None
            except ValueError:
                posted_at = None
            description = item.get("description") or ""
            experience_min, experience_max = extract_experience_range(description)
            jobs.append(NormalizedJob(source=self.name, source_job_id=str(item.get("id")),
                title=item.get("title", "Untitled role"), company=item.get("company_name", "Unknown company"),
                location=item.get("candidate_required_location") or "Remote", remote=True,
                employment_type=item.get("job_type"), description=description, experience_min=experience_min, experience_max=experience_max,
                posted_at=posted_at, job_url=item.get("url"), apply_url=item.get("url"), skills=item.get("tags") or []))
        return jobs

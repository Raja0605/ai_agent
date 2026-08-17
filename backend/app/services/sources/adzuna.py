import httpx
from typing import List, Optional
from datetime import datetime
from app.services.sources.base import JobSource
from app.schemas.job import NormalizedJob
from app.core.config import settings
from app.services.skill_extractor import extract_skills, strip_html

# Adzuna returns salary figures in the local currency of the country endpoint
# being queried. Labelling everything INR made every non-Indian salary wrong.
CURRENCY_BY_COUNTRY = {
    "at": "EUR", "au": "AUD", "be": "EUR", "br": "BRL", "ca": "CAD",
    "ch": "CHF", "de": "EUR", "es": "EUR", "fr": "EUR", "gb": "GBP",
    "in": "INR", "it": "EUR", "mx": "MXN", "nl": "EUR", "nz": "NZD",
    "pl": "PLN", "sg": "SGD", "us": "USD", "za": "ZAR",
}


class AdzunaAdapter(JobSource):
    source_name = "adzuna"

    async def search(
        self,
        keyword: str,
        location: Optional[str] = None,
        remote: bool = False,
        page: int = 1
    ) -> List[NormalizedJob]:
        
        app_id = settings.ADZUNA_APP_ID
        app_key = settings.ADZUNA_APP_KEY
        
        if not app_id or not app_key:
            print(f"[{self.source_name}] Source not configured (Missing ADZUNA_APP_ID/KEY). Skipping.")
            return []
            
        country = (settings.ADZUNA_COUNTRY or "in").lower()
        url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
        
        params = {
            "app_id": app_id,
            "app_key": app_key,
            "results_per_page": 20,
            "what": keyword,
            "content-type": "application/json"
        }
        
        if location:
            params["where"] = location
            
        normalized_jobs = []
        
        try:
            async with httpx.AsyncClient() as client:
               response = await client.get(url, params=params, timeout=15.0)
               response.raise_for_status()
               data = response.json()
               
               for job in data.get("results", []):
                   posted_date = None
                   try:
                       posted_date = datetime.fromisoformat(job["created"].replace('Z', '+00:00'))
                   except Exception:
                       pass

                   title = strip_html(job.get("title", "Unknown")).strip()
                   description = strip_html(job.get("description", "")).strip()

                   # The posting decides whether it is remote — not the search
                   # flag. Echoing the request back meant every result of a
                   # remote search was stamped remote whether it was or not,
                   # and the "Remote only" filter then agreed with itself.
                   job_location = job.get("location", {}).get("display_name", "") or ""
                   is_remote = any(
                       term in f"{job_location} {title}".lower()
                       for term in ("remote", "work from home", "wfh", "anywhere")
                   )

                   # Adzuna sends no skill tags at all. Echoing the search
                   # keyword back as the only "skill" made every job look like
                   # a perfect keyword match, so mine the description instead.
                   contract_time = job.get("contract_time")

                   normalized_job = NormalizedJob(
                       source=self.source_name,
                       source_job_id=str(job.get("id")),
                       title=title or "Unknown",
                       company=job.get("company", {}).get("display_name", "Unknown Company"),
                       location=job_location or "Unknown Location",
                       remote=is_remote,
                       employment_type=contract_time or "full_time",
                       description=description,
                       salary_min=int(job["salary_min"]) if job.get("salary_min") else None,
                       salary_max=int(job["salary_max"]) if job.get("salary_max") else None,
                       currency=CURRENCY_BY_COUNTRY.get(country, "USD"),
                       posted_at=posted_date,
                       job_url=job.get("redirect_url"),
                       apply_url=job.get("redirect_url"),
                       skills=extract_skills(description, title),
                   )
                   normalized_jobs.append(normalized_job)
        except Exception as e:
            print(f"[{self.source_name}] Error fetching jobs: {e}")
            
        return normalized_jobs

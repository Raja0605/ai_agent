import html as html_lib
import re
import httpx
from typing import List, Optional
from datetime import datetime
from app.services.sources.base import JobSource
from app.schemas.job import NormalizedJob
from app.services.skill_extractor import normalize_skills, strip_html


def _clean_description(html: str) -> str:
    """
    Remotive returns descriptions as HTML. The UI renders them as preformatted
    text, so the markup was showing up literally. Convert block boundaries to
    newlines, drop the rest of the tags, and collapse the leftover whitespace.
    """
    if not html:
        return ""
    text = re.sub(r"<\s*(br|/p|/div|/li|/h[1-6])\s*/?\s*>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"<\s*li\s*>", "• ", text, flags=re.IGNORECASE)
    text = strip_html(text)
    text = html_lib.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class RemotiveAdapter(JobSource):
    source_name = "remotive"

    #: The endpoint takes a keyword and nothing else, so there is no location
    #: to pass — one call per keyword is all it can answer.
    uses_location_param = False

    async def search(
        self,
        keyword: str,
        location: Optional[str] = None,
        remote: bool = False, # Remotive is remote by default
        page: int = 1
    ) -> List[NormalizedJob]:
        
        url = "https://remotive.com/api/remote-jobs"
        # Remotive API accepts 'search' for keyword
        params = {"search": keyword, "limit": 20}
        
        normalized_jobs = []
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=15.0)
                response.raise_for_status()
                data = response.json()
                
                jobs = data.get("jobs", [])
                
                for job in jobs:
                    # Remotive mostly serves remote jobs, but let's check candidate_required_location
                    req_location = job.get("candidate_required_location", "Remote")
                    
                    # Parse dates
                    posted_date = None
                    try:
                        pub_date_str = job.get("publication_date")
                        if pub_date_str:
                            posted_date = datetime.fromisoformat(pub_date_str)
                    except ValueError:
                        pass
                        
                    # Build canonical job format
                    title = html_lib.unescape(job.get("title", "Unknown Title"))
                    description = _clean_description(job.get("description", ""))

                    normalized_job = NormalizedJob(
                        source=self.source_name,
                        source_job_id=str(job.get("id")),
                        title=title,
                        company=job.get("company_name", "Unknown Company"),
                        location=req_location,
                        remote=True, # Remotive jobs are remote
                        employment_type=job.get("job_type", "").lower() or "full_time",
                        description=description,
                        salary_min=None, # Remotive provides salary as a raw string usually
                        salary_max=None,
                        currency=None,
                        posted_at=posted_date,
                        job_url=job.get("url"),
                        apply_url=job.get("url"),
                        # Remotive's tags are curated but sparse; top them up
                        # from the description so the matcher has real signal.
                        skills=normalize_skills(job.get("tags", []), description, title),
                    )
                    
                    # No location filtering here. This used to be a raw
                    # substring test, which failed on every alias the Indian
                    # market actually uses — a "Bangalore" search dropped
                    # postings written "Bengaluru" or "India". The shared
                    # filter in `job_filter` is alias-aware and applies to
                    # every source alike.
                    normalized_jobs.append(normalized_job)
                    
        except httpx.HTTPError as e:
            print(f"[RemotiveAdapter] HTTP Error: {e}")
        except Exception as e:
            print(f"[RemotiveAdapter] Unexpected Error: {e}")
            
        return normalized_jobs

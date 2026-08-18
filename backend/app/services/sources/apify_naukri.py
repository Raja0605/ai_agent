"""
Apify Naukri Scraper adapter for direct Naukri job data.

This adapter uses the Apify platform to scrape Naukri.com directly, providing
better data quality than aggregator-based approaches. It captures detailed job
information including experience ranges, company ratings, and salary labels.
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

logger = logging.getLogger("jobpulse.sources")


def _parse_experience(experience_label: Optional[str]) -> Optional[int]:
    """Extract minimum experience from label like '3-8 Yrs' or '2-5'."""
    if not experience_label:
        return None
    
    try:
        # Handle formats like "3-8 Yrs", "2-5", "0-1 Yrs"
        import re
        match = re.search(r'(\d+)', experience_label)
        if match:
            return int(match.group(1))
    except (ValueError, AttributeError):
        pass
    return None


def _parse_salary(salary_label: Optional[str]) -> tuple[Optional[int], Optional[int], Optional[str]]:
    """Parse salary label like '6-10 Lakhs' or 'Not disclosed'."""
    if not salary_label or salary_label.lower() == "not disclosed":
        return None, None, None
    
    # Try Indian salary parser first
    parsed = parse_indian_salary(salary_label)
    if parsed:
        return parsed.min_amount, parsed.max_amount, parsed.currency
    
    return None, None, None


def _parse_posted_date(posted_at: Optional[str], created_date: Optional[int]) -> Optional[datetime]:
    """Parse posting date from relative time or epoch timestamp."""
    # Try epoch timestamp first (more accurate)
    if created_date:
        try:
            # Convert milliseconds to seconds
            timestamp = created_date / 1000
            return datetime.fromtimestamp(timestamp, tz=timezone.utc).replace(tzinfo=None)
        except (ValueError, OSError):
            pass
    
    # Try relative time like "2 Days Ago"
    if posted_at:
        try:
            import re
            match = re.search(r'(\d+)\s*(day|hour|week|month)', posted_at.lower())
            if match:
                value = int(match.group(1))
                unit = match.group(2)
                
                from datetime import timedelta
                now = datetime.now(timezone.utc).replace(tzinfo=None)
                if unit == 'day':
                    return now - timedelta(days=value)
                elif unit == 'hour':
                    return now - timedelta(hours=value)
                elif unit == 'week':
                    return now - timedelta(weeks=value)
                elif unit == 'month':
                    return now - timedelta(days=value * 30)
        except (ValueError, AttributeError):
            pass
    
    return None


class ApifyNaukriAdapter(JobSource):
    """Adapter for Apify Naukri Scraper."""
    
    source_name = "naukri"
    
    async def search(
        self,
        keyword: str,
        location: Optional[str] = None,
        remote: bool = False,
        page: int = 1,
    ) -> List[NormalizedJob]:
        api_token = settings.APIFY_API_TOKEN
        if not api_token:
            logger.info("[apify_naukri] No APIFY_API_TOKEN set — skipping.")
            return []
        
        # Apify doesn't support pagination in the same way, limit to first page
        if page > 1:
            return []
        
        # Build Naukri URL dynamically based on search parameters
        # Format: https://www.naukri.com/{keyword}-jobs-in-{location}?experience={min_exp}
        url_parts = [keyword.lower().replace(" ", "-"), "jobs"]
        if location:
            url_parts.extend(["in", location.lower().replace(" ", "-")])
        
        naukri_url = f"https://www.naukri.com/{'-'.join(url_parts)}"
        
        # Build input for Apify actor using URL approach
        actor_input = {
            "urls": [naukri_url],
            "maxResultsPerQuery": 50,  # Default limit
        }
        
        try:
            async with httpx.AsyncClient() as client:
                # Start the actor run
                response = await client.post(
                    f"https://api.apify.com/v2/acts/{settings.APIFY_NAUKRI_ACTOR_ID}/runs",
                    headers={
                        "Authorization": f"Bearer {api_token}",
                        "Content-Type": "application/json",
                    },
                    json=actor_input,
                    timeout=30.0,
                )
                response.raise_for_status()
                run_data = response.json()
                
                run_id = run_data.get("data", {}).get("id")
                if not run_id:
                    logger.warning("[apify_naukri] No run ID returned")
                    return []
                
                # Wait for run to complete (simplified - in production should poll properly)
                await asyncio.sleep(10)  # Initial wait
                
                # Get results from the run
                results_response = await client.get(
                    f"https://api.apify.com/v2/acts/{settings.APIFY_NAUKRI_ACTOR_ID}/runs/{run_id}/dataset/items",
                    headers={
                        "Authorization": f"Bearer {api_token}",
                    },
                    timeout=30.0,
                )
                results_response.raise_for_status()
                items = results_response.json()
                
                return self._parse(items)
                
        except httpx.HTTPStatusError as exc:
            logger.warning("[apify_naukri] HTTP %s", exc.response.status_code)
            return []
        except Exception as exc:
            logger.warning("[apify_naukri] fetch failed: %s", exc)
            return []
    
    def _parse(self, items: List[dict]) -> List[NormalizedJob]:
        """Parse Apify Naukri scraper results into NormalizedJob objects."""
        jobs: List[NormalizedJob] = []
        
        for item in items:
            try:
                # Extract basic fields
                job_id = item.get("jobId")
                if not job_id:
                    continue
                
                title = item.get("title", "").strip() or "Untitled role"
                company = item.get("companyName", "").strip() or "Unknown Company"
                location = item.get("locationLabel", "").strip() or "India"
                
                # Parse experience
                experience_label = item.get("experienceLabel", "")
                min_experience = _parse_experience(experience_label)
                
                # Parse salary
                salary_label = item.get("salaryLabel", "")
                salary_min, salary_max, currency = _parse_salary(salary_label)
                
                # Parse posting date
                posted_at = _parse_posted_date(
                    item.get("postedAt"),
                    item.get("createdDate")
                )
                
                # Extract skills
                skills_str = item.get("tagsAndSkills", "")
                skills = [s.strip() for s in skills_str.split(",") if s.strip()] if skills_str else []
                
                # Clean description
                description = strip_html(item.get("jobDescription", "")).strip()
                
                # Build apply URL
                jd_url = item.get("jdURL", "")
                apply_url = jd_url if jd_url else f"https://www.naukri.com/job-listings-{job_id}"
                
                # Determine if remote (simplified - could be enhanced)
                is_remote = "remote" in location.lower() or "hybrid" in location.lower()
                
                jobs.append(
                    NormalizedJob(
                        source="naukri",
                        source_job_id=str(job_id),
                        title=title,
                        company=company,
                        location=location,
                        remote=is_remote,
                        employment_type=None,  # Could parse from jobTypeFilter if available
                        description=description,
                        salary_min=salary_min,
                        salary_max=salary_max,
                        currency=currency,
                        posted_at=posted_at,
                        job_url=apply_url,
                        apply_url=apply_url,
                        skills=skills,
                    )
                )
                
            except Exception as exc:
                logger.warning("[apify_naukri] Failed to parse job: %s", exc)
                continue
        
        return jobs


# Import asyncio for the sleep call
import asyncio

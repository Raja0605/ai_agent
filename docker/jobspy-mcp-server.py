#!/usr/bin/env python3
"""
JobSpy MCP Server - Simple HTTP API for job scraping
Provides job scraping capabilities through a simple HTTP API
"""

import logging
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel
from jobspy import scrape_jobs

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jobspy-http")

app = FastAPI(title="JobSpy HTTP Server")

# Exact Site enum values from the installed python-jobspy package.
_ALL_SITES = [
    "indeed",
    "linkedin",
    "glassdoor",
    "zip_recruiter",
    "google",
    "bayt",
    "naukri",
    "bdjobs",
]


class JobSearchRequest(BaseModel):
    search_term: str
    location: Optional[str] = None
    site_name: Optional[list[str]] = None
    results_wanted: int = 20
    job_type: Optional[str] = None
    is_remote: Optional[bool] = False
    distance: Optional[int] = 50
    hours_old: Optional[int] = None
    country_indeed: str = "india"
    google_search_term: Optional[str] = None


class _LogCapture(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.INFO)
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(record.getMessage())


def _google_query(search_term: str, location: Optional[str]) -> str:
    query = f"{search_term} jobs"
    if location:
        query += f" near {location}"
    return query


def _classify(site: str, count: int, logs: list[str], exc: Exception | None) -> tuple[str, Optional[str]]:
    """Distinguish scraper failure from a genuine empty result set."""
    blob = "\n".join(logs).lower()
    err = str(exc).lower() if exc else ""
    combined = f"{blob}\n{err}"

    if exc and "unexpected keyword argument 'user_agent'" in err:
        return "unavailable", f"{site} is unavailable in this JobSpy version (scraper constructor mismatch)"
    if "recaptcha" in combined or "captcha" in combined:
        if site == "naukri":
            return "verification_required", "Naukri requires verification. Open the official Naukri search page and complete the CAPTCHA manually before continuing."
        return "unavailable", f"{site} is blocked by reCAPTCHA"
    if "429" in combined:
        return "unavailable", f"{site} rate-limited by the provider"
    if "403" in combined or "forbidden" in combined:
        return "unavailable", f"{site} returned HTTP 403 (blocked by provider)"
    if "406" in combined:
        return "unavailable", f"{site} rejected the request"
    if "location not parsed" in combined:
        return "unavailable", "Glassdoor blocked or rejected the location lookup"
    if "initial cursor not found" in combined and count == 0:
        return "unavailable", "Google Jobs did not return a results page (blocked or markup changed)"
    if exc:
        return "error", str(exc)
    if count == 0:
        return "no_results", None
    return "success", None


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "jobspy"}


@app.get("/tools")
async def list_tools():
    return {
        "tools": [
            {
                "name": "search_jobs",
                "description": "Search for job postings across multiple job boards",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "search_term": {"type": "string", "description": "Job title or keywords to search for"},
                        "location": {"type": "string", "description": "Location to search in"},
                        "site_name": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Job boards to search",
                            "default": ["indeed", "linkedin"],
                        },
                        "results_wanted": {"type": "integer", "description": "Number of results per site", "default": 20},
                        "job_type": {"type": "string", "enum": ["fulltime", "parttime", "internship", "contract"]},
                        "is_remote": {"type": "boolean", "default": False},
                        "hours_old": {"type": "integer"},
                        "country_indeed": {"type": "string", "default": "india"},
                    },
                    "required": ["search_term"],
                },
            }
        ],
        "sites": _ALL_SITES,
    }


@app.post("/search")
async def search_jobs(request: JobSearchRequest):
    logger.info("Search request: %s", request)

    site_names = request.site_name if request.site_name else ["indeed", "linkedin"]
    unknown = [site for site in site_names if site not in _ALL_SITES]
    if unknown:
        return {
            "results": [],
            "count": 0,
            "error": f"Unsupported job boards: {', '.join(unknown)}",
            "status": "error",
        }

    capture = _LogCapture()
    jobspy_logger = logging.getLogger("JobSpy")
    root_logger = logging.getLogger()
    jobspy_logger.addHandler(capture)
    root_logger.addHandler(capture)

    # Enable propagation for all JobSpy sub-loggers so capture gets their lines
    for name in list(logging.root.manager.loggerDict.keys()):
        if name.startswith("JobSpy"):
            logging.getLogger(name).propagate = True


    google_search_term = request.google_search_term
    if "google" in site_names and not google_search_term:
        google_search_term = _google_query(request.search_term, request.location)

    try:
        jobs_df = scrape_jobs(
            site_name=site_names,
            search_term=request.search_term,
            location=request.location,
            results_wanted=request.results_wanted,
            job_type=request.job_type,
            is_remote=request.is_remote or False,
            distance=request.distance if request.distance is not None else 50,
            hours_old=request.hours_old,
            country_indeed=request.country_indeed,
            google_search_term=google_search_term,
            verbose=1,
        )
        count = 0 if jobs_df is None or jobs_df.empty else len(jobs_df)
        status, error = _classify(site_names[0] if len(site_names) == 1 else "jobspy", count, capture.lines, None)
        if jobs_df is None or jobs_df.empty:
            return {"results": [], "count": 0, "error": error, "status": status, "logs": capture.lines[-8:]}

        jobs_json = jobs_df.to_dict(orient="records")
        results = []
        for job in jobs_json:
            def clean_value(val):
                if val is None or (isinstance(val, float) and (str(val) == "nan" or str(val) == "inf")):
                    return None
                return val

            job_url = clean_value(job.get("job_url"))
            job_dict = {
                "title": clean_value(job.get("title")),
                "company": clean_value(job.get("company")),
                "location": clean_value(job.get("location")),
                "site": clean_value(job.get("site")) or site_names[0],
                "job_url": job_url,
                "description": str(clean_value(job.get("description")) or "")[:500],
                "job_type": clean_value(job.get("job_type")),
                "date_posted": clean_value(job.get("date_posted")),
                "is_remote": clean_value(job.get("is_remote")),
                "min_amount": clean_value(job.get("min_amount")),
                "max_amount": clean_value(job.get("max_amount")),
                "currency": clean_value(job.get("currency")),
                "salary": None,
            }

            min_amount = job_dict["min_amount"]
            max_amount = job_dict["max_amount"]
            if min_amount and max_amount:
                salary = f"${min_amount:,.0f} - ${max_amount:,.0f}"
                if job.get("interval"):
                    salary += f" ({job.get('interval')})"
                job_dict["salary"] = salary

            results.append(job_dict)

        return {"results": results, "count": len(results), "status": "success"}

    except Exception as e:
        logger.error("Error in search_jobs: %s", e, exc_info=True)
        status, error = _classify(site_names[0] if site_names else "jobspy", 0, capture.lines, e)
        return {"results": [], "count": 0, "error": error or str(e), "status": status, "logs": capture.lines[-8:]}
    finally:
        jobspy_logger.removeHandler(capture)
        root_logger.removeHandler(capture)
        for name in list(logging.root.manager.loggerDict.keys()):
            if name.startswith("JobSpy"):
                logging.getLogger(name).propagate = False



if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8500)

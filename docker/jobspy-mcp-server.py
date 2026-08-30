#!/usr/bin/env python3
"""
JobSpy MCP Server - Simple HTTP API for job scraping
Provides job scraping capabilities through a simple HTTP API
"""

import json
import logging
from typing import Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from jobspy import scrape_jobs
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jobspy-http")

app = FastAPI(title="JobSpy HTTP Server")

class JobSearchRequest(BaseModel):
    search_term: str
    location: Optional[str] = None
    site_name: Optional[list[str]] = None
    results_wanted: int = 20
    job_type: Optional[str] = None
    is_remote: bool = False
    distance: int = 50
    hours_old: Optional[int] = None
    country_indeed: str = "usa"

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
                        "site_name": {"type": "array", "items": {"type": "string"}, "description": "Job boards to search", "default": ["indeed", "linkedin"]},
                        "results_wanted": {"type": "integer", "description": "Number of results per site", "default": 20},
                        "job_type": {"type": "string", "enum": ["fulltime", "parttime", "internship", "contract"]},
                        "is_remote": {"type": "boolean", "default": False},
                        "hours_old": {"type": "integer"},
                        "country_indeed": {"type": "string", "default": "usa"}
                    },
                    "required": ["search_term"]
                }
            }
        ],
        "sites": ["indeed", "linkedin", "glassdoor", "zip_recruiter", "google", "bayt", "naukri", "bdjobs"]
    }

@app.post("/search")
async def search_jobs(request: JobSearchRequest):
    try:
        logger.info(f"Raw request received")
        logger.info(f"Search request: {request}")
        logger.info(f"Searching for jobs: {request.search_term} in {request.location}")
        
        # Handle empty site_name
        site_names = request.site_name if request.site_name else ["indeed", "linkedin"]
        logger.info(f"Site names: {site_names}")
        
        jobs_df = scrape_jobs(
            site_name=site_names,
            search_term=request.search_term,
            location=request.location,
            results_wanted=request.results_wanted,
            job_type=request.job_type,
            is_remote=request.is_remote,
            distance=request.distance,
            hours_old=request.hours_old,
            country_indeed=request.country_indeed,
            verbose=1
        )

        if jobs_df.empty:
            return {"results": [], "count": 0}

        # Use pandas to_json with proper NaN handling
        jobs_json = jobs_df.to_dict(orient='records')
        
        # Process each job to format for response
        results = []
        for job in jobs_json:
            # Handle NaN values
            def clean_value(val):
                if val is None or (isinstance(val, float) and (str(val) == 'nan' or str(val) == 'inf')):
                    return None
                return val
            
            job_dict = {
                "title": clean_value(job.get('title')) or 'N/A',
                "company": clean_value(job.get('company')) or 'N/A',
                "location": clean_value(job.get('location')) or 'N/A',
                "site": clean_value(job.get('site')) or 'N/A',
                "job_url": clean_value(job.get('job_url')) or 'N/A',
                "description": str(clean_value(job.get('description')) or '')[:500],
                "job_type": clean_value(job.get('job_type')),
                "date_posted": clean_value(job.get('date_posted')),
                "salary": None
            }
            
            min_amount = clean_value(job.get('min_amount'))
            max_amount = clean_value(job.get('max_amount'))
            
            if min_amount and max_amount:
                salary = f"${min_amount:,.0f} - ${max_amount:,.0f}"
                if job.get('interval'):
                    salary += f" ({job.get('interval')})"
                job_dict["salary"] = salary
            
            results.append(job_dict)

        return {"results": results, "count": len(results)}

    except Exception as e:
        logger.error(f"Error in search_jobs: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8500)

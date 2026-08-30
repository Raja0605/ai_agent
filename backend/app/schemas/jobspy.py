from typing import Optional

from pydantic import BaseModel, Field


class JobSpySearchRequest(BaseModel):
    search_term: str = Field(min_length=1, max_length=200)
    location: Optional[str] = None
    site_name: list[str] = []
    results_wanted: int = Field(default=20, ge=1, le=100)
    job_type: Optional[str] = None
    is_remote: Optional[bool] = None
    distance: Optional[int] = Field(default=None, ge=1, le=200)
    hours_old: Optional[int] = Field(default=None, ge=1, le=720)
    country_indeed: str = "india"

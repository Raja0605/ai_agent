from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class LoopBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    keywords: List[str] = Field(default_factory=list)
    location: Optional[str] = None
    remote_only: bool = False
    resume_id: Optional[str] = None
    # Bounded so a loop cannot be configured to hammer the upstream APIs.
    cadence_hours: int = Field(default=24, ge=1, le=168)
    min_score: int = Field(default=50, ge=0, le=100)
    active: bool = True

    @field_validator("keywords")
    @classmethod
    def non_empty_keywords(cls, value: List[str]) -> List[str]:
        cleaned = [k.strip() for k in value if k and k.strip()]
        if not cleaned:
            raise ValueError("A loop needs at least one keyword to search for.")
        # Each keyword multiplies the number of upstream calls per run.
        return cleaned[:5]


class LoopCreate(LoopBase):
    pass


class LoopUpdate(BaseModel):
    name: Optional[str] = None
    keywords: Optional[List[str]] = None
    location: Optional[str] = None
    remote_only: Optional[bool] = None
    resume_id: Optional[str] = None
    cadence_hours: Optional[int] = Field(default=None, ge=1, le=168)
    min_score: Optional[int] = Field(default=None, ge=0, le=100)
    active: Optional[bool] = None


class LoopResponse(LoopBase):
    id: str
    last_run_at: Optional[datetime] = None
    last_run_status: Optional[str] = None
    last_run_error: Optional[str] = None
    created_at: datetime

    # Denormalized counters so the loop list does not need a query per card.
    total_matches: int = 0
    new_matches: int = 0

    class Config:
        from_attributes = True


class LoopMatchJob(BaseModel):
    """The job attached to a match, flattened for the client."""
    id: str
    title: str
    company: str
    location: Optional[str] = None
    remote: bool = False
    employment_type: Optional[str] = None
    description: str = ""
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: Optional[str] = None
    posted_at: Optional[datetime] = None
    skills: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    apply_url: Optional[str] = None


class LoopMatchResponse(BaseModel):
    id: str
    loop_id: str
    score: int
    score_method: str
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    seen: bool
    created_at: datetime
    job: LoopMatchJob


class LoopRunResult(BaseModel):
    loop_id: str
    status: str
    jobs_fetched: int
    new_matches: int
    below_threshold: int
    error: Optional[str] = None

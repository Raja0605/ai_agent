from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.ai import JobMatchResult
from app.schemas.job import JobResponse


class PromptAISearchRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=2000)
    resume_id: str


class InterpretedPrompt(BaseModel):
    prompt: str
    keywords: List[str] = []
    skills: List[str] = []
    locations: List[str] = []
    country: Optional[str] = None
    remote: Optional[bool] = None
    hybrid: bool = False
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None
    salary_min: Optional[int] = None
    job_type: Optional[str] = None
    hours_old: Optional[int] = None
    posted_after: Optional[date] = None
    company: Optional[str] = None


class SourceStatus(BaseModel):
    status: str
    count: int = 0
    message: Optional[str] = None


class PromptAIJobResult(JobResponse):
    match: JobMatchResult


class PromptAISearchResponse(BaseModel):
    interpreted: InterpretedPrompt
    results: List[PromptAIJobResult]
    source_status: dict[str, SourceStatus]
    progress: List[str]
    total: int
    resume_id: str
    resume_file_name: str

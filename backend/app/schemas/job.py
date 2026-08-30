from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from datetime import datetime

class NormalizedJob(BaseModel):
    source: str
    source_job_id: str
    title: str
    company: str
    location: Optional[str] = None
    remote: bool = False
    employment_type: Optional[str] = None
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None
    description: str
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: Optional[str] = "USD"
    posted_at: Optional[datetime] = None
    job_url: Optional[str] = None
    apply_url: Optional[str] = None
    skills: List[str] = []

class JobSearchRequest(BaseModel):
    keywords: List[str]
    location: Optional[str] = None
    remote: bool = False
    experience_level: Optional[str] = None
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None
    salary_min: Optional[int] = None
    sources: List[str] = []

class JobSourceRecordBase(BaseModel):
    source: str
    source_job_id: str
    job_url: Optional[str] = None
    apply_url: Optional[str] = None

class SkillBase(BaseModel):
    name: str

class JobBase(BaseModel):
    title: str
    company: str
    location: Optional[str] = None
    remote: bool = False
    employment_type: Optional[str] = None
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None
    description: str
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: Optional[str] = None
    posted_at: Optional[datetime] = None

class JobCreate(JobBase):
    skills: List[str] = []
    source_records: List[JobSourceRecordBase] = []

class JobResponse(JobBase):
    id: str
    created_at: datetime
    skills: List[SkillBase] = []
    source_records: List[JobSourceRecordBase] = []

    class Config:
        from_attributes = True

from typing import List, Optional

from pydantic import BaseModel, Field


class ResumeProfile(BaseModel):
    full_name: str = ""
    target_role: str = ""
    summary: str = ""
    skills: List[str] = []
    experience_years: int = 0
    raw_text: str = ""


class JobMatchRequest(BaseModel):
    job_id: str
    job_title: str
    job_description: str = ""
    job_skills: List[str] = []
    company: str = ""
    resume: ResumeProfile
    location: Optional[str] = None
    remote: bool = False
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None


class JobMatchResult(BaseModel):
    job_id: str
    score: int = Field(ge=0, le=100)
    matched_skills: List[str] = []
    missing_skills: List[str] = []
    summary: str = ""
    reason: str = ""
    recommendations: List[str] = []
    method: str = "heuristic"
    confidence: str = "low"
    match_reasons: List[str] = []
    gaps: List[str] = []


class AtsIssue(BaseModel):
    severity: str
    message: str
    fix: str = ""


class AtsCheckRequest(BaseModel):
    resume: ResumeProfile


class AtsCheckResult(BaseModel):
    score: int = Field(ge=0, le=100)
    issues: List[AtsIssue] = []
    detected_sections: List[str] = []
    word_count: int = 0


class TailorResumeRequest(BaseModel):
    job_id: str
    job_title: str
    company: str = ""
    job_description: str = ""
    job_skills: List[str] = []
    resume: ResumeProfile


class TailorResumeResult(BaseModel):
    prioritized_skills: List[str] = []
    keywords_to_add: List[str] = []
    notes: str = ""

from pydantic import BaseModel
from typing import List, Literal, Optional

# How a result was produced. The UI must be able to tell an AI judgement apart
# from a keyword heuristic, because earlier builds presented both identically.
MatchMethod = Literal["ai", "heuristic"]

# How much evidence the score rests on — orthogonal to how high the score is.
MatchConfidence = Literal["high", "medium", "low", "none"]


class ResumeProfile(BaseModel):
    full_name: str
    target_role: str
    summary: str
    skills: List[str]
    experience_years: int
    raw_text: Optional[str] = None


class JobMatchRequest(BaseModel):
    job_id: str
    job_title: str
    job_description: str
    job_skills: List[str]
    company: str
    resume: ResumeProfile


class MatchResult(BaseModel):
    score: int
    matched_skills: List[str]
    missing_skills: List[str]
    summary: str
    recommendations: List[str]
    reason: Optional[str] = None
    method: MatchMethod = "heuristic"
    confidence: MatchConfidence = "medium"


class BatchMatchRequest(BaseModel):
    """Score many jobs against one resume in a single round trip."""
    resume: ResumeProfile
    jobs: List["BatchMatchJob"]


class BatchMatchJob(BaseModel):
    job_id: str
    job_title: str
    job_description: str
    job_skills: List[str]
    company: str


class BatchMatchItem(BaseModel):
    job_id: str
    result: MatchResult


class BatchMatchResponse(BaseModel):
    items: List[BatchMatchItem]


class CoverLetterRequest(BaseModel):
    job_id: str
    job_title: str
    company: str
    job_skills: List[str]
    resume: ResumeProfile


class CoverLetterResult(BaseModel):
    content: str
    method: Literal["ai", "template"] = "template"
    note: Optional[str] = None


class TailorResumeRequest(BaseModel):
    """Ask for a job-specific rewrite of the resume's headline content."""
    job_id: str
    job_title: str
    company: str
    job_description: str
    job_skills: List[str]
    resume: ResumeProfile


class TailorResumeResult(BaseModel):
    tailored_summary: str
    prioritized_skills: List[str]
    keywords_to_add: List[str]
    bullet_suggestions: List[str]
    method: Literal["ai", "heuristic"] = "heuristic"


class AtsCheckRequest(BaseModel):
    resume: ResumeProfile


class AtsIssue(BaseModel):
    severity: Literal["critical", "warning", "info"]
    message: str
    fix: str


class AtsCheckResult(BaseModel):
    score: int
    issues: List[AtsIssue]
    detected_sections: List[str]
    word_count: int
    method: Literal["ai", "heuristic"] = "heuristic"


BatchMatchRequest.model_rebuild()

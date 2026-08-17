from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class FunnelStage(BaseModel):
    stage: str
    count: int


class RatePerformance(BaseModel):
    """Outcomes grouped by some dimension (resume used, job source, ...)."""
    label: str
    applications: int
    responses: int
    interviews: int
    offers: int
    response_rate: Optional[float] = None   # None when there is no data yet
    avg_match_score: Optional[float] = None


class AnalyticsOverviewResponse(BaseModel):
    total_applications: int
    by_status: Dict[str, int] = Field(default_factory=dict)
    funnel: List[FunnelStage] = Field(default_factory=list)

    # Rates are None rather than 0 when the denominator is zero, so the UI can
    # say "no data yet" instead of displaying a confident 0%.
    response_rate: Optional[float] = None
    interview_rate: Optional[float] = None
    offer_rate: Optional[float] = None

    avg_days_to_response: Optional[float] = None
    avg_match_score: Optional[float] = None

    by_resume: List[RatePerformance] = Field(default_factory=list)
    by_source: List[RatePerformance] = Field(default_factory=list)

    jobs_in_database: int = 0
    jobs_by_source: Dict[str, int] = Field(default_factory=dict)
    freshness: Dict[str, int] = Field(default_factory=dict)

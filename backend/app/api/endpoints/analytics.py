"""
Analytics derived entirely from tracked data.

The previous dashboard was decorative: it counted platforms the app never
fetched from, added a literal `+ 2` to one bar, and fell back to a hardcoded
92% average ATS score when there was nothing to average. Every number below
comes from the database, and anything with no data reports null rather than a
confident-looking zero.
"""

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.application import ApplicationTracking
from app.models.job import Job
from app.schemas.analytics import AnalyticsOverviewResponse, FunnelStage, RatePerformance

router = APIRouter()

# Statuses that mean the employer came back with something, either way.
RESPONSE_STATUSES = {"INTERVIEW", "OFFER", "REJECTED"}
INTERVIEW_STATUSES = {"INTERVIEW", "OFFER"}
OFFER_STATUSES = {"OFFER"}

# Statuses that count as the application actually having been sent.
SENT_STATUSES = {"APPLYING", "APPLIED"} | RESPONSE_STATUSES

FUNNEL_ORDER = [
    ("Saved", {"SAVED"}),
    ("Ready to apply", {"READY_TO_APPLY"}),
    ("Applied", SENT_STATUSES),
    ("Response received", RESPONSE_STATUSES),
    ("Interview", INTERVIEW_STATUSES),
    ("Offer", OFFER_STATUSES),
]


def _rate(numerator: int, denominator: int) -> Optional[float]:
    """None when there is nothing to divide by — never a fabricated 0%."""
    if denominator <= 0:
        return None
    return round(numerator / denominator * 100, 1)


def _mean(values: List[float]) -> Optional[float]:
    return round(sum(values) / len(values), 1) if values else None


def _performance(label: str, apps: List[ApplicationTracking]) -> RatePerformance:
    sent = [a for a in apps if a.status in SENT_STATUSES]
    responses = [a for a in apps if a.status in RESPONSE_STATUSES]
    interviews = [a for a in apps if a.status in INTERVIEW_STATUSES]
    offers = [a for a in apps if a.status in OFFER_STATUSES]
    scores = [float(a.ats_score) for a in apps if a.ats_score is not None]

    return RatePerformance(
        label=label,
        applications=len(sent),
        responses=len(responses),
        interviews=len(interviews),
        offers=len(offers),
        response_rate=_rate(len(responses), len(sent)),
        avg_match_score=_mean(scores),
    )


@router.get("/", response_model=AnalyticsOverviewResponse)
async def get_analytics(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    app_stmt = (
        select(ApplicationTracking)
        .options(
            selectinload(ApplicationTracking.job).selectinload(Job.source_records)
        )
        .where(ApplicationTracking.user_id == current_user_id)
    )
    applications = list((await db.execute(app_stmt)).scalars().all())

    by_status = Counter(app.status for app in applications)
    sent = [a for a in applications if a.status in SENT_STATUSES]
    responses = [a for a in applications if a.status in RESPONSE_STATUSES]
    interviews = [a for a in applications if a.status in INTERVIEW_STATUSES]
    offers = [a for a in applications if a.status in OFFER_STATUSES]

    # Days-to-response is approximated from updated_at, since a status change
    # is the only signal the app records that a response arrived. It is
    # therefore "days until we heard back and you logged it".
    turnaround = [
        (a.updated_at - a.applied_at).total_seconds() / 86400
        for a in responses
        if a.applied_at and a.updated_at and a.updated_at >= a.applied_at
    ]

    scores = [float(a.ats_score) for a in applications if a.ats_score is not None]

    by_resume: Dict[str, List[ApplicationTracking]] = defaultdict(list)
    by_source: Dict[str, List[ApplicationTracking]] = defaultdict(list)
    for app in applications:
        by_resume[app.resume_used or "Unspecified"].append(app)
        if app.job and app.job.source_records:
            for record in app.job.source_records:
                by_source[record.source].append(app)
        else:
            by_source["unknown"].append(app)

    # Corpus-level stats: what is actually in the database, by real source.
    job_stmt = select(Job).options(selectinload(Job.source_records))
    jobs = list((await db.execute(job_stmt)).scalars().all())

    jobs_by_source: Counter = Counter()
    for job in jobs:
        for record in job.source_records:
            jobs_by_source[record.source] += 1

    now = datetime.utcnow()
    freshness = {"<1h": 0, "1-24h": 0, "1-2d": 0, "2-3d": 0, "3-7d": 0, ">7d": 0, "unknown": 0}
    for job in jobs:
        if job.posted_at is None:
            freshness["unknown"] += 1
            continue
        posted = job.posted_at.replace(tzinfo=None)
        age = now - posted
        if age < timedelta(hours=1):
            freshness["<1h"] += 1
        elif age < timedelta(hours=24):
            freshness["1-24h"] += 1
        elif age < timedelta(days=2):
            freshness["1-2d"] += 1
        elif age < timedelta(days=3):
            freshness["2-3d"] += 1
        elif age < timedelta(days=7):
            freshness["3-7d"] += 1
        else:
            freshness[">7d"] += 1

    return AnalyticsOverviewResponse(
        total_applications=len(applications),
        by_status=dict(by_status),
        funnel=[
            FunnelStage(
                stage=label,
                count=sum(1 for a in applications if a.status in statuses),
            )
            for label, statuses in FUNNEL_ORDER
        ],
        response_rate=_rate(len(responses), len(sent)),
        interview_rate=_rate(len(interviews), len(sent)),
        offer_rate=_rate(len(offers), len(sent)),
        avg_days_to_response=_mean(turnaround),
        avg_match_score=_mean(scores),
        by_resume=sorted(
            (_performance(label, apps) for label, apps in by_resume.items()),
            key=lambda p: p.applications,
            reverse=True,
        ),
        by_source=sorted(
            (_performance(label, apps) for label, apps in by_source.items()),
            key=lambda p: p.applications,
            reverse=True,
        ),
        jobs_in_database=len(jobs),
        jobs_by_source=dict(jobs_by_source),
        freshness=freshness,
    )

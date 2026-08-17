"""
The one place a search's role/location/remote criteria are enforced.

Before this, enforcement was scattered and inconsistent: the ATS boards
filtered locally, Remotive did a raw substring test on the location, Adzuna
trusted whatever its `where` parameter returned, and `/jobs/search` then
returned everything that got saved — including postings no source had matched
against the query at all. Three sources, three different definitions of "this
job matches", and a fourth (none) at the endpoint that fronts them.

Sources should fetch. Deciding whether a posting answers the user's search is
one decision, made once, here — so every source is held to the same standard
and a new adapter inherits it for free.
"""

from dataclasses import dataclass
from typing import List, Optional, Sequence

from app.schemas.job import NormalizedJob
from app.services.locations import is_indian_location, matches_location_query
from app.services.role_matcher import RELEVANCE_THRESHOLD, role_relevance

#: A search fans out over several roles and cities; past this many the request
#: volume to each source stops being reasonable.
MAX_KEYWORDS = 3
MAX_LOCATIONS = 3


@dataclass(frozen=True)
class SearchCriteria:
    """What the user asked for, normalized into a form sources can fan out on."""

    keywords: tuple[str, ...] = ()
    locations: tuple[str, ...] = ()
    remote: bool = False
    #: Restrict results to postings reachable from India. On by default — this
    #: app serves the Indian market, and without it the remote-first and
    #: aggregator sources bury local results under US and EU postings.
    india_only: bool = True

    @classmethod
    def build(
        cls,
        keywords: Optional[Sequence[Optional[str]]] = None,
        locations: Optional[Sequence[Optional[str]]] = None,
        remote: bool = False,
        india_only: bool = True,
    ) -> "SearchCriteria":
        """Clean, de-duplicate and cap the raw inputs, preserving priority order."""
        return cls(
            keywords=_clean(keywords, MAX_KEYWORDS),
            locations=_clean(locations, MAX_LOCATIONS),
            remote=remote,
            india_only=india_only,
        )


def _clean(values: Optional[Sequence[Optional[str]]], limit: int) -> tuple[str, ...]:
    seen: List[str] = []
    for value in values or []:
        if not value or not value.strip():
            continue
        cleaned = " ".join(value.split())
        if cleaned.lower() not in {v.lower() for v in seen}:
            seen.append(cleaned)
    return tuple(seen[:limit])


def relevance(job: NormalizedJob, criteria: SearchCriteria) -> Optional[float]:
    """
    How well a posting answers the search, or None if it does not.

    A job need only satisfy *one* of the requested roles and *one* of the
    requested cities — the fan-out is a union, not an intersection. Its score
    is that of the best-matching role.
    """
    if criteria.remote and not job.remote:
        return None

    if criteria.india_only and not is_indian_location(job.location, job.remote):
        return None

    if criteria.locations and not any(
        matches_location_query(job.location, wanted, job.remote)
        for wanted in criteria.locations
    ):
        return None

    if not criteria.keywords:
        return 1.0

    best = max(
        role_relevance(keyword, job.title, job.skills, job.company)
        for keyword in criteria.keywords
    )
    return best if best >= RELEVANCE_THRESHOLD else None


def apply(jobs: Sequence[NormalizedJob], criteria: SearchCriteria) -> List[NormalizedJob]:
    """
    Drop everything that does not answer the search, best match first.

    Ties break on recency, and a posting with no date sorts last rather than
    first — an unknown date is not evidence of freshness.
    """
    scored: List[tuple[float, float, NormalizedJob]] = []

    for job in jobs:
        score = relevance(job, criteria)
        if score is None:
            continue
        recency = job.posted_at.timestamp() if job.posted_at else float("-inf")
        scored.append((score, recency, job))

    scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return [job for _, _, job in scored]

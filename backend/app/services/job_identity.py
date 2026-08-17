"""
Canonical identity for a job posting.

The same role is routinely published to more than one board. Deduplicating
only on (source, source_job_id) catches repeat fetches from a single source
but not the same posting arriving from Remotive and Adzuna, which is how the
job list ends up showing the same role twice.

A fingerprint over the normalized company + title + locality gives a cheap,
deterministic canonical key. It is intentionally conservative: it will merge
obvious duplicates and leave genuinely different postings alone, because a
false merge (hiding a real job) is worse than a false split (showing a dupe).
"""

import hashlib
import re
from typing import Optional

from app.services.locations import canonical_city

# Suffixes that appear on a company name in one feed and not another.
_COMPANY_NOISE = re.compile(
    r"\b(inc|llc|ltd|limited|corp|corporation|gmbh|pvt|private|plc|co|company|technologies|technology|solutions|labs|group)\b",
    re.IGNORECASE,
)

# Seniority and contract markers that decorate a title inconsistently across
# feeds. Stripped so "Senior DevOps Engineer (Remote)" and "DevOps Engineer"
# at the same company collapse together.
_TITLE_NOISE = re.compile(
    r"\b(senior|sr|junior|jr|lead|staff|principal|remote|hybrid|onsite|on-site|"
    r"full[- ]?time|part[- ]?time|contract|permanent|urgent|hiring|immediate joiner)\b",
    re.IGNORECASE,
)

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _normalize(value: Optional[str], noise: Optional[re.Pattern[str]] = None) -> str:
    text = (value or "").lower()
    if noise is not None:
        text = noise.sub(" ", text)
    return _NON_ALNUM.sub(" ", text).strip()


def _locality(location: Optional[str], remote: bool) -> str:
    """
    Remote postings are compared without a location, because the same remote
    role is listed as "Worldwide", "Anywhere", "Remote - India" and so on
    depending on the board.

    Non-remote roles use the canonical city. Going through the alias table
    matters here: without it a role listed as "Bangalore, Karnataka" on one
    board and "Bengaluru-VTP, India" on another produced two different
    fingerprints and appeared twice.
    """
    if remote:
        return "remote"

    city = canonical_city(location)
    if city:
        return city

    first_segment = (location or "").split(",")[0]
    return _normalize(first_segment) or "unspecified"


def job_fingerprint(company: str, title: str, location: Optional[str], remote: bool) -> str:
    """Stable canonical key for a posting. Same posting -> same fingerprint."""
    parts = [
        _normalize(company, _COMPANY_NOISE),
        _normalize(title, _TITLE_NOISE),
        _locality(location, remote),
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:32]

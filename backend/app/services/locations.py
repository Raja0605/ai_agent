"""
Indian location handling.

Job boards spell the same Indian city many ways. Across the ATS boards this
app reads, one city appears as "Bengaluru-VTP, India", "Bangalore, Karnataka",
"Bangalore/Bengaluru", "BLR" and plain "Bangalore" — and the official rename
(Bangalore → Bengaluru, Gurgaon → Gurugram) means both forms stay in
circulation indefinitely.

Two things depend on getting this right:

* Searching for "Bangalore" must return the postings written "Bengaluru", or
  the filter silently hides most of the market.
* The canonical fingerprint in `job_identity` includes the city, so without
  normalization the same posting listed as "Bangalore" on one board and
  "Bengaluru" on another fails to merge and shows up twice.
"""

import re
from typing import Optional

# Canonical city -> every alias seen in the wild, lowercase.
CITY_ALIASES: dict[str, set[str]] = {
    "bengaluru": {"bengaluru", "bangalore", "blr", "bangaluru", "bengaluru urban"},
    "gurugram": {"gurugram", "gurgaon"},
    "mumbai": {"mumbai", "bombay", "navi mumbai", "thane"},
    "delhi": {"delhi", "new delhi", "ncr", "delhi ncr", "national capital region"},
    "noida": {"noida", "greater noida"},
    "hyderabad": {"hyderabad", "secunderabad", "hyd", "cyberabad"},
    "chennai": {"chennai", "madras"},
    "kolkata": {"kolkata", "calcutta"},
    "pune": {"pune", "poona", "pimpri", "chinchwad"},
    "ahmedabad": {"ahmedabad", "amdavad", "gandhinagar"},
    "jaipur": {"jaipur"},
    "kochi": {"kochi", "cochin", "ernakulam"},
    "thiruvananthapuram": {"thiruvananthapuram", "trivandrum"},
    "coimbatore": {"coimbatore"},
    "indore": {"indore"},
    "chandigarh": {"chandigarh", "mohali", "panchkula"},
    "bhubaneswar": {"bhubaneswar"},
    "nagpur": {"nagpur"},
    "lucknow": {"lucknow"},
    "vadodara": {"vadodara", "baroda"},
    "visakhapatnam": {"visakhapatnam", "vizag"},
    "mysuru": {"mysuru", "mysore"},
}

# alias -> canonical, built once.
_ALIAS_TO_CANONICAL: dict[str, str] = {
    alias: canonical
    for canonical, aliases in CITY_ALIASES.items()
    for alias in aliases
}

# Indian states and union territories, for postings that name only a state.
INDIAN_REGIONS = {
    "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh",
    "goa", "gujarat", "haryana", "himachal pradesh", "jharkhand", "karnataka",
    "kerala", "madhya pradesh", "maharashtra", "manipur", "meghalaya",
    "mizoram", "nagaland", "odisha", "orissa", "punjab", "rajasthan", "sikkim",
    "tamil nadu", "telangana", "tripura", "uttar pradesh", "uttarakhand",
    "west bengal", "jammu and kashmir", "ladakh", "puducherry", "pondicherry",
}

COUNTRY_TERMS = {"india", "bharat", "in", "ind"}

# Split on separators boards use between city / state / country.
_SPLIT = re.compile(r"[,/|;•·]|\s+-\s+|\s+–\s+")
_CLEAN = re.compile(r"[^a-z0-9\s]")


def _segments(location: Optional[str]) -> list[str]:
    if not location:
        return []
    parts = _SPLIT.split(location.lower())
    return [_CLEAN.sub(" ", p).strip() for p in parts if p and p.strip()]


def canonical_city(location: Optional[str]) -> Optional[str]:
    """
    The canonical Indian city named in a location string, if any.

    Handles compound values like "Bengaluru-VTP, India" (an office suffix) and
    "Bangalore, Karnataka" by testing each segment, and by checking whether any
    known alias appears as a whole word inside a segment.
    """
    for segment in _segments(location):
        if segment in _ALIAS_TO_CANONICAL:
            return _ALIAS_TO_CANONICAL[segment]

        # "bengaluru vtp" or "bangalore hq" — an alias plus an office label.
        for word in segment.split():
            if word in _ALIAS_TO_CANONICAL:
                return _ALIAS_TO_CANONICAL[word]

    return None


def normalize_location(location: Optional[str]) -> str:
    """
    A comparable form of a location string.

    Returns the canonical city when one is recognised, otherwise a cleaned
    version of the original so non-Indian locations still compare sensibly.
    """
    city = canonical_city(location)
    if city:
        return city

    segments = _segments(location)
    return " ".join(segments[0].split()) if segments else ""


def is_indian_location(location: Optional[str], remote: bool = False) -> bool:
    """
    Whether a posting is plausibly open to candidates in India.

    Deliberately inclusive on remote roles: a remote posting with no location
    restriction is available from India, and excluding those would drop a
    large share of what the remote-first boards carry.
    """
    if canonical_city(location):
        return True

    segments = _segments(location)
    for segment in segments:
        if segment in COUNTRY_TERMS or segment in INDIAN_REGIONS:
            return True
        # "remote india", "anywhere in india"
        if any(term in segment.split() for term in ("india", "bharat")):
            return True

    if remote and not segments:
        return True

    # "Worldwide" / "Anywhere" / "Global" remote roles include India.
    if remote and any(
        term in " ".join(segments)
        for term in ("worldwide", "anywhere", "global", "remote")
    ):
        return True

    return False


def location_aliases(query: Optional[str]) -> list[str]:
    """
    Every spelling of a location query, for matching in SQL.

    `matches_location_query` is the authority, but the stored-jobs endpoint
    filters in the database and cannot call Python per row. This gives it the
    same alias awareness as an OR of LIKE patterns: searching "Bangalore"
    still has to find the rows saved as "Bengaluru, Karnataka".

    A country-level query expands to every Indian city and state, since no
    posting stores the word "India" reliably.
    """
    if not query or not query.strip():
        return []

    city = canonical_city(query)
    if city:
        return sorted(CITY_ALIASES[city])

    segments = _segments(query)
    if any(s in COUNTRY_TERMS or s in INDIAN_REGIONS for s in segments):
        every_alias = {alias for aliases in CITY_ALIASES.values() for alias in aliases}
        return sorted(every_alias | INDIAN_REGIONS | {"india"})

    # Unrecognised place — match it literally.
    return [segments[0]] if segments else []


def matches_location_query(job_location: Optional[str], query: Optional[str], remote: bool = False) -> bool:
    """
    Whether a posting satisfies a user's location query.

    Alias-aware in both directions, so searching "Bangalore" matches a posting
    written "Bengaluru, Karnataka" and vice versa. A query naming India as a
    country matches any Indian location.
    """
    if not query or not query.strip():
        return True

    query_city = canonical_city(query)
    job_city = canonical_city(job_location)

    if query_city:
        if job_city == query_city:
            return True
        # A remote role advertised for India is reachable from any Indian city.
        return remote and is_indian_location(job_location, remote)

    query_segments = _segments(query)
    if any(s in COUNTRY_TERMS or s == "india" for s in query_segments):
        return is_indian_location(job_location, remote)

    # Unrecognised query: fall back to substring matching on the raw strings.
    haystack = (job_location or "").lower()
    return any(segment and segment in haystack for segment in query_segments)

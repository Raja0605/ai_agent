"""
Mapping an aggregator's "where this posting came from" string to a source id.

Aggregators index the portals this app cannot query directly, and each one
names the originating publisher in its own way — JSearch says "LinkedIn",
Jooble says "linkedin.com", and either may prefix "Jobs via". Reducing them
all to the same slug is what lets a posting keep the identity of the portal it
was published on, so the UI shows a real "Naukri" or "LinkedIn" badge and the
source filter works per portal rather than per aggregator.
"""

from typing import Optional

# Known publishers -> the slug stored on the job. Anything unrecognised keeps
# a slugified form of whatever the aggregator reported.
PUBLISHER_SLUGS = {
    "naukri": "naukri",
    "naukricom": "naukri",
    "linkedin": "linkedin",
    "linkedincom": "linkedin",
    "indeed": "indeed",
    "indeedcom": "indeed",
    "indeedcoin": "indeed",
    "foundit": "foundit",
    "founditin": "foundit",
    "monster": "foundit",           # Monster India rebranded to Foundit
    "monsterindia": "foundit",
    "monsterindiacom": "foundit",
    "shine": "shine",
    "shinecom": "shine",
    "timesjobs": "timesjobs",
    "timesjobscom": "timesjobs",
    "instahyre": "instahyre",
    "instahyrecom": "instahyre",
    "cutshort": "cutshort",
    "cutshortio": "cutshort",
    "hirist": "hirist",
    "hiristcom": "hirist",
    "iimjobs": "iimjobs",
    "iimjobscom": "iimjobs",
    "wellfound": "wellfound",
    "angellist": "wellfound",
    "glassdoor": "glassdoor",
    "glassdoorcoin": "glassdoor",
    "internshala": "internshala",
    "internshalacom": "internshala",
    "simplyhired": "simplyhired",
    "ziprecruiter": "ziprecruiter",
    "freshersworld": "freshersworld",
    "apna": "apna",
    "apnaco": "apna",
}


def publisher_slug(raw: Optional[str], fallback: str) -> str:
    """
    Reduce a publisher label or domain to a stable source id.

    Handles "LinkedIn", "linkedin.com", "Jobs via Indeed" and "www.naukri.com"
    alike. Falls back to the aggregator's own name when nothing was reported.
    """
    if not raw:
        return fallback

    cleaned = raw.lower()
    for noise in ("jobs via ", "via ", "https://", "http://"):
        cleaned = cleaned.replace(noise, "")
    cleaned = cleaned.split("/")[0].strip()

    # A domain is matched label by label, because the portals are reached
    # through country subdomains as often as bare ones — "in.indeed.com",
    # "in.linkedin.com", "foundit.in". Joining the whole thing first would
    # turn every one of those into its own unrecognised source.
    if "." in cleaned:
        for label in cleaned.split("."):
            slug = "".join(ch for ch in label if ch.isalnum())
            if slug in PUBLISHER_SLUGS:
                return PUBLISHER_SLUGS[slug]

    # Not a known domain: flatten to letters and digits, so "Monster India"
    # and "monsterindia" land on the same slug.
    flattened = "".join(ch for ch in cleaned if ch.isalnum())
    if not flattened:
        return fallback
    return PUBLISHER_SLUGS.get(flattened, flattened[:40])

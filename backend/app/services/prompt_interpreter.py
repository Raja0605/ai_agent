"""Turn a natural-language job prompt into search criteria.

Only fields the user actually stated are filled. Matching against a resume
happens later and does not add extra search filters.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.schemas.prompt_ai import InterpretedPrompt
from app.services.job_filter import extract_experience_range
from app.services.locations import CITY_ALIASES
from app.services.skill_extractor import extract_skills

_NOISE = re.compile(
    r"\b(find|search(?:ing)?|looking|show|get|want|need|please|for|me|my|"
    r"jobs?|roles?|positions?|openings?|vacancies|vacancy|with|that|have|"
    r"preferably|preferred|suitable|using|require(?:s|ing)?|required|"
    r"experience|years?|yrs?|posted|within|last|past|the|a|an|and|or|in|"
    r"across|from|to|at|on|of)\b",
    re.I,
)

_JOB_TYPES = (
    ("fulltime", re.compile(r"\bfull[\s-]?time\b", re.I)),
    ("parttime", re.compile(r"\bpart[\s-]?time\b", re.I)),
    ("contract", re.compile(r"\b(contract|contractor|freelance)\b", re.I)),
    ("internship", re.compile(r"\b(intern|internship)\b", re.I)),
)

_POSTED = (
    (24, re.compile(r"\b(last|past)\s+(24\s+hours|day)\b", re.I)),
    (72, re.compile(r"\b(last|past)\s+3\s+days\b", re.I)),
    (168, re.compile(r"\b(last|past)\s+(7\s+days|week)\b", re.I)),
    (720, re.compile(r"\b(last|past)\s+(30\s+days|month)\b", re.I)),
)

_SALARY = re.compile(r"(\d+(?:\.\d+)?)\s*(?:\+|plus)?\s*(lakh|lpa|lacs?)\b", re.I)
_TITLE = re.compile(
    r"(?:find|search(?:\s+for)?|looking for)?\s*(?:remote\s+|hybrid\s+)?(.+?)\s+jobs?\b",
    re.I,
)
_COMPANY = re.compile(r"\b(?:at|company)\s+([A-Z][\w.&-]*(?:\s+[A-Z][\w.&-]*){0,3})", re.I)


def interpret_prompt(prompt: str) -> InterpretedPrompt:
    text = " ".join((prompt or "").split())
    if not text:
        return InterpretedPrompt(prompt="")

    remote: Optional[bool] = True if re.search(r"\bremote\b", text, re.I) else None
    hybrid = bool(re.search(r"\bhybrid\b", text, re.I))
    if remote is None and re.search(r"\b(on[\s-]?site|office|wfo)\b", text, re.I):
        remote = False

    job_type = None
    for name, pattern in _JOB_TYPES:
        if pattern.search(text):
            job_type = name
            break

    hours_old = None
    posted_after = None
    for hours, pattern in _POSTED:
        if pattern.search(text):
            hours_old = hours
            posted_after = (datetime.now(timezone.utc) - timedelta(hours=hours)).date()
            break

    experience_min, experience_max = extract_experience_range(text)

    salary_min = None
    salary_match = _SALARY.search(text)
    if salary_match:
        salary_min = int(float(salary_match.group(1)) * 100_000)

    locations = _locations(text)
    country = "india" if re.search(r"\b(india|bharat)\b", text, re.I) else None

    skills = extract_skills(text, limit=15)
    keywords = _keywords(text, locations, skills)
    company_match = _COMPANY.search(text)
    company = company_match.group(1).strip() if company_match else None

    return InterpretedPrompt(
        prompt=text,
        keywords=keywords,
        skills=skills,
        locations=locations,
        country=country,
        remote=remote,
        hybrid=hybrid,
        experience_min=experience_min,
        experience_max=experience_max,
        salary_min=salary_min,
        job_type=job_type,
        hours_old=hours_old,
        posted_after=posted_after,
        company=company,
    )


def _locations(text: str) -> list[str]:
    lowered = text.lower()
    found: list[str] = []
    seen: set[str] = set()
    for canonical, aliases in CITY_ALIASES.items():
        for alias in sorted(aliases, key=len, reverse=True):
            if re.search(rf"\b{re.escape(alias)}\b", lowered):
                if canonical not in seen:
                    seen.add(canonical)
                    found.append(canonical.title() if canonical != "delhi" else "Delhi")
                    if canonical == "bengaluru":
                        found[-1] = "Bengaluru"
                    elif canonical == "gurugram":
                        found[-1] = "Gurugram"
                    else:
                        found[-1] = canonical.title()
                break
    return found


def _keywords(text: str, locations: list[str], skills: list[str]) -> list[str]:
    title = None
    match = _TITLE.search(text)
    if match:
        candidate = match.group(1).strip()
        if candidate and not re.fullmatch(r"(find|search|looking for)", candidate, re.I):
            title = candidate

    if title:
        cleaned = title
        for loc in locations:
            cleaned = re.sub(rf"\b{re.escape(loc)}\b", " ", cleaned, flags=re.I)
        for alias_set in CITY_ALIASES.values():
            for alias in alias_set:
                cleaned = re.sub(rf"\b{re.escape(alias)}\b", " ", cleaned, flags=re.I)
        cleaned = re.sub(r"\b(in|near|around|india|remote|hybrid)\b", " ", cleaned, flags=re.I)
        cleaned = " ".join(cleaned.split()).strip(" ,.-")
        if cleaned:
            return [cleaned]

    leftover = text
    leftover = _NOISE.sub(" ", leftover)
    for loc in locations:
        leftover = re.sub(rf"\b{re.escape(loc)}\b", " ", leftover, flags=re.I)
    leftover = re.sub(r"\b(india|remote|hybrid|kubernetes|docker|aws|terraform)\b", " ", leftover, flags=re.I)
    leftover = " ".join(leftover.split()).strip(" ,.-")
    if leftover:
        return [leftover]
    if skills:
        return skills[:3]
    return [text]

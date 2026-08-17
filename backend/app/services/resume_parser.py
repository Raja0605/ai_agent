"""
Resume parsing.

Skill extraction shares the job-side vocabulary in `skill_extractor`. It used
to keep a second, shorter list of its own that returned lowercase strings, so
a resume's "docker" and a job's "Docker" were different vocabularies being
compared against each other — and the browser held a *third* copy with a
different list again. One vocabulary, one casing, one place to change it.
"""

import re
from io import BytesIO

from pypdf import PdfReader

from app.services.skill_extractor import extract_skills

# A candidate's full toolkit is legitimately long, unlike a job ad's padded
# requirement list, so resumes are not held to the job-side cap.
MAX_RESUME_SKILLS = 40

# Roles recognised in resume text, in canonical casing.
KNOWN_ROLES = [
    "DevOps Engineer",
    "Site Reliability Engineer",
    "Platform Engineer",
    "Cloud Engineer",
    "Cloud Architect",
    "Backend Developer",
    "Frontend Developer",
    "Full Stack Developer",
    "Software Engineer",
    "Data Engineer",
    "Data Scientist",
    "Machine Learning Engineer",
    "QA Engineer",
    "Security Engineer",
]

# Skills that imply a role when the resume never names one outright.
ROLE_HINTS = [
    (("Kubernetes", "Docker", "Terraform"), ["DevOps Engineer", "Cloud Engineer"]),
    (("React", "TypeScript", "Vue", "Angular"), ["Frontend Developer"]),
    (("Spark", "Airflow", "dbt", "Snowflake"), ["Data Engineer"]),
    (("PyTorch", "TensorFlow", "Machine Learning"), ["Machine Learning Engineer"]),
]

_EXPERIENCE_PATTERNS = [
    re.compile(r"(\d{1,2})\s*\+?\s*years?\s+(?:of\s+)?experience", re.IGNORECASE),
    re.compile(r"experience\s*[:\-]?\s*(\d{1,2})\s*\+?\s*years?", re.IGNORECASE),
    re.compile(r"over\s+(\d{1,2})\s+years", re.IGNORECASE),
]


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from an uploaded PDF."""
    try:
        reader = PdfReader(BytesIO(file_bytes))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages)
    except Exception as exc:
        raise ValueError(f"Could not parse PDF: {exc}")


def _experience_years(text: str) -> int:
    """
    Years of experience stated in the text.

    Returns 0 when the resume never says. The previous version guessed "2
    years if any skills were found, otherwise 0", and the browser-side copy
    assigned everyone a flat 4 — both of which fed straight into the match
    score as though they were facts about the candidate.
    """
    for pattern in _EXPERIENCE_PATTERNS:
        match = pattern.search(text)
        if match:
            years = int(match.group(1))
            if 0 < years <= 50:
                return years
    return 0


def _target_roles(text: str, skills: list[str]) -> list[str]:
    lowered = text.lower()
    named = [role for role in KNOWN_ROLES if role.lower() in lowered]
    if named:
        return named

    skill_set = set(skills)
    for hints, roles in ROLE_HINTS:
        if skill_set & set(hints):
            return roles

    return ["Software Engineer"]


def parse_resume_text(raw_text: str) -> dict:
    """Extract skills, experience and target roles from resume text."""
    skills = extract_skills(raw_text, limit=MAX_RESUME_SKILLS)
    summary_source = raw_text.strip()
    summary = summary_source[:300] + ("…" if len(summary_source) > 300 else "")

    return {
        "raw_text": raw_text,
        "extracted_skills": skills,
        "experience_years": _experience_years(raw_text),
        "summary": summary,
        "target_roles": _target_roles(raw_text, skills),
    }

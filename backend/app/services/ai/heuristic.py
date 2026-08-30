"""Deterministic resume/job matching used across JobPulse.

This is the existing heuristic engine: no external model, no invented skills.
Prompt AI reuses these functions rather than scoring jobs a second way.
"""

from __future__ import annotations

import re
from typing import Iterable, List, Sequence

from app.schemas.ai import (
    AtsCheckRequest,
    AtsCheckResult,
    AtsIssue,
    JobMatchRequest,
    JobMatchResult,
    TailorResumeRequest,
    TailorResumeResult,
)
from app.services.job_filter import extract_experience_range
from app.services.role_matcher import role_relevance

# Short tokens that appear constantly in English prose. Matching them against
# resume text with a word boundary would claim "Go" from "I go to conferences".
_AMBIGUOUS_SKILLS = {"go", "c", "r", "ai", "js"}

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_PHONE = re.compile(r"\+?\d[\d\s().-]{7,}\d")
_WORD = re.compile(r"[a-z0-9]+")


def _tokens(value: str) -> set[str]:
    return set(_WORD.findall((value or "").lower()))


def _skill_in_list(job_skill: str, resume_skills: Sequence[str]) -> bool:
    wanted = _tokens(job_skill)
    if not wanted:
        return False
    job_lower = job_skill.strip().lower()
    for skill in resume_skills:
        if not skill:
            continue
        if job_lower == skill.strip().lower():
            return True
        have = _tokens(skill)
        if wanted <= have:
            return True
    return False


def _skill_in_text(skill: str, text: str) -> bool:
    if not text or not skill.strip():
        return False
    key = skill.strip()
    if len(key) <= 2 or key.lower() in _AMBIGUOUS_SKILLS:
        return False
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(key)}(?![a-z0-9])", text, re.I))


def _matches_skill(job_skill: str, resume_skills: Sequence[str], raw_text: str) -> bool:
    return _skill_in_list(job_skill, resume_skills) or _skill_in_text(job_skill, raw_text)


def _confidence(skill_count: int, coverage: float) -> str:
    if skill_count == 0:
        return "none"
    if skill_count <= 2:
        return "low"
    if skill_count <= 6:
        return "medium"
    return "high" if coverage > 0 else "low"


def heuristic_match(request: JobMatchRequest) -> JobMatchResult:
    resume = request.resume
    job_skills = [skill.strip() for skill in request.job_skills if skill and skill.strip()]
    resume_skills = resume.skills or []
    raw_text = resume.raw_text or ""

    matched: List[str] = []
    missing: List[str] = []
    for skill in job_skills:
        if _matches_skill(skill, resume_skills, raw_text):
            matched.append(skill)
        else:
            missing.append(skill)

    coverage = (len(matched) / len(job_skills)) if job_skills else 0.0
    title_rel = role_relevance(resume.target_role, request.job_title, job_skills, request.company)

    job_min = request.experience_min
    if job_min is None:
        job_min, _ = extract_experience_range(request.job_description or "")

    exp_penalty = 0
    years = resume.experience_years or 0
    if job_min is not None and years < job_min:
        exp_penalty = min(30, (job_min - years) * 4)

    score = int(round(coverage * 70 + title_rel * 25))
    score = max(0, min(100, score - exp_penalty))

    match_reasons: List[str] = [f"{skill} found in your resume" for skill in matched]
    if title_rel >= 0.7:
        match_reasons.append("Job title matches your target role")
    gaps = [f"{skill} requirement not found in resume" for skill in missing]
    if job_min is not None and years < job_min:
        gaps.append("Experience requirement is higher than the years on this resume")

    if not job_skills:
        summary = (
            "This job listing has no extractable skills, so the score rests on "
            "the title only and should be treated as weak evidence."
        )
    elif not matched:
        summary = "None of the listed requirements were found in the selected resume."
    else:
        summary = f"{len(matched)} of {len(job_skills)} listed skills appear in the resume."

    return JobMatchResult(
        job_id=request.job_id,
        score=score,
        matched_skills=matched,
        missing_skills=missing,
        summary=summary,
        reason=summary,
        recommendations=gaps,
        method="heuristic",
        confidence=_confidence(len(job_skills), coverage),
        match_reasons=match_reasons,
        gaps=gaps,
    )


def heuristic_ats_check(request: AtsCheckRequest) -> AtsCheckResult:
    resume = request.resume
    text = resume.raw_text or ""
    stripped = text.strip()
    word_count = len(stripped.split()) if stripped else 0
    issues: List[AtsIssue] = []
    detected: List[str] = []

    if word_count == 0:
        issues.append(
            AtsIssue(
                severity="critical",
                message="No text could be extracted from this resume.",
                fix="Upload a text-readable PDF or paste the resume text.",
            )
        )
        return AtsCheckResult(score=0, issues=issues, detected_sections=[], word_count=0)

    if _EMAIL.search(text) or _PHONE.search(text):
        detected.append("Contact")
    else:
        issues.append(
            AtsIssue(
                severity="critical",
                message="Missing contact details.",
                fix="Add an email address and phone number near the top of the resume.",
            )
        )

    for label, pattern in (
        ("Summary", r"\bsummary\b"),
        ("Skills", r"\bskills?\b"),
        ("Experience", r"\bexperience\b"),
        ("Education", r"\beducation\b"),
    ):
        if re.search(pattern, text, re.I):
            detected.append(label)

    score = 100
    if "Contact" not in detected:
        score -= 20
    if "Skills" not in detected:
        score -= 15
    if "Experience" not in detected:
        score -= 15
    if "Education" not in detected:
        score -= 10
    if word_count < 80:
        score -= 15
    score = max(0, min(100, score))

    return AtsCheckResult(
        score=score,
        issues=issues,
        detected_sections=detected,
        word_count=word_count,
    )


def _job_skill_matched(job_skill: str, resume_skills: Iterable[str]) -> bool:
    return _skill_in_list(job_skill, list(resume_skills))


def heuristic_tailor(request: TailorResumeRequest) -> TailorResumeResult:
    resume_skills = list(request.resume.skills or [])
    job_skills = [skill.strip() for skill in request.job_skills if skill and skill.strip()]

    prioritized: List[str] = []
    remaining = list(resume_skills)
    for job_skill in job_skills:
        for skill in list(remaining):
            if _skill_in_list(job_skill, [skill]) or skill.lower() == job_skill.lower():
                prioritized.append(skill)
                remaining.remove(skill)
    prioritized.extend(remaining)

    keywords_to_add = [
        skill for skill in job_skills if not _job_skill_matched(skill, resume_skills)
    ]

    return TailorResumeResult(
        prioritized_skills=prioritized,
        keywords_to_add=keywords_to_add,
        notes="Skills were reordered from the resume; nothing was invented.",
    )

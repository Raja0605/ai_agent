"""
Deterministic resume-to-job matcher.

This runs whenever no LLM credential is configured or the provider call fails,
so it is the scorer most deployments actually see. It was previously duplicated
verbatim in both providers and clamped its output to a minimum of 42, which —
combined with job skills never being persisted — made every job in the app
score exactly 42. Nothing here invents a floor: a job with no overlap scores
low, and a job we cannot assess at all says so via `confidence`.
"""

import re
from typing import List, Optional, Tuple

from app.schemas.ai import (
    AtsCheckRequest,
    AtsCheckResult,
    AtsIssue,
    CoverLetterRequest,
    CoverLetterResult,
    JobMatchRequest,
    MatchResult,
    TailorResumeRequest,
    TailorResumeResult,
)

# Component weights. Skill coverage dominates because it is the only signal
# with real evidence behind it; the others are corroborating.
W_SKILLS = 65
W_TITLE = 20
W_EXPERIENCE = 15

# Number of matched requirements that counts as full skill coverage.
#
# Straight matched/total punishes padded listings. Real Remotive data: a
# "Senior DevOps Engineer" description ended with the agency's boilerplate
# roster of every stack they hire for — "React & Python, React & Golang,
# Golang, React & Java, React & Ruby, PHP & Vue…" — so fifteen languages were
# extracted for one infrastructure role. A candidate matching the six that
# mattered scored barely half, because the denominator was full of stacks
# nobody was being asked for.
#
# Past roughly this many matched requirements, more matches say little extra,
# so coverage saturates here instead.
SATURATING_SKILL_COUNT = 6

_WORD = re.compile(r"[a-z0-9+#.]+")
_YEARS = re.compile(r"(\d{1,2})\s*\+?\s*(?:to\s*\d{1,2}\s*)?year", re.IGNORECASE)

# Title words that carry no matching signal.
_TITLE_STOPWORDS = {
    "senior", "junior", "lead", "staff", "principal", "sr", "jr",
    "engineer", "developer", "specialist", "consultant", "manager",
    "the", "and", "for", "with", "of", "a", "an", "remote", "hybrid",
    "i", "ii", "iii", "full", "time", "part", "contract",
}


def _tokens(text: str) -> set[str]:
    return {w for w in _WORD.findall((text or "").lower()) if len(w) > 1}


def _skill_tokens(skill: str) -> set[str]:
    return {t for t in _WORD.findall((skill or "").lower()) if t}


def _skill_equivalent(job_skill: str, resume_skill: str) -> bool:
    """
    Whether two skill names refer to the same thing.

    Token-subset rather than substring matching. Naive substring containment
    matched a job skill of "C" against a resume skill of "Docker", because
    "c" is a substring of "docker" — which then reported C as a matched
    requirement. Comparing whole tokens means "AWS" still matches "AWS EKS"
    while "C" no longer matches anything containing the letter c.
    """
    job_tokens = _skill_tokens(job_skill)
    resume_tokens = _skill_tokens(resume_skill)
    if not job_tokens or not resume_tokens:
        return False
    return job_tokens <= resume_tokens or resume_tokens <= job_tokens


# Below this length, a skill name is not searched for in free prose. Short
# names like "C", "R", "Go" and "ML" are also ordinary English words or
# letters, and word boundaries cannot tell the language "Go" from the verb
# "go". Such skills can still match, but only against an explicitly listed
# resume skill, where the intent is unambiguous.
MIN_PROSE_MATCH_LENGTH = 3


def _mentioned_in_text(skill: str, text: str) -> bool:
    """Whether a skill appears in the resume text as a whole word."""
    tokens = _skill_tokens(skill)
    if not tokens:
        return False
    if sum(len(token) for token in tokens) < MIN_PROSE_MATCH_LENGTH:
        return False
    return all(re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", text) for token in tokens)


def _skill_matches(job_skills: List[str], resume_skills: List[str], raw_text: str) -> Tuple[List[str], List[str]]:
    """
    Split job skills into matched and missing.

    A skill counts as matched if it lines up with a listed resume skill, or if
    it appears in the resume text — a technology proven by an experience bullet
    is real even when it never made the skills list.
    """
    text_lower = (raw_text or "").lower()

    matched: List[str] = []
    missing: List[str] = []

    for skill in job_skills:
        if not (skill or "").strip():
            continue
        found = any(_skill_equivalent(skill, rs) for rs in resume_skills if rs)
        if not found:
            found = _mentioned_in_text(skill, text_lower)
        (matched if found else missing).append(skill)

    return matched, missing


def _title_alignment(job_title: str, target_role: str) -> Optional[float]:
    """Jaccard-ish overlap of meaningful title words. None if unassessable."""
    job_words = _tokens(job_title) - _TITLE_STOPWORDS
    role_words = _tokens(target_role) - _TITLE_STOPWORDS

    if not job_words or not role_words:
        return None

    overlap = job_words & role_words
    return len(overlap) / len(job_words)


def _required_years(description: str) -> Optional[int]:
    """Lowest year figure mentioned near 'year(s)' in the description."""
    candidates = [int(m) for m in _YEARS.findall(description or "") if int(m) <= 25]
    return min(candidates) if candidates else None


def _experience_fit(description: str, candidate_years: int) -> Optional[float]:
    """
    1.0 when the candidate meets the stated requirement, scaling down when
    they fall short. None when the posting never states a requirement — in
    which case this component is dropped rather than guessed at.
    """
    required = _required_years(description)
    if required is None:
        return None
    if required == 0:
        return 1.0
    return min(1.0, candidate_years / required)


def heuristic_match(request: JobMatchRequest, note: str = "") -> MatchResult:
    """Score a resume against a job without calling any model."""
    matched, missing = _skill_matches(
        request.job_skills, request.resume.skills, request.resume.raw_text or ""
    )

    # (label, 0..1 value, weight) — labels are carried through so the
    # explanation below describes exactly the components that were used.
    components: List[Tuple[str, float, int]] = []
    caveats: List[str] = []

    total_skills = len(request.job_skills)
    if total_skills:
        # Denominator saturates so a padded requirement list cannot drag a
        # genuinely strong match down. See SATURATING_SKILL_COUNT.
        denominator = min(total_skills, SATURATING_SKILL_COUNT)
        coverage = min(1.0, len(matched) / denominator)
        components.append(("skill coverage", coverage, W_SKILLS))
    else:
        # No skills on the job means the strongest signal is unavailable. Say
        # so instead of silently scoring on the remaining weak signals.
        caveats.append("this posting lists no extractable skills")

    title_fit = _title_alignment(request.job_title, request.resume.target_role)
    if title_fit is not None:
        components.append(("title alignment", title_fit, W_TITLE))

    exp_fit = _experience_fit(request.job_description, request.resume.experience_years)
    if exp_fit is not None:
        components.append(("experience fit", exp_fit, W_EXPERIENCE))
    else:
        caveats.append("the posting does not state a years-of-experience requirement")

    if not components:
        return MatchResult(
            score=0,
            matched_skills=[],
            missing_skills=[],
            summary="Not enough information in this posting to assess a match.",
            recommendations=["Open the original listing to review the requirements manually."],
            reason="No skills, comparable title, or experience requirement could be extracted.",
            method="heuristic",
            confidence="none",
        )

    weight_total = sum(weight for _, _, weight in components)
    score = round(sum(value * weight for _, value, weight in components) / weight_total * 100)
    score = max(0, min(100, score))

    # Confidence reflects how much evidence the score rests on, which is a
    # separate question from how high the score is.
    if total_skills >= 5:
        confidence = "high"
    elif total_skills >= 1:
        confidence = "medium"
    else:
        confidence = "low"

    if total_skills:
        summary = f"{len(matched)} of {total_skills} listed requirements matched."
    else:
        summary = "Scored on title and experience alignment only."

    if caveats:
        summary += " Note: " + "; ".join(caveats) + "."

    recommendations: List[str] = []
    if missing:
        recommendations.append(
            "Surface these on your resume if you have them: " + ", ".join(missing[:4])
        )
    if exp_fit is not None and exp_fit < 1.0:
        required = _required_years(request.job_description)
        recommendations.append(
            f"The posting asks for around {required} years; your profile lists "
            f"{request.resume.experience_years}."
        )
    if not recommendations:
        recommendations.append("Strong alignment — apply with your current resume.")

    reason = "Deterministic scoring: " + ", ".join(
        f"{label} {value:.0%} (weight {weight})" for label, value, weight in components
    ) + "."
    if note:
        reason = f"{note} {reason}"

    return MatchResult(
        score=score,
        matched_skills=matched,
        missing_skills=missing,
        summary=summary,
        recommendations=recommendations,
        reason=reason,
        method="heuristic",
        confidence=confidence,
    )


def heuristic_tailor(request: TailorResumeRequest) -> TailorResumeResult:
    """
    Deterministic tailoring: reorder what the candidate already has by
    relevance to the posting, and name the posting's terms they have not
    written down. It never fabricates experience — it only reprioritises.
    """
    job_terms = {s.lower(): s for s in request.job_skills}
    description_lower = (request.job_description or "").lower()

    relevant: List[str] = []
    rest: List[str] = []
    for skill in request.resume.skills:
        needle = skill.lower()
        if any(needle in jt or jt in needle for jt in job_terms) or needle in description_lower:
            relevant.append(skill)
        else:
            rest.append(skill)

    resume_lower = [s.lower() for s in request.resume.skills]
    raw_lower = (request.resume.raw_text or "").lower()
    keywords_to_add = [
        original
        for lowered, original in job_terms.items()
        if not any(lowered in rs or rs in lowered for rs in resume_lower)
        and lowered not in raw_lower
    ]

    if relevant:
        lead = ", ".join(relevant[:5])
        tailored = (
            f"{request.resume.target_role} with {request.resume.experience_years} years of "
            f"experience, focused on {lead}. Seeking the {request.job_title} role at "
            f"{request.company}, where this background maps directly onto the stated requirements."
        )
    else:
        tailored = request.resume.summary

    bullets = [
        f"Applied {skill} in production work relevant to {request.job_title}."
        for skill in relevant[:3]
    ]

    return TailorResumeResult(
        tailored_summary=tailored,
        prioritized_skills=relevant + rest,
        keywords_to_add=keywords_to_add[:8],
        bullet_suggestions=bullets,
        method="heuristic",
    )


# Section headings an ATS parser looks for, and the words that signal each.
_ATS_SECTIONS = {
    "Contact": ("email", "@", "phone"),
    "Summary": ("summary", "objective", "profile", "about"),
    "Skills": ("skills", "technologies", "technical"),
    "Experience": ("experience", "employment", "work history"),
    "Education": ("education", "degree", "university", "b.tech", "bachelor"),
}

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_PHONE = re.compile(r"(\+?\d[\d\s().-]{7,}\d)")


def heuristic_ats_check(request: AtsCheckRequest) -> AtsCheckResult:
    """
    Structural parseability check.

    LoopCV calls a resume that an ATS cannot parse "the silent killer of most
    applications", and whether a document has a Skills heading or a findable
    email address is a mechanical fact — no model needed.
    """
    text = request.resume.raw_text or request.resume.summary or ""
    lowered = text.lower()
    words = text.split()
    word_count = len(words)

    detected = [
        section
        for section, markers in _ATS_SECTIONS.items()
        if any(marker in lowered for marker in markers)
    ]

    issues: List[AtsIssue] = []

    for section in _ATS_SECTIONS:
        if section not in detected:
            issues.append(
                AtsIssue(
                    severity="critical" if section in ("Contact", "Experience", "Skills") else "warning",
                    message=f"No {section} section was detected.",
                    fix=f"Add a clearly labelled '{section}' heading — parsers key off literal headings.",
                )
            )

    if not _EMAIL.search(text):
        issues.append(
            AtsIssue(
                severity="critical",
                message="No email address could be extracted.",
                fix="Put a plain-text email in the document body, not in a header, footer or image.",
            )
        )
    if not _PHONE.search(text):
        issues.append(
            AtsIssue(
                severity="warning",
                message="No phone number could be extracted.",
                fix="Add a plain-text phone number near your email.",
            )
        )

    if word_count == 0:
        issues.append(
            AtsIssue(
                severity="critical",
                message="No text could be extracted from this resume at all.",
                fix="The file is likely a scan or image-only PDF. Export a text-based PDF instead.",
            )
        )
    elif word_count < 200:
        issues.append(
            AtsIssue(
                severity="warning",
                message=f"Only {word_count} words were extracted, which is unusually short.",
                fix="Either the resume is thin or the PDF's text layer is partial — check the extraction.",
            )
        )
    elif word_count > 1200:
        issues.append(
            AtsIssue(
                severity="info",
                message=f"{word_count} words is long for a resume.",
                fix="Trim toward two pages; reviewers rarely read past that.",
            )
        )

    if len(request.resume.skills) < 5:
        issues.append(
            AtsIssue(
                severity="warning",
                message=f"Only {len(request.resume.skills)} skills were extracted.",
                fix="List your technologies explicitly in a Skills section so keyword filters can find them.",
            )
        )

    penalty = sum({"critical": 20, "warning": 8, "info": 2}[issue.severity] for issue in issues)
    score = max(0, 100 - penalty)

    return AtsCheckResult(
        score=score,
        issues=issues,
        detected_sections=detected,
        word_count=word_count,
        method="heuristic",
    )


def heuristic_cover_letter(request: CoverLetterRequest, note: str = "") -> CoverLetterResult:
    """Template cover note used when no model is available."""
    skills = ", ".join(request.resume.skills[:4]) or "my background"
    content = (
        f"Dear Hiring Manager at {request.company},\n\n"
        f"I am writing to express my interest in the {request.job_title} role. "
        f"With my experience in {skills}, I believe I can contribute meaningfully "
        f"to your team.\n\n"
        f"I would welcome the chance to discuss how my background aligns with what "
        f"you are looking for.\n\n"
        f"Best regards,\n{request.resume.full_name}"
    )
    return CoverLetterResult(content=content, method="template", note=note or None)

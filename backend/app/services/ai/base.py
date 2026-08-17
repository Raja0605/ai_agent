"""
LLM provider contract and the shared logic layered on top of it.

Gemini and OpenAI previously carried byte-identical prompt construction,
response parsing, heuristic fallbacks and cover-letter templates — roughly 90%
of each file. The only genuine difference is how a prompt is sent and where the
text sits in the response, so that is all a concrete provider implements now.
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, List, Optional

from app.schemas.ai import (
    AtsCheckRequest,
    AtsCheckResult,
    CoverLetterRequest,
    CoverLetterResult,
    JobMatchRequest,
    MatchResult,
    TailorResumeRequest,
    TailorResumeResult,
)
from app.services.ai.heuristic import (
    heuristic_ats_check,
    heuristic_cover_letter,
    heuristic_match,
    heuristic_tailor,
)

logger = logging.getLogger("jobpulse.ai")

_DECODER = json.JSONDecoder()


def _extract_json(raw: str, provider: str) -> Optional[dict[str, Any]]:
    """
    Pull the first complete JSON object out of a model response.

    Models wrap JSON in prose or code fences despite instructions, and some
    emit more than one object. A greedy `\\{[\\s\\S]*\\}` match spanning the
    first brace to the last then fails with "Extra data", which is what
    happened once a thinking model started returning commentary alongside the
    answer. Scanning brace-by-brace with raw_decode takes the first object
    that actually parses and ignores whatever follows.
    """
    for index, char in enumerate(raw):
        if char != "{":
            continue
        try:
            parsed, _ = _DECODER.raw_decode(raw[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed

    logger.warning("[%s] Response contained no parsable JSON object.", provider)
    return None


class LLMProvider(ABC):
    """Transport-level contract. One method per provider."""

    name: str   # human-readable provider name, surfaced in fallback messages
    model: str  # the model id actually being called

    @abstractmethod
    async def complete(self, prompt: str, json_mode: bool = False) -> Optional[str]:
        """
        Send a prompt and return the model's raw text, or None if the provider
        is unconfigured or the call failed. Implementations must not raise.
        """

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """True when a usable credential is present."""


class BaseAIService(LLMProvider):
    """
    Provider-agnostic behaviour: prompt text, JSON extraction, and the
    deterministic fallback taken whenever the model is unavailable or returns
    something unusable. Every fallback is labelled in the result so the UI can
    never present a keyword heuristic as an AI judgement.
    """

    async def _json_call(self, prompt: str) -> Optional[dict[str, Any]]:
        if not self.is_configured:
            return None

        raw = await self.complete(prompt, json_mode=True)
        if not raw:
            return None

        return _extract_json(raw, self.name)

    # ------------------------------------------------------------------ match

    async def match_job(self, request: JobMatchRequest) -> MatchResult:
        if not self.is_configured:
            return heuristic_match(request, note="No AI credential configured.")

        prompt = f"""You are an experienced technical recruiter screening a candidate.

TARGET JOB: {request.job_title} at {request.company}
LISTED SKILLS: {', '.join(request.job_skills) or '(none listed)'}
JOB DESCRIPTION:
{request.job_description[:4000]}

CANDIDATE: {request.resume.full_name} — {request.resume.target_role}
CANDIDATE SKILLS: {', '.join(request.resume.skills)}
YEARS OF EXPERIENCE: {request.resume.experience_years}
RESUME SUMMARY: {request.resume.summary}

Score this match honestly. A weak match must receive a low score — do not
inflate. Use the full 0-100 range.

Return ONLY a JSON object, no markdown:
{{
  "score": <integer 0-100>,
  "matched_skills": ["..."],
  "missing_skills": ["..."],
  "summary": "<one sentence>",
  "recommendations": ["..."],
  "reason": "<why this score>",
  "confidence": "high" | "medium" | "low"
}}"""

        parsed = await self._json_call(prompt)
        if parsed is None:
            return heuristic_match(request, note=f"{self.name} unavailable; scored locally.")

        try:
            score = int(parsed["score"])
        except (KeyError, TypeError, ValueError):
            return heuristic_match(request, note=f"{self.name} returned no usable score.")

        confidence = parsed.get("confidence")
        if confidence not in ("high", "medium", "low", "none"):
            confidence = "medium"

        return MatchResult(
            score=max(0, min(100, score)),
            matched_skills=_str_list(parsed.get("matched_skills")),
            missing_skills=_str_list(parsed.get("missing_skills")),
            summary=str(parsed.get("summary") or "Evaluation complete."),
            recommendations=_str_list(parsed.get("recommendations")),
            reason=str(parsed.get("reason") or ""),
            method="ai",
            confidence=confidence,
        )

    # ----------------------------------------------------------- cover letter

    async def generate_cover_letter(self, request: CoverLetterRequest) -> CoverLetterResult:
        if not self.is_configured:
            return heuristic_cover_letter(request, note="No AI credential configured.")

        prompt = f"""Write a concise three-paragraph cover note for a job application.
Be specific and factual — use only what the candidate profile below supports.
Do not invent employers, dates, or achievements. No placeholders or brackets.

Candidate: {request.resume.full_name}
Target role: {request.job_title} at {request.company}
Candidate skills: {', '.join(request.resume.skills)}
Years of experience: {request.resume.experience_years}
Candidate summary: {request.resume.summary}
Role requirements: {', '.join(request.job_skills) or '(not listed)'}

Return the letter text only."""

        text = await self.complete(prompt) if self.is_configured else None
        if not text:
            return heuristic_cover_letter(request, note=f"{self.name} unavailable; used a template.")

        return CoverLetterResult(content=text.strip(), method="ai")

    # ----------------------------------------------------------------- tailor

    async def tailor_resume(self, request: TailorResumeRequest) -> TailorResumeResult:
        if not self.is_configured:
            return heuristic_tailor(request)

        prompt = f"""You are helping a candidate tailor an existing resume to one job.
You may reorder, re-emphasise and rephrase what the candidate already has.
You must NOT invent skills, employers or experience they have not claimed.

TARGET: {request.job_title} at {request.company}
ROLE REQUIREMENTS: {', '.join(request.job_skills) or '(not listed)'}
JOB DESCRIPTION:
{request.job_description[:3000]}

CANDIDATE SUMMARY: {request.resume.summary}
CANDIDATE SKILLS: {', '.join(request.resume.skills)}
YEARS: {request.resume.experience_years}

Return ONLY JSON:
{{
  "tailored_summary": "<2-3 sentence summary rewritten for this role>",
  "prioritized_skills": ["<candidate's own skills, most relevant first>"],
  "keywords_to_add": ["<terms from the posting the candidate plausibly has but has not written down>"],
  "bullet_suggestions": ["<2-4 resume bullets rephrasing existing experience toward this role>"]
}}"""

        parsed = await self._json_call(prompt)
        if parsed is None:
            return heuristic_tailor(request)

        return TailorResumeResult(
            tailored_summary=str(parsed.get("tailored_summary") or request.resume.summary),
            prioritized_skills=_str_list(parsed.get("prioritized_skills")) or request.resume.skills,
            keywords_to_add=_str_list(parsed.get("keywords_to_add")),
            bullet_suggestions=_str_list(parsed.get("bullet_suggestions")),
            method="ai",
        )

    # -------------------------------------------------------------- ats check

    async def check_ats(self, request: AtsCheckRequest) -> AtsCheckResult:
        # Structural parseability is a mechanical property of the document, so
        # the deterministic check is the authoritative one here. The model is
        # not a better judge of whether a "Skills" heading exists.
        return heuristic_ats_check(request)


def _str_list(value: Any) -> List[str]:
    """Coerce a model's list field into clean strings, dropping junk."""
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]

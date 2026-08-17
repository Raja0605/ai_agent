"""
Regression tests for the match scorer.

The bug these exist to prevent: job skills were never persisted, so every
match request arrived with an empty `job_skills`, the coverage ratio was 0,
and a `max(42, ...)` clamp turned that into a constant score of 42 for every
job in the product. Both halves are covered here — the scorer must not have a
floor, and it must react to its inputs.
"""

import pytest

from app.schemas.ai import JobMatchRequest, ResumeProfile
from app.services.ai.heuristic import heuristic_match

DEVOPS_RESUME = ResumeProfile(
    full_name="Test Candidate",
    target_role="DevOps Engineer",
    summary="Cloud infrastructure and CI/CD automation.",
    skills=["Docker", "Kubernetes", "Terraform", "AWS", "Python", "Jenkins"],
    experience_years=5,
    raw_text="Built CI/CD pipelines with Jenkins, deployed to AWS EKS using Terraform.",
)


def _request(title: str, skills: list[str], description: str = "") -> JobMatchRequest:
    return JobMatchRequest(
        job_id="job-1",
        job_title=title,
        job_description=description,
        job_skills=skills,
        company="Test Corp",
        resume=DEVOPS_RESUME,
    )


def test_perfect_overlap_scores_high():
    result = heuristic_match(
        _request("DevOps Engineer", ["Docker", "Kubernetes", "Terraform", "AWS"])
    )
    assert result.score >= 85
    assert result.missing_skills == []
    assert result.confidence == "medium"  # 4 skills -> medium evidence


def test_no_overlap_scores_low_and_is_not_floored_at_42():
    """The old clamp made this impossible to observe."""
    result = heuristic_match(
        _request("Pastry Chef", ["Baking", "Cake Decorating", "Food Safety", "Pastry"])
    )
    assert result.score < 42, f"expected a low score, got {result.score}"
    assert result.matched_skills == []


def test_scores_differ_across_jobs():
    """The headline symptom: every job scoring identically."""
    strong = heuristic_match(_request("DevOps Engineer", ["Docker", "Kubernetes", "AWS"]))
    partial = heuristic_match(_request("Backend Engineer", ["Docker", "Ruby", "Rails"]))
    weak = heuristic_match(_request("Sales Manager", ["Salesforce", "Cold Calling"]))

    scores = {strong.score, partial.score, weak.score}
    assert len(scores) == 3, f"scores collapsed to {scores}"
    assert strong.score > partial.score > weak.score


def test_empty_skill_list_is_reported_not_faked():
    """
    A job with no extractable skills must not silently produce a confident
    number — that is precisely what the 42 bug did.
    """
    result = heuristic_match(_request("Some Role", []))
    assert result.confidence in ("low", "none")
    assert "no extractable skills" in result.summary.lower()


def test_experience_shortfall_reduces_score():
    senior = _request(
        "DevOps Engineer",
        ["Docker", "Kubernetes"],
        description="We require 12 years of experience in platform engineering.",
    )
    junior = _request(
        "DevOps Engineer",
        ["Docker", "Kubernetes"],
        description="We require 2 years of experience in platform engineering.",
    )
    assert heuristic_match(senior).score < heuristic_match(junior).score


def test_score_stays_in_range():
    for skills in ([], ["Docker"], ["Docker"] * 20, ["Nonexistent"] * 5):
        result = heuristic_match(_request("Engineer", skills))
        assert 0 <= result.score <= 100


def test_skills_found_only_in_raw_text_still_match():
    """A skill proven by an experience bullet counts even if not listed."""
    result = heuristic_match(_request("SRE", ["EKS"]))
    assert "EKS" in result.matched_skills


def test_single_letter_skills_do_not_match_by_substring():
    """
    Found in live data: a job listing "C" was reported as matched because the
    old check asked whether "c" was a substring of "Docker".
    """
    result = heuristic_match(_request("Embedded Engineer", ["C"]))
    assert "C" not in result.matched_skills
    assert "C" in result.missing_skills


def test_short_skill_names_do_not_match_prose_fragments():
    """'Go' must not match on 'Golang'-free prose that merely contains 'go'."""
    resume = DEVOPS_RESUME.model_copy(
        update={"raw_text": "I go to conferences and organise team goals."}
    )
    request = JobMatchRequest(
        job_id="job-1", job_title="Backend Engineer", job_description="",
        job_skills=["Go"], company="Test Corp", resume=resume,
    )
    assert "Go" in heuristic_match(request).missing_skills


def test_multi_word_skill_matches_a_broader_resume_skill():
    """Token-subset matching must still let 'AWS' match 'AWS EKS'."""
    resume = DEVOPS_RESUME.model_copy(update={"skills": ["AWS EKS"], "raw_text": ""})
    request = JobMatchRequest(
        job_id="job-1", job_title="SRE", job_description="",
        job_skills=["AWS"], company="Test Corp", resume=resume,
    )
    assert "AWS" in heuristic_match(request).matched_skills

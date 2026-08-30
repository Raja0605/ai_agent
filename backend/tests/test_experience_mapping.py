import pytest

from app.experience.linkedin import LinkedInExperienceMapper
from app.experience.naukri import NaukriExperienceMapper
from app.services.job_filter import extract_experience_range


@pytest.mark.parametrize("text,expected", [
    ("1 year experience", (1, None)), ("1+ years", (1, None)),
    ("1-3 years", (1, 3)), ("3 to 5 years", (3, 5)),
    ("minimum 3 years", (3, None)), ("at least 5 years", (5, None)),
    ("5 years of experience", (5, None)),
])
def test_experience_extraction(text, expected):
    assert extract_experience_range(text) == expected


def test_linkedin_sends_only_a_schema_supported_level():
    mapper = LinkedInExperienceMapper()
    schema = {"properties": {"experience_level": {"enum": ["Entry-level", "Director"]}}}
    assert mapper.map(1, 1, schema) == {"experience_level": "Entry-level"}
    assert mapper.map(4, 5, schema) == {}


def test_linkedin_uses_values_explicitly_documented_by_an_mcp_schema():
    schema = {"properties": {"experience_level": {
        "description": "Filter by experience level (internship, entry, associate, mid_senior, director, executive)"
    }}}
    assert LinkedInExperienceMapper().map(1, 1, schema) == {"experience_level": "entry"}


def test_numeric_portal_uses_only_declared_fields():
    mapper = NaukriExperienceMapper()
    assert mapper.map(3, 5, {"properties": {"experience_min": {}, "experience_max": {}}}) == {
        "experience_min": 3, "experience_max": 5
    }
    assert mapper.map(3, 5, {"properties": {}}) == {}

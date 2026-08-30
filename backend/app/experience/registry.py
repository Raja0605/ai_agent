from .adzuna import AdzunaExperienceMapper
from .base import ExperienceMapper
from .generic import NumericExperienceMapper
from .indeed import IndeedExperienceMapper
from .linkedin import LinkedInExperienceMapper
from .naukri import NaukriExperienceMapper
from .remotive import RemotiveExperienceMapper


_MAPPERS: dict[str, ExperienceMapper] = {
    "linkedin": LinkedInExperienceMapper(), "naukri": NaukriExperienceMapper(),
    "indeed": IndeedExperienceMapper(), "remotive": RemotiveExperienceMapper(), "adzuna": AdzunaExperienceMapper(),
}


def mapper_for(source: str, source_schema: dict | None = None) -> ExperienceMapper:
    key = source.lower()
    if key in _MAPPERS:
        return _MAPPERS[key]
    # Server display names are user-configurable (for example "test-mcp").
    # Identify the LinkedIn mapper from its discovered job-tool schema, not a
    # naming convention, when it publishes LinkedIn's documented levels.
    properties = (source_schema or {}).get("properties", {})
    experience = properties.get("experience_level", {})
    if "linkedin" in str(experience.get("description", "")).lower() or "mid_senior" in str(experience).lower():
        return _MAPPERS["linkedin"]
    return NumericExperienceMapper()

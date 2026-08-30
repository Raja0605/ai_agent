from typing import Any, Mapping, Optional

from .base import ExperienceMapper


class LinkedInExperienceMapper(ExperienceMapper):
    """LinkedIn levels are sent only if discovered verbatim in a tool schema."""

    _bands = ((1, "entry"), (3, "associate"), (7, "mid_senior"), (10, "director"), (float("inf"), "executive"))

    def map(self, experience_min: Optional[int], experience_max: Optional[int], source_schema: Mapping[str, Any]) -> dict[str, Any]:
        properties = source_schema.get("properties", source_schema)
        field = next((name for name in ("experience_level", "experience", "seniority") if name in properties), None)
        if field is None or experience_min is None:
            return {}
        definition = properties.get(field) or {}
        allowed = definition.get("enum", [])
        # Some MCPs document allowed values in prose instead of JSON Schema
        # enum. This LinkedIn tool explicitly lists the values in its field
        # description, so extracting those documented tokens is not a guess.
        description = str(definition.get("description", "")).lower()
        documented = ("internship", "entry", "associate", "mid_senior", "director", "executive")
        if not allowed and "experience level" in description:
            allowed = [value for value in documented if value in description]
        if not allowed:
            return {}
        candidate = next(level for limit, level in self._bands if experience_min <= limit)
        aliases = {
            "entry": ("entry", "Entry-level"), "associate": ("associate", "Associate"),
            "mid_senior": ("mid_senior", "Mid-Senior level"), "director": ("director", "Director"),
            "executive": ("executive", "Executive"),
        }
        value = next((option for option in aliases[candidate] if option in allowed), None)
        return {field: value} if value is not None else {}

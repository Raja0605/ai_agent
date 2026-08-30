from typing import Any, Mapping, Optional

from .base import ExperienceMapper


class NumericExperienceMapper(ExperienceMapper):
    """Use numeric fields only when tool/API schema explicitly declares them."""

    def map(self, experience_min: Optional[int], experience_max: Optional[int], source_schema: Mapping[str, Any]) -> dict[str, Any]:
        properties = source_schema.get("properties", source_schema)
        mapped: dict[str, Any] = {}
        if "experience_min" in properties and experience_min is not None:
            mapped["experience_min"] = experience_min
        if "experience_max" in properties and experience_max is not None:
            mapped["experience_max"] = experience_max
        elif "min_experience" in properties and experience_min is not None:
            mapped["min_experience"] = experience_min
        return mapped

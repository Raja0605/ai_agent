from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class ExperienceRange:
    """The only experience representation shared between frontend and API."""

    minimum: Optional[int] = None
    maximum: Optional[int] = None


class ExperienceMapper(ABC):
    """Maps a normalized range only to parameters advertised by a source."""

    @abstractmethod
    def map(
        self, experience_min: Optional[int], experience_max: Optional[int], source_schema: Mapping[str, Any]
    ) -> dict[str, Any]:
        raise NotImplementedError

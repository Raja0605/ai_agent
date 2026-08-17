from abc import ABC, abstractmethod
from typing import List, Optional

from app.schemas.job import NormalizedJob


class JobSource(ABC):
    source_name: str

    #: Whether `location` is worth passing to this source.
    #:
    #: True for sources whose endpoint accepts a place and filters server-side.
    #: False for sources that fetch a fixed list and are filtered afterwards —
    #: asking those the same question once per city just refetches one list
    #: several times. `SourceManager` uses this to plan the fan-out.
    uses_location_param: bool = True

    @abstractmethod
    async def search(
        self,
        keyword: str,
        location: Optional[str] = None,
        remote: bool = False,
        page: int = 1
    ) -> List[NormalizedJob]:
        """
        Search this source and return NormalizedJob objects.

        Filter server-side where the endpoint supports it, but do not try to
        be the final authority on whether a posting matches: that decision
        belongs to `app.services.job_filter`, which applies the same rules to
        every source. Returning a few extra postings is fine; inventing a
        private definition of "matches" is what made results inconsistent
        between sources.
        """
        pass

from abc import ABC, abstractmethod
from typing import List, Any, Optional

class JobSource(ABC):
    """Abstract base class for all job source adapters.

    Providers are isolated: a failure is reported by the manager and never
    blocks results from the other sources.
    """

    @abstractmethod
    async def search_jobs(self, keywords: List[str], location: Optional[str] = None,
                          filters: Optional[dict] = None) -> List[Any]:
        """Fetch jobs based on the given criteria.

        Args:
            criteria: Search parameters (keywords, locations, remote flag, etc.)
        Returns:
            List of job representations.
        """
        raise NotImplementedError

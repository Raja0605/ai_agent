from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "JobPulse API"
    DATABASE_URL: str = "postgresql+asyncpg://jobpulse:jobpulse_pass@localhost:5432/jobpulse"
    # Log every SQL statement. Debugging aid only — leave off in normal use.
    SQL_ECHO: bool = False

    # Comma-separated list of allowed browser origins.
    # Never widen this to "*" while allow_credentials is enabled.
    CORS_ORIGINS: str = "http://localhost:8080,http://localhost:5173"

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    INDEED_ENABLED: bool = False
    INDEED_API_KEY: Optional[str] = None
    NAUKRI_ENABLED: bool = False
    NAUKRI_API_KEY: Optional[str] = None
    LINKEDIN_ENABLED: bool = False
    LINKEDIN_API_KEY: Optional[str] = None
    REMOTIVE_ENABLED: bool = True
    ADZUNA_ENABLED: bool = True
    ADZUNA_APP_ID: Optional[str] = None
    ADZUNA_APP_KEY: Optional[str] = None

    # ── Market scope ──────────────────────────────────────────────────
    # Restrict results to postings reachable from India. The Indian market is
    # what this app is for, and the remote-first and global sources otherwise
    # bury local results under US and EU postings. Turn off to search
    # worldwide.
    INDIA_ONLY: bool = True

    # ── Portal aggregators ────────────────────────────────────────────
    # Naukri, Indeed and LinkedIn cannot be queried directly — Naukri has no
    # public API, Indeed retired its Publisher API and XML feed, and LinkedIn
    # gates job data behind Talent Solutions partnership. All three syndicate
    # into Google for Jobs, which licensed aggregators index and resell, so
    # these keys are the supported route to that inventory. Each posting keeps
    # the name of the portal it came from, so results still show as Naukri,
    # LinkedIn or Indeed rather than as one opaque aggregator.

    # ── Approved company career boards ─────────────────────────────────
    # Public ATS endpoints, as `platform:company-slug`. No credentials are
    # needed: these are the same URLs each company's own careers page calls.
    #
    # This is the main India source. Naukri, Indeed, LinkedIn and Foundit have
    # no usable public API and prohibit scraping, whereas most Indian product
    # companies run hiring on Greenhouse, Lever or Ashby.
    #
    # A slug that 404s is skipped with a warning, so a stale entry degrades to
    # "one fewer employer" rather than breaking the search.
    ATS_BOARDS: str = ",".join([
        "greenhouse:phonepe",
        "greenhouse:razorpaysoftwareprivatelimited",
        "greenhouse:groww",
        "greenhouse:netradyne",
        "greenhouse:druva",
        "greenhouse:postman",
        "greenhouse:zetaindia",
        "greenhouse:browserstack",
        "greenhouse:innovaccer",
        "greenhouse:sprinklr",
        "greenhouse:mindtickle",
        "greenhouse:clevertap",
        "greenhouse:whatfix",
        "greenhouse:icertis",
        "greenhouse:gupshup",
        "greenhouse:chargebee",
        "greenhouse:hasura",
        "greenhouse:freshworks",
        "lever:meesho",
        "lever:cred",
        "lever:porter",
        "ashby:atlan",
    ])

    @property
    def ats_board_list(self) -> List[str]:
        return [entry.strip() for entry in self.ATS_BOARDS.split(",") if entry.strip()]
    # Adzuna is country-scoped: the country decides both the endpoint and the
    # currency of the salary figures it returns. Was hardcoded to India.
    ADZUNA_COUNTRY: str = "in"
    JOBSPY_ENABLED: bool = True
    JOBSPY_HOST: str = "jobspy_mcp"
    JOBSPY_PORT: int = 8500
    JOBSPY_TIMEOUT_SECONDS: int = 90
    JOBSPY_SITE_TIMEOUT_SECONDS: int = 60

    class Config:
        env_file = ".env"

settings = Settings()

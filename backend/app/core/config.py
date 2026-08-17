from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "JobPulse Auto Apply API"
    DATABASE_URL: str = "postgresql+asyncpg://jobpulse:jobpulse_pass@localhost:5432/jobpulse"
    # Log every SQL statement. Debugging aid only — leave off in normal use.
    SQL_ECHO: bool = False

    # Comma-separated list of allowed browser origins.
    # Never widen this to "*" while allow_credentials is enabled.
    CORS_ORIGINS: str = "http://localhost:8080,http://localhost:5173"

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    LLM_PROVIDER: str = "google"
    GOOGLE_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    # Model ids go stale. The previous default, gemini-1.5-pro-preview-0409,
    # had been retired and returned 404 for every request — the provider then
    # fell back to the keyword scorer, correctly labelled but silently less
    # useful than the configured key implied. Check the current list with:
    #   curl -H "x-goog-api-key: $GOOGLE_API_KEY" \
    #        https://generativelanguage.googleapis.com/v1beta/models
    GEMINI_MODEL: str = "gemini-3.1-pro-preview"
    OPENAI_MODEL: str = "gpt-4-turbo"

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

    # JSearch (RapidAPI by default) — Google for Jobs coverage.
    JSEARCH_API_KEY: Optional[str] = None
    JSEARCH_API_HOST: str = "jsearch.p.rapidapi.com"
    # Configurable because the path has already moved once: the documented
    # `/search` now 404s and the live endpoint is `/search-v2`.
    JSEARCH_ENDPOINT: str = "/search-v2"
    # Results per call, in pages of ~10. Each page costs quota, so this stays
    # low by default — the endpoint paginates by cursor, which a stateless
    # search cannot resume, so this is the only way to widen one call.
    JSEARCH_NUM_PAGES: int = 1
    JSEARCH_COUNTRY: str = "in"
    # "all" | "today" | "3days" | "week" | "month". A month keeps the index
    # broad; the freshness filter in the UI narrows it per search.
    JSEARCH_DATE_POSTED: str = "month"
    # Optional allowlist of portal slugs, e.g. "naukri,linkedin,indeed".
    # Empty means keep every publisher the aggregator returns.
    JSEARCH_PUBLISHERS: str = ""

    @property
    def jsearch_publisher_list(self) -> List[str]:
        return [p.strip().lower() for p in self.JSEARCH_PUBLISHERS.split(",") if p.strip()]

    # Careerjet — free affiliate key, India locale.
    CAREERJET_API_KEY: Optional[str] = None
    CAREERJET_LOCALE: str = "en_IN"
    # The API requires the end user's IP for its own abuse accounting. Server
    # -side searches have no browser IP to forward, so a placeholder stands in.
    CAREERJET_USER_IP: str = "127.0.0.1"

    # Jooble — free key, country-specific index.
    JOOBLE_API_KEY: Optional[str] = None
    JOOBLE_API_HOST: str = "in.jooble.org"

    # ── Company career boards ─────────────────────────────────────────
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

    # How often the loop scheduler wakes up to check for due campaigns.
    LOOP_SCHEDULER_INTERVAL_SECONDS: int = 300
    # Master switch — disable to run the API without background fetching.
    LOOP_SCHEDULER_ENABLED: bool = True

    class Config:
        env_file = ".env"

settings = Settings()
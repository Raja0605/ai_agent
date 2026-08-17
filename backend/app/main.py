import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.router import api_router
from app.core.config import settings
from app.core.database import Base, engine, get_db
from app.services import scheduler

# Import all models so they are registered on SQLAlchemy's metadata before
# create_all runs.
from app.models.application import ApplicationTracking  # noqa: F401
from app.models.job import Job, JobSourceRecord, Skill  # noqa: F401
from app.models.loop import JobLoop, LoopMatch  # noqa: F401
from app.models.user import Resume, User, UserProfile  # noqa: F401

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jobpulse")


def _check_ai_credentials() -> None:
    """
    The AI providers degrade to keyword heuristics when no key is present, and
    they do it silently. Say so loudly at boot so a misconfigured deployment is
    obvious instead of quietly serving heuristic scores as AI results.
    """
    provider = settings.LLM_PROVIDER.lower()
    key = settings.OPENAI_API_KEY if provider == "openai" else settings.GOOGLE_API_KEY

    if not key:
        logger.warning(
            "No API key found for LLM_PROVIDER=%s. /api/ai/* will return "
            "HEURISTIC fallback results, not AI results. Set %s in your .env "
            "and ensure docker-compose passes it through (env_file).",
            provider,
            "OPENAI_API_KEY" if provider == "openai" else "GOOGLE_API_KEY",
        )
    else:
        logger.info("AI provider '%s' configured with a credential.", provider)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown. Replaces the deprecated @app.on_event handlers."""
    _check_ai_credentials()

    # Schema bootstrap for local development. Alembic owns schema changes —
    # see backend/alembic/ and `alembic upgrade head`.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    scheduler.start()
    try:
        yield
    finally:
        await scheduler.stop()


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(api_router, prefix="/api")


@app.get("/")
def read_root():
    return {"message": "Welcome to JobPulse API"}


@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}

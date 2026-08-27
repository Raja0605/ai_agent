import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.router import api_router
from app.core.config import settings
from app.core.database import Base, engine, get_db

# Import all models so they are registered on SQLAlchemy's metadata before
# create_all runs.
from app.models.application import ApplicationTracking  # noqa: F401
from app.models.job import Job, JobSourceRecord, Skill  # noqa: F401
from app.models.mcp import MCPServer  # noqa: F401
from app.models.user import Resume, User, UserProfile  # noqa: F401

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jobpulse")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown. Replaces the deprecated @app.on_event handlers."""

    # Schema bootstrap for local development. Alembic owns schema changes —
    # see backend/alembic/ and `alembic upgrade head`.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield


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

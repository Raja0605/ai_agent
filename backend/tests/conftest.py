"""
Test fixtures.

The suite runs against in-memory SQLite rather than the Postgres in
docker-compose so it needs no running services. The models use portable column
types, so this is a faithful enough stand-in for persistence behaviour.
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base
# Importing every model registers it on Base.metadata before create_all.
from app.models.application import ApplicationTracking  # noqa: F401
from app.models.job import Job, JobSourceRecord, Skill  # noqa: F401
from app.models.user import Resume, User, UserProfile  # noqa: F401


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def session_factory(monkeypatch):
    """
    A fresh in-memory database per test, wired in wherever the code reaches
    for the global session factory.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        # A single shared connection, so ":memory:" is the same database for
        # every session opened during the test.
        connect_args={"check_same_thread": False},
        poolclass=None,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)

    import app.services.job_service as job_service
    monkeypatch.setattr(job_service, "AsyncSessionLocal", factory)

    yield factory

    await engine.dispose()

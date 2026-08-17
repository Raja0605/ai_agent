from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from app.core.config import settings

# echo was hardcoded to True, so every statement — including row values — was
# written to the log on every request. Noisy, slow, and a poor place for user
# data to end up. Off by default; set SQL_ECHO=true when debugging a query.
engine = create_async_engine(settings.DATABASE_URL, echo=settings.SQL_ECHO)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import Resume
from app.schemas.prompt_ai import PromptAISearchRequest
from app.services.prompt_ai_service import PromptAIService

router = APIRouter()
service = PromptAIService()


async def _load_resume(db: AsyncSession, user_id: str, resume_id: str) -> Resume:
    stmt = select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
    resume = (await db.execute(stmt)).scalars().first()
    if resume is None:
        raise HTTPException(404, "Resume not found")
    return resume


@router.post("/search")
async def search(
    payload: PromptAISearchRequest,
    stream: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
):
    if not payload.prompt.strip():
        raise HTTPException(400, "Enter a job search prompt.")
    resume = await _load_resume(db, current_user_id, payload.resume_id)

    if stream:
        async def events():
            async for chunk in service.stream(payload.prompt.strip(), resume, db):
                yield chunk

        return StreamingResponse(events(), media_type="text/event-stream")

    return await service.search(payload.prompt.strip(), resume, db)

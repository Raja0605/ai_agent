from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import UserProfile, Resume
from app.schemas.user import (
    ResumeBase,
    ResumeResponse,
    ResumeTextCreate,
    UserProfileResponse,
    UserProfileUpdate,
)
from app.services.resume_parser import extract_text_from_pdf, parse_resume_text

router = APIRouter()

@router.get("/", response_model=UserProfileResponse)
async def get_profile(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user)
):
    """Get current user profile."""
    stmt = select(UserProfile).where(UserProfile.user_id == current_user_id)
    result = await db.execute(stmt)
    profile = result.scalars().first()
    
    if not profile:
        # Create a default profile
        profile = UserProfile(user_id=current_user_id, full_name="Default User")
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
        
    return profile

@router.patch("/", response_model=UserProfileResponse)
async def update_profile(
    profile_update: UserProfileUpdate, 
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user)
):
    """Update current user profile."""
    stmt = select(UserProfile).where(UserProfile.user_id == current_user_id)
    result = await db.execute(stmt)
    profile = result.scalars().first()
    
    if not profile:
        profile = UserProfile(user_id=current_user_id, **profile_update.dict())
        db.add(profile)
    else:
        for key, value in profile_update.dict().items():
            setattr(profile, key, value)
            
    await db.commit()
    await db.refresh(profile)
    return profile

async def _store_parsed_resume(
    db: AsyncSession, user_id: str, file_name: str, parsed: dict
) -> Resume:
    """Persist a parsed resume and sync the profile's target roles."""
    stmt = select(UserProfile).where(UserProfile.user_id == user_id)
    profile = (await db.execute(stmt)).scalars().first()
    if profile:
        profile.target_roles = parsed.get("target_roles", [])

    roles = parsed.get("target_roles") or []
    db_resume = Resume(
        user_id=user_id,
        file_name=file_name,
        raw_text=parsed["raw_text"],
        extracted_skills=parsed["extracted_skills"],
        summary=parsed["summary"],
        experience_years=parsed["experience_years"],
        target_role=roles[0] if roles else None,
    )

    db.add(db_resume)
    await db.commit()
    await db.refresh(db_resume)
    return db_resume


@router.post("/resume", response_model=ResumeResponse)
async def upload_resume(
    resume_in: ResumeBase,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user)
):
    """Store a resume whose fields have already been extracted by the caller."""
    db_resume = Resume(user_id=current_user_id, **resume_in.dict())
    db.add(db_resume)
    await db.commit()
    await db.refresh(db_resume)
    return db_resume


@router.post("/resume/text", response_model=ResumeResponse)
async def create_resume_from_text(
    resume_in: ResumeTextCreate,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user)
):
    """
    Accept pasted resume text and parse it server-side.

    Parsing lived in the browser as a second, divergent copy of the backend
    heuristics — a different skill vocabulary and a made-up experience figure
    of 4 years for everyone. One parser, on the server.
    """
    if not resume_in.raw_text.strip():
        raise HTTPException(status_code=400, detail="Resume text is empty.")

    parsed = parse_resume_text(resume_in.raw_text)
    return await _store_parsed_resume(db, current_user_id, resume_in.file_name, parsed)


@router.delete("/resume/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(
    resume_id: str,
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user)
):
    """
    Delete a resume.

    There was no endpoint for this at all: the client's deleteResume() simply
    reloaded the list and reported success, so deleted resumes came straight
    back.
    """
    stmt = select(Resume).where(Resume.id == resume_id, Resume.user_id == current_user_id)
    resume = (await db.execute(stmt)).scalars().first()
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")

    await db.delete(resume)
    await db.commit()

@router.post("/resume/upload", response_model=ResumeResponse)
async def upload_resume_pdf(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user)
):
    """Accepts a raw PDF upload, parses it, and creates a Resume entry."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
    try:
        contents = await file.read()
        raw_text = extract_text_from_pdf(contents)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {e}")
        
    if not raw_text.strip():
        raise HTTPException(
            status_code=400,
            detail="No text could be extracted — this looks like a scanned or image-only PDF.",
        )

    parsed_data = parse_resume_text(raw_text)
    return await _store_parsed_resume(db, current_user_id, file.filename, parsed_data)

@router.get("/resume", response_model=List[ResumeResponse])
async def get_resumes(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user)
):
    """Get all resumes for user."""
    stmt = select(Resume).where(Resume.user_id == current_user_id)
    result = await db.execute(stmt)
    return result.scalars().all()

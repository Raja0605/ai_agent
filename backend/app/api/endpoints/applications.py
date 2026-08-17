from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List
import datetime

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.application import ApplicationTracking
from app.schemas.application import ApplicationCreate, ApplicationUpdate, ApplicationResponse

router = APIRouter()

@router.get("/", response_model=List[ApplicationResponse])
async def get_applications(
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user)
):
    """
    Get all tracked applications for the current user.
    """
    stmt = select(ApplicationTracking).options(selectinload(ApplicationTracking.job)).where(ApplicationTracking.user_id == current_user_id)
    result = await db.execute(stmt)
    apps = result.scalars().all()
    
    response_apps = []
    for app in apps:
        app_dict = {c.name: getattr(app, c.name) for c in app.__table__.columns}
        if app.job:
            app_dict["job_title"] = app.job.title
            app_dict["company"] = app.job.company
            # Assuming first source record is the primary platform
            app_dict["platform"] = "web" 
        response_apps.append(ApplicationResponse(**app_dict))
        
    return response_apps

@router.post("/", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
async def create_application(
    app_in: ApplicationCreate, 
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user)
):
    """
    Save a job or track an application.
    """
    # Verify Job actually exists first to avoid FK IntegrityErrors
    from app.models.job import Job
    job_stmt = select(Job).where(Job.id == app_in.job_id)
    job_res = await db.execute(job_stmt)
    if not job_res.scalars().first():
        raise HTTPException(status_code=404, detail="Job not found in database.")

    # Check if already tracking this job
    stmt = select(ApplicationTracking).where(
        ApplicationTracking.job_id == app_in.job_id,
        ApplicationTracking.user_id == current_user_id
    )
    res = await db.execute(stmt)
    existing = res.scalars().first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Already tracking this job.")
        
    db_app = ApplicationTracking(
        **app_in.dict(),
        user_id=current_user_id,
        applied_at=datetime.datetime.utcnow() if app_in.status == "APPLIED" else None
    )
    
    db.add(db_app)
    await db.commit()
    await db.refresh(db_app)
    return db_app

@router.patch("/{app_id}", response_model=ApplicationResponse)
async def update_application(
    app_id: str, 
    app_update: ApplicationUpdate, 
    db: AsyncSession = Depends(get_db),
    current_user_id: str = Depends(get_current_user)
):
    """
    Update the status or notes of an application.
    """
    stmt = select(ApplicationTracking).where(
        ApplicationTracking.id == app_id,
        ApplicationTracking.user_id == current_user_id
    )
    res = await db.execute(stmt)
    db_app = res.scalars().first()
    
    if not db_app:
        raise HTTPException(status_code=404, detail="Application not found")
        
    update_data = app_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_app, key, value)
        
    if update_data.get("status") == "APPLIED" and not db_app.applied_at:
        db_app.applied_at = datetime.datetime.utcnow()
        
    await db.commit()
    await db.refresh(db_app)
    return db_app

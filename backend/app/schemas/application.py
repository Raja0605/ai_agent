from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ApplicationBase(BaseModel):
    job_id: str
    status: str
    resume_used: Optional[str] = None
    ats_score: Optional[int] = None
    cover_note: Optional[str] = None
    failure_reason: Optional[str] = None
    notes: Optional[str] = None

class ApplicationCreate(ApplicationBase):
    pass

class ApplicationUpdate(BaseModel):
    status: Optional[str] = None
    ats_score: Optional[int] = None
    cover_note: Optional[str] = None
    failure_reason: Optional[str] = None
    notes: Optional[str] = None

class ApplicationResponse(ApplicationBase):
    id: str
    user_id: str
    applied_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    job_title: Optional[str] = None
    company: Optional[str] = None
    platform: Optional[str] = None
    
    class Config:
        from_attributes = True

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class UserProfileBase(BaseModel):
    full_name: str
    target_roles: List[str] = []
    preferred_locations: List[str] = []
    remote_preference: bool = True
    experience_level: str = "mid"
    expected_salary_min: Optional[int] = None

class UserProfileUpdate(UserProfileBase):
    pass

class UserProfileResponse(UserProfileBase):
    id: str
    user_id: str

    class Config:
        from_attributes = True

class ResumeBase(BaseModel):
    file_name: str
    raw_text: Optional[str] = None
    extracted_skills: List[str] = []
    summary: Optional[str] = None
    experience_years: int = 0

class ResumeTextCreate(BaseModel):
    """Resume supplied as pasted text; the server does the parsing."""
    file_name: str
    raw_text: str

class ResumeResponse(ResumeBase):
    id: str
    user_id: str
    created_at: datetime
    # Derived at parse time from the resume text, so the UI does not have to
    # guess a target role (or invent one).
    target_role: Optional[str] = None

    class Config:
        from_attributes = True

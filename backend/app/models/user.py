from sqlalchemy import Column, String, Boolean, Integer, DateTime, JSON, Text
from datetime import datetime
from app.core.database import Base
from app.models.job import generate_uuid

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserProfile(Base):
    __tablename__ = "user_profiles"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, index=True)
    full_name = Column(String)
    target_roles = Column(JSON, default=list)
    preferred_locations = Column(JSON, default=list)
    remote_preference = Column(Boolean, default=True)
    experience_level = Column(String, default="mid")
    expected_salary_min = Column(Integer, nullable=True)
    
class Resume(Base):
    __tablename__ = "resumes"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, index=True)
    file_name = Column(String)
    raw_text = Column(Text, nullable=True)
    extracted_skills = Column(JSON, default=list)
    summary = Column(Text, nullable=True)
    experience_years = Column(Integer, default=0)
    # Best-guess role from the parsed text. Stored so the client does not have
    # to re-derive (or fabricate) it on every render.
    target_role = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

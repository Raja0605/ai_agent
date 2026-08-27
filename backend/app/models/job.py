from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

job_skills_table = Table(
    "job_skills",
    Base.metadata,
    Column("job_id", String, ForeignKey("jobs.id"), primary_key=True),
    Column("skill_id", String, ForeignKey("skills.id"), primary_key=True)
)

class Skill(Base):
    __tablename__ = "skills"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, unique=True, index=True)

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    # Canonical content key (see services/job_identity.py). Lets the same
    # posting arriving from two different boards collapse onto one row.
    fingerprint = Column(String, index=True, nullable=True)
    title = Column(String, index=True)
    company = Column(String, index=True)
    location = Column(String, index=True)
    remote = Column(Boolean, default=False)
    employment_type = Column(String, nullable=True)
    experience_min = Column(Integer, nullable=True)
    experience_max = Column(Integer, nullable=True)
    description = Column(String)
    salary_min = Column(Integer, nullable=True)
    salary_max = Column(Integer, nullable=True)
    currency = Column(String, nullable=True)
    posted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    source_records = relationship("JobSourceRecord", back_populates="job", cascade="all, delete-orphan")
    skills = relationship("Skill", secondary=job_skills_table)

class JobSourceRecord(Base):
    __tablename__ = "job_source_records"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("jobs.id"))
    source = Column(String, index=True) # e.g., "linkedin", "greenhouse"
    source_job_id = Column(String, index=True)
    job_url = Column(String, nullable=True)
    apply_url = Column(String, nullable=True)
    
    job = relationship("Job", back_populates="source_records")

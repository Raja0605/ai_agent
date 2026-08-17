from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base
from app.models.job import generate_uuid

class ApplicationTracking(Base):
    __tablename__ = "applications"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("jobs.id"), index=True)
    user_id = Column(String, index=True)  # Ready for multi-tenant users later
    status = Column(String, index=True, default="SAVED") 
    # Statuses: SAVED, READY_TO_APPLY, APPLYING, APPLIED, FAILED, REJECTED, INTERVIEW, OFFER, WITHDRAWN
    
    applied_at = Column(DateTime, nullable=True)
    resume_used = Column(String, nullable=True)
    ats_score = Column(Integer, nullable=True)
    cover_note = Column(Text, nullable=True)
    failure_reason = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    job = relationship("Job")

"""
Loops — saved search campaigns that run on a schedule.

The app was request-response: search, look, leave. A Loop is a standing search
(keywords + location + remote preference + which resume to score against) that
the scheduler re-runs on a cadence, so new postings accumulate between visits
instead of only existing while someone is watching.

Every match a loop finds is recorded, so "what is new since I last looked" is
answerable and a posting is never re-surfaced as new.
"""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base
from app.models.job import generate_uuid


class JobLoop(Base):
    __tablename__ = "job_loops"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, index=True)

    name = Column(String, nullable=False)
    keywords = Column(JSON, default=list)          # roles/titles to search for
    location = Column(String, nullable=True)
    remote_only = Column(Boolean, default=False)

    # Which resume incoming jobs are scored against. Null means the user's
    # most recent resume is used at run time.
    resume_id = Column(String, nullable=True)

    # How often this loop is due, and the floor a job must clear to be
    # recorded as a match at all.
    cadence_hours = Column(Integer, default=24)
    min_score = Column(Integer, default=50)

    active = Column(Boolean, default=True, index=True)
    last_run_at = Column(DateTime, nullable=True)
    last_run_status = Column(String, nullable=True)
    last_run_error = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    matches = relationship(
        "LoopMatch", back_populates="loop", cascade="all, delete-orphan"
    )


class LoopMatch(Base):
    __tablename__ = "loop_matches"

    id = Column(String, primary_key=True, default=generate_uuid)
    loop_id = Column(String, ForeignKey("job_loops.id"), index=True)
    job_id = Column(String, ForeignKey("jobs.id"), index=True)

    score = Column(Integer, default=0)
    # Whether the score came from the model or the deterministic scorer, so
    # the UI can label it rather than implying every number is an AI verdict.
    score_method = Column(String, default="heuristic")
    matched_skills = Column(JSON, default=list)
    missing_skills = Column(JSON, default=list)

    # False until the user has actually looked at it — this is what makes a
    # "new since last visit" count meaningful.
    seen = Column(Boolean, default=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    loop = relationship("JobLoop", back_populates="matches")
    job = relationship("Job")

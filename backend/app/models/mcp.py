from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, String
from app.core.database import Base
from app.models.job import generate_uuid


class MCPServer(Base):
    __tablename__ = "mcp_servers"
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    server_type = Column(String, nullable=False, default="job-search")
    transport = Column(String, nullable=False)  # stdio | sse | streamable-http
    endpoint = Column(String, nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    status = Column(String, nullable=False, default="disconnected")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

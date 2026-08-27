from fastapi import APIRouter
from app.api.endpoints import analytics, applications, jobs, mcp, profile

api_router = APIRouter()
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(applications.router, prefix="/applications", tags=["applications"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(profile.router, prefix="/profile", tags=["profile"])
api_router.include_router(mcp.router, prefix="/mcp", tags=["mcp"])

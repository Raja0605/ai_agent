from fastapi import APIRouter
from app.api.endpoints import ai, analytics, applications, jobs, loops, profile

api_router = APIRouter()
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(applications.router, prefix="/applications", tags=["applications"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(loops.router, prefix="/loops", tags=["loops"])
api_router.include_router(profile.router, prefix="/profile", tags=["profile"])

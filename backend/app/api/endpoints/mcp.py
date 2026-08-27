import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.mcp import MCPServer
from app.schemas.mcp import MCPServerCreate, MCPServerUpdate, MCPServerResponse, MCPSearchRequest
from mcp_agent.job_search import MCPJobSearch
from mcp_agent.models import MCPServerConfig
from mcp_agent.server_manager import MCPServerManager
from app.services.job_service import save_normalized_jobs

router = APIRouter()

@router.get("/servers", response_model=list[MCPServerResponse])
async def list_servers(db: AsyncSession = Depends(get_db)): return (await db.execute(select(MCPServer))).scalars().all()

@router.post("/servers", response_model=MCPServerResponse)
async def create_server(payload: MCPServerCreate, db: AsyncSession = Depends(get_db)):
    server = MCPServer(**payload.model_dump()); db.add(server); await db.commit(); await db.refresh(server); return server

async def _server(server_id, db):
    server = await db.get(MCPServer, server_id)
    if not server: raise HTTPException(404, "MCP server not found")
    return server

@router.get("/servers/{server_id}", response_model=MCPServerResponse)
async def get_server(server_id: str, db: AsyncSession = Depends(get_db)): return await _server(server_id, db)

@router.patch("/servers/{server_id}", response_model=MCPServerResponse)
async def update_server(server_id: str, payload: MCPServerUpdate, db: AsyncSession = Depends(get_db)):
    server = await _server(server_id, db)
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(server, key, value)
    await db.commit(); await db.refresh(server); return server

@router.delete("/servers/{server_id}")
async def delete_server(server_id: str, db: AsyncSession = Depends(get_db)):
    await db.delete(await _server(server_id, db)); await db.commit(); return {"status": "deleted"}

@router.post("/servers/{server_id}/test")
async def test(server_id: str, db: AsyncSession = Depends(get_db)):
    server = await _server(server_id, db)
    manager = MCPServerManager()
    try:
        await manager.connect(MCPServerConfig(server.name, server.transport, server.endpoint, server.enabled)); tools = await manager.list_tools(); server.status = "connected"
    except Exception: tools = []; server.status = "unavailable"
    finally: await manager.disconnect()
    await db.commit(); return {"status": server.status, "tool_count": len(tools)}

@router.get("/servers/{server_id}/tools")
async def tools(server_id: str, db: AsyncSession = Depends(get_db)):
    server = await _server(server_id, db); manager = MCPServerManager()
    try:
        await manager.connect(MCPServerConfig(server.name, server.transport, server.endpoint, server.enabled)); found = await manager.list_tools(); return {"tools": [t.__dict__ for t in found], "status": "connected"}
    except Exception: return {"tools": [], "status": "unavailable"}
    finally: await manager.disconnect()

@router.post("/search")
async def search(payload: MCPSearchRequest, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(MCPServer).where(MCPServer.id.in_(payload.server_ids), MCPServer.enabled.is_(True)))).scalars().all()
    filters = payload.model_dump(exclude={"server_ids", "keywords", "location", "remote"})
    results = await asyncio.gather(*(MCPJobSearch(MCPServerConfig(s.name, s.transport, s.endpoint, s.enabled)).search(payload.keywords, payload.location, payload.remote, filters=filters) for s in rows), return_exceptions=True)
    jobs, states = [], {}
    for server, result in zip(rows, results):
        if isinstance(result, Exception): states[server.id] = {"status": "error", "result_count": 0}
        else: jobs.extend(result[0]); states[server.id] = {"status": "success", "result_count": len(result[0]), "source": f"{server.name.lower()}-mcp"}
    saved = await save_normalized_jobs(jobs)
    return {"results": saved, "servers": states}

"""Entrypoint helpers for using mcp_agent independently of FastAPI."""
from .config import MCPAgentSettings
from .job_search import MCPJobSearch

async def search_configured_server(keywords, location=None, remote=None):
    config = MCPAgentSettings().server_config()
    if not config: return []
    jobs, _ = await MCPJobSearch(config).search(keywords, location, remote)
    return jobs

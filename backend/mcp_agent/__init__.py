"""Protocol-only MCP job search integration for JobPulse."""
from .job_search import MCPJobSearch
from .models import MCPServerConfig

__all__ = ["MCPJobSearch", "MCPServerConfig"]

import logging
from .exceptions import MCPToolDiscoveryError
from .models import MCPTool

logger = logging.getLogger("jobpulse.mcp_agent")

class MCPToolDiscovery:
    async def discover_tools(self, client) -> list[MCPTool]:
        logger.info("MCP tool discovery started")
        result = await client.call("tools/list")
        raw = result.get("tools", []) if isinstance(result, dict) else []
        tools = [MCPTool(x.get("name", ""), x.get("description", ""), x.get("inputSchema", {})) for x in raw if x.get("name")]
        logger.info("MCP tools discovered", extra={"count": len(tools)})
        return tools

    async def find_job_search_tool(self, tools: list[MCPTool]) -> MCPTool:
        for tool in tools:
            text = f"{tool.name} {tool.description} {' '.join(tool.input_schema.get('properties', {}))}".lower()
            if ("job" in text or "career" in text) and ("search" in text or "find" in text or "list" in text):
                logger.info("Job-search tool selected", extra={"tool": tool.name})
                return tool
        raise MCPToolDiscoveryError("No job-search tool was found on this MCP server")

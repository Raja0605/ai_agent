import asyncio
import json
import logging
from typing import Any
from urllib.parse import urlparse
import httpx
from .exceptions import MCPConfigurationError, MCPConnectionError
from .models import MCPServerConfig

logger = logging.getLogger("jobpulse.mcp_agent")

class MCPClient:
    """Small JSON-RPC MCP client for stdio, SSE, and Streamable HTTP."""
    def __init__(self, config: MCPServerConfig):
        if config.transport not in {"stdio", "sse", "streamable-http"} or not config.endpoint:
            raise MCPConfigurationError("MCP server configuration is incomplete")
        self.config, self._id, self._session_id = config, 0, None

    async def connect(self):
        logger.info("MCP connection started", extra={"server": self.config.name})
        try:
            result = await self.call("initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "jobpulse", "version": "1.0"}})
            # Streamable HTTP servers require this notification before they
            # accept normal requests such as tools/list.
            await self.call("notifications/initialized", notification=True)
            return result
        except Exception as exc:
            logger.warning("MCP connection failed", extra={"server": self.config.name})
            raise MCPConnectionError("MCP server unavailable") from exc

    async def close(self):
        return None

    async def call(self, method: str, params: dict | None = None, notification: bool = False) -> Any:
        if notification:
            payload = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        else:
            self._id += 1
            payload = {"jsonrpc": "2.0", "id": self._id, "method": method, "params": params or {}}
        try:
            if self.config.transport == "stdio":
                process = await asyncio.create_subprocess_shell(self.config.endpoint, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
                out, _ = await asyncio.wait_for(process.communicate((json.dumps(payload) + "\n").encode()), timeout=15)
                response = json.loads(out.decode().splitlines()[0])
            else:
                headers = {"accept": "application/json, text/event-stream", "content-type": "application/json"}
                # Docker Desktop exposes Windows-host services through this
                # hostname. FastMCP's DNS-rebinding protection only trusts the
                # local host name, so retain the publicly reachable URL while
                # identifying the request as localhost to that host service.
                endpoint = urlparse(self.config.endpoint)
                if endpoint.hostname == "host.docker.internal":
                    headers["host"] = f"localhost:{endpoint.port or 80}"
                if self._session_id:
                    headers["mcp-session-id"] = self._session_id
                # Browser-backed MCP tools (such as LinkedIn job search) can
                # legitimately take longer than a lightweight initialization
                # or tools/list request.
                timeout = 210 if method == "tools/call" else 15
                async with httpx.AsyncClient(timeout=timeout) as client:
                    reply = await client.post(self.config.endpoint, json=payload, headers=headers)
                    reply.raise_for_status()
                self._session_id = reply.headers.get("mcp-session-id", self._session_id)
                raw = reply.text
                if notification and not raw.strip():
                    return None
                response = json.loads(raw.split("data:", 1)[-1].strip())
        except Exception as exc:
            raise MCPConnectionError("MCP server unavailable") from exc
        if notification:
            return None
        if response.get("error"):
            raise MCPConnectionError("MCP server rejected the request")
        return response.get("result")

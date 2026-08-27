from .client import MCPClient
from .models import MCPServerConfig
from .tool_discovery import MCPToolDiscovery

class MCPServerManager:
    def __init__(self): self.client = None
    async def connect(self, server_config: MCPServerConfig):
        self.client = MCPClient(server_config); await self.client.connect(); return self.client
    async def disconnect(self):
        if self.client: await self.client.close()
        self.client = None
    async def list_tools(self):
        if not self.client: return []
        return await MCPToolDiscovery().discover_tools(self.client)
    async def get_server_info(self):
        if not self.client: return {"status": "disconnected"}
        return {"status": "connected", "server": self.client.config.name, "transport": self.client.config.transport}

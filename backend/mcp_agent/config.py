from pydantic_settings import BaseSettings
from .models import MCPServerConfig

class MCPAgentSettings(BaseSettings):
    MCP_SERVER_NAME: str = "linkedin"
    MCP_TRANSPORT: str = ""
    MCP_ENDPOINT: str = ""
    MCP_ENABLED: bool = False
    class Config: env_file = ".env"

    def server_config(self) -> MCPServerConfig | None:
        if not self.MCP_ENABLED or not self.MCP_TRANSPORT or not self.MCP_ENDPOINT:
            return None
        return MCPServerConfig(self.MCP_SERVER_NAME, self.MCP_TRANSPORT, self.MCP_ENDPOINT, True)

from dataclasses import dataclass
from typing import Any, Optional

@dataclass(frozen=True)
class MCPServerConfig:
    name: str
    transport: str
    endpoint: str
    enabled: bool = True

    @property
    def source(self) -> str:
        return f"{self.name.lower()}-mcp"

@dataclass
class MCPTool:
    name: str
    description: str
    input_schema: dict[str, Any]

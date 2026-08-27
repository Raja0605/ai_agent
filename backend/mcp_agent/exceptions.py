class MCPAgentError(Exception):
    """Safe, user-facing MCP error."""

class MCPConfigurationError(MCPAgentError): pass
class MCPConnectionError(MCPAgentError): pass
class MCPToolDiscoveryError(MCPAgentError): pass
class MCPSearchError(MCPAgentError): pass

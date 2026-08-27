# mcp_agent

`mcp_agent` is JobPulse's protocol-only MCP job-search component. It has no database, authentication, scheduler, resume, application-tracking, or model-provider dependency.

Configure one external MCP server with `MCP_SERVER_NAME`, `MCP_TRANSPORT` (`stdio`, `sse`, or `streamable-http`), `MCP_ENDPOINT`, and `MCP_ENABLED=true`. Use the endpoint/command supplied by Docker Desktop MCP Toolkit; no LinkedIn endpoint is invented here.

On an explicit search, the agent initializes the server, lists tools, selects a tool from its name, description, and input schema, maps the user search fields to that schema, and returns canonical `NormalizedJob` objects. Failed connections return safe errors without credentials, paths, or server internals.

The FastAPI `/api/mcp` routes own saved server configuration and may pass normalized results to normal JobPulse ingestion for deduplication. Test a configured server with `POST /api/mcp/servers/{id}/test` before searching.

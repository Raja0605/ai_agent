# Thin image that clones the upstream JobSpy MCP stack at build time.
# JobSpy source is not vendored into this repository.
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        git gcc g++ ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy our HTTP server before cloning to avoid ownership issues
COPY docker/jobspy-mcp-server.py /tmp/jobspy-mcp-server.py

# Copy local jobspy changes to temp location
COPY jobspy_mcp/jobspy /tmp/local-jobspy

RUN git clone --depth 1 https://github.com/supg/jobspy-mcp-stack.git /tmp/jobspy-mcp-stack \
    && cp -a /tmp/jobspy-mcp-stack/. /app \
    && rm -rf /tmp/jobspy-mcp-stack \
    && cp /tmp/jobspy-mcp-server.py /app/jobspy-mcp-server.py \
    && cp -a /tmp/local-jobspy/* /app/jobspy/ \
    && pip install --no-cache-dir fastapi uvicorn \
    && pip install --no-cache-dir -r requirements.txt \
    && groupadd -r mcpuser && useradd -r -g mcpuser mcpuser \
    && chown -R mcpuser:mcpuser /app

USER mcpuser
EXPOSE 8500

# Run HTTP server directly
CMD ["python", "-u", "/app/jobspy-mcp-server.py"]

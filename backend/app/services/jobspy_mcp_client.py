"""MCP session client used only by Job Spy.

Kept out of mcp_agent so the existing LinkedIn MCP path stays independent.
Speaks JSON-RPC MCP over TCP, matching the official JobSpy stdio server
exposed through socat (Content-Length framing), with a newline-delimited
fallback for simpler TCP wrappers.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any


class JobSpyMCPError(RuntimeError):
    pass


class JobSpyMCPClient:
    def __init__(self, host: str, port: int, timeout: float = 15.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._id = 0
        self._framing = "content-length"

    async def connect(self) -> dict[str, Any]:
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=min(self.timeout, 15),
            )
        except Exception as exc:
            raise JobSpyMCPError("JobSpy MCP is unreachable") from exc
        result = await self.call(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "jobpulse-jobspy", "version": "1.0"},
            },
        )
        await self.call("notifications/initialized", notification=True)
        return result if isinstance(result, dict) else {}

    async def close(self) -> None:
        if self._writer is not None:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except Exception:
                pass
        self._reader = self._writer = None

    async def list_tools(self) -> list[dict[str, Any]]:
        result = await self.call("tools/list")
        tools = result.get("tools", []) if isinstance(result, dict) else []
        return [tool for tool in tools if isinstance(tool, dict) and tool.get("name")]

    async def list_resources(self) -> list[dict[str, Any]]:
        try:
            result = await self.call("resources/list")
        except JobSpyMCPError:
            return []
        resources = result.get("resources", []) if isinstance(result, dict) else []
        return [item for item in resources if isinstance(item, dict)]

    async def read_resource(self, uri: str) -> str:
        result = await self.call("resources/read", {"uri": uri})
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            contents = result.get("contents") or result.get("text") or ""
            if isinstance(contents, list):
                parts = []
                for item in contents:
                    if isinstance(item, dict) and item.get("text"):
                        parts.append(str(item["text"]))
                    elif isinstance(item, str):
                        parts.append(item)
                return "\n".join(parts)
            if isinstance(contents, str):
                return contents
        return ""

    async def call_tool(self, name: str, arguments: dict[str, Any], timeout: float | None = None) -> Any:
        return await self.call(
            "tools/call",
            {"name": name, "arguments": arguments},
            timeout=timeout,
        )

    async def call(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        notification: bool = False,
        timeout: float | None = None,
    ) -> Any:
        if self._reader is None or self._writer is None:
            raise JobSpyMCPError("JobSpy MCP is not connected")
        wait = timeout if timeout is not None else (self.timeout if method != "tools/call" else max(self.timeout, 60))
        if notification:
            payload: dict[str, Any] = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        else:
            self._id += 1
            payload = {"jsonrpc": "2.0", "id": self._id, "method": method, "params": params or {}}
        raw = json.dumps(payload).encode("utf-8")
        try:
            if self._framing == "content-length":
                header = f"Content-Length: {len(raw)}\r\n\r\n".encode("utf-8")
                self._writer.write(header + raw)
            else:
                self._writer.write(raw + b"\n")
            await self._writer.drain()
            if notification:
                return None
            response = await self._read_response(wait)
        except JobSpyMCPError:
            raise
        except Exception as exc:
            raise JobSpyMCPError("JobSpy MCP request failed") from exc
        if not isinstance(response, dict):
            raise JobSpyMCPError("JobSpy MCP returned an invalid response")
        if response.get("error"):
            raise JobSpyMCPError("JobSpy MCP rejected the request")
        return response.get("result")

    async def _read_response(self, timeout: float) -> Any:
        assert self._reader is not None
        first = await asyncio.wait_for(self._reader.readline(), timeout=timeout)
        if not first:
            raise JobSpyMCPError("JobSpy MCP closed the connection")
        stripped = first.lstrip()
        if stripped.startswith(b"{") or stripped.startswith(b"["):
            self._framing = "newline"
            return json.loads(first.decode("utf-8"))
        headers = first
        while True:
            line = await asyncio.wait_for(self._reader.readline(), timeout=timeout)
            if not line or line in (b"\r\n", b"\n"):
                break
            headers += line
        length = None
        for header_line in headers.decode("utf-8", errors="replace").splitlines():
            if header_line.lower().startswith("content-length:"):
                length = int(header_line.split(":", 1)[1].strip())
                break
        if length is None:
            raise JobSpyMCPError("JobSpy MCP response was missing Content-Length")
        body = await asyncio.wait_for(self._reader.readexactly(length), timeout=timeout)
        return json.loads(body.decode("utf-8"))

import json
import logging
from html import unescape
from .exceptions import MCPSearchError
from .normalizer import MCPJobNormalizer
from .server_manager import MCPServerManager
from .tool_discovery import MCPToolDiscovery

logger = logging.getLogger("jobpulse.mcp_agent")

class MCPJobSearch:
    def __init__(self, config): self.config = config
    async def search(self, keywords, location=None, remote=None, experience_level=None, filters=None):
        manager = MCPServerManager()
        try:
            client = await manager.connect(self.config)
            tool = await MCPToolDiscovery().find_job_search_tool(await manager.list_tools())
            args = self._arguments(tool.input_schema, keywords, location, remote, experience_level, filters or {})
            if tool.name == "search_jobs":
                # A page is enough for an interactive UI search and keeps the
                # follow-up detail requests bounded.
                args.setdefault("max_pages", 1)
            logger.info("MCP search started", extra={"server": self.config.name})
            result = await client.call("tools/call", {"name": tool.name, "arguments": args})
            result = self._unwrap(result)
            if isinstance(result, dict) and result.get("isError"):
                message = self._tool_error(result)
                raise MCPSearchError(message or "The MCP server could not complete the search")
            # LinkedIn's search_jobs intentionally returns lightweight search
            # rows with job IDs. Hydrate only rows that lack a title so the
            # normalizer receives complete postings without extra calls when
            # another MCP already returns full job objects.
            if tool.name == "search_jobs":
                result = await self._hydrate_linkedin_jobs(client, result)
            jobs = MCPJobNormalizer().normalize(result, self.config.source)
            logger.info("MCP search completed", extra={"server": self.config.name, "count": len(jobs)})
            return jobs, tool
        except Exception as exc:
            logger.warning("MCP search failed", extra={"server": self.config.name})
            raise MCPSearchError("MCP server unavailable") from exc
        finally: await manager.disconnect()
    @staticmethod
    def _arguments(schema, keywords, location, remote, experience_level, filters):
        args = {}; properties = schema.get("properties", {})
        for key, value in properties.items():
            lower = key.lower(); kind = value.get("type")
            if "keyword" in lower or lower in {"query", "search", "q"}: args[key] = keywords if kind == "array" else " ".join(keywords)
            elif "location" in lower or lower in {"city", "place"}: args[key] = location
            elif "remote" in lower: args[key] = remote
            elif "experience" in lower or "level" in lower: args[key] = experience_level
        return {k: v for k, v in args.items() if v is not None}
    @staticmethod
    def _unwrap(result):
        if isinstance(result, dict) and isinstance(result.get("content"), list):
            for block in result["content"]:
                if block.get("type") == "text":
                    try: return json.loads(block["text"])
                    except (KeyError, json.JSONDecodeError): pass
        return result

    @staticmethod
    def _tool_error(result):
        for block in result.get("content", []):
            if block.get("type") == "text":
                return block.get("text", "")
        return ""

    @staticmethod
    def _items(result):
        if isinstance(result, list):
            return [item for item in result if isinstance(item, dict)]
        if not isinstance(result, dict):
            return []
        if isinstance(result.get("job_ids"), list):
            return [{"job_id": job_id} for job_id in result["job_ids"]]
        raw = result.get("jobs") or result.get("results") or result.get("data") or result.get("job") or []
        if isinstance(raw, dict):
            raw = [raw]
        return [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []

    async def _hydrate_linkedin_jobs(self, client, result):
        jobs = self._items(result)
        hydrated = []
        for job in jobs:
            if job.get("title"):
                hydrated.append(job)
                continue
            job_id = job.get("job_id") or job.get("id")
            if not job_id:
                hydrated.append(job)
                continue
            detail = self._unwrap(await client.call("tools/call", {"name": "get_job_details", "arguments": {"job_id": str(job_id)}}))
            if isinstance(detail, dict) and detail.get("isError"):
                continue
            detail_items = self._items(detail)
            hydrated.append(detail_items[0] if detail_items else self._linkedin_detail(detail, str(job_id)))
        return {"jobs": hydrated}

    @staticmethod
    def _linkedin_detail(detail, job_id):
        """Convert linkedin-mcp-server's scraped detail text into one job."""
        if not isinstance(detail, dict):
            return {"job_id": job_id}
        text = detail.get("sections", {}).get("job_posting", "")
        lines = [unescape(line).strip() for line in text.splitlines() if line.strip()]
        if len(lines) < 2:
            return {"job_id": job_id}
        location = next((line.split(" · ", 1)[0] for line in lines[2:] if "India" in line or "Remote" in line), None)
        employment_type = next((line for line in lines[2:12] if line.lower() in {"full-time", "part-time", "contract", "temporary", "internship"}), None)
        return {
            "job_id": job_id,
            "title": lines[1],
            "company": lines[0],
            "location": location,
            "employment_type": employment_type,
            "description": text,
            "job_url": detail.get("url"),
            "apply_url": detail.get("url"),
        }

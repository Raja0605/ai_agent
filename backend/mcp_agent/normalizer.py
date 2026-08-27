import hashlib
import json
from typing import Any
from app.schemas.job import NormalizedJob

class MCPJobNormalizer:
    def normalize(self, result: Any, source: str) -> list[NormalizedJob]:
        if isinstance(result, dict):
            raw = result.get("jobs") or result.get("results") or result.get("data") or result.get("job")
            if raw is None:
                raw = result if result.get("title") or result.get("job_title") else []
        else:
            raw = result
        if isinstance(raw, dict): raw = [raw]
        output = []
        for item in raw if isinstance(raw, list) else []:
            if not isinstance(item, dict): continue
            title = item.get("title") or item.get("job_title")
            if not title: continue
            identifier = str(item.get("id") or item.get("job_id") or hashlib.sha256(json.dumps(item, sort_keys=True, default=str).encode()).hexdigest())
            output.append(NormalizedJob(source=source, source_job_id=identifier, title=title, company=item.get("company") or item.get("company_name") or "Unknown company", location=item.get("location"), remote=bool(item.get("remote", False)), employment_type=item.get("employment_type"), description=item.get("description") or "", salary_min=item.get("salary_min"), salary_max=item.get("salary_max"), currency=item.get("currency"), posted_at=item.get("posted_at"), job_url=item.get("job_url") or item.get("url"), apply_url=item.get("apply_url") or item.get("url"), skills=item.get("skills") or []))
        return output

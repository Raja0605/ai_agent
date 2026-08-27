import hashlib
import json
import re
from typing import Any
from app.schemas.job import NormalizedJob

class MCPJobNormalizer:
    @staticmethod
    def experience(text: str) -> tuple[int | None, int | None]:
        """Extract only explicit experience requirements; never estimate."""
        value = text or ""
        ranged = re.search(r"\b(\d{1,2})\s*(?:-|–|to)\s*(\d{1,2})\s*(?:\+?\s*)?(?:years?|yrs?)\b", value, re.I)
        if ranged: return int(ranged.group(1)), int(ranged.group(2))
        minimum = re.search(r"\b(?:minimum|min\.?|at least)\s*(\d{1,2})\s*(?:years?|yrs?)\b", value, re.I)
        if minimum: return int(minimum.group(1)), None
        plus = re.search(r"\b(\d{1,2})\s*\+\s*(?:years?|yrs?)\b", value, re.I)
        if plus: return int(plus.group(1)), None
        exact = re.search(r"\b(\d{1,2})\s*(?:years?|yrs?)\s*(?:of\s*)?experience\b", value, re.I)
        return (int(exact.group(1)), None) if exact else (None, None)

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
            description = item.get("description") or ""
            exp_min = item.get("experience_min")
            exp_max = item.get("experience_max")
            if exp_min is None and exp_max is None: exp_min, exp_max = self.experience(description)
            output.append(NormalizedJob(source=source, source_job_id=identifier, title=title, company=item.get("company") or item.get("company_name") or "Unknown company", location=item.get("location"), remote=bool(item.get("remote", False)), employment_type=item.get("employment_type"), experience_min=exp_min, experience_max=exp_max, description=description, salary_min=item.get("salary_min"), salary_max=item.get("salary_max"), currency=item.get("currency"), posted_at=item.get("posted_at"), job_url=item.get("job_url") or item.get("url"), apply_url=item.get("apply_url") or item.get("url"), skills=item.get("skills") or []))
        return output

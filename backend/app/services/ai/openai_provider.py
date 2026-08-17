import logging
from typing import Optional

import httpx

from app.services.ai.base import BaseAIService

logger = logging.getLogger("jobpulse.ai")


class OpenAIProvider(BaseAIService):
    """OpenAI chat-completions transport. All behaviour is in BaseAIService."""

    name = "OpenAI"

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key or ""
        self.model = model
        self.base_url = "https://api.openai.com/v1/chat/completions"

    @property
    def is_configured(self) -> bool:
        return self.api_key.startswith("sk-")

    async def complete(self, prompt: str, json_mode: bool = False) -> Optional[str]:
        if not self.is_configured:
            return None

        payload: dict = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

            choices = data.get("choices") or []
            if not choices:
                logger.warning("[OpenAI] Response had no choices.")
                return None

            return choices[0].get("message", {}).get("content") or None

        except httpx.HTTPStatusError as exc:
            logger.warning("[OpenAI] HTTP %s: %s", exc.response.status_code, exc.response.text[:300])
        except Exception as exc:
            logger.warning("[OpenAI] Request failed: %s", exc)

        return None

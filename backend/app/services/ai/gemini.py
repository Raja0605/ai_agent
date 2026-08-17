import logging
from typing import Optional

import httpx

from app.services.ai.base import BaseAIService

logger = logging.getLogger("jobpulse.ai")


class GeminiProvider(BaseAIService):
    """Google Generative Language API transport. All behaviour is in BaseAIService."""

    name = "Gemini"

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key or ""
        self.model = model
        self.base_url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        )

    @property
    def is_configured(self) -> bool:
        # Google API keys are AIza-prefixed; anything else is a misconfigured
        # value (an OpenAI key in the wrong variable, a placeholder) and would
        # cost a round trip to discover.
        return self.api_key.startswith("AIza")

    async def complete(self, prompt: str, json_mode: bool = False) -> Optional[str]:
        if not self.is_configured:
            return None

        payload: dict = {"contents": [{"parts": [{"text": prompt}]}]}
        if json_mode:
            payload["generationConfig"] = {"responseMimeType": "application/json"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    # Sent as a header, not a `?key=` query parameter: httpx
                    # logs the full request URL at INFO, so a query-string key
                    # ends up in the application log, in `docker compose logs`,
                    # and in anything shipping those logs elsewhere.
                    headers={"x-goog-api-key": self.api_key},
                    json=payload,
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

            candidates = data.get("candidates") or []
            if not candidates:
                logger.warning("[Gemini] Response had no candidates: %s", data.get("promptFeedback"))
                return None

            parts = candidates[0].get("content", {}).get("parts") or []
            # Thinking models (Gemini 2.5+/3.x) return the reasoning trace as
            # extra parts flagged `thought`. Concatenating everything glued the
            # reasoning onto the answer, so a JSON response no longer parsed.
            answer = "".join(
                part.get("text", "") for part in parts if not part.get("thought")
            )
            return answer or None

        except httpx.HTTPStatusError as exc:
            logger.warning("[Gemini] HTTP %s: %s", exc.response.status_code, exc.response.text[:300])
        except Exception as exc:
            logger.warning("[Gemini] Request failed: %s", exc)

        return None

import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def summarize_with_ollama(prompt: str) -> str | None:
    if not settings.ai_enabled:
        return None

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.ollama_base_url.rstrip('/')}/api/generate",
                json={
                    "model": settings.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.2},
                },
            )
            response.raise_for_status()
            data = response.json()
            return str(data.get("response", "")).strip() or None
    except httpx.HTTPError as exc:
        logger.warning("Ollama summary failed: %s", exc)
        return None

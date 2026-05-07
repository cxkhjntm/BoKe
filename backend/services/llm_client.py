import json

import httpx

from backend.config import CHAT_MAX_TIMEOUT
from backend.utils.logger import get_logger

logger = get_logger("llm_client")


async def stream_llm_response(
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict],
):
    """Async generator that yields delta content strings from OpenAI-compatible chat API."""
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
    }

    async with httpx.AsyncClient(timeout=CHAT_MAX_TIMEOUT) as client:
        async with client.stream("POST", url, headers=headers, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = (
                            chunk.get("choices", [{}])[0]
                            .get("delta", {})
                            .get("content", "")
                        )
                        if delta:
                            yield delta
                    except json.JSONDecodeError:
                        continue

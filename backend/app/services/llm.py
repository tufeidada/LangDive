import httpx
import asyncio
import logging
from app.config import settings

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "qwen/qwen3.6-plus:free"
MAX_RETRIES = 3

async def call_llm(
    system_prompt: str,
    user_prompt: str,
    json_mode: bool = False,
    timeout: float = 60.0,
) -> str:
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    delay = 1.0
    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(OPENROUTER_URL, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = await resp.json() if asyncio.iscoroutinefunction(resp.json) else resp.json()
                    return data["choices"][0]["message"]["content"]
                logger.warning(f"LLM API returned {resp.status_code}: {resp.text}")
        except httpx.TimeoutException:
            logger.warning(f"LLM timeout on attempt {attempt + 1}")
        except Exception as e:
            logger.error(f"LLM error: {e}")
        if attempt < MAX_RETRIES - 1:
            await asyncio.sleep(min(delay, 30.0))
            delay *= 2

    raise RuntimeError("LLM call failed after retries")

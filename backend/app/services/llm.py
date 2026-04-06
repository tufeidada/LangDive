import httpx
import asyncio
import logging
from app.config import settings

logger = logging.getLogger(__name__)

# 阿里云百炼 (DashScope) OpenAI 兼容接口
API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
MODEL = "qwen-turbo"
MAX_RETRIES = 3

async def call_llm(
    system_prompt: str,
    user_prompt: str,
    json_mode: bool = False,
    timeout: float = 120.0,
) -> str:
    headers = {
        "Authorization": f"Bearer {settings.DASHSCOPE_API_KEY}",
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
                resp = await client.post(API_URL, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
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

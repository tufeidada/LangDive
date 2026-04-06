import httpx
import asyncio
import logging
from datetime import datetime, timezone
from app.config import settings

logger = logging.getLogger(__name__)

# 阿里云百炼 (DashScope) OpenAI 兼容接口
API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
MODEL = "qwen-turbo"
MAX_RETRIES = 3

# Usage tracking
_usage_log: list[dict] = []

def get_usage_log() -> list[dict]:
    return _usage_log.copy()

def reset_usage_log():
    _usage_log.clear()

async def _log_usage(model: str, usage: dict, purpose: str = ""):
    """Log API usage to in-memory list and database."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
        "purpose": purpose,
    }
    _usage_log.append(entry)
    logger.info(f"LLM usage: {entry['total_tokens']} tokens ({entry['prompt_tokens']}+{entry['completion_tokens']}) [{purpose}]")

    # Also store in DB
    try:
        from app.database import AsyncSessionLocal
        from app.models import EventLog
        async with AsyncSessionLocal() as session:
            session.add(EventLog(
                event_type="api_usage",
                extra_json={
                    "service": "llm",
                    "model": model,
                    **entry,
                },
            ))
            await session.commit()
    except Exception:
        pass  # Don't fail on usage logging


async def call_llm(
    system_prompt: str,
    user_prompt: str,
    json_mode: bool = False,
    timeout: float = 120.0,
    purpose: str = "",
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
                    # Track usage
                    usage = data.get("usage", {})
                    if usage:
                        await _log_usage(MODEL, usage, purpose)
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

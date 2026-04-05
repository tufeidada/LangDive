import asyncio
from sqlalchemy import text
from app.database import async_engine

DEFAULTS = {
    "vocab_baseline": "3500",
    "keywords": '["AI","Finance","Tech","Management"]',
    "daily_content_count": "5",
    "video_count_min": "1",
    "video_count_max": "2",
    "tts_provider": "google",
    "tts_fallback": "qwen",
    "tts_speed": "1.0",
    "show_chinese": "false",
    "daily_new_word_cap": "20",
    "daily_review_cap": "50",
}


async def seed():
    async with async_engine.begin() as conn:
        for k, v in DEFAULTS.items():
            await conn.execute(
                text("INSERT INTO settings (key, value) VALUES (:k, :v) ON CONFLICT (key) DO NOTHING"),
                {"k": k, "v": v},
            )
    print("Settings seeded.")


if __name__ == "__main__":
    asyncio.run(seed())

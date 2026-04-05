import pytest
import pytest_asyncio
from sqlalchemy import text
from app.database import AsyncSessionLocal, async_engine
from app.services.cache import get_cached, set_cached
from app.models import Base


@pytest_asyncio.fixture(autouse=True)
async def setup_tables():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with async_engine.begin() as conn:
        await conn.execute(text("DELETE FROM cached_asset"))


@pytest.mark.asyncio
async def test_cache_miss_returns_none():
    async with AsyncSessionLocal() as session:
        result = await get_cached(session, "hash123", "raw_text")
        assert result is None


@pytest.mark.asyncio
async def test_cache_set_and_get_text():
    async with AsyncSessionLocal() as session:
        await set_cached(session, "hash123", "raw_text", text_content="hello world")
        await session.commit()
    async with AsyncSessionLocal() as session:
        result = await get_cached(session, "hash123", "raw_text")
        assert result == "hello world"


@pytest.mark.asyncio
async def test_cache_set_and_get_file():
    async with AsyncSessionLocal() as session:
        await set_cached(session, "hash456", "tts_en", file_path="/data/audio/1_0.mp3")
        await session.commit()
    async with AsyncSessionLocal() as session:
        result = await get_cached(session, "hash456", "tts_en")
        assert result == "/data/audio/1_0.mp3"

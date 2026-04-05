import pytest
import pytest_asyncio
from sqlalchemy import delete
from app.database import async_engine, AsyncSessionLocal
from app.models import Base, Vocabulary

# Words touched by these tests — cleaned up before each test run
_TEST_WORDS = ["paradigm", "ubiquitous", "resilience", "scalable"]


@pytest_asyncio.fixture(autouse=True)
async def setup():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        await session.execute(delete(Vocabulary).where(Vocabulary.word.in_(_TEST_WORDS)))
        await session.commit()
    async with AsyncSessionLocal() as session:
        v = Vocabulary(word="paradigm", meaning_zh="范式", level="IELTS", status="unknown")
        session.add(v)
        await session.commit()
    yield


@pytest.mark.asyncio
async def test_get_vocab_list(client):
    resp = await client.get("/api/vocab")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_add_word(client):
    resp = await client.post("/api/vocab", json={"word": "ubiquitous", "meaning_zh": "无处不在的"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_update_word_status(client):
    resp = await client.put("/api/vocab/paradigm/status", json={"status": "known"})
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_review_word(client):
    resp = await client.put("/api/vocab/paradigm/review", json={"grade": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert data["srs_level"] == 1


@pytest.mark.asyncio
async def test_preview_add_all(client):
    words = [
        {"word": "resilience", "meaning_zh": "韧性", "level": "IELTS"},
        {"word": "scalable", "meaning_zh": "可扩展的", "level": "CET-6"},
    ]
    resp = await client.post("/api/vocab/preview-add-all", json={"words": words})
    assert resp.status_code == 200
    assert resp.json()["added"] == 2

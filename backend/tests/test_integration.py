import pytest
import pytest_asyncio
from sqlalchemy import delete
from app.database import async_engine, AsyncSessionLocal
from app.models import Base, Vocabulary

_TEST_WORDS = ["serendipity"]


@pytest_asyncio.fixture(autouse=True)
async def setup():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        await session.execute(delete(Vocabulary).where(Vocabulary.word.in_(_TEST_WORDS)))
        await session.commit()
    yield


@pytest.mark.asyncio
async def test_full_api_flow(client):
    """Test the complete user flow through API endpoints."""
    # 1. Check today's content (may be empty if pipeline hasn't run)
    resp = await client.get("/api/content/today")
    assert resp.status_code == 200

    # 2. Get settings
    resp = await client.get("/api/settings")
    assert resp.status_code == 200

    # 3. Add a word manually
    resp = await client.post("/api/vocab", json={"word": "serendipity", "meaning_zh": "偶然发现"})
    assert resp.status_code == 200

    # 4. Check vocab list
    resp = await client.get("/api/vocab")
    assert resp.status_code == 200
    words = resp.json()
    assert any(w["word"] == "serendipity" for w in words)

    # 5. Log an event
    resp = await client.post("/api/events", json={"event_type": "word_add", "word": "serendipity"})
    assert resp.status_code == 200

    # 6. Update word status
    resp = await client.put("/api/vocab/serendipity/status", json={"status": "focus"})
    assert resp.status_code == 200

    # 7. Review word
    resp = await client.put("/api/vocab/serendipity/review", json={"grade": 2})
    assert resp.status_code == 200
    assert resp.json()["srs_level"] == 1

    # 8. Health check
    resp = await client.get("/api/health")
    assert resp.status_code == 200

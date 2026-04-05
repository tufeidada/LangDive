import pytest
import pytest_asyncio
from app.database import async_engine
from app.models import Base

@pytest_asyncio.fixture(autouse=True)
async def setup():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

@pytest.mark.asyncio
async def test_post_event(client):
    resp = await client.post("/api/events", json={"event_type": "content_open", "content_id": 1})
    assert resp.status_code == 200

@pytest.mark.asyncio
async def test_post_event_minimal(client):
    resp = await client.post("/api/events", json={"event_type": "toggle_chinese"})
    assert resp.status_code == 200

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

@pytest.mark.asyncio
async def test_get_stats_default(client):
    resp = await client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["period_days"] == 7
    assert "content_opened" in data
    assert "segments_completed" in data
    assert "words_added" in data
    assert "words_reviewed" in data
    assert "review_accuracy" in data
    assert "again" in data["review_accuracy"]
    assert "hard" in data["review_accuracy"]
    assert "easy" in data["review_accuracy"]
    assert "total_events" in data
    assert "active_days" in data
    assert "vocab_total" in data
    assert "vocab_by_status" in data
    assert "daily_activity" in data
    assert len(data["daily_activity"]) == 7

@pytest.mark.asyncio
async def test_get_stats_30days(client):
    resp = await client.get("/api/stats?days=30")
    assert resp.status_code == 200
    data = resp.json()
    assert data["period_days"] == 30
    assert len(data["daily_activity"]) == 30

@pytest.mark.asyncio
async def test_get_stats_aggregates_events(client):
    # Post some events
    await client.post("/api/events", json={"event_type": "content_open", "content_id": 1})
    await client.post("/api/events", json={"event_type": "content_open", "content_id": 2})
    await client.post("/api/events", json={"event_type": "segment_complete", "content_id": 1, "segment_index": 0})
    await client.post("/api/events", json={"event_type": "word_add", "word": "hello"})
    await client.post("/api/events", json={"event_type": "review_grade", "word": "hello", "extra_json": {"grade": 2}})

    resp = await client.get("/api/stats?days=7")
    assert resp.status_code == 200
    data = resp.json()
    assert data["content_opened"] >= 2
    assert data["segments_completed"] >= 1
    assert data["words_added"] >= 1
    assert data["words_reviewed"] >= 1
    assert data["total_events"] >= 5
    assert data["active_days"] >= 1

import pytest
import pytest_asyncio
from datetime import date
from app.database import async_engine, AsyncSessionLocal
from app.models import Base, Content, ContentSegment


@pytest_asyncio.fixture(autouse=True)
async def setup():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        c = Content(
            type="article", title="Test Article", source="TestSource",
            url="https://example.com", difficulty="B1", date=date.today(),
            segment_count=1, has_subtitles=True, content_text="Test content.",
            summary_zh="测试摘要", preview_words_json=[{"word": "test"}],
        )
        session.add(c)
        await session.flush()
        seg = ContentSegment(
            content_id=c.id, segment_index=0, title="Full",
            text_en="Test content.", preview_words_json=[{"word": "test"}],
            words_json=[{"word": "test", "meaning_zh": "测试"}],
        )
        session.add(seg)
        await session.commit()
    yield


@pytest.mark.asyncio
async def test_get_today_content(client):
    resp = await client.get("/api/content/today")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["title"] == "Test Article"


@pytest.mark.asyncio
async def test_get_content_detail(client):
    resp = await client.get("/api/content/today")
    content_id = resp.json()[0]["id"]
    resp = await client.get(f"/api/content/{content_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Test Article"


@pytest.mark.asyncio
async def test_get_segments(client):
    resp = await client.get("/api/content/today")
    content_id = resp.json()[0]["id"]
    resp = await client.get(f"/api/content/{content_id}/segments")
    assert resp.status_code == 200
    segments = resp.json()
    assert len(segments) == 1
    assert segments[0]["title"] == "Full"


@pytest.mark.asyncio
async def test_mark_segment_complete(client):
    resp = await client.get("/api/content/today")
    content_id = resp.json()[0]["id"]
    resp = await client.post(f"/api/content/{content_id}/segments/0/complete")
    assert resp.status_code == 200

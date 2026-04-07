import pytest
import pytest_asyncio
from datetime import date
from sqlalchemy import delete
from app.database import async_engine, AsyncSessionLocal
from app.models import Base, Content, ContentSegment


@pytest_asyncio.fixture(autouse=True)
async def setup():
    """Insert test data, yield, then clean up. Never touches real content."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Insert test content
    test_content_id = None
    async with AsyncSessionLocal() as session:
        c = Content(
            type="article", title="__TEST_ARTICLE__", source="TestSource",
            url="https://example.com/test", difficulty="B1", date=date.today(),
            segment_count=1, has_subtitles=True, content_text="Test content for automated tests.",
            summary_zh="测试摘要", preview_words_json=[{"word": "test"}],
        )
        session.add(c)
        await session.flush()
        test_content_id = c.id
        seg = ContentSegment(
            content_id=c.id, segment_index=0, title="Full",
            text_en="Test content for automated tests.",
            preview_words_json=[{"word": "test"}],
            words_json=[{"word": "test", "meaning_zh": "测试"}],
        )
        session.add(seg)
        await session.commit()

    yield test_content_id

    # Clean up test data — only delete what we created
    async with AsyncSessionLocal() as session:
        await session.execute(delete(ContentSegment).where(ContentSegment.content_id == test_content_id))
        await session.execute(delete(Content).where(Content.id == test_content_id))
        await session.commit()


@pytest.mark.asyncio
async def test_get_today_content(client, setup):
    resp = await client.get("/api/content/today")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # Find our test article (don't assume position)
    test_items = [d for d in data if d["title"] == "__TEST_ARTICLE__"]
    assert len(test_items) == 1


@pytest.mark.asyncio
async def test_get_content_detail(client, setup):
    content_id = setup  # fixture returns the test content id
    resp = await client.get(f"/api/content/{content_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "__TEST_ARTICLE__"


@pytest.mark.asyncio
async def test_get_segments(client, setup):
    content_id = setup
    resp = await client.get(f"/api/content/{content_id}/segments")
    assert resp.status_code == 200
    segments = resp.json()
    assert len(segments) == 1
    assert segments[0]["title"] == "Full"


@pytest.mark.asyncio
async def test_mark_segment_complete(client, setup):
    content_id = setup
    resp = await client.post(f"/api/content/{content_id}/segments/0/complete")
    assert resp.status_code == 200

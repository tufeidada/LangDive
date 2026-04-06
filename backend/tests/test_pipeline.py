import pytest
from unittest.mock import AsyncMock, patch
import json
from app.pipeline.steps import (
    step1_fetch_candidates,
    step2_filter_and_rank,
    step3_extract_content,
)


@pytest.mark.asyncio
async def test_step1_fetch_candidates():
    mock_queries = '["AI interview 2026", "tech leadership discussion"]'
    mock_yt_results = [
        {
            "video_id": "abc",
            "title": "Test Video",
            "type": "video",
            "source": "youtube",
            "url": "https://youtube.com/watch?v=abc",
        }
    ]
    mock_rss_results = [
        {
            "title": "RSS Article",
            "url": "https://example.com",
            "type": "article",
            "source": "TechCrunch",
        }
    ]

    with patch("app.pipeline.steps.call_llm", new_callable=AsyncMock, return_value=mock_queries):
        with patch("app.pipeline.steps.search_youtube", new_callable=AsyncMock, return_value=mock_yt_results):
            with patch("app.pipeline.steps.filter_by_view_count", new_callable=AsyncMock, return_value=mock_yt_results):
                with patch("app.pipeline.steps.fetch_all_rss_candidates", return_value=mock_rss_results):
                    with patch("app.pipeline.steps.AsyncSessionLocal") as mock_session_cls:
                        mock_session = AsyncMock()
                        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                        mock_session.__aexit__ = AsyncMock(return_value=False)
                        mock_session_cls.return_value = mock_session
                        candidates = await step1_fetch_candidates()
                        assert len(candidates) >= 2


@pytest.mark.asyncio
async def test_step2_filter_returns_max_5():
    candidates = [
        {"title": f"Item {i}", "type": "article", "source": "test", "url": f"https://example.com/{i}"}
        for i in range(20)
    ]
    candidates[0]["type"] = "video"
    candidates[1]["type"] = "video"

    selected_json = json.dumps([
        {"title": "Item 0", "type": "video", "difficulty": "B1", "relevance": 0.9, "url": "https://example.com/0", "source": "test"},
        {"title": "Item 1", "type": "video", "difficulty": "B2", "relevance": 0.8, "url": "https://example.com/1", "source": "test"},
        {"title": "Item 2", "type": "article", "difficulty": "B1", "relevance": 0.85, "url": "https://example.com/2", "source": "test"},
        {"title": "Item 3", "type": "article", "difficulty": "A2", "relevance": 0.7, "url": "https://example.com/3", "source": "test"},
        {"title": "Item 4", "type": "article", "difficulty": "B2", "relevance": 0.6, "url": "https://example.com/4", "source": "test"},
    ])

    with patch("app.pipeline.steps.call_llm", new_callable=AsyncMock, return_value=selected_json):
        result = await step2_filter_and_rank(candidates)
        assert len(result) <= 5
        video_count = sum(1 for r in result if r.get("type") == "video")
        assert video_count <= 2


@pytest.mark.asyncio
async def test_step2_empty_candidates():
    """Empty input returns empty list without errors."""
    result = await step2_filter_and_rank([])
    assert result == []


@pytest.mark.asyncio
async def test_step2_fills_articles_when_no_videos():
    """When LLM returns 0 videos, fills from article candidates."""
    candidates = [
        {"title": f"Article {i}", "type": "article", "source": "test", "url": f"https://example.com/{i}"}
        for i in range(10)
    ]

    # LLM returns no videos
    selected_json = json.dumps([
        {"title": "Article 0", "type": "article", "difficulty": "B1", "relevance": 0.9, "url": "https://example.com/0", "source": "test"},
    ])

    with patch("app.pipeline.steps.call_llm", new_callable=AsyncMock, return_value=selected_json):
        result = await step2_filter_and_rank(candidates)
        assert len(result) <= 5
        video_count = sum(1 for r in result if r.get("type") == "video")
        assert video_count == 0


@pytest.mark.asyncio
async def test_step3_extract_content_article():
    """Article items get content_text via extract_article_text."""
    items = [
        {"title": "Test Article", "type": "article", "url": "https://example.com/1", "source": "test"},
    ]
    with patch("app.pipeline.steps.extract_article_text", return_value="Sample article text"):
        result = await step3_extract_content(items)
        assert result[0]["content_text"] == "Sample article text"
        assert result[0]["has_subtitles"] is False


@pytest.mark.asyncio
async def test_step3_extract_content_video_with_transcript():
    """Video items get content_text from transcript and has_subtitles=True."""
    items = [
        {"title": "Test Video", "type": "video", "url": "https://youtube.com/watch?v=abc123", "source": "youtube"},
    ]
    mock_transcript = [{"text": "Hello world", "start": 0.0, "duration": 2.0}]
    with patch("app.pipeline.steps.fetch_transcript", return_value=mock_transcript):
        result = await step3_extract_content(items)
        assert result[0]["content_text"] == "Hello world"
        assert result[0]["has_subtitles"] is True


@pytest.mark.asyncio
async def test_step3_extract_content_video_no_transcript():
    """Video items with no transcript get has_subtitles=False."""
    items = [
        {"title": "Test Video", "type": "video", "url": "https://youtube.com/watch?v=abc123", "source": "youtube"},
    ]
    with patch("app.pipeline.steps.fetch_transcript", return_value=None):
        result = await step3_extract_content(items)
        assert result[0]["content_text"] is None
        assert result[0]["has_subtitles"] is False

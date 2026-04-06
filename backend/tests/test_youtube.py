import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.youtube import search_youtube, fetch_transcript

@pytest.mark.asyncio
async def test_search_youtube_returns_videos():
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "items": [
            {
                "id": {"videoId": "abc123"},
                "snippet": {
                    "title": "AI Interview",
                    "channelTitle": "TechChannel",
                    "publishedAt": "2026-04-01T00:00:00Z",
                }
            }
        ]
    }
    with patch("app.services.youtube.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.get.return_value = mock_resp
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance
        results = await search_youtube("AI interview 2026")
        assert len(results) == 1
        assert results[0]["video_id"] == "abc123"

def test_fetch_transcript_returns_subtitles():
    mock_transcript = [
        {"text": "Hello world", "start": 0.0, "duration": 2.5},
        {"text": "This is a test", "start": 2.5, "duration": 3.0},
    ]
    with patch("app.services.youtube.YouTubeTranscriptApi") as MockApi:
        MockApi.get_transcript.return_value = mock_transcript
        result = fetch_transcript("abc123")
        assert len(result) == 2
        assert result[0]["text"] == "Hello world"

def test_fetch_transcript_no_subtitles():
    with patch("app.services.youtube.YouTubeTranscriptApi") as MockApi:
        MockApi.get_transcript.side_effect = Exception("No subtitles")
        result = fetch_transcript("abc123")
        assert result is None

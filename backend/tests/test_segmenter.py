import pytest
import json
from unittest.mock import AsyncMock, patch
from app.services.segmenter import segment_content

@pytest.mark.asyncio
async def test_short_content_returns_single_segment():
    result = await segment_content("Short article text under 800 words.", content_type="article")
    assert len(result) == 1
    assert result[0]["segment_index"] == 0
    assert result[0]["text_en"] == "Short article text under 800 words."

@pytest.mark.asyncio
async def test_long_content_calls_llm():
    long_text = "word " * 900  # > 800 words
    llm_response = json.dumps([
        {"segment_index": 0, "title": "Part 1", "start_time": None, "end_time": None, "text_en": "word " * 450},
        {"segment_index": 1, "title": "Part 2", "start_time": None, "end_time": None, "text_en": "word " * 450},
    ])
    with patch("app.services.segmenter.call_llm", new_callable=AsyncMock, return_value=llm_response):
        result = await segment_content(long_text, content_type="article")
        assert len(result) == 2
        assert result[0]["title"] == "Part 1"

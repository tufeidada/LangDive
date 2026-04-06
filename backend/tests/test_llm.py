import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.llm import call_llm

@pytest.mark.asyncio
async def test_call_llm_returns_content():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "test response"}}]
    }
    with patch("app.services.llm.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.return_value = mock_response
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance
        result = await call_llm("system prompt", "user prompt")
        assert result == "test response"

@pytest.mark.asyncio
async def test_call_llm_json_mode():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": '[{"word": "test"}]'}}]
    }
    with patch("app.services.llm.httpx.AsyncClient") as MockClient:
        instance = AsyncMock()
        instance.post.return_value = mock_response
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value = instance
        result = await call_llm("system", "user", json_mode=True)
        parsed = json.loads(result)
        assert parsed[0]["word"] == "test"

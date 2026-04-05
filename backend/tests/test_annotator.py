import pytest
import json
from unittest.mock import AsyncMock, patch
from app.services.annotator import annotate_vocabulary, load_cet4_set

def test_load_cet4_set():
    words = load_cet4_set()
    assert isinstance(words, set)

@pytest.mark.asyncio
async def test_annotate_vocabulary_calls_llm():
    llm_response = json.dumps([
        {
            "word": "paradigm", "ipa": "/ˈpærədaɪm/", "freq_in_content": 3,
            "importance_score": 0.9, "meaning_zh": "范式",
            "detail_zh": "一种模式或模型", "example_en": "A new paradigm.",
            "example_zh": "一种新范式。", "level": "IELTS"
        }
    ])
    with patch("app.services.annotator.call_llm", new_callable=AsyncMock, return_value=llm_response):
        result = await annotate_vocabulary("The paradigm shift in AI is remarkable.")
        assert len(result) == 1
        assert result[0]["word"] == "paradigm"
        assert result[0]["level"] == "IELTS"

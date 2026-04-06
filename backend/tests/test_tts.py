import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.tts import generate_segment_audio


@pytest.mark.asyncio
async def test_generate_audio_google_success(tmp_path):
    with patch("app.services.tts._google_synthesize_rest", new_callable=AsyncMock, return_value=b"fake-mp3-data"):
        output_path = str(tmp_path / "test_audio.mp3")
        result = await generate_segment_audio("Hello world.", output_path)
        assert result == output_path
        with open(output_path, "rb") as f:
            assert f.read() == b"fake-mp3-data"


@pytest.mark.asyncio
async def test_generate_audio_google_fails_falls_back_to_qwen(tmp_path):
    with patch("app.services.tts._google_synthesize_rest", new_callable=AsyncMock, side_effect=Exception("Google TTS error")):
        with patch("app.services.tts._qwen_synthesize", return_value=b"fake-qwen-mp3"):
            output_path = str(tmp_path / "test_audio.mp3")
            result = await generate_segment_audio("Hello world.", output_path)
            assert result == output_path
            with open(output_path, "rb") as f:
                assert f.read() == b"fake-qwen-mp3"

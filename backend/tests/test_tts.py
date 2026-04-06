import pytest
from unittest.mock import patch, MagicMock
from app.services.tts import generate_segment_audio


@pytest.mark.asyncio
async def test_generate_audio_google_success(tmp_path):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.audio_content = b"fake-mp3-data"
    mock_client.synthesize_speech.return_value = mock_response

    with patch("app.services.tts._google_synthesize", return_value=b"fake-mp3-data"):
        output_path = str(tmp_path / "test_audio.mp3")
        result = await generate_segment_audio("Hello world.", output_path)
        assert result == output_path
        with open(output_path, "rb") as f:
            assert f.read() == b"fake-mp3-data"


@pytest.mark.asyncio
async def test_generate_audio_google_fails_falls_back_to_qwen(tmp_path):
    with patch("app.services.tts._google_synthesize", side_effect=Exception("Google TTS error")):
        with patch("app.services.tts._qwen_synthesize", return_value=b"fake-qwen-mp3"):
            output_path = str(tmp_path / "test_audio.mp3")
            result = await generate_segment_audio("Hello world.", output_path)
            assert result == output_path
            with open(output_path, "rb") as f:
                assert f.read() == b"fake-qwen-mp3"

import logging
import httpx
import asyncio
from google.cloud import texttospeech
from app.config import settings

logger = logging.getLogger(__name__)


def _google_synthesize(text: str) -> bytes:
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Neural2-D",
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        sample_rate_hertz=24000,
    )
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    return response.audio_content


async def _call_qwen_tts(text: str) -> bytes:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://dashscope.aliyuncs.com/api/v1/services/tts/text-to-speech",
            headers={"Authorization": f"Bearer {settings.DASHSCOPE_API_KEY}"},
            json={
                "model": "qwen-tts-2025-05-22",
                "input": {"text": text},
            },
        )
        resp.raise_for_status()
        return resp.content


async def generate_segment_audio(text: str, output_path: str) -> str:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text]

    all_audio = b""
    for para in paragraphs:
        audio_bytes = None
        # Try Google first
        try:
            audio_bytes = await asyncio.get_event_loop().run_in_executor(
                None, _google_synthesize, para
            )
        except Exception as e:
            logger.warning(f"Google TTS failed, falling back to Qwen: {e}")

        # Fallback to Qwen
        if audio_bytes is None:
            try:
                audio_bytes = await _call_qwen_tts(para)
            except Exception as e:
                logger.error(f"Qwen TTS also failed: {e}")
                continue

        if audio_bytes:
            all_audio += audio_bytes

    with open(output_path, "wb") as f:
        f.write(all_audio)

    return output_path

import logging
import asyncio
from app.config import settings

logger = logging.getLogger(__name__)


def _google_synthesize(text: str) -> bytes:
    from google.cloud import texttospeech
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


def _qwen_synthesize(text: str) -> bytes:
    import dashscope
    import urllib.request
    resp = dashscope.audio.qwen_tts.SpeechSynthesizer.call(
        model="qwen3-tts-flash",
        api_key=settings.DASHSCOPE_API_KEY,
        text=text,
        voice="Cherry",
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Qwen TTS failed: {resp.code} {resp.message}")
    audio_url = resp["output"]["audio"]["url"]
    with urllib.request.urlopen(audio_url) as r:
        return r.read()


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

        # Fallback to Qwen (DashScope SDK)
        if audio_bytes is None:
            try:
                audio_bytes = await asyncio.get_event_loop().run_in_executor(
                    None, _qwen_synthesize, para
                )
            except Exception as e:
                logger.error(f"Qwen TTS also failed: {e}")
                continue

        if audio_bytes:
            all_audio += audio_bytes

    with open(output_path, "wb") as f:
        f.write(all_audio)

    return output_path

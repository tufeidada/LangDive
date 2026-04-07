import logging
import asyncio
import json
import base64
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


def _get_google_access_token() -> str:
    """Get OAuth2 access token from service account JSON."""
    import os
    os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", settings.GOOGLE_APPLICATION_CREDENTIALS)
    import google.auth
    import google.auth.transport.requests
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    credentials.refresh(google.auth.transport.requests.Request())
    return credentials.token


async def _google_synthesize_rest(text: str) -> bytes:
    """Call Google TTS via REST API (works through HTTP proxy)."""
    token = await asyncio.get_event_loop().run_in_executor(None, _get_google_access_token)
    payload = {
        "input": {"text": text},
        "voice": {"languageCode": "en-US", "name": "en-US-Neural2-D"},
        "audioConfig": {"audioEncoding": "MP3", "sampleRateHertz": 24000},
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://texttospeech.googleapis.com/v1/text:synthesize",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json=payload,
        )
        resp.raise_for_status()
        audio_b64 = resp.json()["audioContent"]
        return base64.b64decode(audio_b64)


def _qwen_synthesize(text: str) -> bytes:
    """Call Qwen TTS via DashScope SDK."""
    import dashscope
    import urllib.request
    resp = dashscope.audio.qwen_tts.SpeechSynthesizer.call(
        model="qwen3-tts-instruct-flash",
        api_key=settings.DASHSCOPE_API_KEY,
        text=text,
        voice="Cherry",
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Qwen TTS failed: {resp.code} {resp.message}")
    audio_url = resp["output"]["audio"]["url"]
    with urllib.request.urlopen(audio_url) as r:
        return r.read()


def _split_text_for_tts(text: str, max_chars: int = 4000) -> list[str]:
    """Split text into chunks safe for TTS APIs."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text]
    # Further split any paragraph exceeding max_chars at sentence boundaries
    chunks = []
    for para in paragraphs:
        if len(para) <= max_chars:
            chunks.append(para)
        else:
            sentences = para.replace('. ', '.\n').split('\n')
            current = ""
            for sent in sentences:
                if len(current) + len(sent) + 1 > max_chars and current:
                    chunks.append(current.strip())
                    current = sent
                else:
                    current = current + " " + sent if current else sent
            if current.strip():
                chunks.append(current.strip())
    return chunks

async def generate_segment_audio(text: str, output_path: str) -> str:
    paragraphs = _split_text_for_tts(text)

    all_audio = b""
    for para in paragraphs:
        audio_bytes = None
        # Try Google REST API first (works through proxy)
        try:
            audio_bytes = await _google_synthesize_rest(para)
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

    if not all_audio:
        logger.error(f"No audio generated for {output_path}")
        return output_path

    with open(output_path, "wb") as f:
        f.write(all_audio)

    return output_path

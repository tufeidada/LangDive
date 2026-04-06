import inspect
import httpx
import logging
from datetime import datetime, timedelta, timezone
from youtube_transcript_api import YouTubeTranscriptApi
from app.config import settings

logger = logging.getLogger(__name__)

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"

async def search_youtube(query: str, max_results: int = 5) -> list[dict]:
    seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "order": "date",
        "publishedAfter": seven_days_ago,
        "videoCaption": "closedCaption",
        "maxResults": max_results,
        "key": settings.YOUTUBE_API_KEY,
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(YOUTUBE_SEARCH_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
        if inspect.isawaitable(data):
            data = await data
        items = data.get("items", [])
    return [
        {
            "video_id": item["id"]["videoId"],
            "title": item["snippet"]["title"],
            "channel": item["snippet"].get("channelTitle", ""),
            "published_at": item["snippet"]["publishedAt"],
            "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}",
            "type": "video",
            "source": "youtube",
        }
        for item in items
        if item.get("id", {}).get("videoId")
    ]

def fetch_transcript(video_id: str) -> list[dict] | None:
    try:
        # Try English first, then en-US, then any available with English translation
        for langs in [["en"], ["en-US"], ["en-GB"]]:
            try:
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=langs)
                return [
                    {"text": entry["text"], "start": entry["start"], "duration": entry["duration"]}
                    for entry in transcript
                ]
            except Exception:
                continue
        # Try auto-generated English
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        for t in transcript_list:
            if t.language_code.startswith("en"):
                entries = t.fetch()
                return [
                    {"text": e["text"], "start": e["start"], "duration": e["duration"]}
                    for e in entries
                ]
        logger.warning(f"No English transcript for {video_id}")
        return None
    except Exception as e:
        logger.warning(f"No transcript for {video_id}: {e}")
        return None

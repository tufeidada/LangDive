import inspect
import httpx
import logging
from datetime import datetime, timedelta, timezone
from youtube_transcript_api import YouTubeTranscriptApi
from app.config import settings

logger = logging.getLogger(__name__)

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"

async def search_youtube(query: str, max_results: int = 5) -> list[dict]:
    thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "order": "relevance",
        "publishedAfter": thirty_days_ago,
        "relevanceLanguage": "en",
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
    """Fetch English transcript using youtube-transcript-api v1.x."""
    try:
        api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id, languages=["en", "en-US", "en-GB"])
        return [
            {"text": snippet.text, "start": snippet.start, "duration": snippet.duration}
            for snippet in transcript
        ]
    except Exception as e:
        logger.warning(f"No transcript for {video_id}: {e}")
        return None

import inspect
import httpx
import logging
from datetime import datetime, timedelta, timezone
from youtube_transcript_api import YouTubeTranscriptApi
from app.config import settings

logger = logging.getLogger(__name__)

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


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


async def get_video_statistics(video_ids: list[str]) -> dict[str, dict]:
    """Fetch view counts and other stats for a batch of video IDs."""
    if not video_ids:
        return {}
    stats = {}
    # API supports up to 50 IDs per request
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        params = {
            "part": "statistics",
            "id": ",".join(batch),
            "key": settings.YOUTUBE_API_KEY,
        }
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(YOUTUBE_VIDEOS_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
                if inspect.isawaitable(data):
                    data = await data
                for item in data.get("items", []):
                    vid = item["id"]
                    s = item.get("statistics", {})
                    stats[vid] = {
                        "viewCount": int(s.get("viewCount", 0)),
                        "likeCount": int(s.get("likeCount", 0)),
                    }
        except Exception as e:
            logger.warning(f"Failed to fetch video statistics: {e}")
    return stats


async def filter_by_view_count(results: list[dict], min_views: int = 10000) -> list[dict]:
    """Filter YouTube results by minimum view count."""
    if not results:
        return results
    video_ids = [r["video_id"] for r in results]
    stats = await get_video_statistics(video_ids)
    filtered = []
    for r in results:
        vid = r["video_id"]
        views = stats.get(vid, {}).get("viewCount", 0)
        r["view_count"] = views
        if views >= min_views:
            filtered.append(r)
        else:
            logger.info(f"Filtered out video {vid} ({views} views < {min_views}): {r['title'][:50]}")
    logger.info(f"View count filter: {len(results)} → {len(filtered)} videos (min {min_views} views)")
    return filtered


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

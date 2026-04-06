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


def _parse_duration(iso_duration: str) -> int:
    """Parse ISO 8601 duration (PT1H2M3S) to seconds."""
    import re
    m = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso_duration or '')
    if not m:
        return 0
    hours = int(m.group(1) or 0)
    minutes = int(m.group(2) or 0)
    seconds = int(m.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


async def get_video_details(video_ids: list[str]) -> dict[str, dict]:
    """Fetch statistics + duration for a batch of video IDs."""
    if not video_ids:
        return {}
    details = {}
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        params = {
            "part": "statistics,contentDetails",
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
                    cd = item.get("contentDetails", {})
                    duration_sec = _parse_duration(cd.get("duration", ""))
                    details[vid] = {
                        "viewCount": int(s.get("viewCount", 0)),
                        "likeCount": int(s.get("likeCount", 0)),
                        "duration_seconds": duration_sec,
                        "duration_str": cd.get("duration", ""),
                    }
        except Exception as e:
            logger.warning(f"Failed to fetch video details: {e}")
    return details


async def filter_videos(
    results: list[dict],
    min_views: int = 10000,
    max_duration_sec: int = 600,
) -> list[dict]:
    """Filter YouTube results by view count and duration (default max 10 min)."""
    if not results:
        return results
    video_ids = [r["video_id"] for r in results]
    details = await get_video_details(video_ids)
    filtered = []
    for r in results:
        vid = r["video_id"]
        info = details.get(vid, {})
        views = info.get("viewCount", 0)
        dur = info.get("duration_seconds", 0)
        r["view_count"] = views
        r["duration_seconds"] = dur
        r["duration"] = f"{dur // 60}:{dur % 60:02d}"

        if views < min_views:
            logger.info(f"Filtered: {vid} ({views} views < {min_views}): {r['title'][:40]}")
            continue
        if dur > max_duration_sec:
            logger.info(f"Filtered: {vid} ({dur}s > {max_duration_sec}s): {r['title'][:40]}")
            continue
        if dur < 60:
            logger.info(f"Filtered: {vid} (too short {dur}s): {r['title'][:40]}")
            continue
        filtered.append(r)

    logger.info(f"Video filter: {len(results)} → {len(filtered)} (min {min_views} views, max {max_duration_sec}s)")
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

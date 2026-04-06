"""Multi-layer content fetcher for the three-layer content pool.

Layer 1: Whitelist sources (YouTube channels, newsletters, blogs, HN)
Layer 2: Classic library (random draw when Layer 1 is thin)
Layer 3: Search fallback (LLM-generated queries, emergency only)
"""

import logging
from datetime import datetime, timedelta, timezone

import feedparser
import httpx

from app.config import settings
from app.services.hn import fetch_hn_top
from app.services.newsletter_parser import extract_outbound_links
from app.services.youtube import _parse_duration

logger = logging.getLogger(__name__)

YOUTUBE_PLAYLIST_ITEMS_URL = "https://www.googleapis.com/youtube/v3/playlistItems"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


# ---------------------------------------------------------------------------
# YouTube channel fetcher (uses playlistItems.list, NOT search.list)
# ---------------------------------------------------------------------------

async def fetch_youtube_channels(sources: list[dict]) -> list[dict]:
    """Fetch latest videos from YouTube channels via uploads playlist.

    Args:
        sources: List of source dicts with extra_config containing
                 'uploads_playlist', 'channel_id', 'min_duration_minutes'.

    Returns:
        List of candidate dicts.
    """
    all_candidates = []
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)

    for src in sources:
        config = src.get("extra_config") or {}
        playlist_id = config.get("uploads_playlist")
        if not playlist_id:
            logger.warning(f"YouTube source '{src.get('name')}' has no uploads_playlist in extra_config")
            continue

        min_duration_sec = config.get("min_duration_minutes", 5) * 60

        try:
            # Step 1: Get latest playlist items
            params = {
                "part": "snippet",
                "playlistId": playlist_id,
                "maxResults": 5,
                "key": settings.YOUTUBE_API_KEY,
            }
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(YOUTUBE_PLAYLIST_ITEMS_URL, params=params)
                resp.raise_for_status()
                data = resp.json()

            items = data.get("items", [])
            if not items:
                continue

            # Step 2: Filter by publish date and get video details
            video_ids = []
            video_snippets = {}
            for item in items:
                snippet = item.get("snippet", {})
                published_str = snippet.get("publishedAt", "")
                vid = snippet.get("resourceId", {}).get("videoId")
                if not vid:
                    continue

                try:
                    published = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
                    if published < seven_days_ago:
                        continue
                except (ValueError, TypeError):
                    pass

                video_ids.append(vid)
                video_snippets[vid] = snippet

            if not video_ids:
                continue

            # Step 3: Get duration and caption info
            detail_params = {
                "part": "contentDetails,statistics",
                "id": ",".join(video_ids),
                "key": settings.YOUTUBE_API_KEY,
            }
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(YOUTUBE_VIDEOS_URL, params=detail_params)
                resp.raise_for_status()
                details = resp.json()

            for detail_item in details.get("items", []):
                vid = detail_item["id"]
                snippet = video_snippets.get(vid)
                if not snippet:
                    continue

                content_details = detail_item.get("contentDetails", {})
                stats = detail_item.get("statistics", {})
                duration_sec = _parse_duration(content_details.get("duration", ""))

                # Filter by minimum duration
                if duration_sec < min_duration_sec:
                    continue

                published_str = snippet.get("publishedAt", "")
                published_at = None
                try:
                    published_at = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass

                all_candidates.append({
                    "title": snippet.get("title", ""),
                    "url": f"https://www.youtube.com/watch?v={vid}",
                    "video_id": vid,
                    "type": "video",
                    "source": src.get("name", "YouTube"),
                    "source_id": src.get("id"),
                    "channel": snippet.get("channelTitle", ""),
                    "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url"),
                    "duration": f"{duration_sec // 60}:{duration_sec % 60:02d}",
                    "duration_seconds": duration_sec,
                    "view_count": int(stats.get("viewCount", 0)),
                    "published_at": published_at,
                    "estimated_difficulty": src.get("default_difficulty"),
                    "tags": src.get("tags"),
                })

        except Exception as e:
            logger.error(f"Failed to fetch YouTube channel '{src.get('name')}': {e}")

    logger.info(f"YouTube channels: fetched {len(all_candidates)} candidates from {len(sources)} channels")
    return all_candidates


# ---------------------------------------------------------------------------
# Blog RSS fetcher
# ---------------------------------------------------------------------------

async def fetch_blog_rss(sources: list[dict]) -> list[dict]:
    """Fetch new articles from blog RSS feeds.

    Args:
        sources: List of source dicts with 'url' as RSS feed URL.

    Returns:
        List of candidate dicts.
    """
    all_candidates = []
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)

    for src in sources:
        feed_url = src.get("url", "")
        if not feed_url:
            continue

        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:10]:  # limit per source
                # Try to filter by date
                published_at = None
                published_str = entry.get("published") or entry.get("updated")
                if published_str:
                    try:
                        import email.utils
                        parsed_time = email.utils.parsedate_to_datetime(published_str)
                        published_at = parsed_time
                        if parsed_time.tzinfo and parsed_time < seven_days_ago:
                            continue
                    except (ValueError, TypeError):
                        pass

                all_candidates.append({
                    "title": entry.get("title", "Untitled"),
                    "url": entry.get("link", ""),
                    "type": "article",
                    "source": src.get("name", feed.feed.get("title", feed_url)),
                    "source_id": src.get("id"),
                    "published_at": published_at,
                    "estimated_difficulty": src.get("default_difficulty"),
                    "tags": src.get("tags"),
                })

        except Exception as e:
            logger.error(f"RSS fetch failed for '{src.get('name')}' ({feed_url}): {e}")

    logger.info(f"Blog RSS: fetched {len(all_candidates)} candidates from {len(sources)} feeds")
    return all_candidates


# ---------------------------------------------------------------------------
# Newsletter RSS fetcher (extracts outbound links)
# ---------------------------------------------------------------------------

async def fetch_newsletter_links(sources: list[dict]) -> list[dict]:
    """Fetch newsletters via RSS and extract outbound article links.

    Args:
        sources: List of newsletter source dicts with extra_config.

    Returns:
        List of candidate dicts (one per extracted link).
    """
    all_candidates = []

    for src in sources:
        feed_url = src.get("url", "")
        config = src.get("extra_config") or {}
        max_links = config.get("max_links_per_issue", 10)
        extract_links = config.get("extract_links", True)

        if not feed_url:
            continue

        try:
            feed = feedparser.parse(feed_url)
            # Process only the latest 2 issues
            for entry in feed.entries[:2]:
                if not extract_links:
                    # Treat the issue itself as a candidate
                    all_candidates.append({
                        "title": entry.get("title", "Untitled"),
                        "url": entry.get("link", ""),
                        "type": "article",
                        "source": src.get("name", "Newsletter"),
                        "source_id": src.get("id"),
                        "published_at": None,
                        "estimated_difficulty": src.get("default_difficulty"),
                        "tags": src.get("tags"),
                    })
                    continue

                # Extract the HTML body
                html = ""
                if entry.get("content"):
                    html = entry["content"][0].get("value", "")
                elif entry.get("summary"):
                    html = entry["summary"]

                if not html:
                    continue

                # Parse newsletter domain to skip internal links
                from urllib.parse import urlparse
                newsletter_domain = urlparse(feed_url).netloc

                links = extract_outbound_links(
                    html,
                    newsletter_domain=newsletter_domain,
                    max_links=max_links,
                )

                for link in links:
                    all_candidates.append({
                        "title": link["title"],
                        "url": link["url"],
                        "type": "article",
                        "source": f"{src.get('name', 'Newsletter')} (link)",
                        "source_id": src.get("id"),
                        "published_at": None,
                        "estimated_difficulty": src.get("default_difficulty"),
                        "tags": src.get("tags"),
                    })

        except Exception as e:
            logger.error(f"Newsletter fetch failed for '{src.get('name')}' ({feed_url}): {e}")

    logger.info(f"Newsletters: extracted {len(all_candidates)} link candidates from {len(sources)} newsletters")
    return all_candidates


# ---------------------------------------------------------------------------
# Hacker News fetcher (wraps hn.py)
# ---------------------------------------------------------------------------

async def fetch_hn(source: dict) -> list[dict]:
    """Fetch top HN stories via Algolia API.

    Args:
        source: The HN source dict with extra_config.

    Returns:
        List of candidate dicts.
    """
    config = source.get("extra_config") or {}
    min_score = config.get("min_score", 100)
    max_items = config.get("max_items", 10)

    results = await fetch_hn_top(min_score=min_score, max_items=max_items)

    # Attach source metadata
    for r in results:
        r["source_id"] = source.get("id")
        r["estimated_difficulty"] = source.get("default_difficulty")
        r["tags"] = source.get("tags")

    return results


# ---------------------------------------------------------------------------
# Classic library draw
# ---------------------------------------------------------------------------

async def draw_classics(session, needed: int) -> list[dict]:
    """Random draw from classic library items.

    Args:
        session: SQLAlchemy async session.
        needed: Number of items to draw.

    Returns:
        List of candidate dicts.
    """
    from sqlalchemy import select, func
    from app.models import ContentCandidate

    if needed <= 0:
        return []

    stmt = (
        select(ContentCandidate)
        .where(ContentCandidate.status == "library")
        .order_by(func.random())
        .limit(needed)
    )
    result = await session.execute(stmt)
    classics = result.scalars().all()

    drawn = []
    for c in classics:
        drawn.append({
            "title": c.title,
            "url": c.url,
            "type": c.type or "article",
            "source": "Classic Library",
            "source_id": c.source_id,
            "estimated_difficulty": c.estimated_difficulty,
            "candidate_id": c.id,  # track which library item was drawn
        })

    logger.info(f"Classic library: drew {len(drawn)} items (requested {needed})")
    return drawn

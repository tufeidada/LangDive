"""Hacker News client using the Algolia HN API."""

import logging
from datetime import datetime, timedelta, timezone

import httpx

logger = logging.getLogger(__name__)

HN_ALGOLIA_URL = "https://hn.algolia.com/api/v1/search"


async def fetch_hn_top(
    min_score: int = 100,
    max_items: int = 10,
    hours: int = 48,
) -> list[dict]:
    """Fetch top HN stories with score >= min_score from the last `hours` hours.

    Returns a list of candidate dicts ready for content_candidate insertion.
    """
    cutoff_ts = int((datetime.now(timezone.utc) - timedelta(hours=hours)).timestamp())
    params = {
        "tags": "story",
        "numericFilters": f"points>{min_score},created_at_i>{cutoff_ts}",
        "hitsPerPage": max_items * 2,  # fetch extra, filter below
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(HN_ALGOLIA_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.error(f"HN Algolia API request failed: {e}")
        return []

    hits = data.get("hits", [])
    results = []

    for hit in hits:
        title = hit.get("title", "")
        url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"

        # Skip Ask HN, Show HN, job posts
        title_lower = title.lower()
        if any(prefix in title_lower for prefix in ("ask hn:", "show hn:", "launch hn:", "hiring")):
            continue

        # Skip items without an external URL (self-posts)
        if not hit.get("url"):
            continue

        published_str = hit.get("created_at")
        published_at = None
        if published_str:
            try:
                published_at = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        results.append({
            "title": title,
            "url": url,
            "type": "article",
            "source": "Hacker News",
            "hn_score": hit.get("points", 0),
            "hn_comments": hit.get("num_comments", 0),
            "published_at": published_at,
        })

        if len(results) >= max_items:
            break

    logger.info(f"HN: fetched {len(results)} stories (score>{min_score}, last {hours}h)")
    return results

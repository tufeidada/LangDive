import feedparser
import trafilatura
import logging

logger = logging.getLogger(__name__)

RSS_SOURCES = [
    {"name": "TechCrunch", "url": "https://feeds.feedburner.com/TechCrunch"},
    {"name": "MIT Tech Review", "url": "https://www.technologyreview.com/feed"},
    {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica"},
    {"name": "BBC Tech", "url": "https://feeds.bbci.co.uk/news/technology/rss.xml"},
    {"name": "Reuters Tech", "url": "https://www.reuters.com/technology"},
]

def fetch_rss_candidates(feed_url: str) -> list[dict]:
    try:
        feed = feedparser.parse(feed_url)
        return [
            {
                "title": entry.title,
                "url": entry.link,
                "source": feed.feed.get("title", feed_url),
                "type": "article",
                "published_at": entry.get("published", None),
            }
            for entry in feed.entries
        ]
    except Exception as e:
        logger.error(f"RSS fetch failed for {feed_url}: {e}")
        return []

def fetch_all_rss_candidates() -> list[dict]:
    all_candidates = []
    for source in RSS_SOURCES:
        candidates = fetch_rss_candidates(source["url"])
        all_candidates.extend(candidates)
    return all_candidates

def extract_article_text(url: str) -> str | None:
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded is None:
            return None
        return trafilatura.extract(downloaded)
    except Exception as e:
        logger.error(f"Article extraction failed for {url}: {e}")
        return None

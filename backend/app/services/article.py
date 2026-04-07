import os
import re
import feedparser
import trafilatura
import logging
from app.config import settings

logger = logging.getLogger(__name__)

# Set proxy env vars so trafilatura/feedparser/urllib pick them up
if settings.HTTP_PROXY:
    os.environ["HTTP_PROXY"] = settings.HTTP_PROXY
if settings.HTTPS_PROXY:
    os.environ["HTTPS_PROXY"] = settings.HTTPS_PROXY

RSS_SOURCES = [
    {"name": "MIT Tech Review", "url": "https://www.technologyreview.com/feed"},
    {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica"},
    {"name": "BBC Tech", "url": "https://feeds.bbci.co.uk/news/technology/rss.xml"},
    {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
    {"name": "Wired", "url": "https://www.wired.com/feed/rss"},
    {"name": "Nature News", "url": "https://www.nature.com/nature.rss"},
    {"name": "The Guardian Tech", "url": "https://www.theguardian.com/technology/rss"},
]

# Patterns that indicate footer/related content — truncate from here
_FOOTER_RE = re.compile(
    r'^(Related|See also|More from|Read more|Also read|You may also like|'
    r'Recommended|Popular|Trending|Sign up|Subscribe|Follow us|Newsletter|'
    r'Copyright|Share this|Tags:|Filed under|More on this|Keep reading)',
    re.IGNORECASE,
)


def _clean_article_text(text: str | None) -> str | None:
    """Remove related-articles and footer sections from extracted text."""
    if not text:
        return text
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        if _FOOTER_RE.match(line.strip()):
            break
        cleaned.append(line)
    result = '\n'.join(cleaned).strip()
    return result or None


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
    # Filter out low-quality sources
    all_candidates = [
        c for c in all_candidates
        if 'blogspot' not in (c.get('url', '') + c.get('source', '')).lower()
    ]
    return all_candidates


def extract_article_text(url: str, min_words: int = 300) -> str | None:
    """Extract article text preserving paragraph structure and subheadings."""
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        if not html:
            return None

        # Extract with formatting options to preserve structure
        text = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=False,
            favor_precision=True,     # less noise
            output_format='txt',      # preserve paragraph breaks (\n\n)
        )
        text = _clean_article_text(text)

        # Post-process: ensure paragraph breaks exist between long lines
        if text and '\n\n' not in text:
            lines = text.split('\n')
            rebuilt = []
            for line in lines:
                if rebuilt and len(line) > 50 and len(rebuilt[-1]) > 50:
                    rebuilt.append('')  # insert blank line = paragraph break
                rebuilt.append(line)
            text = '\n'.join(rebuilt)

        if not text:
            return None

        word_count = len(text.split())

        # Filter: too short = probably paywall, homepage, or stub
        if word_count < min_words:
            logger.info(f"Rejected (too short: {word_count} words): {url}")
            return None

        # Filter: paywall indicators
        paywall_markers = [
            "subscribe to continue", "sign up to read", "members only",
            "premium content", "create a free account", "already a subscriber",
            "this content is for subscribers", "unlock this article",
        ]
        text_lower = text.lower()
        for marker in paywall_markers:
            if marker in text_lower and word_count < 500:
                logger.info(f"Rejected (likely paywall): {url}")
                return None

        return text
    except Exception as e:
        logger.error(f"Article extraction failed for {url}: {e}")
        return None

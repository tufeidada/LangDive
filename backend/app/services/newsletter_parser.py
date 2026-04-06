"""Parse newsletter HTML and extract outbound article links.

Newsletters like TLDR AI and Ben's Bites are meta-curators that link to
original articles. This module extracts those outbound links, filtering out
internal navigation, social media, and unsubscribe links.
"""

import logging
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Domains / patterns to skip (navigation, social, tracking, internal)
_SKIP_DOMAINS = {
    "twitter.com", "x.com",
    "facebook.com", "fb.com",
    "linkedin.com",
    "instagram.com",
    "youtube.com", "youtu.be",  # we handle YT channels separately
    "reddit.com",
    "t.me", "telegram.org",
    "discord.com", "discord.gg",
    "github.com",  # usually code repos, not articles
    "apps.apple.com", "play.google.com",
    "mailto:",
}

_SKIP_PATH_PATTERNS = re.compile(
    r"(unsubscribe|manage.preferences|email-preferences|opt-out|privacy|terms|"
    r"login|signup|register|account|settings|contact|about|faq|help|"
    r"sponsor|advertise|careers|jobs)",
    re.IGNORECASE,
)

# Tracking / redirect URL patterns
_TRACKING_PATTERNS = re.compile(
    r"(click\.|tracking\.|links\.|email\.|campaign-archive|mailchimp\.com|"
    r"list-manage\.com|substack\.com/subscribe|buttondown\.email)",
    re.IGNORECASE,
)


def extract_outbound_links(
    html: str,
    newsletter_domain: str | None = None,
    max_links: int = 10,
) -> list[dict]:
    """Extract outbound article links from newsletter HTML body.

    Args:
        html: Raw HTML of the newsletter issue.
        newsletter_domain: Domain of the newsletter itself (to skip internal links).
        max_links: Maximum number of links to return.

    Returns:
        List of dicts with 'title' and 'url' keys.
    """
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")

    # Remove nav, header, footer elements
    for tag in soup.find_all(["nav", "header", "footer"]):
        tag.decompose()

    links = []
    seen_urls = set()

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()

        # Skip empty, anchor, and mailto links
        if not href or href.startswith("#") or href.startswith("mailto:"):
            continue

        # Parse URL
        try:
            parsed = urlparse(href)
        except Exception:
            continue

        domain = parsed.netloc.lower()

        # Skip if no domain (relative link) or matches skip list
        if not domain:
            continue
        if any(skip in domain for skip in _SKIP_DOMAINS):
            continue

        # Skip internal newsletter links
        if newsletter_domain and newsletter_domain in domain:
            continue

        # Skip tracking/redirect URLs
        if _TRACKING_PATTERNS.search(href):
            continue

        # Skip navigation-looking paths
        path = parsed.path.lower()
        if _SKIP_PATH_PATTERNS.search(path):
            continue

        # Skip very short paths (likely homepages)
        if len(path.strip("/")) < 3:
            continue

        # Normalize URL (strip tracking params)
        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if clean_url in seen_urls:
            continue
        seen_urls.add(clean_url)

        # Extract link text as title
        text = a_tag.get_text(strip=True)
        if not text or len(text) < 5:
            continue
        # Skip if text is just "Read more", "Click here", etc.
        if text.lower() in ("read more", "click here", "link", "here", "source", "more"):
            continue

        links.append({
            "title": text[:200],
            "url": clean_url,
        })

        if len(links) >= max_links:
            break

    logger.info(f"Newsletter parser: extracted {len(links)} outbound links")
    return links

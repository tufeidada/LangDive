"""Seed the content_source table with all 25 whitelist sources from the addendum."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import ContentSource

SOURCES = [
    # Layer 1: YouTube Channels
    {"name": "Lex Fridman Podcast", "type": "youtube_channel", "layer": 1, "priority": 95,
     "url": "https://youtube.com/@lexfridman",
     "extra_config": {"channel_id": "UCSHZKyawb77ixDdsGog4iWA", "uploads_playlist": "UUSHZKyawb77ixDdsGog4iWA", "min_duration_minutes": 10},
     "tags": ["AI", "Tech"], "default_difficulty": "B2"},

    {"name": "All-In Podcast", "type": "youtube_channel", "layer": 1, "priority": 90,
     "url": "https://youtube.com/@alaborofjoy",
     "extra_config": {"channel_id": "UCESLZhusAkFfsNsApnjF_Cg", "uploads_playlist": "UUESLZhusAkFfsNsApnjF_Cg", "min_duration_minutes": 10},
     "tags": ["Finance", "Tech"], "default_difficulty": "B2"},

    {"name": "Bloomberg Technology", "type": "youtube_channel", "layer": 1, "priority": 85,
     "url": "https://youtube.com/@BloombergTelevision",
     "extra_config": {"channel_id": "UCrBzBOMcUVV8ryyAU_c6P5g", "uploads_playlist": "UUrBzBOMcUVV8ryyAU_c6P5g", "min_duration_minutes": 5},
     "tags": ["Finance", "Tech"], "default_difficulty": "B2"},

    {"name": "a16z", "type": "youtube_channel", "layer": 1, "priority": 80,
     "url": "https://youtube.com/@a16z",
     "extra_config": {"channel_id": "UC9cn0TuPq4dnbTY-CBsm8XA", "uploads_playlist": "UU9cn0TuPq4dnbTY-CBsm8XA", "min_duration_minutes": 5},
     "tags": ["Tech", "Finance"], "default_difficulty": "B2"},

    {"name": "Y Combinator", "type": "youtube_channel", "layer": 1, "priority": 80,
     "url": "https://youtube.com/@ycombinator",
     "extra_config": {"channel_id": "UCcefcZRL2oaA_uBNeo5UOWg", "uploads_playlist": "UUcefcZRL2oaA_uBNeo5UOWg", "min_duration_minutes": 5},
     "tags": ["Tech", "Management"], "default_difficulty": "B1"},

    {"name": "TED", "type": "youtube_channel", "layer": 1, "priority": 70,
     "url": "https://youtube.com/@TED",
     "extra_config": {"channel_id": "UCAuUUnT6oDeKwE6v1NGQxug", "uploads_playlist": "UUAuUUnT6oDeKwE6v1NGQxug", "min_duration_minutes": 5},
     "tags": ["General"], "default_difficulty": "B1"},

    {"name": "Acquired Podcast", "type": "youtube_channel", "layer": 1, "priority": 85,
     "url": "https://youtube.com/@AcquiredFM",
     "extra_config": {"channel_id": "UCyFqFYfTW2VoIQKylJ04Rtw", "uploads_playlist": "UUyFqFYfTW2VoIQKylJ04Rtw", "min_duration_minutes": 15},
     "tags": ["Tech", "Finance"], "default_difficulty": "B2"},

    {"name": "Patrick Boyle", "type": "youtube_channel", "layer": 1, "priority": 80,
     "url": "https://youtube.com/@PBoyle",
     "extra_config": {"channel_id": "UCASM0cgfkJxQ1ICmRilfHLw", "uploads_playlist": "UUASM0cgfkJxQ1ICmRilfHLw", "min_duration_minutes": 8},
     "tags": ["Finance"], "default_difficulty": "B2"},

    {"name": "Ben Felix", "type": "youtube_channel", "layer": 1, "priority": 75,
     "url": "https://youtube.com/@BenFelixCSI",
     "extra_config": {"channel_id": "UCDXTQ8nWmx_EhZ2v-kp7QxA", "uploads_playlist": "UUDXTQ8nWmx_EhZ2v-kp7QxA", "min_duration_minutes": 5},
     "tags": ["Finance"], "default_difficulty": "B2"},

    {"name": "Tim Ferriss Show", "type": "youtube_channel", "layer": 1, "priority": 75,
     "url": "https://youtube.com/@timferriss",
     "extra_config": {"channel_id": "UCznv7Vf9nBdJYvBagFdAHWw", "uploads_playlist": "UUznv7Vf9nBdJYvBagFdAHWw", "min_duration_minutes": 10},
     "tags": ["Management", "General"], "default_difficulty": "B2"},

    # Layer 1: Newsletter RSS (extract links)
    {"name": "TLDR AI", "type": "newsletter_rss", "layer": 1, "priority": 85,
     "url": "https://tldr.tech/ai/rss",
     "extra_config": {"extract_links": True, "max_links_per_issue": 8},
     "tags": ["AI"], "default_difficulty": "B1"},

    {"name": "Ben's Bites", "type": "newsletter_rss", "layer": 1, "priority": 80,
     "url": "https://bensbites.com/feed",
     "extra_config": {"extract_links": True, "max_links_per_issue": 6},
     "tags": ["AI", "Tech"], "default_difficulty": "B1"},

    {"name": "The Batch (deeplearning.ai)", "type": "newsletter_rss", "layer": 1, "priority": 75,
     "url": "https://www.deeplearning.ai/the-batch/feed",
     "extra_config": {"extract_links": True, "max_links_per_issue": 5},
     "tags": ["AI"], "default_difficulty": "B2"},

    # Layer 1: Blog RSS (direct content)
    {"name": "Stratechery", "type": "blog_rss", "layer": 1, "priority": 90,
     "url": "https://stratechery.com/feed/",
     "extra_config": {},
     "tags": ["Tech", "Finance"], "default_difficulty": "B2"},

    {"name": "Not Boring", "type": "blog_rss", "layer": 1, "priority": 85,
     "url": "https://www.notboring.co/feed",
     "extra_config": {},
     "tags": ["Tech", "Finance"], "default_difficulty": "B2"},

    {"name": "Lenny's Newsletter", "type": "blog_rss", "layer": 1, "priority": 80,
     "url": "https://www.lennysnewsletter.com/feed",
     "extra_config": {},
     "tags": ["Tech", "Management"], "default_difficulty": "B2"},

    {"name": "Paul Graham", "type": "blog_rss", "layer": 1, "priority": 85,
     "url": "http://www.paulgraham.com/rss.html",
     "extra_config": {},
     "tags": ["Tech", "Management"], "default_difficulty": "B2"},

    {"name": "Morgan Housel", "type": "blog_rss", "layer": 1, "priority": 80,
     "url": "https://collabfund.com/blog/feed/",
     "extra_config": {},
     "tags": ["Finance"], "default_difficulty": "B2"},

    {"name": "Farnam Street", "type": "blog_rss", "layer": 1, "priority": 75,
     "url": "https://fs.blog/feed/",
     "extra_config": {},
     "tags": ["Management", "General"], "default_difficulty": "B2"},

    {"name": "a16z Blog", "type": "blog_rss", "layer": 1, "priority": 70,
     "url": "https://a16z.com/feed/",
     "extra_config": {},
     "tags": ["Tech", "Finance"], "default_difficulty": "B2"},

    {"name": "MIT Technology Review", "type": "blog_rss", "layer": 1, "priority": 70,
     "url": "https://www.technologyreview.com/feed/",
     "extra_config": {},
     "tags": ["AI", "Tech"], "default_difficulty": "B2"},

    {"name": "Ars Technica", "type": "blog_rss", "layer": 1, "priority": 60,
     "url": "https://feeds.arstechnica.com/arstechnica/index",
     "extra_config": {},
     "tags": ["Tech"], "default_difficulty": "B1"},

    {"name": "BBC Technology", "type": "blog_rss", "layer": 1, "priority": 55,
     "url": "https://feeds.bbci.co.uk/news/technology/rss.xml",
     "extra_config": {},
     "tags": ["Tech"], "default_difficulty": "B1"},

    # Layer 1: Hacker News
    {"name": "Hacker News Top", "type": "hn_api", "layer": 1, "priority": 65,
     "url": "https://hn.algolia.com/api/v1/search",
     "extra_config": {"min_score": 100, "max_items": 10},
     "tags": ["Tech"], "default_difficulty": "B2"},

    # Layer 2: Classic Library (seeded separately by seed_classics.py)
    {"name": "Classic Library", "type": "classic_library", "layer": 2, "priority": 50,
     "url": "internal://classic-library",
     "extra_config": {"import_script": "seed_classics.py"},
     "tags": ["General"], "default_difficulty": "B2"},
]


async def seed():
    async with AsyncSessionLocal() as session:
        # Check if already seeded
        result = await session.execute(select(ContentSource).limit(1))
        if result.scalars().first():
            print("content_source table already has data. Skipping seed.")
            return

        for src in SOURCES:
            obj = ContentSource(
                name=src["name"],
                type=src["type"],
                url=src["url"],
                extra_config=src.get("extra_config"),
                layer=src["layer"],
                priority=src["priority"],
                quality_score=0.5,
                default_difficulty=src.get("default_difficulty"),
                tags=src.get("tags"),
                is_active=True,
            )
            session.add(obj)

        await session.commit()
        print(f"Seeded {len(SOURCES)} content sources.")


if __name__ == "__main__":
    asyncio.run(seed())

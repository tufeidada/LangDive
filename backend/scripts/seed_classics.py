"""Seed the content_candidate table with classic library items.

Stub script: inserts a handful of Paul Graham essays as classic library entries.
Expand this later with Naval Ravikant, Morgan Housel, Wait But Why, Farnam Street,
and curated TED Talks to reach ~400 items.
"""

import asyncio
import sys
import os
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models import ContentCandidate, ContentSource

# Classic Paul Graham essays (a small starter set)
CLASSICS = [
    {
        "title": "How to Do Great Work",
        "url": "http://www.paulgraham.com/greatwork.html",
        "type": "article",
        "estimated_difficulty": "B2",
    },
    {
        "title": "Cities and Ambition",
        "url": "http://www.paulgraham.com/cities.html",
        "type": "article",
        "estimated_difficulty": "B2",
    },
    {
        "title": "Maker's Schedule, Manager's Schedule",
        "url": "http://www.paulgraham.com/makersschedule.html",
        "type": "article",
        "estimated_difficulty": "B2",
    },
    {
        "title": "Do Things That Don't Scale",
        "url": "http://www.paulgraham.com/ds.html",
        "type": "article",
        "estimated_difficulty": "B1",
    },
    {
        "title": "How to Get Startup Ideas",
        "url": "http://www.paulgraham.com/startupideas.html",
        "type": "article",
        "estimated_difficulty": "B2",
    },
    {
        "title": "Keep Your Identity Small",
        "url": "http://www.paulgraham.com/identity.html",
        "type": "article",
        "estimated_difficulty": "B1",
    },
    {
        "title": "Life is Short",
        "url": "http://www.paulgraham.com/vb.html",
        "type": "article",
        "estimated_difficulty": "B1",
    },
    {
        "title": "What You'll Wish You'd Known",
        "url": "http://www.paulgraham.com/hs.html",
        "type": "article",
        "estimated_difficulty": "B1",
    },
    {
        "title": "The Bus Ticket Theory of Genius",
        "url": "http://www.paulgraham.com/genius.html",
        "type": "article",
        "estimated_difficulty": "B2",
    },
    {
        "title": "Putting Ideas into Words",
        "url": "http://www.paulgraham.com/words.html",
        "type": "article",
        "estimated_difficulty": "B1",
    },
]


async def seed():
    async with AsyncSessionLocal() as session:
        # Find the Classic Library source
        result = await session.execute(
            select(ContentSource).where(ContentSource.type == "classic_library").limit(1)
        )
        classic_source = result.scalars().first()
        source_id = classic_source.id if classic_source else None

        # Check existing classics to avoid duplicates
        result = await session.execute(
            select(ContentCandidate.url).where(ContentCandidate.status == "library")
        )
        existing_urls = {row[0] for row in result.fetchall()}

        inserted = 0
        for item in CLASSICS:
            if item["url"] in existing_urls:
                continue
            candidate = ContentCandidate(
                title=item["title"],
                url=item["url"],
                source_id=source_id,
                source_layer=2,
                type=item["type"],
                estimated_difficulty=item.get("estimated_difficulty"),
                status="library",
                date=date(2000, 1, 1),  # sentinel date for library items
            )
            session.add(candidate)
            inserted += 1

        await session.commit()
        print(f"Seeded {inserted} classic library items ({len(existing_urls)} already existed).")


if __name__ == "__main__":
    asyncio.run(seed())

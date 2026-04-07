import json
import hashlib
import logging
import os
from datetime import date, datetime, timedelta, timezone
from sqlalchemy import select, func, and_

from app.services.llm import call_llm
from app.services.youtube import search_youtube, fetch_transcript, filter_videos
from app.services.article import fetch_all_rss_candidates, extract_article_text
from app.services.segmenter import segment_content
from app.services.annotator import annotate_vocabulary
from app.services.tts import generate_segment_audio
from app.services.cache import get_cached, set_cached
from app.services.dictionary import lookup_word, get_word_level
from app.services.fetcher import (
    fetch_youtube_channels,
    fetch_blog_rss,
    fetch_newsletter_links,
    fetch_hn,
    draw_classics,
)
from app.database import AsyncSessionLocal
from app.models import Content, ContentSegment, SearchQueryLog, ContentSource, ContentCandidate
from app.config import settings

logger = logging.getLogger(__name__)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Step 0: Fetch candidates from all three layers
# ---------------------------------------------------------------------------

async def step0_fetch_all_layers() -> int:
    """Fetch content from all 3 layers, store in content_candidate table, deduplicate.

    Returns:
        Number of new candidates inserted today.
    """
    today = date.today()
    inserted_count = 0

    async with AsyncSessionLocal() as session:
        # Load active sources grouped by type
        result = await session.execute(
            select(ContentSource).where(ContentSource.is_active == True)  # noqa: E712
        )
        sources = result.scalars().all()

        sources_by_type: dict[str, list] = {}
        for src in sources:
            src_dict = {
                "id": src.id,
                "name": src.name,
                "type": src.type,
                "url": src.url,
                "extra_config": src.extra_config,
                "layer": src.layer,
                "priority": src.priority,
                "default_difficulty": src.default_difficulty,
                "tags": src.tags,
            }
            sources_by_type.setdefault(src.type, []).append(src_dict)

        # Collect existing URLs from last 30 days for dedup
        cutoff_30d = today - timedelta(days=30)
        result = await session.execute(
            select(ContentCandidate.url).where(ContentCandidate.date >= cutoff_30d)
        )
        recent_urls = {row[0] for row in result.fetchall()}

        # --- Layer 1: Whitelist sources ---
        all_raw_candidates: list[dict] = []

        # YouTube channels
        yt_sources = sources_by_type.get("youtube_channel", [])
        if yt_sources:
            try:
                yt_candidates = await fetch_youtube_channels(yt_sources)
                all_raw_candidates.extend(yt_candidates)
            except Exception as e:
                logger.error(f"Step 0: YouTube channel fetch failed: {e}")

        # Blog RSS
        blog_sources = sources_by_type.get("blog_rss", [])
        if blog_sources:
            try:
                blog_candidates = await fetch_blog_rss(blog_sources)
                all_raw_candidates.extend(blog_candidates)
            except Exception as e:
                logger.error(f"Step 0: Blog RSS fetch failed: {e}")

        # Newsletter RSS (extract links)
        newsletter_sources = sources_by_type.get("newsletter_rss", [])
        if newsletter_sources:
            try:
                newsletter_candidates = await fetch_newsletter_links(newsletter_sources)
                all_raw_candidates.extend(newsletter_candidates)
            except Exception as e:
                logger.error(f"Step 0: Newsletter fetch failed: {e}")

        # Hacker News
        hn_sources = sources_by_type.get("hn_api", [])
        for hn_src in hn_sources:
            try:
                hn_candidates = await fetch_hn(hn_src)
                all_raw_candidates.extend(hn_candidates)
            except Exception as e:
                logger.error(f"Step 0: HN fetch failed: {e}")

        # Insert Layer 1 candidates (dedup against recent URLs)
        for raw in all_raw_candidates:
            url = raw.get("url", "")
            if not url or url in recent_urls:
                continue
            recent_urls.add(url)

            published_at = raw.get("published_at")
            if published_at and isinstance(published_at, str):
                try:
                    published_at = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    published_at = None

            candidate = ContentCandidate(
                title=raw.get("title", "Untitled"),
                url=url,
                source_id=raw.get("source_id"),
                source_layer=1,
                type=raw.get("type", "article"),
                estimated_difficulty=raw.get("estimated_difficulty"),
                thumbnail_url=raw.get("thumbnail_url"),
                duration=raw.get("duration"),
                published_at=published_at,
                status="pending",
                date=today,
            )
            session.add(candidate)
            inserted_count += 1

        # Update last_fetched for all active sources
        now = datetime.now(timezone.utc)
        for src in sources:
            if src.type != "classic_library":
                src.last_fetched = now

        await session.flush()

        # --- Layer 2: Classic library supplement ---
        layer1_count = inserted_count
        if layer1_count < 15:
            needed = 15 - layer1_count
            try:
                classics = await draw_classics(session, needed)
                for classic in classics:
                    url = classic.get("url", "")
                    if url in recent_urls:
                        continue
                    recent_urls.add(url)

                    candidate = ContentCandidate(
                        title=classic.get("title", "Untitled"),
                        url=url,
                        source_id=classic.get("source_id"),
                        source_layer=2,
                        type=classic.get("type", "article"),
                        estimated_difficulty=classic.get("estimated_difficulty"),
                        status="pending",
                        date=today,
                    )
                    session.add(candidate)
                    inserted_count += 1

                    # Mark the original library item as used
                    if classic.get("candidate_id"):
                        orig = await session.get(ContentCandidate, classic["candidate_id"])
                        if orig:
                            orig.status = "library_used"
            except Exception as e:
                logger.error(f"Step 0: Classic library draw failed: {e}")

        # --- Layer 3: Search fallback (emergency only) ---
        total_so_far = inserted_count
        if total_so_far < 10:
            logger.info(f"Step 0: Only {total_so_far} candidates, activating Layer 3 search fallback")
            try:
                # Reuse existing search logic
                fallback_candidates = await _layer3_search_fallback(session)
                for raw in fallback_candidates:
                    url = raw.get("url", "")
                    if not url or url in recent_urls:
                        continue
                    recent_urls.add(url)

                    candidate = ContentCandidate(
                        title=raw.get("title", "Untitled"),
                        url=url,
                        source_layer=3,
                        type=raw.get("type", "article"),
                        estimated_difficulty=raw.get("estimated_difficulty"),
                        status="pending",
                        date=today,
                    )
                    session.add(candidate)
                    inserted_count += 1
            except Exception as e:
                logger.error(f"Step 0: Layer 3 search fallback failed: {e}")

        await session.commit()

    logger.info(f"Step 0: inserted {inserted_count} candidates for {today}")
    return inserted_count


# ---------------------------------------------------------------------------
# Step 0.5 (new): Pre-extract content + quality filter
# ---------------------------------------------------------------------------

async def step05_preextract_and_filter() -> int:
    """Pre-extract article content for today's pending candidates.
    Filters out paywall, empty, and low-quality content.
    Calculates objective difficulty scores using ECDICT.

    Returns: number of candidates that passed quality filter.
    """
    from app.services.dictionary import analyze_difficulty

    today = date.today()
    passed = 0
    rejected = 0

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(ContentCandidate).where(
                and_(
                    ContentCandidate.date == today,
                    ContentCandidate.status == "pending",
                    ContentCandidate.type == "article",  # only articles need pre-extract
                )
            )
        )
        candidates = result.scalars().all()

        if not candidates:
            logger.info("Step 0.5: No article candidates to pre-extract")
            return 0

        logger.info(f"Step 0.5: Pre-extracting {len(candidates)} article candidates...")

        for c in candidates:
            try:
                text = extract_article_text(c.url, min_words=300)

                if not text:
                    c.status = "rejected"
                    c.ai_reason = "No extractable content (paywall, empty, or too short)"
                    rejected += 1
                    continue

                # Analyze difficulty with ECDICT
                analysis = analyze_difficulty(text)
                word_count = analysis["word_count"]
                cefr = analysis["estimated_cefr"]
                difficulty_score = analysis["difficulty_score"]

                # Store results in candidate
                c.estimated_word_count = word_count
                c.estimated_difficulty = cefr
                c.summary = text[:200] + "..."  # first 200 chars as preview

                # Multi-dimensional quality score
                # Relevance: check for topic keywords
                text_lower = text.lower()
                topic_keywords = {"ai", "artificial intelligence", "machine learning", "finance",
                                  "technology", "startup", "investment", "management", "leadership",
                                  "crypto", "blockchain", "cloud", "data", "software", "engineering"}
                keyword_hits = sum(1 for kw in topic_keywords if kw in text_lower)
                relevance = min(1.0, keyword_hits / 5)

                # Quality: based on word count and structure
                has_paragraphs = text.count("\n\n") >= 2
                quality = min(1.0, (word_count / 2000) * 0.7 + (0.3 if has_paragraphs else 0))

                # Difficulty match: how close to B1-B2 target (sweet spot around 0.3-0.5)
                diff_match = 1.0 - abs(difficulty_score - 0.4) * 2
                diff_match = max(0, min(1.0, diff_match))

                # Composite score
                c.ai_score = round(relevance * 0.4 + quality * 0.3 + diff_match * 0.3, 3)
                c.ai_reason = f"words={word_count}, {cefr}, relevance={relevance:.1f}, quality={quality:.1f}, diff_match={diff_match:.1f}"

                passed += 1

            except Exception as e:
                logger.warning(f"Step 0.5: Failed to pre-extract '{c.title[:40]}': {e}")
                c.status = "rejected"
                c.ai_reason = f"Extraction error: {str(e)[:100]}"
                rejected += 1

        # Also score video candidates (they don't need pre-extraction, just basic scoring)
        video_result = await session.execute(
            select(ContentCandidate).where(
                and_(
                    ContentCandidate.date == today,
                    ContentCandidate.status == "pending",
                    ContentCandidate.type == "video",
                )
            )
        )
        for c in video_result.scalars().all():
            # Videos get a base score from source priority
            c.ai_score = 0.7  # default decent score for whitelisted videos
            c.ai_reason = "Video candidate (scored after transcript extraction)"
            passed += 1

        await session.commit()

    logger.info(f"Step 0.5: Pre-extracted {passed} passed, {rejected} rejected")
    return passed


async def _layer3_search_fallback(session) -> list[dict]:
    """Layer 3 emergency fallback: LLM-generated YouTube search + RSS."""
    # Load recent queries to avoid repeats
    cutoff = date.today() - timedelta(days=7)
    result = await session.execute(
        select(SearchQueryLog.query).where(SearchQueryLog.date >= cutoff)
    )
    recent_queries = [row[0] for row in result.fetchall()]
    recent_str = json.dumps(recent_queries) if recent_queries else "[]"

    system_prompt = (
        "You are a content curator for an English learning platform targeting Chinese learners at B1-B2 level. "
        "Generate YouTube search queries for high-quality interview and discussion videos."
    )
    user_prompt = (
        f"Generate 4 YouTube search queries for English interview/discussion videos on AI, tech, finance, or management. "
        f"Avoid repeating these recent queries: {recent_str}. "
        f"Return ONLY a JSON array of strings."
    )

    queries_raw = await call_llm(system_prompt, user_prompt)
    try:
        queries = json.loads(queries_raw)
        if not isinstance(queries, list):
            raise ValueError
    except (json.JSONDecodeError, ValueError):
        queries = ["AI technology interview 2026", "finance podcast discussion"]

    yt_results: list[dict] = []
    seen_ids: set[str] = set()

    for query in queries:
        try:
            results = await search_youtube(query, max_results=5)
            for item in results:
                vid = item.get("video_id")
                if vid and vid not in seen_ids:
                    seen_ids.add(vid)
                    yt_results.append(item)

            log_entry = SearchQueryLog(
                query=query, source="youtube",
                result_count=len(results), date=date.today(),
            )
            session.add(log_entry)
        except Exception as e:
            logger.warning(f"Layer 3 YouTube search failed for '{query}': {e}")

    # Also pull RSS as fallback
    rss_results = []
    try:
        rss_results = fetch_all_rss_candidates()
    except Exception as e:
        logger.warning(f"Layer 3 RSS fallback failed: {e}")

    return yt_results + rss_results


# ---------------------------------------------------------------------------
# Step 1 (new): AI Ranking of candidates
# ---------------------------------------------------------------------------

async def step1_ai_ranking() -> list[dict]:
    """LLM ranks today's candidates, selects top 5, updates content_candidate status.

    Returns:
        List of selected candidate dicts (for downstream processing).
    """
    today = date.today()

    async with AsyncSessionLocal() as session:
        # Get all pending candidates for today
        result = await session.execute(
            select(ContentCandidate).where(
                and_(
                    ContentCandidate.date == today,
                    ContentCandidate.status.in_(["pending", "user_promoted", "user_submitted"]),
                )
            )
        )
        candidates = result.scalars().all()

        if not candidates:
            logger.warning("Step 1: No candidates to rank")
            return []

        # User-override items are always included
        forced = [c for c in candidates if c.status in ("user_promoted", "user_submitted")]
        pending = [c for c in candidates if c.status == "pending"]

        # Build candidate list for LLM — now includes pre-computed scores and summaries
        candidate_lines = []
        candidate_map = {c.id: c for c in candidates}
        for c in candidates:
            layer_label = f"L{c.source_layer}"
            score_str = f"score={c.ai_score:.2f}" if c.ai_score else "score=?"
            words_str = f"{c.estimated_word_count}w" if c.estimated_word_count else "?w"
            diff_str = c.estimated_difficulty or "?"
            preview = (c.summary or "")[:80]
            candidate_lines.append(
                f"[{c.id}] [{c.type or 'article'}] [{layer_label}] [{diff_str}] [{words_str}] [{score_str}] {c.title} | {preview}"
            )

        candidate_list_str = "\n".join(candidate_lines)
        forced_ids = {c.id for c in forced}
        forced_note = ""
        if forced_ids:
            forced_note = f"\nIMPORTANT: Items with IDs {list(forced_ids)} are user-selected and MUST be included.\n"

        system_prompt = (
            "You are selecting today's English learning content for a Chinese learner.\n"
            "Learner profile: IELTS B1-B2, interests in AI/finance/tech/management."
        )
        user_prompt = (
            f"Candidates (one per line, format: [ID] [TYPE] [LAYER] [TITLE]):\n"
            f"{candidate_list_str}\n\n"
            f"{forced_note}"
            f"Select exactly 5 items following these rules:\n"
            f"- 1-2 videos + 3-4 articles (hard constraint)\n"
            f"- Prioritize Layer 1 over Layer 2, Layer 2 over Layer 3\n"
            f"- Prefer diverse sources (don't pick 3 from same source)\n"
            f"- Prefer difficulty B1-B2 (allow 1 item at C1 for challenge)\n"
            f"- Prefer content published in last 7 days (except classics)\n\n"
            f"For each candidate, provide:\n"
            f"- id: the candidate ID\n"
            f"- score: 0-1 (relevance * quality * difficulty_match)\n"
            f"- selected: true/false\n"
            f"- reason: one sentence explanation\n\n"
            f"Return ONLY a JSON array sorted by score DESC."
        )

        ranked_raw = await call_llm(system_prompt, user_prompt)
        try:
            content = ranked_raw.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]
            ranked: list[dict] = json.loads(content)
            if not isinstance(ranked, list):
                raise ValueError("Expected JSON array")
        except (json.JSONDecodeError, ValueError):
            logger.warning("Step 1: Failed to parse LLM ranking, falling back to priority order")
            # Fallback: sort by source priority, pick top 5
            ranked = [{"id": c.id, "score": 0.5, "selected": i < 5, "reason": "fallback"}
                      for i, c in enumerate(sorted(pending, key=lambda x: x.source_layer))]

        # Determine selected IDs (LLM may return id as string or int)
        selected_ids = set(forced_ids)  # always include forced
        for item in ranked:
            try:
                item_id = int(item.get("id", 0))
            except (ValueError, TypeError):
                continue
            if item.get("selected") and item_id in candidate_map:
                selected_ids.add(item_id)

        # Fallback: if LLM selected 0, pick top 5 by score
        if len(selected_ids) == 0 and ranked:
            sorted_by_score = sorted(ranked, key=lambda x: float(x.get("score", 0)), reverse=True)
            for item in sorted_by_score[:5]:
                try:
                    item_id = int(item.get("id", 0))
                    if item_id in candidate_map:
                        selected_ids.add(item_id)
                except (ValueError, TypeError):
                    continue

        # Enforce max 5
        selected_ids_list = list(selected_ids)[:5]
        selected_ids = set(selected_ids_list)

        # Enforce 1-2 videos max
        selected_objs = [candidate_map[cid] for cid in selected_ids if cid in candidate_map]
        videos = [c for c in selected_objs if c.type == "video"]
        articles = [c for c in selected_objs if c.type != "video"]
        if len(videos) > 2:
            videos = videos[:2]
            selected_objs = (videos + articles)[:5]
            selected_ids = {c.id for c in selected_objs}

        # Update statuses and scores
        score_map = {}
        for item in ranked:
            try:
                item_id = int(item.get("id", 0))
                score_map[item_id] = item
            except (ValueError, TypeError):
                continue
        for c in candidates:
            rank_info = score_map.get(c.id, {})
            c.ai_score = rank_info.get("score")
            c.ai_reason = rank_info.get("reason")

            if c.id in selected_ids:
                if c.status not in ("user_promoted", "user_submitted"):
                    c.status = "selected"
            else:
                if c.status == "pending":
                    c.status = "rejected"

        await session.commit()

        # Build output dicts for pipeline processing
        selected_dicts = []
        for c in candidates:
            if c.id not in selected_ids:
                continue
            # Look up source name from ContentSource table
            source_name = ""
            if c.source_id:
                src = await session.get(ContentSource, c.source_id)
                if src:
                    source_name = src.name
            selected_dicts.append({
                "candidate_id": c.id,
                "title": c.title,
                "url": c.url,
                "type": c.type or "article",
                "source": source_name,
                "difficulty": c.estimated_difficulty,
                "video_id": _extract_video_id(c.url) if c.type == "video" else None,
                "duration": c.duration,
            })

    logger.info(
        f"Step 1: ranked {len(candidates)} candidates, selected {len(selected_dicts)} "
        f"({sum(1 for d in selected_dicts if d['type'] == 'video')} videos)"
    )
    return selected_dicts


# ---------------------------------------------------------------------------
# Step 1 (old): Fetch candidates from YouTube + RSS — kept for backward compat
# ---------------------------------------------------------------------------

async def step1_fetch_candidates() -> list[dict]:
    """Generate search queries, fetch YouTube videos, fetch RSS articles."""
    # Load recent queries to avoid repetition, within a single session context
    recent_queries: list[str] = []
    cutoff = date.today() - timedelta(days=7)

    async with AsyncSessionLocal() as session:
        try:
            stmt = select(SearchQueryLog.query).where(SearchQueryLog.date >= cutoff)
            result = await session.execute(stmt)
            rows = result.fetchall()
            recent_queries = [row[0] for row in rows]
        except Exception as e:
            logger.warning(f"Failed to load recent queries: {e}")

    recent_str = json.dumps(recent_queries) if recent_queries else "[]"

    system_prompt = (
        "You are a content curator for an English language learning platform targeting Chinese learners at B1-B2 level. "
        "Focus on finding HIGH-QUALITY interview and discussion videos with experts, thought leaders, and industry professionals. "
        "Prefer long-form conversations (10+ minutes) over short clips."
    )
    user_prompt = (
        f"Generate 6-8 YouTube search queries to find English interview/discussion videos on AI, technology, finance, management, or geopolitics. "
        f"Include terms like 'interview', 'discussion', 'conversation', 'talk', 'podcast' in queries. "
        f"Example good queries: 'AI expert interview 2025', 'tech CEO discussion future of work', 'finance podcast investment strategy'. "
        f"Avoid repeating these recent queries: {recent_str}. "
        f"Return ONLY a JSON array of strings."
    )

    queries_raw = await call_llm(system_prompt, user_prompt)
    try:
        queries: list[str] = json.loads(queries_raw)
        if not isinstance(queries, list):
            raise ValueError("Expected a JSON array")
    except (json.JSONDecodeError, ValueError):
        logger.warning("Failed to parse LLM query list, using fallback queries")
        queries = [
            "AI technology interview 2026",
            "tech leadership discussion",
            "science news 2026",
        ]

    # Fetch YouTube results for each query and log them
    yt_results: list[dict] = []
    seen_video_ids: set[str] = set()

    async with AsyncSessionLocal() as session:
        for query in queries:
            try:
                results = await search_youtube(query, max_results=5)
                # Deduplicate
                for item in results:
                    vid = item.get("video_id")
                    if vid and vid not in seen_video_ids:
                        seen_video_ids.add(vid)
                        yt_results.append(item)

                log_entry = SearchQueryLog(
                    query=query,
                    source="youtube",
                    result_count=len(results),
                    date=date.today(),
                )
                session.add(log_entry)
            except Exception as e:
                logger.warning(f"YouTube search failed for query '{query}': {e}")

        await session.commit()

    # Filter YouTube: min 10000 views, max 10 min, min 1 min
    if yt_results:
        yt_results = await filter_videos(yt_results, min_views=10000, max_duration_sec=600)

    # Fetch RSS articles
    rss_results: list[dict] = []
    try:
        rss_results = fetch_all_rss_candidates()
    except Exception as e:
        logger.warning(f"RSS fetch failed: {e}")

    candidates = yt_results + rss_results
    logger.info(f"Step 1: {len(yt_results)} YouTube + {len(rss_results)} RSS = {len(candidates)} candidates")
    return candidates


# ---------------------------------------------------------------------------
# Step 2: Filter and rank — top 5, max 2 videos
# ---------------------------------------------------------------------------

async def step2_filter_and_rank(candidates: list[dict]) -> list[dict]:
    """Send candidates to LLM for selection; enforce max 2 videos, top 5 total."""
    if not candidates:
        return []

    # Build a slim representation to send to LLM (avoid huge payload)
    slim = [
        {
            "title": c.get("title", ""),
            "type": c.get("type", "article"),
            "source": c.get("source", ""),
            "url": c.get("url", ""),
        }
        for c in candidates
    ]

    system_prompt = (
        "You are an English content curator for a Chinese B1-B2 learner. "
        "Select the 5 most educational, level-appropriate, and diverse items. "
        "Prefer articles from reputable sources (MIT Tech Review, BBC, Ars Technica, Nature, Wired, The Verge, The Guardian). "
        "Avoid clickbait, listicles ('Top 10...'), opinion pieces, and outdated content (>6 months old). "
        "Prefer in-depth analysis, news reports, expert interviews, and substantive discussions."
    )
    # Count available videos in candidates
    video_count = sum(1 for c in slim if c.get("type") == "video")
    video_instruction = "You MUST include 1-2 videos in your selection." if video_count > 0 else "No videos available, select 5 articles."

    user_prompt = (
        f"From these {len(slim)} candidates, select exactly 5 items. "
        f"{video_instruction} "
        "For each selected item, add fields: difficulty (A2/B1/B2/C1), relevance (0.0-1.0). "
        "Prefer recent technology, science, society topics. Ensure diversity. "
        "Return ONLY a JSON array with the same fields plus difficulty and relevance:\n"
        f"{json.dumps(slim, ensure_ascii=False)}"
    )

    selected_raw = await call_llm(system_prompt, user_prompt)
    try:
        content = selected_raw.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]
        selected: list[dict] = json.loads(content)
        if not isinstance(selected, list):
            raise ValueError("Expected a JSON array")
    except (json.JSONDecodeError, ValueError):
        logger.warning("Failed to parse LLM filter response, falling back to first 5")
        selected = slim[:5]

    # Enforce max 5
    selected = selected[:5]

    # Enforce max 2 videos
    videos = [s for s in selected if s.get("type") == "video"]
    articles = [s for s in selected if s.get("type") != "video"]

    if len(videos) > 2:
        videos = videos[:2]

    result = (videos + articles)[:5]

    # If 0 videos came back from LLM selection, fill entirely with articles
    if len(videos) == 0:
        article_candidates = [c for c in candidates if c.get("type") != "video"]
        result = article_candidates[:5] if article_candidates else candidates[:5]

    # Ensure we have at most 5
    result = result[:5]

    logger.info(f"Step 2: selected {len(result)} items ({sum(1 for r in result if r.get('type') == 'video')} videos)")
    return result


# ---------------------------------------------------------------------------
# Step 3: Extract content text
# ---------------------------------------------------------------------------

async def step3_extract_content(selected: list[dict]) -> list[dict]:
    """Fetch transcript for videos; extract article text for articles."""
    items = []
    for item in selected:
        item = dict(item)  # shallow copy to avoid mutating input
        content_type = item.get("type", "article")

        if content_type == "video":
            video_id = item.get("video_id") or _extract_video_id(item.get("url", ""))
            if video_id:
                transcript = fetch_transcript(video_id)
                if transcript:
                    item["content_text"] = " ".join(t["text"] for t in transcript)
                    item["has_subtitles"] = True
                    item["transcript_raw"] = transcript
                else:
                    item["content_text"] = None
                    item["has_subtitles"] = False
            else:
                item["content_text"] = None
                item["has_subtitles"] = False
        else:
            url = item.get("url", "")
            if url:
                try:
                    text = extract_article_text(url)
                    item["content_text"] = text
                except Exception as e:
                    logger.warning(f"Article extraction failed for {url}: {e}")
                    item["content_text"] = None
            else:
                item["content_text"] = None
            item["has_subtitles"] = False

        items.append(item)

    return items


def _extract_video_id(url: str) -> str | None:
    """Extract YouTube video ID from URL."""
    if "v=" in url:
        return url.split("v=")[-1].split("&")[0]
    if "youtu.be/" in url:
        return url.split("youtu.be/")[-1].split("?")[0]
    return None


# ---------------------------------------------------------------------------
# Steps 4+5+6 MERGED: Segment + Annotate + Summarize in ONE LLM call
# ---------------------------------------------------------------------------

COMBINED_SYSTEM = """You are an English learning content processor for a Chinese learner at B1-B2 level (~3500 word baseline, CET-4).

Given an English article/transcript, do ALL THREE tasks in ONE response:

1. **Segment**: Split into semantic segments by major topic. Rules:
   - Under 500 words: DO NOT split. Return exactly 1 segment.
   - 500+ words: Split into 2-3 segments MAX. Never more than 3 segments.
   - Each segment MUST be at least 200 words.
   - Format each segment's text_en with proper paragraphs (use \n\n between paragraphs).
   - Add a clear, descriptive title for each segment.

2. **Annotate**: For each segment, identify 25-50 vocabulary words above CET-4 level.
   CRITICAL: You MUST distribute importance_score across the full range:
   - 8-12 words with importance_score 0.8-1.0 (essential topic-specific terms)
   - 6-10 words with importance_score 0.5-0.8 (important but not critical)
   - 4-8 words with importance_score 0.2-0.5 (nice-to-know, lower frequency)
   This distribution is REQUIRED — the UI uses importance_score to filter density levels.
   If all scores are above 0.8, the density filter breaks. Spread them out.

3. **Summarize**: Chinese summary for the full content (2-3 sentences) and each segment (1 sentence).

Return ONLY valid JSON:
{
  "summary_zh": "全文中文摘要",
  "segments": [
    {
      "segment_index": 0,
      "title": "Segment Title",
      "text_en": "Full text of segment...",
      "summary_zh": "本段中文摘要",
      "words": [
        {"word": "paradigm", "ipa": "/ˈpærədaɪm/", "freq_in_content": 2, "importance_score": 0.95, "meaning_zh": "范式", "detail_zh": "一种模式或框架", "example_en": "A paradigm shift.", "example_zh": "范式转变。", "level": "IELTS"},
        {"word": "leverage", "ipa": "/ˈlevərɪdʒ/", "freq_in_content": 1, "importance_score": 0.6, "meaning_zh": "利用", "detail_zh": "充分利用某事物", "example_en": "Leverage AI tools.", "example_zh": "利用AI工具。", "level": "CET-6"},
        {"word": "albeit", "ipa": "/ɔːlˈbiːɪt/", "freq_in_content": 1, "importance_score": 0.35, "meaning_zh": "尽管", "detail_zh": "虽然，即使", "example_en": "Albeit slowly.", "example_zh": "尽管缓慢。", "level": "Advanced"}
      ]
    }
  ]
}

Word levels: CET-4 (~4500), CET-6 (~6500), IELTS (~8000), Advanced (beyond).
Sort words by importance_score DESC. Include 25-50 words per segment with VARIED scores."""


async def step4_segment_annotate_summarize(items: list[dict]) -> list[dict]:
    """Combined step: segment + annotate + summarize in ONE LLM call per article."""
    async with AsyncSessionLocal() as session:
        for item in items:
            text = item.get("content_text") or ""
            if not text.strip():
                item["segments"] = []
                item["summary_zh"] = None
                item["words_json"] = []
                item["preview_words_json"] = []
                continue

            # Check cache
            cache_key = content_hash(text)
            cached = await get_cached(session, cache_key, "combined_analysis", provider="llm")

            if cached:
                try:
                    result = json.loads(cached)
                except json.JSONDecodeError:
                    result = None
            else:
                result = None

            if not result:
                try:
                    content_type = item.get("type", "article")
                    extra = ""
                    if content_type == "video":
                        extra = "\nThis is a video transcript. For segments, align to topic boundaries."

                    raw = await call_llm(
                        COMBINED_SYSTEM,
                        f"Process this English content ({len(text.split())} words):{extra}\n\n{text[:12000]}",
                        timeout=180.0,
                    )
                    # Strip markdown fences if present
                    content = raw.strip()
                    if content.startswith("```"):
                        content = content.split("\n", 1)[1].rsplit("```", 1)[0]
                    result = json.loads(content)

                    # Cache the result
                    await set_cached(
                        session, cache_key, "combined_analysis",
                        text_content=json.dumps(result, ensure_ascii=False),
                        provider="llm",
                    )
                    await session.commit()
                except Exception as e:
                    logger.warning(f"Combined analysis failed for '{item.get('title')}': {e}")
                    # Fallback: single segment, no annotation
                    result = {
                        "summary_zh": None,
                        "segments": [{
                            "segment_index": 0, "title": "Full Content",
                            "text_en": text, "summary_zh": None, "words": [],
                        }]
                    }

            # Unpack result
            item["summary_zh"] = result.get("summary_zh")
            segments = result.get("segments", [])
            all_words = []
            all_preview = []

            for i, seg in enumerate(segments):
                seg["segment_index"] = i
                words = seg.get("words", [])
                # Ensure every word has a level field
                for w in words:
                    if "level" not in w:
                        score = w.get("importance_score", 0.5)
                        w["level"] = "Advanced" if score >= 0.8 else "IELTS" if score >= 0.5 else "CET-6"
                # Enrich words with ECDICT data for any missing fields
                for w in words:
                    ecdict = lookup_word(w.get("word", ""))
                    if ecdict:
                        if not w.get("ipa"):
                            w["ipa"] = ecdict.get("phonetic", "")
                        if not w.get("level"):
                            w["level"] = get_word_level(w["word"]) or w.get("level", "CET-6")
                preview = []
                for w in sorted(words, key=lambda w: w.get("importance_score", 0), reverse=True)[:5]:
                    pw = dict(w)
                    pw["example_in_context"] = w.get("example_en", "")
                    preview.append(pw)
                seg["preview_words"] = preview
                all_words.extend(words)
                all_preview.extend(preview)

            item["segments"] = segments
            item["words_json"] = all_words
            item["preview_words_json"] = all_preview  # actual sum across segments, no cap

    return items


# Keep old step functions as aliases for backward compat in daily_pipeline.py
async def step4_segment(items: list[dict]) -> list[dict]:
    return items  # no-op, handled by combined step

async def step5_annotate(items: list[dict]) -> list[dict]:
    return items  # no-op, handled by combined step

async def step6_generate_summary(items: list[dict]) -> list[dict]:
    return items  # no-op, handled by combined step


# ---------------------------------------------------------------------------
# Step 7: Generate TTS audio
# ---------------------------------------------------------------------------

async def step7_generate_tts(items: list[dict]) -> list[dict]:
    """Generate TTS audio for each segment."""
    audio_dir = settings.AUDIO_DIR
    os.makedirs(audio_dir, exist_ok=True)

    for item in items:
        for seg in item.get("segments", []):
            text = seg.get("text_en", "")
            if not text.strip():
                seg["audio_en_path"] = None
                continue

            seg_hash = content_hash(text)
            filename = f"{seg_hash}.mp3"
            output_path = os.path.join(audio_dir, filename)

            if os.path.exists(output_path):
                seg["audio_en_path"] = output_path
                continue

            try:
                path = await generate_segment_audio(text, output_path)
                seg["audio_en_path"] = path
            except Exception as e:
                logger.warning(f"TTS generation failed: {e}")
                seg["audio_en_path"] = None

    return items


# ---------------------------------------------------------------------------
# Step 8: Translate video subtitles to Chinese
# ---------------------------------------------------------------------------

async def step8_translate_videos(items: list[dict]) -> list[dict]:
    """For video items, translate subtitle text to Chinese via LLM."""
    system_prompt = (
        "You are a professional subtitle translator. Translate the English text to Chinese accurately. "
        "Return ONLY the translated Chinese text."
    )

    for item in items:
        if item.get("type") != "video":
            continue

        for seg in item.get("segments", []):
            text = seg.get("text_en", "")
            if not text.strip():
                seg["text_zh"] = None
                continue
            try:
                translated = await call_llm(
                    system_prompt,
                    f"Translate to Chinese:\n\n{text[:6000]}",
                )
                seg["text_zh"] = translated
            except Exception as e:
                logger.warning(f"Translation failed for segment: {e}")
                seg["text_zh"] = None

    return items


# ---------------------------------------------------------------------------
# Step 9: Store to database
# ---------------------------------------------------------------------------

async def step9_store(items: list[dict]) -> None:
    """Insert Content and ContentSegment rows into the database."""
    async with AsyncSessionLocal() as session:
        for item in items:
            title = item.get("title") or "Untitled"
            content_type = item.get("type", "article")
            url = item.get("url")
            source = item.get("source", "")
            difficulty = item.get("difficulty")
            text = item.get("content_text") or ""
            c_hash = content_hash(text) if text else None

            # Validate difficulty value against allowed set
            allowed_difficulties = {"A2", "B1", "B2", "C1"}
            if difficulty not in allowed_difficulties:
                difficulty = "B1"  # default

            # Compute read_time for articles; pass through duration for videos
            read_time = item.get("read_time")
            if not read_time and content_type != "video" and text:
                word_count = len(text.split())
                read_time = f"{max(1, word_count // 200)} min read"

            # For video content, store raw transcript in tags field for the transcript API endpoint
            tags = item.get("tags")
            if content_type == "video" and item.get("transcript_raw"):
                tags = item["transcript_raw"]

            content_obj = Content(
                type=content_type,
                title=title,
                source=source,
                url=url,
                difficulty=difficulty,
                tags=tags,
                content_text=text or None,
                summary_zh=item.get("summary_zh"),
                audio_path=None,
                words_json=item.get("words_json"),
                preview_words_json=item.get("preview_words_json"),
                segment_count=len(item.get("segments", [])) or 1,
                has_subtitles=item.get("has_subtitles", False),
                date=date.today(),
                duration=item.get("duration"),
                read_time=read_time,
                content_hash=c_hash,
            )
            session.add(content_obj)
            await session.flush()  # get content_obj.id

            for seg in item.get("segments", []):
                seg_obj = ContentSegment(
                    content_id=content_obj.id,
                    segment_index=seg.get("segment_index", 0),
                    title=seg.get("title", "Segment"),
                    start_time=seg.get("start_time"),
                    end_time=seg.get("end_time"),
                    text_en=seg.get("text_en", ""),
                    summary_zh=seg.get("summary_zh"),
                    audio_en_path=seg.get("audio_en_path"),
                    preview_words_json=seg.get("preview_words"),
                    words_json=seg.get("words"),
                )
                session.add(seg_obj)

            # Link back to content_candidate if this came from the new pipeline
            candidate_id = item.get("candidate_id")
            if candidate_id:
                candidate = await session.get(ContentCandidate, candidate_id)
                if candidate:
                    candidate.content_id = content_obj.id
                    candidate.content_hash = c_hash

        await session.commit()

    logger.info(f"Step 9: stored {len(items)} content items to database")

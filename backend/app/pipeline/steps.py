import json
import hashlib
import logging
import os
from datetime import date, timedelta
from sqlalchemy import select

from app.services.llm import call_llm
from app.services.youtube import search_youtube, fetch_transcript, filter_videos
from app.services.article import fetch_all_rss_candidates, extract_article_text
from app.services.segmenter import segment_content
from app.services.annotator import annotate_vocabulary
from app.services.tts import generate_segment_audio
from app.services.cache import get_cached, set_cached
from app.database import AsyncSessionLocal
from app.models import Content, ContentSegment, SearchQueryLog
from app.config import settings

logger = logging.getLogger(__name__)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Step 1: Fetch candidates from YouTube + RSS
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
   - 5-10 words with importance_score 0.9-1.0 (essential topic-specific terms)
   - 10-15 words with importance_score 0.6-0.8 (important but not critical)
   - 10-15 words with importance_score 0.3-0.5 (nice-to-know, lower frequency)
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
                preview = sorted(words, key=lambda w: w.get("importance_score", 0), reverse=True)[:5]
                seg["preview_words"] = preview
                all_words.extend(words)
                all_preview.extend(preview)

            item["segments"] = segments
            item["words_json"] = all_words
            item["preview_words_json"] = all_preview[:10]

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
                read_time=item.get("read_time"),
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

        await session.commit()

    logger.info(f"Step 9: stored {len(items)} content items to database")

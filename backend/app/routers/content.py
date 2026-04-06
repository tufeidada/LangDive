from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Content, ContentSegment, ContentCandidate
from app.pipeline.steps import (
    step3_extract_content,
    step4_segment_annotate_summarize,
    step7_generate_tts,
    step8_translate_videos,
    step9_store,
)

router = APIRouter()


@router.get("/content/today")
async def get_today_content(db: AsyncSession = Depends(get_db)):
    """Get latest content. If nothing today, fall back to yesterday."""
    stmt = select(Content).where(Content.date == date.today()).order_by(Content.id)
    result = await db.execute(stmt)
    items = result.scalars().all()
    # Fallback: if no content today, show yesterday's
    if not items:
        yesterday = date.today() - timedelta(days=1)
        stmt = select(Content).where(Content.date == yesterday).order_by(Content.id)
        result = await db.execute(stmt)
        items = result.scalars().all()
    return [
        {
            "id": c.id, "type": c.type, "title": c.title, "source": c.source,
            "url": c.url, "difficulty": c.difficulty, "date": str(c.date),
            "segment_count": c.segment_count, "has_subtitles": c.has_subtitles,
            "duration": c.duration, "read_time": c.read_time,
            "preview_word_count": len(c.preview_words_json) if c.preview_words_json else 0,
            "summary_zh": c.summary_zh,
        }
        for c in items
    ]


@router.get("/content/history")
async def get_content_history(date: str | None = None, db: AsyncSession = Depends(get_db)):
    stmt = select(Content).order_by(Content.date.desc())
    if date:
        stmt = stmt.where(Content.date == date)
    result = await db.execute(stmt)
    items = result.scalars().all()
    return [
        {"id": c.id, "type": c.type, "title": c.title, "source": c.source,
         "difficulty": c.difficulty, "date": str(c.date),
         "segment_count": c.segment_count, "has_subtitles": c.has_subtitles}
        for c in items
    ]


@router.post("/content/refresh")
async def refresh_content(db: AsyncSession = Depends(get_db)):
    return {"status": "ok", "message": "Use cron script to re-run pipeline"}


class SubmitUrlRequest(BaseModel):
    url: str


@router.post("/content/submit-url")
async def submit_url(body: SubmitUrlRequest, db: AsyncSession = Depends(get_db)):
    """User submits a URL: create candidate with status='user_submitted', run pipeline steps 3-9.

    Processing is synchronous (30-60s acceptable for single user).
    """
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="url must not be empty")

    # Detect type: YouTube vs article
    is_video = "youtube.com" in url or "youtu.be" in url
    content_type = "video" if is_video else "article"

    # Create candidate record
    candidate = ContentCandidate(
        title=url,  # title will be updated after extraction
        url=url,
        source_id=None,
        source_layer=0,
        type=content_type,
        status="user_submitted",
        date=date.today(),
    )
    db.add(candidate)
    await db.commit()
    await db.refresh(candidate)

    # Build item dict for pipeline
    item = {
        "candidate_id": candidate.id,
        "title": url,
        "url": url,
        "type": content_type,
        "source": "user_submitted",
        "difficulty": None,
        "video_id": None,
        "duration": None,
    }

    # Steps 3-9 synchronously
    items = await step3_extract_content([item])
    items = await step4_segment_annotate_summarize(items)
    items = await step7_generate_tts(items)
    items = await step8_translate_videos(items)
    await step9_store(items)

    # Reload candidate to get content_id set by step9_store
    await db.refresh(candidate)

    return {
        "candidate_id": candidate.id,
        "content_id": candidate.content_id,
        "status": "completed",
    }


@router.get("/content/{content_id}")
async def get_content_detail(content_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(Content).where(Content.id == content_id)
    result = await db.execute(stmt)
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Content not found")
    return {
        "id": c.id, "type": c.type, "title": c.title, "source": c.source,
        "url": c.url, "difficulty": c.difficulty, "date": str(c.date),
        "content_text": c.content_text, "summary_zh": c.summary_zh,
        "segment_count": c.segment_count, "has_subtitles": c.has_subtitles,
        "audio_path": c.audio_path, "words_json": c.words_json,
        "preview_words_json": c.preview_words_json,
    }


@router.get("/content/{content_id}/transcript")
async def get_transcript(content_id: int, db: AsyncSession = Depends(get_db)):
    """Return raw transcript entries for video content. Stored in content.tags."""
    stmt = select(Content).where(Content.id == content_id)
    result = await db.execute(stmt)
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Content not found")
    # tags holds transcript list for videos: [{text, start, duration}, ...]
    if c.type != "video" or not c.tags:
        return []
    if isinstance(c.tags, list):
        return c.tags
    return []


@router.get("/content/{content_id}/segments")
async def get_segments(content_id: int, db: AsyncSession = Depends(get_db)):
    stmt = select(ContentSegment).where(ContentSegment.content_id == content_id).order_by(ContentSegment.segment_index)
    result = await db.execute(stmt)
    segs = result.scalars().all()
    def _audio_url(path: str | None) -> str | None:
        if not path:
            return None
        # Strip directory prefix, keep just filename
        import os
        filename = os.path.basename(path)
        return f"/static/audio/{filename}"

    return [
        {"id": s.id, "content_id": s.content_id, "segment_index": s.segment_index,
         "title": s.title, "start_time": s.start_time, "end_time": s.end_time,
         "text_en": s.text_en, "summary_zh": s.summary_zh,
         "audio_en_path": s.audio_en_path,
         "audio_url": _audio_url(s.audio_en_path),
         "preview_words_json": s.preview_words_json, "words_json": s.words_json,
         "is_completed": s.is_completed}
        for s in segs
    ]


@router.get("/content/{content_id}/segments/{idx}")
async def get_segment(content_id: int, idx: int, db: AsyncSession = Depends(get_db)):
    stmt = select(ContentSegment).where(
        ContentSegment.content_id == content_id, ContentSegment.segment_index == idx)
    result = await db.execute(stmt)
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Segment not found")
    import os
    audio_url = f"/static/audio/{os.path.basename(s.audio_en_path)}" if s.audio_en_path else None
    return {"id": s.id, "content_id": s.content_id, "segment_index": s.segment_index,
            "title": s.title, "text_en": s.text_en, "summary_zh": s.summary_zh,
            "audio_url": audio_url, "preview_words_json": s.preview_words_json,
            "words_json": s.words_json, "is_completed": s.is_completed}


@router.post("/content/{content_id}/segments/{idx}/complete")
async def mark_segment_complete(content_id: int, idx: int, db: AsyncSession = Depends(get_db)):
    stmt = select(ContentSegment).where(
        ContentSegment.content_id == content_id, ContentSegment.segment_index == idx)
    result = await db.execute(stmt)
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Segment not found")
    s.is_completed = True
    await db.commit()
    return {"status": "ok"}

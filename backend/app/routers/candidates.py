from datetime import date as date_type
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ContentCandidate
from app.pipeline.steps import (
    step3_extract_content,
    step4_segment_annotate_summarize,
    step7_generate_tts,
    step8_translate_videos,
    step9_store,
)

router = APIRouter()


def _candidate_dict(c: ContentCandidate) -> dict:
    return {
        "id": c.id,
        "title": c.title,
        "url": c.url,
        "source_id": c.source_id,
        "source_layer": c.source_layer,
        "type": c.type,
        "estimated_difficulty": c.estimated_difficulty,
        "estimated_word_count": c.estimated_word_count,
        "summary": c.summary,
        "thumbnail_url": c.thumbnail_url,
        "duration": c.duration,
        "published_at": c.published_at.isoformat() if c.published_at else None,
        "ai_score": c.ai_score,
        "ai_reason": c.ai_reason,
        "status": c.status,
        "date": str(c.date),
        "content_id": c.content_id,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


async def _run_pipeline_for_candidate(candidate: ContentCandidate) -> int | None:
    """Run pipeline steps 3-9 for a single candidate. Returns content_id or None."""
    item = {
        "candidate_id": candidate.id,
        "title": candidate.title,
        "url": candidate.url,
        "type": candidate.type or "article",
        "source": "",
        "difficulty": candidate.estimated_difficulty,
        "video_id": None,
        "duration": candidate.duration,
    }

    # Step 3: extract content
    items = await step3_extract_content([item])

    # Step 4: segment + annotate + summarize
    items = await step4_segment_annotate_summarize(items)

    # Step 7: TTS
    items = await step7_generate_tts(items)

    # Step 8: translate videos
    items = await step8_translate_videos(items)

    # Step 9: store
    await step9_store(items)

    # After step9_store, the candidate's content_id is set via the candidate FK link
    # We need to reload the candidate to get content_id — return from stored item
    return None  # caller will re-query the candidate


@router.get("/candidates")
async def list_candidates(
    date: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List all candidates for a given date (default: today), grouped by status."""
    target_date = date_type.today()
    if date:
        try:
            target_date = date_type.fromisoformat(date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    stmt = select(ContentCandidate).where(ContentCandidate.date == target_date).order_by(
        ContentCandidate.ai_score.desc().nulls_last(),
        ContentCandidate.id,
    )
    result = await db.execute(stmt)
    candidates = result.scalars().all()

    # Group by status
    grouped: dict[str, list] = {}
    for c in candidates:
        grouped.setdefault(c.status, []).append(_candidate_dict(c))

    return {
        "date": str(target_date),
        "total": len(candidates),
        "by_status": grouped,
    }


@router.put("/candidates/{candidate_id}/promote")
async def promote_candidate(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Promote a candidate: set status='user_promoted', then run pipeline steps 3-9."""
    candidate = await db.get(ContentCandidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    candidate.status = "user_promoted"
    await db.commit()
    await db.refresh(candidate)

    # Run pipeline synchronously (30-60s acceptable for single user)
    await _run_pipeline_for_candidate(candidate)

    # Reload to get updated content_id
    await db.refresh(candidate)

    return {
        "status": "ok",
        "candidate_id": candidate.id,
        "content_id": candidate.content_id,
        "pipeline_status": "completed",
    }


@router.put("/candidates/{candidate_id}/reject")
async def reject_candidate(
    candidate_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Reject a candidate: set status='user_rejected'."""
    candidate = await db.get(ContentCandidate, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    candidate.status = "user_rejected"
    await db.commit()

    return {"status": "ok", "candidate_id": candidate.id}

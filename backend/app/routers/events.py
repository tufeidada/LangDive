from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import EventLog, Vocabulary

router = APIRouter()

class EventRequest(BaseModel):
    event_type: str
    content_id: int | None = None
    segment_index: int | None = None
    word: str | None = None
    extra_json: dict | None = None

@router.post("/events")
async def post_event(req: EventRequest, db: AsyncSession = Depends(get_db)):
    event = EventLog(
        event_type=req.event_type,
        content_id=req.content_id,
        segment_index=req.segment_index,
        word=req.word,
        extra_json=req.extra_json,
    )
    db.add(event)
    await db.commit()
    return {"status": "ok"}


@router.get("/stats")
async def get_stats(days: int = Query(default=7, ge=1, le=365), db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)

    # Query all events in the period
    events_result = await db.execute(
        select(EventLog.event_type, EventLog.created_at)
        .where(EventLog.created_at >= since)
    )
    events = events_result.fetchall()

    # Aggregate counts
    content_opened = sum(1 for e in events if e.event_type == "content_open")
    segments_completed = sum(1 for e in events if e.event_type == "segment_complete")
    words_added = sum(1 for e in events if e.event_type in ("word_add", "word_custom_add"))
    words_reviewed = sum(1 for e in events if e.event_type == "review_grade")
    total_events = len(events)

    # Review accuracy — need grade from extra_json; query separately
    review_events_result = await db.execute(
        select(EventLog.extra_json)
        .where(EventLog.created_at >= since, EventLog.event_type == "review_grade")
    )
    review_events = review_events_result.fetchall()
    again_count = 0
    hard_count = 0
    easy_count = 0
    for (extra,) in review_events:
        if extra:
            grade = extra.get("grade")
            if grade == 0:
                again_count += 1
            elif grade == 1:
                hard_count += 1
            elif grade == 2:
                easy_count += 1

    # Active days
    active_days_set = set()
    for e in events:
        if e.created_at:
            dt = e.created_at
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            active_days_set.add(dt.date())
    active_days = len(active_days_set)

    # Vocabulary totals
    vocab_total_result = await db.execute(select(func.count()).select_from(Vocabulary))
    vocab_total = vocab_total_result.scalar() or 0

    vocab_status_result = await db.execute(
        select(Vocabulary.status, func.count())
        .group_by(Vocabulary.status)
    )
    vocab_by_status = {row[0]: row[1] for row in vocab_status_result.fetchall()}
    for s in ("unknown", "fuzzy", "known", "focus", "ignored"):
        vocab_by_status.setdefault(s, 0)

    # Daily activity breakdown
    daily: dict[str, dict] = {}
    for i in range(days):
        day = (now - timedelta(days=days - 1 - i)).date()
        daily[str(day)] = {"date": str(day), "events": 0, "words_added": 0, "reviews": 0}

    for e in events:
        if e.created_at:
            dt = e.created_at
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            day_str = str(dt.date())
            if day_str in daily:
                daily[day_str]["events"] += 1
                if e.event_type in ("word_add", "word_custom_add"):
                    daily[day_str]["words_added"] += 1
                if e.event_type == "review_grade":
                    daily[day_str]["reviews"] += 1

    return {
        "period_days": days,
        "content_opened": content_opened,
        "segments_completed": segments_completed,
        "words_added": words_added,
        "words_reviewed": words_reviewed,
        "review_accuracy": {"again": again_count, "hard": hard_count, "easy": easy_count},
        "total_events": total_events,
        "active_days": active_days,
        "vocab_total": vocab_total,
        "vocab_by_status": vocab_by_status,
        "daily_activity": list(daily.values()),
    }


@router.get("/pipeline-status")
async def get_pipeline_status(db: AsyncSession = Depends(get_db)):
    """Return the latest pipeline run status from event_log."""
    result = await db.execute(
        select(EventLog)
        .where(EventLog.event_type == "pipeline_run")
        .order_by(EventLog.created_at.desc())
        .limit(1)
    )
    latest = result.scalar_one_or_none()
    if latest is None:
        return {"status": "no_runs", "last_run": None, "details": {}}
    return {
        "status": (latest.extra_json or {}).get("status", "unknown"),
        "last_run": latest.created_at,
        "details": latest.extra_json or {},
    }

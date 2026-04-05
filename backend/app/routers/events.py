from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import EventLog

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

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Bookmark
from app.services.llm import call_llm

router = APIRouter()

EXPLAIN_SYSTEM = (
    "You are an English teacher helping Chinese learners at B1-B2 level. "
    "Explain sentences clearly and concisely in Chinese."
)


class BookmarkCreate(BaseModel):
    content_id: int
    segment_index: int
    sentence_text: str
    note: str | None = None


class ExplainRequest(BaseModel):
    sentence: str
    context: str | None = None


@router.post("/bookmarks")
async def create_bookmark(req: BookmarkCreate, db: AsyncSession = Depends(get_db)):
    b = Bookmark(
        content_id=req.content_id,
        segment_index=req.segment_index,
        sentence_text=req.sentence_text,
        note=req.note,
    )
    db.add(b)
    await db.commit()
    await db.refresh(b)
    return {
        "id": b.id,
        "content_id": b.content_id,
        "segment_index": b.segment_index,
        "sentence_text": b.sentence_text,
        "note": b.note,
        "created_at": str(b.created_at),
    }


@router.get("/bookmarks")
async def list_bookmarks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Bookmark).order_by(Bookmark.created_at.desc()))
    items = result.scalars().all()
    return [
        {
            "id": b.id,
            "content_id": b.content_id,
            "segment_index": b.segment_index,
            "sentence_text": b.sentence_text,
            "note": b.note,
            "created_at": str(b.created_at),
        }
        for b in items
    ]


@router.delete("/bookmarks/{bookmark_id}")
async def delete_bookmark(bookmark_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Bookmark).where(Bookmark.id == bookmark_id))
    b = result.scalar_one_or_none()
    if not b:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    await db.delete(b)
    await db.commit()
    return {"status": "deleted"}


@router.post("/sentences/explain")
async def explain_sentence(req: ExplainRequest):
    prompt = f'Explain this English sentence for a Chinese B1-B2 learner. Cover: grammar structure, key vocabulary, and meaning.\nSentence: "{req.sentence}"\nReturn in Chinese.'
    if req.context:
        prompt += f'\nContext: {req.context}'
    explanation = await call_llm(EXPLAIN_SYSTEM, prompt, purpose="sentence_explain")
    return {"explanation": explanation}

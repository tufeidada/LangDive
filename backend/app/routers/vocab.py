from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from app.database import get_db
from app.models import Vocabulary
from app.services.srs import calculate_next_review
from app.services.annotator import annotate_custom_word

router = APIRouter()


class AddWordRequest(BaseModel):
    word: str
    meaning_zh: str | None = None
    source: str | None = None


class StatusUpdateRequest(BaseModel):
    status: str


class ReviewRequest(BaseModel):
    grade: int


class PreviewAddAllRequest(BaseModel):
    words: list[dict]


class AILookupRequest(BaseModel):
    word: str
    context_sentence: str | None = None


@router.get("/vocab")
async def get_vocab(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Vocabulary).order_by(Vocabulary.created_at.desc()))
    items = result.scalars().all()
    return [{"word": v.word, "ipa": v.ipa, "meaning_zh": v.meaning_zh,
             "level": v.level, "status": v.status, "srs_level": v.srs_level,
             "next_review": str(v.next_review) if v.next_review else None,
             "easy_streak": v.easy_streak, "again_count": v.again_count,
             "encounter_count": v.encounter_count, "added_method": v.added_method}
            for v in items]


@router.get("/vocab/review")
async def get_review_words(db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    stmt = (select(Vocabulary)
            .where(Vocabulary.next_review <= now)
            .where(Vocabulary.status.notin_(["known", "ignored"]))
            .order_by(Vocabulary.next_review).limit(50))
    result = await db.execute(stmt)
    items = result.scalars().all()
    return [{"word": v.word, "ipa": v.ipa, "meaning_zh": v.meaning_zh,
             "detail_zh": v.detail_zh, "example_en": v.example_en,
             "example_zh": v.example_zh, "level": v.level,
             "srs_level": v.srs_level, "again_count": v.again_count}
            for v in items]


@router.post("/vocab")
async def add_word(req: AddWordRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Vocabulary).where(Vocabulary.word == req.word.lower()))
    if existing.scalar_one_or_none():
        return {"status": "exists"}
    v = Vocabulary(word=req.word.lower(), meaning_zh=req.meaning_zh or "",
                   source=req.source, added_method="manual",
                   next_review=datetime.now(timezone.utc))
    db.add(v)
    await db.commit()
    return {"status": "ok"}


@router.put("/vocab/{word}/status")
async def update_status(word: str, req: StatusUpdateRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Vocabulary).where(Vocabulary.word == word.lower()))
    v = result.scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=404, detail="Word not found")
    v.status = req.status
    await db.commit()
    return {"status": "ok"}


@router.put("/vocab/{word}/review")
async def review_word(word: str, req: ReviewRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Vocabulary).where(Vocabulary.word == word.lower()))
    v = result.scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=404, detail="Word not found")
    srs_result = calculate_next_review(req.grade, v.srs_level, v.easy_streak)
    v.srs_level = srs_result["srs_level"]
    v.easy_streak = srs_result["easy_streak"]
    v.next_review = srs_result["next_review"]
    v.last_reviewed = datetime.now(timezone.utc)
    v.total_reviews = (v.total_reviews or 0) + 1
    if req.grade == 0:
        v.again_count = (v.again_count or 0) + 1
    if srs_result.get("auto_hibernate"):
        v.status = "known"
    await db.commit()
    return {"srs_level": v.srs_level, "next_review": str(v.next_review), "status": v.status}


@router.post("/vocab/ai-lookup")
async def ai_lookup(req: AILookupRequest, db: AsyncSession = Depends(get_db)):
    result = await annotate_custom_word(req.word, req.context_sentence or "")
    if result is None:
        raise HTTPException(status_code=500, detail="AI lookup failed")
    return result


@router.post("/vocab/preview-add-all")
async def preview_add_all(req: PreviewAddAllRequest, db: AsyncSession = Depends(get_db)):
    added = 0
    for w in req.words:
        word_text = w.get("word", "").lower()
        existing = await db.execute(select(Vocabulary).where(Vocabulary.word == word_text))
        if existing.scalar_one_or_none():
            continue
        v = Vocabulary(word=word_text, meaning_zh=w.get("meaning_zh", ""),
                       ipa=w.get("ipa"), level=w.get("level"),
                       added_method="preview", next_review=datetime.now(timezone.utc))
        db.add(v)
        added += 1
    await db.commit()
    return {"added": added}

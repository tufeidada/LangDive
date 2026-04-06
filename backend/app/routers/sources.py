from typing import Optional, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import ContentSource, ContentCandidate

router = APIRouter()


class SourceCreate(BaseModel):
    name: str
    type: str
    url: str
    layer: int = 1
    priority: int = 50
    quality_score: float = 0.5
    default_difficulty: Optional[str] = None
    tags: Optional[list[str]] = None
    extra_config: Optional[dict[str, Any]] = None
    is_active: bool = True


class SourceUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    layer: Optional[int] = None
    priority: Optional[int] = None
    quality_score: Optional[float] = None
    default_difficulty: Optional[str] = None
    tags: Optional[list[str]] = None
    extra_config: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None


def _source_dict(s: ContentSource, candidate_count: int = 0) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "type": s.type,
        "url": s.url,
        "layer": s.layer,
        "priority": s.priority,
        "quality_score": s.quality_score,
        "default_difficulty": s.default_difficulty,
        "tags": s.tags,
        "extra_config": s.extra_config,
        "is_active": s.is_active,
        "last_fetched": s.last_fetched.isoformat() if s.last_fetched else None,
        "fetch_error_count": s.fetch_error_count,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "candidate_count": candidate_count,
    }


@router.get("/sources")
async def list_sources(db: AsyncSession = Depends(get_db)):
    """List all content sources with candidate stats."""
    # Fetch all sources
    stmt = select(ContentSource).order_by(ContentSource.layer, ContentSource.priority.desc())
    result = await db.execute(stmt)
    sources = result.scalars().all()

    # Get candidate counts per source
    count_stmt = select(
        ContentCandidate.source_id,
        func.count(ContentCandidate.id).label("cnt"),
    ).group_by(ContentCandidate.source_id)
    count_result = await db.execute(count_stmt)
    count_map: dict[int, int] = {row.source_id: row.cnt for row in count_result if row.source_id}

    return [_source_dict(s, count_map.get(s.id, 0)) for s in sources]


@router.post("/sources", status_code=201)
async def create_source(body: SourceCreate, db: AsyncSession = Depends(get_db)):
    """Add a new content source."""
    valid_types = {"youtube_channel", "newsletter_rss", "blog_rss", "hn_api", "classic_library"}
    if body.type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid type. Must be one of: {sorted(valid_types)}",
        )
    if body.layer not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="layer must be 1, 2, or 3")

    source = ContentSource(
        name=body.name,
        type=body.type,
        url=body.url,
        layer=body.layer,
        priority=body.priority,
        quality_score=body.quality_score,
        default_difficulty=body.default_difficulty,
        tags=body.tags,
        extra_config=body.extra_config,
        is_active=body.is_active,
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return _source_dict(source)


@router.put("/sources/{source_id}")
async def update_source(
    source_id: int,
    body: SourceUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update source fields (priority, is_active, tags, etc.)."""
    source = await db.get(ContentSource, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    update_data = body.model_dump(exclude_unset=True)
    if "layer" in update_data and update_data["layer"] not in (1, 2, 3):
        raise HTTPException(status_code=400, detail="layer must be 1, 2, or 3")

    for field, value in update_data.items():
        setattr(source, field, value)

    await db.commit()
    await db.refresh(source)
    return _source_dict(source)


@router.delete("/sources/{source_id}")
async def delete_source(source_id: int, db: AsyncSession = Depends(get_db)):
    """Soft delete: set is_active=false."""
    source = await db.get(ContentSource, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    source.is_active = False
    await db.commit()
    return {"status": "ok", "source_id": source_id, "is_active": False}

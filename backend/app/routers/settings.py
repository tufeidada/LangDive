from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Setting

router = APIRouter()

@router.get("/settings")
async def get_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Setting))
    items = result.scalars().all()
    return {s.key: s.value for s in items}

@router.put("/settings")
async def update_settings(updates: dict, db: AsyncSession = Depends(get_db)):
    for key, value in updates.items():
        result = await db.execute(select(Setting).where(Setting.key == key))
        s = result.scalar_one_or_none()
        if s:
            s.value = str(value)
        else:
            db.add(Setting(key=key, value=str(value)))
    await db.commit()
    return {"status": "ok"}

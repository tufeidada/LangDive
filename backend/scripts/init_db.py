import asyncio
from sqlalchemy import text
from app.database import async_engine
from app.models import Base


async def init():
    # Safety check: warn if content data exists
    try:
        async with async_engine.connect() as conn:
            result = await conn.execute(text("SELECT count(*) FROM content"))
            count = result.scalar()
            if count and count > 0:
                print(f"⚠️  WARNING: content table has {count} rows. Only creating missing tables (no drop).")
    except Exception:
        pass  # table doesn't exist yet, safe to proceed

    # create_all only creates tables that don't exist — NEVER drops
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("All tables created (existing data preserved).")


if __name__ == "__main__":
    asyncio.run(init())

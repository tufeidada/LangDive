import asyncio
from app.database import async_engine
from app.models import Base


async def init():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("All tables created.")


if __name__ == "__main__":
    asyncio.run(init())

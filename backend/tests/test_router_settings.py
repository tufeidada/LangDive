import pytest
import pytest_asyncio
from sqlalchemy import delete
from app.database import async_engine, AsyncSessionLocal
from app.models import Base, Setting

@pytest_asyncio.fixture(autouse=True)
async def setup():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        await session.execute(delete(Setting))
        session.add(Setting(key="tts_speed", value="1.0"))
        session.add(Setting(key="show_chinese", value="false"))
        await session.commit()
    yield

@pytest.mark.asyncio
async def test_get_settings(client):
    resp = await client.get("/api/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tts_speed"] == "1.0"

@pytest.mark.asyncio
async def test_update_settings(client):
    resp = await client.put("/api/settings", json={"tts_speed": "1.5"})
    assert resp.status_code == 200
    resp = await client.get("/api/settings")
    assert resp.json()["tts_speed"] == "1.5"

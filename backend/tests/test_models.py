import pytest
from sqlalchemy import inspect
from app.database import async_engine
from app.models import Base


@pytest.mark.asyncio
async def test_create_all_tables():
    # NEVER drop_all — just verify create_all works without destroying data
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_engine.connect() as conn:
        tables = await conn.run_sync(
            lambda sync_conn: inspect(sync_conn).get_table_names()
        )
    expected = {"content", "content_segment", "vocabulary", "event_log",
                "cached_asset", "settings", "search_query_log"}
    assert expected.issubset(set(tables))

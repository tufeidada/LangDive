from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import CachedAsset


async def get_cached(
    session: AsyncSession,
    content_hash: str,
    asset_type: str,
    provider: str | None = None,
    version: str = "1",
) -> str | None:
    stmt = select(CachedAsset).where(
        CachedAsset.content_hash == content_hash,
        CachedAsset.asset_type == asset_type,
        CachedAsset.version == version,
    )
    if provider:
        stmt = stmt.where(CachedAsset.provider == provider)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return row.text_content if row.text_content else row.file_path


async def set_cached(
    session: AsyncSession,
    content_hash: str,
    asset_type: str,
    text_content: str | None = None,
    file_path: str | None = None,
    provider: str | None = None,
    version: str = "1",
) -> None:
    asset = CachedAsset(
        content_hash=content_hash,
        asset_type=asset_type,
        provider=provider,
        version=version,
        text_content=text_content,
        file_path=file_path,
    )
    session.add(asset)

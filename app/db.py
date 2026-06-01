from collections.abc import AsyncIterator
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings


def _normalize_url(url: str) -> tuple[str, dict]:
    """Convert any Postgres URL to use the asyncpg driver and strip
    sync-driver-only query params (like sslmode). Returns (clean_url, connect_args).
    """
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    parts = urlsplit(url)
    query = parse_qs(parts.query)

    connect_args: dict = {}

    sslmode_values = query.pop("sslmode", None)
    if sslmode_values and sslmode_values[0] in {"require", "verify-ca", "verify-full"}:
        connect_args["ssl"] = True

    clean_query = urlencode({k: v[0] for k, v in query.items()})
    clean_url = urlunsplit(
        (parts.scheme, parts.netloc, parts.path, clean_query, parts.fragment)
    )
    return clean_url, connect_args


_url, _connect_args = _normalize_url(settings.database_url)

engine = create_async_engine(
    _url,
    echo=False,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session

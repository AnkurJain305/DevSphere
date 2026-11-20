from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "postgres"})
_LIBPQ_SSL_KEYS = frozenset({"ssl", "sslmode"})


def prepare_database_url(database_url: str) -> str:
    """Use the asyncpg driver and drop libpq SSL query keys asyncpg does not accept."""
    parts = urlsplit(database_url)
    scheme = "postgresql+asyncpg" if parts.scheme in {"postgres", "postgresql"} else parts.scheme
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key not in _LIBPQ_SSL_KEYS
    ]
    return urlunsplit((scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def asyncpg_connect_args(database_url: str) -> dict[str, Any]:
    """Supabase requires TLS. A local Postgres container does not."""
    host = urlsplit(database_url).hostname
    if host in _LOCAL_HOSTS:
        return {}
    return {"ssl": True}


def create_db_engine(database_url: str) -> AsyncEngine:
    """Open a pool only when a caller asks for one. Importing the app does not connect."""
    url = prepare_database_url(database_url)
    return create_async_engine(
        url,
        pool_pre_ping=True,
        connect_args=asyncpg_connect_args(url),
    )

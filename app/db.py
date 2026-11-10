"""Postgres connection pool with pgvector registered."""

from __future__ import annotations

from pgvector.psycopg import register_vector
from psycopg_pool import ConnectionPool

from app.config import settings

_pool: ConnectionPool | None = None


def _configure(conn) -> None:
    register_vector(conn)
    conn.commit()  # end the implicit transaction so the connection is returned idle


def get_pool() -> ConnectionPool:
    """Return the process-wide pool, creating it on first use."""
    global _pool
    if _pool is None:
        _pool = ConnectionPool(settings.database_url, min_size=1, max_size=5, configure=_configure, open=True)
    return _pool


def reset_pool() -> None:
    """Close and forget the pool (used by tests that switch databases)."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None

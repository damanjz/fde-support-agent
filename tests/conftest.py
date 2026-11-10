"""Shared fixtures: an isolated test database and a deterministic fake embedder."""

from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path

import psycopg
import pytest

from app import db, llm
from app.config import settings

SCHEMA = Path(__file__).resolve().parent.parent / "db" / "schema.sql"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
TEST_DB = "larkfield_test"


def fake_embed(texts: list[str], kind: str = "document") -> list[list[float]]:
    """Bag-of-words hashing embedding: texts sharing words get similar vectors."""
    out = []
    for text in texts:
        vec = [0.0] * settings.embed_dims
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            vec[int(hashlib.md5(word.encode()).hexdigest(), 16) % settings.embed_dims] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        out.append([v / norm for v in vec])
    return out


@pytest.fixture(scope="session")
def test_db():
    """Create a throwaway database next to the compose one; skip if Postgres is down."""
    admin_url = settings.database_url
    base, _, _ = admin_url.rpartition("/")
    try:
        with psycopg.connect(admin_url, autocommit=True, connect_timeout=2) as conn:
            conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB}")
            conn.execute(f"CREATE DATABASE {TEST_DB}")
    except psycopg.OperationalError:
        pytest.skip("Postgres is not running")
    test_url = f"{base}/{TEST_DB}"
    with psycopg.connect(test_url, autocommit=True) as conn:
        conn.execute(SCHEMA.read_text(encoding="utf-8"))
    original = settings.database_url
    settings.database_url = test_url
    db.reset_pool()
    yield test_url
    db.reset_pool()
    settings.database_url = original
    with psycopg.connect(admin_url, autocommit=True) as conn:
        conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)")


@pytest.fixture
def ingested(test_db, monkeypatch):
    from app import ingest

    monkeypatch.setattr(llm, "embed", fake_embed)
    ingest.ingest(FIXTURES)

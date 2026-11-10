"""Hybrid retrieval: Postgres full-text + pgvector cosine, fused with reciprocal rank fusion."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import date
from typing import Literal

from pgvector import Vector

from app import db, llm

RRF_K = 60
CANDIDATES = 20  # per ranker, before fusion


@dataclass
class Chunk:
    chunk_id: int
    article_id: str
    title: str
    section: str
    content: str
    updated: date
    score: float


_COLUMNS = "c.id, c.article_id, a.title, c.section, c.content, a.updated"

_KEYWORD_SQL = f"""
SELECT {_COLUMNS}, ts_rank_cd(c.tsv, q) AS score
FROM chunks c JOIN articles a ON a.id = c.article_id,
     websearch_to_tsquery('english', %(q)s) q
WHERE c.tsv @@ q
ORDER BY score DESC, c.id LIMIT %(n)s
"""

_VECTOR_SQL = f"""
SELECT {_COLUMNS}, 1 - (c.embedding <=> %(v)s) AS score
FROM chunks c JOIN articles a ON a.id = c.article_id
WHERE c.embedding IS NOT NULL
ORDER BY c.embedding <=> %(v)s, c.id LIMIT %(n)s
"""


def _or_query(text: str) -> str:
    """Turn a question into 'a or b or c' so one missing word does not kill the match."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return " or ".join(words)


def _run(sql: str, params: dict) -> list[Chunk]:
    with db.get_pool().connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [Chunk(*row) for row in rows]


def keyword_search(query: str, n: int) -> list[Chunk]:
    q = _or_query(query)
    return _run(_KEYWORD_SQL, {"q": q, "n": n}) if q else []


def vector_search(query: str, n: int) -> list[Chunk]:
    vec = llm.embed([query], kind="query")[0]
    return _run(_VECTOR_SQL, {"v": Vector(vec), "n": n})


def rrf_fuse(rankings: list[list[Chunk]], k: int = RRF_K) -> list[Chunk]:
    """Reciprocal rank fusion: score(d) = sum over rankers of 1 / (k + rank)."""
    scores: dict[int, float] = {}
    by_id: dict[int, Chunk] = {}
    for ranking in rankings:
        for rank, chunk in enumerate(ranking, start=1):
            scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + 1.0 / (k + rank)
            by_id[chunk.chunk_id] = chunk
    ordered = sorted(scores, key=lambda cid: (-scores[cid], cid))
    return [replace(by_id[cid], score=scores[cid]) for cid in ordered]


_ARTICLE_SQL = f"""
SELECT {_COLUMNS}, 0.0 AS score
FROM chunks c JOIN articles a ON a.id = c.article_id
WHERE c.article_id = ANY(%(ids)s) ORDER BY c.article_id, c.id
"""


def expand_articles(chunks: list[Chunk], top_articles: int = 3) -> list[Chunk]:
    """Add the sibling sections of the top articles, keeping retrieval order otherwise.

    Sections are small, so a question often hits the right article but the wrong section (eval run 2:
    "express delivery cost" got KB-001 'Delivery times' but not 'Shipping charges'). Help-centre
    articles are short, so the whole article for the best 3 hits is cheap context.
    """
    top: list[str] = []
    for c in chunks:
        if c.article_id not in top:
            top.append(c.article_id)
        if len(top) == top_articles:
            break
    if not top:
        return chunks
    have = {c.chunk_id for c in chunks}
    siblings = [c for c in _run(_ARTICLE_SQL, {"ids": top}) if c.chunk_id not in have]
    out: list[Chunk] = []
    for c in chunks:  # each sibling goes right after the first hit from its article
        out.append(c)
        if c.article_id in top:
            out.extend(s for s in siblings if s.article_id == c.article_id)
            siblings = [s for s in siblings if s.article_id != c.article_id]
    return out


def search(
    query: str, k: int = 5, mode: Literal["hybrid", "keyword", "vector"] = "hybrid"
) -> list[Chunk]:
    if mode == "keyword":
        return keyword_search(query, k)
    if mode == "vector":
        return vector_search(query, k)
    fused = rrf_fuse([keyword_search(query, CANDIDATES), vector_search(query, CANDIDATES)])
    return fused[:k]

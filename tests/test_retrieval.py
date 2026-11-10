from datetime import date

import pytest

from app import ingest, retrieval
from app.retrieval import Chunk


def chunk(cid: int) -> Chunk:
    return Chunk(cid, f"KB-{cid}", "t", "s", "c", date(2026, 1, 1), 0.0)


def test_rrf_rewards_agreement_between_rankers():
    fused = retrieval.rrf_fuse([[chunk(1), chunk(2), chunk(3)], [chunk(3), chunk(2), chunk(9)]])
    assert [c.chunk_id for c in fused] == [3, 2, 1, 9]
    assert fused[0].score == pytest.approx(1 / 63 + 1 / 61)


def test_rrf_single_ranker_keeps_order():
    assert [c.chunk_id for c in retrieval.rrf_fuse([[chunk(5), chunk(4)]])] == [5, 4]


def test_or_query_joins_words():
    assert retrieval._or_query("Can I return opened beans?") == "can or i or return or opened or beans"


def test_parse_article_strips_comment_and_chunks_sections():
    text = """---
id: KB-1
title: T
category: returns   # a|b
updated: 2026-01-02
---
Intro

## A
one

## B
two
"""
    art = ingest.parse_article(text)
    assert art.category == "returns" and art.updated == date(2026, 1, 2)
    assert ingest.chunk_article(art.body) == [("Overview", "Intro"), ("A", "one"), ("B", "two")]


@pytest.mark.db
def test_ingest_is_idempotent(ingested):
    from tests.conftest import FIXTURES

    counts = ingest.ingest(FIXTURES)
    assert counts["articles"] == 2 and counts["chunks"] == 4


@pytest.mark.db
def test_keyword_search_finds_section(ingested):
    hits = retrieval.search("Can I return opened beans?", mode="keyword")
    assert hits[0].article_id == "KB-901" and hits[0].section == "Opened beans"
    assert hits[0].updated == date(2026, 8, 14)


@pytest.mark.db
def test_vector_and_hybrid_search(ingested):
    assert retrieval.search("BlueDart delivery days", mode="vector")[0].article_id == "KB-902"
    hybrid = retrieval.search("delivery estimates for my parcel", k=2)
    assert hybrid[0].article_id == "KB-902" and len(hybrid) <= 2


def test_expand_articles_adds_siblings_of_top_articles(monkeypatch):
    def ch(cid, aid, section):
        return Chunk(cid, aid, "t", section, "x", date(2026, 1, 1), 0.0)

    hits = [ch(1, "KB-001", "Delivery times"), ch(30, "KB-003", "Late"), ch(50, "KB-004", "Remote")]
    siblings = [ch(1, "KB-001", "Delivery times"), ch(3, "KB-001", "Shipping charges"), ch(31, "KB-003", "Trace")]
    seen = {}
    monkeypatch.setattr(retrieval, "_run", lambda sql, params: seen.update(params) or siblings)
    out = retrieval.expand_articles(hits, top_articles=2)
    assert seen["ids"] == ["KB-001", "KB-003"]
    assert [c.chunk_id for c in out] == [1, 3, 30, 31, 50]

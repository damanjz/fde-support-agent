"""Load data/ into Postgres: python -m app.ingest (truncate + reload, idempotent)."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from pgvector import Vector

from app import db, llm

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
EMBED_BATCH = 16


@dataclass
class Article:
    id: str
    title: str
    category: str
    updated: date
    body: str


def parse_article(text: str) -> Article:
    """Parse `---` front matter (key: value lines) followed by a markdown body."""
    m = re.match(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", text.replace("\r\n", "\n"), re.DOTALL)
    if not m:
        raise ValueError("article has no front matter")
    meta = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = re.sub(r"\s+#.*$", "", value).strip()
    return Article(
        id=meta["id"],
        title=meta["title"],
        category=meta["category"],
        updated=date.fromisoformat(meta["updated"]),
        body=m.group(2).strip(),
    )


def chunk_article(body: str) -> list[tuple[str, str]]:
    """Split a body into (section, content) pairs at `## ` headings; any intro becomes 'Overview'."""
    sections: list[tuple[str, str]] = []
    heading, lines = "Overview", []
    for line in body.splitlines():
        if line.startswith("## "):
            if "".join(lines).strip():
                sections.append((heading, "\n".join(lines).strip()))
            heading, lines = line[3:].strip(), []
        else:
            lines.append(line)
    if "".join(lines).strip():
        sections.append((heading, "\n".join(lines).strip()))
    return sections


def _load_json(name: str, data_dir: Path) -> list[dict]:
    path = data_dir / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def ingest(data_dir: Path = DATA_DIR) -> dict[str, int]:
    paths = sorted((data_dir / "articles").glob("*.md"))
    articles = [parse_article(p.read_text(encoding="utf-8")) for p in paths]
    products = _load_json("products.json", data_dir)
    orders = _load_json("orders.json", data_dir)
    tickets = _load_json("tickets.json", data_dir)

    # Chunk text carries the title so both rankers can match on it.
    pieces = [(a, section, content) for a in articles for section, content in chunk_article(a.body)]
    texts = [f"{a.title} - {section}\n{content}" for a, section, content in pieces]
    embeddings: list[list[float]] = []
    for i in range(0, len(texts), EMBED_BATCH):
        embeddings += llm.embed(texts[i : i + EMBED_BATCH], kind="document")

    with db.get_pool().connection() as conn:
        conn.execute("TRUNCATE articles, products, orders, order_items, past_tickets CASCADE")
        for a in articles:
            conn.execute(
                "INSERT INTO articles (id, title, category, updated, body) VALUES (%s,%s,%s,%s,%s)",
                (a.id, a.title, a.category, a.updated, a.body),
            )
        for (a, section, content), text, emb in zip(pieces, texts, embeddings, strict=True):
            conn.execute(
                "INSERT INTO chunks (article_id, section, content, embedding, tsv) "
                "VALUES (%s,%s,%s,%s, to_tsvector('english', %s))",
                (a.id, section, content, Vector(emb), text),
            )
        for p in products:
            conn.execute(
                "INSERT INTO products (sku, name, category, price_inr, stock, warranty_months) "
                "VALUES (%(sku)s,%(name)s,%(category)s,%(price_inr)s,%(stock)s,%(warranty_months)s)",
                p,
            )
        for o in orders:
            conn.execute(
                "INSERT INTO orders (order_id, customer_name, email, phone, total_inr, status, ordered_at,"
                " shipped_at, delivered_at, carrier, tracking) VALUES (%(order_id)s,%(customer_name)s,"
                "%(email)s,%(phone)s,%(total_inr)s,%(status)s,%(ordered_at)s,%(shipped_at)s,"
                "%(delivered_at)s,%(carrier)s,%(tracking)s)",
                o,
            )
            for item in o["items"]:
                conn.execute(
                    "INSERT INTO order_items (order_id, sku, qty, price_inr) VALUES (%s,%s,%s,%s)",
                    (o["order_id"], item["sku"], item["qty"], item["price_inr"]),
                )
        for t in tickets:
            conn.execute(
                "INSERT INTO past_tickets (ticket_id, created_at, subject, body, resolution) "
                "VALUES (%(ticket_id)s,%(created_at)s,%(subject)s,%(body)s,%(resolution)s)",
                t,
            )
    return {
        "articles": len(articles),
        "chunks": len(pieces),
        "products": len(products),
        "orders": len(orders),
        "tickets": len(tickets),
    }


if __name__ == "__main__":
    print("ingested:", ingest(Path(sys.argv[1]) if len(sys.argv) > 1 else DATA_DIR))
    db.reset_pool()

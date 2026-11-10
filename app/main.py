"""FastAPI service: /chat, /health, /metrics and the static chat page."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import agent, db
from app.config import settings

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Larkfield support agent")


class ChatRequest(BaseModel):
    session_id: str
    message: str
    confirm: bool | None = None


@app.post("/chat")
def chat(req: ChatRequest) -> dict:
    return asdict(agent.run_turn(req.session_id, req.message, confirm=req.confirm))


def _check_db() -> bool:
    try:
        with db.get_pool().connection() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:  # noqa: BLE001 - any failure means unhealthy
        return False


def _check_ollama() -> bool:
    try:
        return httpx.get(f"{settings.ollama_url}/api/tags", timeout=3).status_code == 200
    except httpx.HTTPError:
        return False


@app.get("/health")
def health() -> dict:
    db_ok, ollama_ok = _check_db(), _check_ollama()
    return {"status": "ok" if db_ok and ollama_ok else "degraded", "db": db_ok, "ollama": ollama_ok}


_METRICS_SQL = """
SELECT count(*),
       count(*) FILTER (WHERE (record->>'escalated')::boolean),
       percentile_cont(0.5) WITHIN GROUP (ORDER BY latency_ms),
       percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms)
FROM request_log
"""


@app.get("/metrics")
def metrics() -> dict:
    with db.get_pool().connection() as conn:
        total, escalated, p50, p95 = conn.execute(_METRICS_SQL).fetchone()
    return {
        "requests": total,
        "escalated": escalated,
        "latency_ms_p50": round(p50) if p50 is not None else None,
        "latency_ms_p95": round(p95) if p95 is not None else None,
    }


# Mounted last so the API routes above take precedence over the catch-all static files.
if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

"""Request logging: PII-masked JSONL file plus request_log table. Never raises."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from app.config import settings
from app.guardrails import mask_pii

LOG_PATH = Path(__file__).resolve().parent.parent / "logs" / "requests.jsonl"
_log = logging.getLogger(__name__)


def _mask(value: Any) -> Any:
    if isinstance(value, str):
        return mask_pii(value)
    if isinstance(value, dict):
        return {k: _mask(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_mask(v) for v in value]
    return value


def _latency(record: dict) -> int | None:
    val = record.get("latency_ms")
    if val is None and isinstance(record.get("usage"), dict):
        val = record["usage"].get("latency_ms")
    try:
        return int(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def _write_file(line: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def _write_db(masked: dict) -> None:
    session_id = masked.get("session_id")
    with psycopg.connect(settings.database_url, connect_timeout=3, autocommit=True) as conn:
        conn.execute(
            "INSERT INTO request_log (session_id, record, latency_ms) VALUES (%s, %s, %s)",
            (str(session_id) if session_id is not None else None, Jsonb(masked, dumps=_dumps), _latency(masked)),
        )


def _dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def log_request(record: dict) -> None:
    """Mask PII, append a JSON line to logs/requests.jsonl and insert into request_log."""
    try:
        masked = _mask(record)
    except Exception:  # noqa: BLE001 - logging must never raise
        _log.exception("log_request: masking failed")
        return
    try:
        _write_file(_dumps(masked))
    except Exception:  # noqa: BLE001
        _log.exception("log_request: file write failed")
    try:
        _write_db(masked)
    except Exception:  # noqa: BLE001
        _log.warning("log_request: db insert failed", exc_info=True)

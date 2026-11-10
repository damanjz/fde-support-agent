"""Send one customer message to the running agent API and print the reply as JSON.

Usage:
  python scripts/talk.py <session_id> "message"
  python scripts/talk.py <session_id> confirm --confirm yes
  python scripts/talk.py <session_id> cancel --confirm no
"""

import argparse
import json
import sys

import httpx


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("session_id")
    p.add_argument("message")
    p.add_argument("--confirm", choices=["yes", "no"])
    p.add_argument("--url", default="http://localhost:8000/chat")
    a = p.parse_args()
    body = {"session_id": a.session_id, "message": a.message}
    if a.confirm:
        body["confirm"] = a.confirm == "yes"
    r = httpx.post(a.url, json=body, timeout=300)
    r.raise_for_status()
    d = r.json()
    out = {
        "text": d.get("text"),
        "citations": d.get("citations"),
        "tools": [{"name": t.get("name"), "args": t.get("args"), "result": t.get("result")} for t in d.get("tool_calls") or []],
        "pending_action": d.get("pending_action"),
        "escalated": d.get("escalated"),
        "latency_ms": (d.get("usage") or {}).get("latency_ms"),
    }
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

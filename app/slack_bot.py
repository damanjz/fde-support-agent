"""Slack bot (Socket Mode). One agent session per thread; Confirm/Cancel buttons for pending actions.

Run: python -m app.slack_bot   (needs SLACK_BOT_TOKEN and SLACK_APP_TOKEN)
"""

from __future__ import annotations

import dataclasses
import json
import re
import sys
from typing import Any

from app.config import settings

MENTION_RE = re.compile(r"<@[A-Z0-9]+>")
FAIL_TEXT = "Sorry, I hit a problem. I'll pass this to a person."


def strip_mention(text: str) -> str:
    return MENTION_RE.sub("", text or "").strip()


def session_id_for(channel: str, thread_ts: str | None, ts: str) -> str:
    return f"slack-{channel}-{thread_ts or ts}"


def _as_dict(reply: Any) -> dict:
    if isinstance(reply, dict):
        return reply
    if dataclasses.is_dataclass(reply) and not isinstance(reply, type):
        return dataclasses.asdict(reply)
    return reply.model_dump()


def build_blocks(reply: Any, session_id: str) -> list[dict]:
    """Block Kit message for an agent reply; adds Confirm/Cancel buttons when an action is pending."""
    r = _as_dict(reply)
    text = r.get("text") or "(no reply)"
    blocks: list[dict] = [{"type": "section", "text": {"type": "mrkdwn", "text": text}}]
    if r.get("citations"):
        sources = ", ".join(f"`{c}`" for c in r["citations"])
        blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": f"Sources: {sources}"}]})
    pending = r.get("pending_action")
    if pending:
        name = pending.get("tool") or pending.get("name") or "action"
        args = json.dumps(pending.get("args") or {}, ensure_ascii=False)
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"Pending action: `{name}` {args}"}})
        blocks.append({
            "type": "actions",
            "block_id": "pending_action",
            "elements": [
                {"type": "button", "action_id": "confirm_action", "style": "primary", "value": session_id,
                 "text": {"type": "plain_text", "text": "Confirm"}},
                {"type": "button", "action_id": "cancel_action", "value": session_id,
                 "text": {"type": "plain_text", "text": "Cancel"}},
            ],
        })
    u = r.get("usage") or {}
    if u:
        tokens = int(u.get("prompt_tokens", 0)) + int(u.get("completion_tokens", 0))
        blocks.append({"type": "context", "elements": [
            {"type": "mrkdwn", "text": f"{float(u.get('latency_ms', 0)) / 1000:.1f}s, {tokens} tokens"}]})
    return blocks


def _run(session_id: str, message: str, confirm: bool | None = None) -> Any:
    from app.agent import run_turn  # lazy: keeps this module importable on its own

    return run_turn(session_id, message, confirm=confirm)


def build_app(bot_token: str):
    from slack_bolt import App

    app = App(token=bot_token)

    def answer(say, event: dict, text: str) -> None:
        channel = event["channel"]
        thread = event.get("thread_ts") or event["ts"]
        sid = session_id_for(channel, event.get("thread_ts"), event["ts"])
        try:
            reply = _run(sid, text)
            say(text=_as_dict(reply).get("text") or "", blocks=build_blocks(reply, sid), thread_ts=thread)
        except Exception:  # noqa: BLE001 - never leave the user without a reply
            say(text=FAIL_TEXT, thread_ts=thread)

    @app.event("app_mention")
    def on_mention(event, say):
        answer(say, event, strip_mention(event.get("text", "")))

    @app.event("message")
    def on_message(event, say):
        if event.get("channel_type") != "im" or event.get("bot_id") or event.get("subtype"):
            return
        answer(say, event, event.get("text", "").strip())

    def decide(ack, body, client, confirm: bool) -> None:
        ack()
        action = body["actions"][0]
        sid = action["value"]
        channel = body["channel"]["id"]
        msg = body["message"]
        thread = msg.get("thread_ts") or msg["ts"]
        try:
            reply = _run(sid, "confirm" if confirm else "cancel", confirm=confirm)
            out = _as_dict(reply).get("text") or ""
        except Exception:  # noqa: BLE001
            out = FAIL_TEXT
        # Replace the buttons so they cannot be pressed twice.
        kept = [b for b in msg.get("blocks", []) if b.get("block_id") != "pending_action"]
        kept.append({"type": "context", "elements": [
            {"type": "mrkdwn", "text": "Confirmed." if confirm else "Cancelled."}]})
        client.chat_update(channel=channel, ts=msg["ts"], blocks=kept, text=msg.get("text", ""))
        client.chat_postMessage(channel=channel, thread_ts=thread, text=out)

    @app.action("confirm_action")
    def on_confirm(ack, body, client):
        decide(ack, body, client, True)

    @app.action("cancel_action")
    def on_cancel(ack, body, client):
        decide(ack, body, client, False)

    return app


def main() -> int:
    if not settings.slack_bot_token or not settings.slack_app_token:
        print(
            "Slack bot not started: SLACK_BOT_TOKEN and SLACK_APP_TOKEN must both be set "
            "(environment or .env). Create a Slack app with Socket Mode enabled, then set the bot "
            "token (xoxb-...) and app-level token (xapp-...).",
            file=sys.stderr,
        )
        return 1
    from slack_bolt.adapter.socket_mode import SocketModeHandler

    app = build_app(settings.slack_bot_token)
    SocketModeHandler(app, settings.slack_app_token).start()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

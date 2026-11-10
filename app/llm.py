"""LLM and embedding clients (Ollama by default, Anthropic optional)."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

import httpx

from app.config import settings

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


class LLMError(RuntimeError):
    """Raised when the provider cannot be reached or returns something unusable."""


@dataclass
class ToolCall:
    name: str
    args: dict


@dataclass
class LLMResponse:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    provider: str = ""
    model: str = ""


def _post(url: str, payload: dict, headers: dict | None = None) -> dict:
    """POST JSON with a timeout and one retry on transport errors and 5xx."""
    last: Exception | None = None
    for _ in range(2):
        try:
            r = httpx.post(url, json=payload, headers=headers, timeout=settings.llm_timeout_s)
            if r.status_code >= 500:
                raise httpx.HTTPStatusError("server error", request=r.request, response=r)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPError as exc:
            last = exc
    raise LLMError(f"request to {url} failed: {last!r}") from last


def chat(messages: list[dict], tools: list[dict] | None = None) -> LLMResponse:
    """Send a chat turn. Messages use the Ollama shape; the Anthropic provider converts them."""
    start = time.monotonic()
    if settings.llm_provider == "anthropic":
        resp = _chat_anthropic(messages, tools)
    else:
        resp = _chat_ollama(messages, tools)
    resp.latency_ms = int((time.monotonic() - start) * 1000)
    return resp


# --- Ollama ----------------------------------------------------------------------------------------


def _chat_ollama(messages: list[dict], tools: list[dict] | None) -> LLMResponse:
    payload: dict = {
        "model": settings.ollama_model,
        "messages": messages,
        "stream": False,
        "think": False,
        "options": {"temperature": 0.2},
    }
    if tools:
        payload["tools"] = tools
    return parse_ollama(_post(f"{settings.ollama_url}/api/chat", payload))


def parse_ollama(data: dict) -> LLMResponse:
    msg = data.get("message") or {}
    calls = []
    for tc in msg.get("tool_calls") or []:
        fn = tc.get("function", {})
        args = fn.get("arguments") or {}
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}
        calls.append(ToolCall(name=fn.get("name", ""), args=args))
    return LLMResponse(
        content=(msg.get("content") or "").strip(),
        tool_calls=calls,
        prompt_tokens=data.get("prompt_eval_count", 0),
        completion_tokens=data.get("eval_count", 0),
        provider="ollama",
        model=data.get("model", settings.ollama_model),
    )


# --- Anthropic -------------------------------------------------------------------------------------


def to_anthropic_tools(tools: list[dict]) -> list[dict]:
    """OpenAI/Ollama function specs -> Anthropic tool definitions."""
    out = []
    for t in tools:
        fn = t["function"]
        out.append(
            {
                "name": fn["name"],
                "description": fn.get("description", ""),
                "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
            }
        )
    return out


def to_anthropic_messages(messages: list[dict]) -> tuple[str, list[dict]]:
    """Split out the system prompt and convert tool calls/results to content blocks.

    Tool results are paired with the preceding assistant tool calls by order.
    """
    system_parts: list[str] = []
    out: list[dict] = []
    pending_ids: list[str] = []
    counter = 0
    for m in messages:
        role = m["role"]
        if role == "system":
            system_parts.append(m["content"])
        elif role == "assistant" and m.get("tool_calls"):
            blocks: list[dict] = []
            if m.get("content"):
                blocks.append({"type": "text", "text": m["content"]})
            for tc in m["tool_calls"]:
                counter += 1
                tool_id = f"toolu_{counter:04d}"
                pending_ids.append(tool_id)
                fn = tc["function"]
                blocks.append({"type": "tool_use", "id": tool_id, "name": fn["name"], "input": fn["arguments"]})
            out.append({"role": "assistant", "content": blocks})
        elif role == "tool":
            block = {"type": "tool_result", "tool_use_id": pending_ids.pop(0), "content": m["content"]}
            if out and out[-1]["role"] == "user" and isinstance(out[-1]["content"], list):
                out[-1]["content"].append(block)  # parallel results share one user message
            else:
                out.append({"role": "user", "content": [block]})
        else:
            out.append({"role": role, "content": m["content"]})
    return "\n\n".join(system_parts), out


def parse_anthropic(data: dict) -> LLMResponse:
    text, calls = [], []
    for block in data.get("content", []):
        if block.get("type") == "text":
            text.append(block["text"])
        elif block.get("type") == "tool_use":
            calls.append(ToolCall(name=block["name"], args=block.get("input") or {}))
    usage = data.get("usage", {})
    return LLMResponse(
        content="".join(text).strip(),
        tool_calls=calls,
        prompt_tokens=usage.get("input_tokens", 0),
        completion_tokens=usage.get("output_tokens", 0),
        provider="anthropic",
        model=data.get("model", settings.anthropic_model),
    )


def _chat_anthropic(messages: list[dict], tools: list[dict] | None) -> LLMResponse:
    if not settings.anthropic_api_key:
        raise LLMError("LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set")
    system, converted = to_anthropic_messages(messages)
    payload: dict = {
        "model": settings.anthropic_model,
        "max_tokens": 1024,
        "system": system,
        "messages": converted,
    }
    if tools:
        payload["tools"] = to_anthropic_tools(tools)
    headers = {
        "x-api-key": settings.anthropic_api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    return parse_anthropic(_post(ANTHROPIC_URL, payload, headers))


# --- Embeddings ------------------------------------------------------------------------------------


def embed(texts: list[str], kind: str = "document") -> list[list[float]]:
    """Embed texts with nomic-embed-text. kind is 'document' (chunks) or 'query'."""
    prefix = "search_query: " if kind == "query" else "search_document: "
    data = _post(
        f"{settings.ollama_url}/api/embed",
        {"model": settings.embed_model, "input": [prefix + t for t in texts]},
    )
    return data["embeddings"]

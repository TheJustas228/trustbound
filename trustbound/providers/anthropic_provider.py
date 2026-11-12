"""Anthropic Messages API backend (official `anthropic` SDK).

Converts TrustBound's internal OpenAI-format messages and tools to Anthropic's
format. Notes for current Claude models (Haiku 5.5 / Sonnet 5.5 / Opus 5.5):
  * sampling parameters (temperature/top_p/top_k) are NOT sent: current models
    reject non-default values, so every Claude call runs at default sampling;
  * adaptive thinking is on by default; depth is set with `output_config.effort`;
  * thinking blocks must be passed back unchanged in multi-turn tool loops (the
    API checks that the history is append-only), so each assistant turn keeps the
    raw content blocks under the private key `_anthropic_content` and they are
    replayed verbatim;
  * no server-side refusal fallback is configured: a refusal is recorded as data
    (finish_reason "refusal") instead of silently switching to another model.
The API key is read by the SDK from ANTHROPIC_API_KEY; it is never logged.
"""
from __future__ import annotations

import json
import os
from typing import Any

from .base import ChatResponse, GenParams, ToolCall, Usage
from .common import CachedProvider, TransientError

RAW_KEY = "_anthropic_content"


def to_anthropic(messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None
                 ) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    system_parts: list[str] = []
    out: list[dict[str, Any]] = []

    def append(role: str, block: dict[str, Any]) -> None:
        if out and out[-1]["role"] == role:
            out[-1]["content"].append(block)
        else:
            out.append({"role": role, "content": [block]})

    for m in messages:
        role = m["role"]
        if role in ("system", "developer"):
            system_parts.append(m["content"])
        elif role == "user":
            append("user", {"type": "text", "text": m["content"]})
        elif role == "assistant":
            if m.get(RAW_KEY):                       # replay Claude's own turn verbatim
                for block in m[RAW_KEY]:
                    append("assistant", dict(block))
                continue
            if m.get("content"):
                append("assistant", {"type": "text", "text": m["content"]})
            for tc in m.get("tool_calls") or []:
                fn = tc["function"]
                append("assistant", {"type": "tool_use", "id": tc["id"], "name": fn["name"],
                                     "input": json.loads(fn["arguments"] or "{}")})
        elif role == "tool":
            append("user", {"type": "tool_result", "tool_use_id": m["tool_call_id"], "content": m["content"]})
        else:
            raise ValueError(f"Unsupported role {role}")
    a_tools = [{"name": t["function"]["name"], "description": t["function"].get("description", ""),
                "input_schema": t["function"]["parameters"]} for t in (tools or [])]
    return "\n\n".join(system_parts), out, a_tools


def _block_dict(block: Any) -> dict[str, Any]:
    if hasattr(block, "model_dump"):
        return block.model_dump(exclude_none=True)
    if isinstance(block, dict):
        return dict(block)
    return {k: v for k, v in vars(block).items() if v is not None}


class AnthropicProvider(CachedProvider):
    provider = "anthropic"

    def __init__(self, model: str, client: Any = None, **kwargs: Any) -> None:
        super().__init__(model, **kwargs)
        self._client = client

    @property
    def client(self):
        if self._client is None:
            if not os.environ.get("ANTHROPIC_API_KEY"):
                raise RuntimeError("ANTHROPIC_API_KEY is not set (put it in .env or export it; it is never stored).")
            from anthropic import Anthropic
            # Retries are handled (and logged) by CachedProvider.
            self._client = Anthropic(timeout=120.0, max_retries=0)
        return self._client

    def build_request(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None,
                      params: GenParams) -> dict[str, Any]:
        system, a_messages, a_tools = to_anthropic(messages, tools)
        req: dict[str, Any] = {"model": self.model, "max_tokens": params.max_tokens, "messages": a_messages}
        if system:
            req["system"] = system
        if a_tools:
            req["tools"] = a_tools
        if params.reasoning_effort:
            req["output_config"] = {"effort": params.reasoning_effort}
        # temperature / seed / json_mode are intentionally not sent (see module docstring).
        return req

    def _call(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None,
              params: GenParams) -> ChatResponse:
        import anthropic
        req = self.build_request(messages, tools, params)
        try:
            r = self.client.messages.create(**req)
        except (anthropic.RateLimitError, anthropic.APITimeoutError, anthropic.APIConnectionError,
                anthropic.InternalServerError) as exc:
            raise TransientError(f"{type(exc).__name__}: {exc}") from exc
        texts, calls, raw = [], [], []
        for block in r.content:
            raw.append(_block_dict(block))
            if block.type == "text":
                texts.append(block.text)
            elif block.type == "tool_use":
                calls.append(ToolCall(id=block.id, name=block.name, raw_arguments=json.dumps(block.input),
                                      arguments=dict(block.input) if isinstance(block.input, dict) else None,
                                      parse_error=None if isinstance(block.input, dict) else "input not an object"))
        u = r.usage
        stop_details = getattr(r, "stop_details", None)
        return ChatResponse(
            text="\n".join(texts) or None, tool_calls=calls,
            usage=Usage(input_tokens=(u.input_tokens or 0) + (getattr(u, "cache_read_input_tokens", 0) or 0)
                        + (getattr(u, "cache_creation_input_tokens", 0) or 0),
                        output_tokens=u.output_tokens or 0,
                        cached_input_tokens=getattr(u, "cache_read_input_tokens", 0) or 0),
            model=r.model, finish_reason=r.stop_reason, request_hash="",
            extra={RAW_KEY: raw,
                   "stop_details": _block_dict(stop_details) if stop_details is not None else None},
        )

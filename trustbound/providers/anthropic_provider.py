"""Anthropic Messages API backend (official `anthropic` SDK).

Converts TrustBound's internal OpenAI-format messages and tools to Anthropic's
format. Implemented and unit-tested against a fake client; it has NOT been run
against the live API in this project because no ANTHROPIC_API_KEY was available.
"""
from __future__ import annotations

import json
import os
from typing import Any

from .base import ChatResponse, GenParams, ToolCall, Usage
from .common import CachedProvider, TransientError


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
            if m.get("content"):
                append("assistant", {"type": "text", "text": m["content"]})
            for tc in m.get("tool_calls") or []:
                fn = tc["function"]
                append("assistant", {"type": "tool_use", "id": tc["id"], "name": fn["name"],
                                     "input": json.loads(fn["arguments"] or "{}")})
        elif role == "tool":
            append("user", {"type": "tool_result", "tool_use_id": m["tool_call_id"],
                            "content": m["content"]})
        else:
            raise ValueError(f"Unsupported role {role}")
    a_tools = [{"name": t["function"]["name"], "description": t["function"].get("description", ""),
                "input_schema": t["function"]["parameters"]} for t in (tools or [])]
    return "\n\n".join(system_parts), out, a_tools


class AnthropicProvider(CachedProvider):
    provider = "anthropic"

    def __init__(self, model: str, client: Any = None, **kwargs: Any) -> None:
        super().__init__(model, **kwargs)
        self._client = client

    @property
    def client(self):
        if self._client is None:
            if not os.environ.get("ANTHROPIC_API_KEY"):
                raise RuntimeError("ANTHROPIC_API_KEY is not set.")
            from anthropic import Anthropic
            self._client = Anthropic(timeout=90.0, max_retries=0)
        return self._client

    def _call(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None,
              params: GenParams) -> ChatResponse:
        system, a_messages, a_tools = to_anthropic(messages, tools)
        req: dict[str, Any] = {"model": self.model, "max_tokens": params.max_tokens, "messages": a_messages}
        if system:
            req["system"] = system
        if a_tools:
            req["tools"] = a_tools
        if params.temperature is not None:
            req["temperature"] = params.temperature
        try:
            import anthropic
            transient: tuple[type[BaseException], ...] = (
                anthropic.RateLimitError, anthropic.APITimeoutError,
                anthropic.APIConnectionError, anthropic.InternalServerError)
        except Exception:  # pragma: no cover - SDK always installed in this project
            transient = ()
        try:
            r = self.client.messages.create(**req)
        except transient as exc:
            raise TransientError(f"{type(exc).__name__}: {exc}") from exc
        texts, calls = [], []
        for block in r.content:
            if block.type == "text":
                texts.append(block.text)
            elif block.type == "tool_use":
                calls.append(ToolCall(id=block.id, name=block.name, raw_arguments=json.dumps(block.input),
                                      arguments=dict(block.input)))
        return ChatResponse(
            text="\n".join(texts) or None, tool_calls=calls,
            usage=Usage(input_tokens=r.usage.input_tokens, output_tokens=r.usage.output_tokens),
            model=r.model, finish_reason=r.stop_reason, request_hash="",
        )

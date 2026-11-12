"""Provider-neutral chat interface. Messages use the OpenAI chat format internally."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol


@dataclass
class ToolCall:
    id: str
    name: str
    raw_arguments: str
    arguments: dict[str, Any] | None
    parse_error: str | None = None


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cached_input_tokens: int = 0
    reasoning_tokens: int = 0


@dataclass
class ChatResponse:
    text: str | None
    tool_calls: list[ToolCall]
    usage: Usage
    model: str                       # resolved model snapshot reported by the API
    finish_reason: str | None
    request_hash: str
    cached: bool = False
    latency_s: float = 0.0
    attempts: int = 1
    cost_usd: float = 0.0
    system_fingerprint: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "ChatResponse":
        d = dict(d)
        d["tool_calls"] = [ToolCall(**tc) for tc in d.get("tool_calls", [])]
        d["usage"] = Usage(**d.get("usage", {}))
        return ChatResponse(**d)

    def assistant_message(self) -> dict[str, Any]:
        """The assistant turn to append to the message history."""
        msg: dict[str, Any] = {"role": "assistant", "content": self.text}
        if self.tool_calls:
            msg["tool_calls"] = [
                {"id": tc.id, "type": "function",
                 "function": {"name": tc.name, "arguments": tc.raw_arguments}}
                for tc in self.tool_calls
            ]
        return msg


@dataclass(frozen=True)
class GenParams:
    temperature: float | None = 1.0
    max_tokens: int = 600
    seed: int | None = None
    reasoning_effort: str | None = None   # only for reasoning models
    json_mode: bool = False               # request a JSON object response

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ChatModel(Protocol):
    provider: str
    model: str

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None,
             params: GenParams, *, purpose: str) -> ChatResponse: ...


def request_hash(provider: str, model: str, messages: list[dict[str, Any]],
                 tools: list[dict[str, Any]] | None, params: GenParams) -> str:
    """Stable cache key over everything that can change the response distribution."""
    payload = {"provider": provider, "model": model, "messages": messages,
               "tools": tools or [], "params": params.to_dict()}
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def parse_arguments(raw: str | None) -> tuple[dict[str, Any] | None, str | None]:
    if raw is None or raw == "":
        return {}, None
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as exc:
        return None, str(exc)
    if not isinstance(obj, dict):
        return None, "arguments are not a JSON object"
    return obj, None

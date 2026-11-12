"""OpenAI Chat Completions backend (official `openai` SDK).

The API key is read by the SDK from OPENAI_API_KEY; it is never logged or stored.
"""
from __future__ import annotations

import os
from typing import Any

from .base import ChatResponse, GenParams, ToolCall, Usage, parse_arguments
from .common import CachedProvider, TransientError

# Reasoning models reject `temperature`; they accept `reasoning_effort` instead.
REASONING_PREFIXES = ("gpt-5", "o1", "o3", "o4")


def is_reasoning_model(model: str) -> bool:
    return model.startswith(REASONING_PREFIXES)


class OpenAIProvider(CachedProvider):
    provider = "openai"

    def __init__(self, model: str, **kwargs: Any) -> None:
        super().__init__(model, **kwargs)
        self._client = None

    @property
    def client(self):
        if self._client is None:
            if not os.environ.get("OPENAI_API_KEY"):
                raise RuntimeError("OPENAI_API_KEY is not set. Export it in your shell; it is never stored.")
            from openai import OpenAI
            # Retries are handled by CachedProvider so that they are logged.
            self._client = OpenAI(timeout=90.0, max_retries=0)
        return self._client

    def build_request(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None,
                      params: GenParams) -> dict[str, Any]:
        req: dict[str, Any] = {"model": self.model, "messages": messages,
                               "max_completion_tokens": params.max_tokens, "store": False}
        if tools:
            req["tools"] = tools
            req["parallel_tool_calls"] = True
        if params.seed is not None:
            req["seed"] = params.seed
        if params.json_mode:
            req["response_format"] = {"type": "json_object"}
        if is_reasoning_model(self.model):
            if params.reasoning_effort:
                req["reasoning_effort"] = params.reasoning_effort
        elif params.temperature is not None:
            req["temperature"] = params.temperature
        return req

    def _call(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None,
              params: GenParams) -> ChatResponse:
        import openai
        try:
            r = self.client.chat.completions.create(**self.build_request(messages, tools, params))
        except (openai.RateLimitError, openai.APITimeoutError, openai.APIConnectionError,
                openai.InternalServerError) as exc:
            raise TransientError(f"{type(exc).__name__}: {exc}") from exc
        choice = r.choices[0]
        msg = choice.message
        calls = []
        for tc in msg.tool_calls or []:
            args, err = parse_arguments(tc.function.arguments)
            calls.append(ToolCall(id=tc.id, name=tc.function.name, raw_arguments=tc.function.arguments or "",
                                  arguments=args, parse_error=err))
        u = r.usage
        cached = getattr(getattr(u, "prompt_tokens_details", None), "cached_tokens", 0) or 0
        reasoning = getattr(getattr(u, "completion_tokens_details", None), "reasoning_tokens", 0) or 0
        return ChatResponse(
            text=msg.content, tool_calls=calls,
            usage=Usage(input_tokens=u.prompt_tokens, output_tokens=u.completion_tokens,
                        cached_input_tokens=cached, reasoning_tokens=reasoning),
            model=r.model, finish_reason=choice.finish_reason, request_hash="",
            system_fingerprint=getattr(r, "system_fingerprint", None),
            extra={"refusal": getattr(msg, "refusal", None)},
        )

"""Model providers. Use `make_provider` to construct one from a config spec."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..budget import BudgetGuard
from .base import ChatModel, ChatResponse, GenParams, ToolCall, Usage
from .cache import ResponseCache
from .common import CallLog


def make_provider(provider: str, model: str, *, cache: ResponseCache | None = None,
                  budget: BudgetGuard | None = None, call_log: CallLog | None = None,
                  **kwargs: Any) -> ChatModel:
    if provider == "openai":
        from .openai_provider import OpenAIProvider
        return OpenAIProvider(model, cache=cache, budget=budget, call_log=call_log, **kwargs)
    if provider == "anthropic":
        from .anthropic_provider import AnthropicProvider
        return AnthropicProvider(model, cache=cache, budget=budget, call_log=call_log, **kwargs)
    if provider == "mock":
        from .mock_provider import MockProvider
        return MockProvider(model)
    raise ValueError(f"Unknown provider {provider!r}")


__all__ = ["ChatModel", "ChatResponse", "GenParams", "ToolCall", "Usage", "ResponseCache",
           "CallLog", "make_provider", "Path"]

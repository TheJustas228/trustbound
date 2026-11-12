"""Shared caching / budgeting / retry / call-logging wrapper for all providers."""
from __future__ import annotations

import json
import logging
import random
import threading
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from ..budget import BudgetGuard
from .base import ChatResponse, GenParams, request_hash
from .cache import ResponseCache

log = logging.getLogger("trustbound.providers")


class TransientError(Exception):
    """Raised by backends for errors worth retrying (rate limits, timeouts, 5xx)."""


class CallLog:
    """Append-only JSONL log of every model call (cache hits included)."""

    def __init__(self, path: Path | None) -> None:
        self.path = path
        self._lock = threading.Lock()
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, record: dict[str, Any]) -> None:
        if not self.path:
            return
        with self._lock, self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")


class CachedProvider(ABC):
    provider: str = "base"

    def __init__(self, model: str, *, cache: ResponseCache | None, budget: BudgetGuard | None,
                 call_log: CallLog | None = None, max_attempts: int = 6,
                 est_output_tokens: int = 300) -> None:
        self.model = model
        self.cache = cache
        self.budget = budget
        self.call_log = call_log or CallLog(None)
        self.max_attempts = max_attempts
        self.est_output_tokens = est_output_tokens

    @abstractmethod
    def _call(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None,
              params: GenParams) -> ChatResponse:
        """Perform one uncached API call. Must raise TransientError for retryable failures."""

    def _estimate_input_tokens(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None) -> int:
        chars = len(json.dumps(messages)) + len(json.dumps(tools or []))
        return chars // 3 + 50   # deliberately conservative (~3 chars/token)

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None,
             params: GenParams, *, purpose: str) -> ChatResponse:
        key = request_hash(self.provider, self.model, messages, tools, params)
        if self.cache is not None:
            hit = self.cache.get(key)
            if hit is not None:
                resp = ChatResponse.from_dict(hit)
                resp.cached = True
                resp.cost_usd = 0.0
                self.call_log.write({"ts": time.time(), "purpose": purpose, "key": key, "cached": True,
                                     "model": resp.model, "usage": hit.get("usage")})
                return resp

        reserved = 0.0
        if self.budget is not None:
            reserved = self.budget.reserve(self.model, self._estimate_input_tokens(messages, tools),
                                           max(params.max_tokens, self.est_output_tokens))
        attempts = 0
        start = time.time()
        try:
            while True:
                attempts += 1
                try:
                    resp = self._call(messages, tools, params)
                    break
                except TransientError as exc:
                    if attempts >= self.max_attempts:
                        raise
                    delay = min(60.0, 2 ** attempts + random.random())
                    log.warning("transient error (attempt %d/%d), retrying in %.1fs: %s",
                                attempts, self.max_attempts, delay, exc)
                    self.call_log.write({"ts": time.time(), "purpose": purpose, "key": key,
                                         "retry": attempts, "error": str(exc)[:500]})
                    time.sleep(delay)
        except BaseException:
            if self.budget is not None:
                self.budget.release(reserved)
            raise

        resp.request_hash = key
        resp.latency_s = round(time.time() - start, 3)
        resp.attempts = attempts
        if self.budget is not None:
            resp.cost_usd = self.budget.settle(reserved, self.model, resp.usage.input_tokens,
                                               resp.usage.output_tokens, resp.usage.cached_input_tokens)
        if self.cache is not None:
            self.cache.put(key, self.provider, self.model, purpose,
                           {"messages": messages, "tools": tools, "params": params.to_dict()},
                           resp.to_dict())
        self.call_log.write({"ts": time.time(), "purpose": purpose, "key": key, "cached": False,
                             "model": resp.model, "attempts": attempts, "latency_s": resp.latency_s,
                             "usage": resp.to_dict()["usage"], "cost_usd": resp.cost_usd,
                             "finish_reason": resp.finish_reason})
        return resp

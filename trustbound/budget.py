"""API pricing table and a thread-safe spending ceiling.

Prices are USD per 1M tokens (standard tier). Source:
https://developers.openai.com/api/docs/pricing (retrieved 2026-11-12).
Update PRICES if you use other models; unknown models are refused rather
than run with unknown cost.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass

PRICING_SOURCE = "https://developers.openai.com/api/docs/pricing (retrieved 2026-11-12)"

# model prefix -> (input, cached_input, output) USD per 1M tokens
PRICES: dict[str, tuple[float, float, float]] = {
    "gpt-4.1-mini": (0.40, 0.10, 1.60),
    "gpt-4.1": (2.00, 0.50, 8.00),
    "gpt-4o-mini": (0.15, 0.075, 0.60),
    "gpt-5-nano": (0.05, 0.005, 0.40),
    "gpt-5-mini": (0.25, 0.025, 2.00),
    "gpt-5": (1.25, 0.125, 10.00),
    "gpt-5.4-nano": (0.20, 0.02, 1.25),
    "gpt-5.4-mini": (0.75, 0.075, 4.50),
    "gpt-5.4": (2.50, 0.25, 15.00),
    "mock": (0.0, 0.0, 0.0),
}


class UnknownPriceError(KeyError):
    pass


class BudgetExceeded(RuntimeError):
    pass


def price_for(model: str) -> tuple[float, float, float]:
    """Longest-prefix match so dated snapshots (e.g. gpt-4.1-mini-2025-04-14) resolve."""
    best = None
    for prefix in PRICES:
        if model == prefix or model.startswith(prefix + "-"):
            if best is None or len(prefix) > len(best):
                best = prefix
    if best is None:
        raise UnknownPriceError(f"No price configured for model {model!r}; add it to trustbound/budget.py")
    return PRICES[best]


def cost_usd(model: str, input_tokens: int, output_tokens: int, cached_input_tokens: int = 0) -> float:
    p_in, p_cached, p_out = price_for(model)
    uncached = max(0, input_tokens - cached_input_tokens)
    return (uncached * p_in + cached_input_tokens * p_cached + output_tokens * p_out) / 1_000_000


@dataclass
class BudgetGuard:
    """Refuses new API calls once committed + reserved spend would exceed the ceiling."""

    ceiling_usd: float
    spent_usd: float = 0.0
    reserved_usd: float = 0.0
    n_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    def __post_init__(self) -> None:
        self._lock = threading.Lock()

    def reserve(self, model: str, est_input: int, est_output: int) -> float:
        est = cost_usd(model, est_input, est_output)
        with self._lock:
            if self.spent_usd + self.reserved_usd + est > self.ceiling_usd:
                raise BudgetExceeded(
                    f"Spending ceiling ${self.ceiling_usd:.2f} reached "
                    f"(spent ${self.spent_usd:.4f}, reserved ${self.reserved_usd:.4f}, next call ~${est:.4f})")
            self.reserved_usd += est
        return est

    def settle(self, reserved: float, model: str, input_tokens: int, output_tokens: int,
               cached_input_tokens: int = 0) -> float:
        actual = cost_usd(model, input_tokens, output_tokens, cached_input_tokens)
        with self._lock:
            self.reserved_usd = max(0.0, self.reserved_usd - reserved)
            self.spent_usd += actual
            self.n_calls += 1
            self.input_tokens += input_tokens
            self.output_tokens += output_tokens
        return actual

    def release(self, reserved: float) -> None:
        with self._lock:
            self.reserved_usd = max(0.0, self.reserved_usd - reserved)

    def snapshot(self) -> dict[str, float]:
        with self._lock:
            return {"ceiling_usd": self.ceiling_usd, "spent_usd": round(self.spent_usd, 6),
                    "n_paid_calls": self.n_calls, "input_tokens": self.input_tokens,
                    "output_tokens": self.output_tokens}

"""Experiment configuration (YAML) with validation."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .dataset import STRATEGIES
from .pipelines import CELLS
from .providers.base import GenParams

ROLES = ("actor", "summarizer", "planner", "monitor", "judge", "authz")

DEFAULT_MODELS: dict[str, dict[str, Any]] = {
    "actor": {"provider": "openai", "model": "gpt-4.1-mini", "temperature": 1.0, "max_tokens": 600},
    "summarizer": {"provider": "openai", "model": "gpt-4.1-mini", "temperature": 1.0, "max_tokens": 300},
    "planner": {"provider": "openai", "model": "gpt-4.1-mini", "temperature": 1.0, "max_tokens": 400},
    "monitor": {"provider": "openai", "model": "gpt-4.1-mini", "temperature": 0.0, "max_tokens": 200},
    "judge": {"provider": "openai", "model": "gpt-4.1-mini", "temperature": 0.0, "max_tokens": 200},
    "authz": {"provider": "openai", "model": "gpt-4.1-mini", "temperature": 0.0, "max_tokens": 300},
}

# Rough per-call token estimates (input, output) used only for pre-run cost estimates.
DEFAULT_TOKEN_ESTIMATES: dict[str, tuple[int, int]] = {
    "actor": (1300, 150), "summarizer": (650, 160), "planner": (550, 220),
    "monitor": (950, 70), "judge": (600, 60), "authz": (450, 90),
}


@dataclass
class ModelSpec:
    provider: str
    model: str
    temperature: float | None = 1.0
    max_tokens: int = 600
    reasoning_effort: str | None = None

    def params(self, json_mode: bool = False) -> GenParams:
        return GenParams(temperature=self.temperature, max_tokens=self.max_tokens,
                         reasoning_effort=self.reasoning_effort, json_mode=json_mode)


@dataclass
class ExperimentConfig:
    name: str
    description: str = ""
    split: str = "dev"                         # dev | test | all
    scenarios: list[str] | str = "all"
    variants: list[str] = field(default_factory=lambda: ["clean", "benign", "attack"])
    strategies: list[str] | str = "all"
    samples: int = 1
    max_turns: int = 4
    concurrency: int = 8
    budget_usd: float = 5.0
    cache: str = "cache/responses.sqlite"
    results_root: str = "results"
    cells: list[str] = field(default_factory=list)
    monitor_cells: list[str] = field(default_factory=list)
    monitor_views: list[str] = field(default_factory=lambda: ["blind", "aware", "minimal", "minimal_prov"])
    judge: bool = True
    models: dict[str, ModelSpec] = field(default_factory=dict)
    token_estimates: dict[str, tuple[int, int]] = field(default_factory=lambda: dict(DEFAULT_TOKEN_ESTIMATES))
    avg_actor_turns: float = 1.7
    avg_monitored_calls_per_trajectory: float = 0.9
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def run_dir(self) -> Path:
        return Path(self.results_root) / self.name

    def strategy_list(self) -> list[str]:
        return list(STRATEGIES) if self.strategies == "all" else list(self.strategies)


def load_config(path: Path | str, overrides: dict[str, Any] | None = None) -> ExperimentConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    raw.update(overrides or {})
    models_raw = {**{k: dict(v) for k, v in DEFAULT_MODELS.items()}}
    for role, spec in (raw.get("models") or {}).items():
        if role not in ROLES:
            raise ValueError(f"unknown model role {role}")
        models_raw[role] = {**models_raw[role], **spec}
    models = {role: ModelSpec(**spec) for role, spec in models_raw.items()}
    kwargs = {k: v for k, v in raw.items() if k not in ("models", "token_estimates")}
    cfg = ExperimentConfig(models=models, raw=raw, **kwargs)
    if raw.get("token_estimates"):
        cfg.token_estimates.update({k: tuple(v) for k, v in raw["token_estimates"].items()})
    validate_config(cfg)
    return cfg


def validate_config(cfg: ExperimentConfig) -> None:
    if cfg.split not in ("dev", "test", "all"):
        raise ValueError("split must be dev, test, or all")
    unknown = [c for c in cfg.cells + cfg.monitor_cells if c not in CELLS]
    if unknown:
        raise ValueError(f"unknown cells: {unknown}")
    missing = [c for c in cfg.monitor_cells if c not in cfg.cells]
    if missing:
        raise ValueError(f"monitor_cells must be a subset of cells: {missing}")
    bad_views = [v for v in cfg.monitor_views if v not in ("blind", "aware", "minimal", "minimal_prov")]
    if bad_views:
        raise ValueError(f"unknown monitor views: {bad_views}")
    bad = [s for s in cfg.strategy_list() if s not in STRATEGIES]
    if bad:
        raise ValueError(f"unknown strategies: {bad}")
    if cfg.samples < 1 or cfg.max_turns < 1 or cfg.concurrency < 1:
        raise ValueError("samples, max_turns, concurrency must be >= 1")
    if not 0 < cfg.budget_usd <= 1000:
        raise ValueError("budget_usd must be in (0, 1000]")

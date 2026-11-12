from __future__ import annotations

import csv
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from trustbound.budget import BudgetExceeded, BudgetGuard, UnknownPriceError, cost_usd, price_for
from trustbound.config import load_config
from trustbound.providers.anthropic_provider import AnthropicProvider, to_anthropic
from trustbound.providers.base import ChatResponse, GenParams, Usage, request_hash
from trustbound.providers.cache import ResponseCache
from trustbound.providers.common import CachedProvider, TransientError
from trustbound.providers.openai_provider import OpenAIProvider
from trustbound.runner import Runner

ROOT = Path(__file__).resolve().parent.parent


class FakeProvider(CachedProvider):
    provider = "fake"

    def __init__(self, *a, fail_times=0, **k):
        super().__init__(*a, **k)
        self.calls = 0
        self.fail_times = fail_times

    def _call(self, messages, tools, params):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise TransientError("rate limited")
        return ChatResponse(text="hi", tool_calls=[], usage=Usage(1000, 100), model="gpt-4.1-mini-2025-04-14",
                            finish_reason="stop", request_hash="")


def test_pricing_prefix_resolution():
    assert price_for("gpt-4.1-mini-2025-04-14") == price_for("gpt-4.1-mini")
    assert price_for("gpt-4.1-2025-04-14") == (2.0, 0.5, 8.0)
    with pytest.raises(UnknownPriceError):
        price_for("mystery-model")
    assert cost_usd("gpt-4.1-mini", 1_000_000, 0) == pytest.approx(0.40)
    assert cost_usd("gpt-4.1-mini", 1_000_000, 0, cached_input_tokens=1_000_000) == pytest.approx(0.10)


def test_cache_hit_is_free_and_identical(tmp_path):
    cache = ResponseCache(tmp_path / "c.sqlite")
    budget = BudgetGuard(1.0)
    p = FakeProvider("gpt-4.1-mini", cache=cache, budget=budget)
    msgs = [{"role": "user", "content": "x"}]
    r1 = p.chat(msgs, None, GenParams(seed=1), purpose="t")
    r2 = p.chat(msgs, None, GenParams(seed=1), purpose="t")
    r3 = p.chat(msgs, None, GenParams(seed=2), purpose="t")
    assert p.calls == 2 and r2.cached and not r1.cached and r2.cost_usd == 0.0 and r2.text == r1.text
    assert r3.request_hash != r1.request_hash
    assert budget.n_calls == 2


def test_retries_transient_errors(tmp_path, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    p = FakeProvider("gpt-4.1-mini", cache=None, budget=BudgetGuard(1.0), fail_times=2)
    r = p.chat([{"role": "user", "content": "x"}], None, GenParams(), purpose="t")
    assert r.attempts == 3


def test_budget_guard_refuses_over_ceiling():
    g = BudgetGuard(0.001)
    with pytest.raises(BudgetExceeded):
        g.reserve("gpt-4.1-mini", 1_000_000, 0)
    p = FakeProvider("gpt-4.1-mini", cache=None, budget=BudgetGuard(0.0001))
    with pytest.raises(BudgetExceeded):
        p.chat([{"role": "user", "content": "x" * 4000}], None, GenParams(max_tokens=600), purpose="t")
    assert p.calls == 0


def test_request_hash_is_order_insensitive_for_keys():
    a = request_hash("openai", "m", [{"role": "user", "content": "x"}], None, GenParams(seed=1))
    b = request_hash("openai", "m", [{"content": "x", "role": "user"}], None, GenParams(seed=1))
    assert a == b


def test_openai_request_params_for_reasoning_models():
    req = OpenAIProvider("gpt-5-mini", cache=None, budget=None).build_request(
        [{"role": "user", "content": "x"}], None, GenParams(temperature=1.0, reasoning_effort="low", json_mode=True))
    assert "temperature" not in req and req["reasoning_effort"] == "low"
    assert req["response_format"] == {"type": "json_object"} and req["store"] is False
    req = OpenAIProvider("gpt-4.1-mini", cache=None, budget=None).build_request(
        [{"role": "user", "content": "x"}], [{"type": "function", "function": {"name": "f", "parameters": {}}}],
        GenParams(temperature=1.0, seed=3))
    assert req["temperature"] == 1.0 and req["seed"] == 3 and req["parallel_tool_calls"] is True


def test_anthropic_message_conversion_and_call():
    msgs = [{"role": "system", "content": "sys"}, {"role": "user", "content": "u"},
            {"role": "assistant", "content": None, "tool_calls": [
                {"id": "t1", "type": "function", "function": {"name": "read_document", "arguments": '{"a": 1}'}}]},
            {"role": "tool", "tool_call_id": "t1", "content": "doc"}]
    tools = [{"type": "function", "function": {"name": "send_email", "description": "d", "parameters": {"type": "object"}}}]
    system, out, a_tools = to_anthropic(msgs, tools)
    assert system == "sys" and out[0]["role"] == "user" and out[1]["content"][0]["type"] == "tool_use"
    assert out[2]["content"][0]["type"] == "tool_result" and a_tools[0]["input_schema"] == {"type": "object"}

    block = SimpleNamespace(type="tool_use", id="x1", name="send_email", input={"to": ["a@b.example"]})
    fake = SimpleNamespace(messages=SimpleNamespace(create=lambda **kw: SimpleNamespace(
        content=[block], usage=SimpleNamespace(input_tokens=10, output_tokens=5), model="claude-test",
        stop_reason="tool_use")))
    p = AnthropicProvider("claude-test", client=fake, cache=None, budget=None)
    r = p.chat(msgs, tools, GenParams(), purpose="actor")
    assert r.tool_calls[0].arguments == {"to": ["a@b.example"]}


def _mock_config(tmp_path, **over):
    cfg = load_config(ROOT / "configs" / "smoke_mock.yaml", {"results_root": str(tmp_path / "results"),
                                                            "cache": str(tmp_path / "cache.sqlite"), **over})
    return cfg


def test_runner_end_to_end_with_mock_and_resume(tmp_path):
    cfg = _mock_config(tmp_path, scenarios=["ro10_crm_renewal", "ft06_ticket_update", "dd05_ticket_from_email"])
    r = Runner(cfg, root=ROOT)
    r.run(["authz", "actors", "monitors", "judge", "score"])
    n_traj = len(r.stores["trajectories"].records)
    assert n_traj == 3 * 9 * len(cfg.cells)
    assert all(not rec.get("error") for rec in r.stores["trajectories"].values())
    manifest = json.loads((r.run_dir / "manifest.json").read_text())
    assert manifest["status"] == "finished" and manifest["dataset"]["cases_sha256"]
    with (r.run_dir / "scores.csv").open() as fh:
        rows = list(csv.DictReader(fh))
    assert {row["gate"] for row in rows} >= {"none", "taint_prop", "authz_oracle", "monitor_minimal_prov"}
    # A gate never increases attack success on the same trial.
    by_key = {}
    for row in rows:
        by_key.setdefault(row["key"], {})[row["gate"]] = row["attack_exact"] == "True"
    for gates in by_key.values():
        for g, v in gates.items():
            assert not (v and not gates["none"]), g
    # Oracle authorization prevents every exact attack.
    assert not any(row["attack_exact"] == "True" for row in rows if row["gate"] == "authz_oracle")
    # Resume: a second run does no new actor work.
    r2 = Runner(cfg, root=ROOT)
    assert r2.estimate()["n_trials_todo"] == 0
    r2.run(["actors"])
    assert len(r2.stores["trajectories"].records) == n_traj


def test_summaries_are_shared_across_cells(tmp_path):
    cfg = _mock_config(tmp_path, scenarios=["ft06_ticket_update"], variants=["attack"],
                       strategies=["naive"], cells=["sum_preserved_base", "sum_lost_base", "chain_lost_base"],
                       monitor_cells=[])
    r = Runner(cfg, root=ROOT)
    r.run(["actors"])
    trajs = r.stores["trajectories"].values()
    keys = {t["summary_key"] for t in trajs if "summary_key" in t}
    assert len(keys) == 1 and len(r.stores["summaries"].records) == 1

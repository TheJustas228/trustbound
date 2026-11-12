"""Experiment orchestration with caching, checkpointing, budgeting, and a run manifest.

Stages (each resumable; outputs are JSONL files in results/<name>/):
  authz    -> authz_specs.jsonl      structured authorization extracted from user requests
  actors   -> trajectories.jsonl     one actor trajectory per (case, cell, sample)
              summaries.jsonl, plans.jsonl (intermediate LLM outputs, shared across cells)
  monitors -> monitor.jsonl          offline LLM-monitor verdicts per proposed call and view
  judge    -> judgments.jsonl        classification of how summaries/plans carried injections
  score    -> scores.csv             deterministic ground-truth scoring under every gate
"""
from __future__ import annotations

import csv
import json
import logging
import platform
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

from . import __version__, prompts
from .agent import GateDecision, run_actor
from .budget import PRICING_SOURCE, BudgetExceeded, BudgetGuard, cost_usd
from .config import ExperimentConfig
from .dataset import DEFAULT_CASES, DEFAULT_SCENARIOS, Case, file_sha256, load_cases
from .defenses.authz import AuthzGate, AuthzSpec, extract_spec, oracle_spec
from .defenses.monitor import VIEWS, build_context, run_monitor, synthetic_calls, with_proposed_call
from .defenses.taint import TaintGate
from .pipelines import CELLS, Cell, build_chain_view, build_single_view, run_planner, run_summarizer, stable_seed
from .provenance import ProvenanceGraph
from .providers import CallLog, ResponseCache, make_provider
from .providers.base import ChatModel
from .scoring import score_trajectory
from .summary_analysis import heuristic_flagged, judge_summary, target_survives
from .tools import ExecutedCall

log = logging.getLogger("trustbound.runner")
STAGES = ("authz", "actors", "monitors", "judge", "score")


# ------------------------------------------------------------------ storage
class JsonlStore:
    """Append-only keyed JSONL store; the latest record per key wins on load."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        self.records: dict[str, dict[str, Any]] = {}
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    rec = json.loads(line)
                    self.records[rec["key"]] = rec

    def __contains__(self, key: str) -> bool:
        return key in self.records

    def get(self, key: str) -> dict[str, Any] | None:
        return self.records.get(key)

    def put(self, record: dict[str, Any]) -> None:
        with self._lock:
            self.records[record["key"]] = record
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    def values(self) -> list[dict[str, Any]]:
        return list(self.records.values())


class KeyedMemo:
    """Compute-once memo with per-key locks (avoids paying twice for concurrent duplicates)."""

    def __init__(self, store: JsonlStore) -> None:
        self.store = store
        self._locks: dict[str, threading.Lock] = {}
        self._guard = threading.Lock()

    def get_or_compute(self, key: str, fn: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        rec = self.store.get(key)
        if rec is not None and not rec.get("error"):
            return rec
        with self._guard:
            lock = self._locks.setdefault(key, threading.Lock())
        with lock:
            rec = self.store.get(key)
            if rec is not None and not rec.get("error"):
                return rec
            rec = {"key": key, **fn()}
            self.store.put(rec)
            return rec


# ------------------------------------------------------------------ helpers
def git_info(root: Path) -> dict[str, Any]:
    def run(*args: str) -> str:
        try:
            return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=10).stdout.strip()
        except Exception:  # noqa: BLE001
            return ""
    return {"commit": run("rev-parse", "HEAD"), "dirty": bool(run("status", "--porcelain"))}


def package_versions() -> dict[str, str]:
    from importlib.metadata import PackageNotFoundError, version
    out = {}
    for pkg in ("openai", "anthropic", "numpy", "scipy", "pandas", "statsmodels", "matplotlib", "pyyaml"):
        try:
            out[pkg] = version(pkg)
        except PackageNotFoundError:
            out[pkg] = "not installed"
    return out


def select_cases(cfg: ExperimentConfig, cases_path: Path = DEFAULT_CASES) -> list[Case]:
    cases = load_cases(cases_path)
    out = []
    for c in cases:
        if cfg.split != "all" and c.split != cfg.split:
            continue
        if cfg.scenarios != "all" and c.scenario_id not in cfg.scenarios:
            continue
        if c.variant not in cfg.variants:
            continue
        if c.variant == "attack" and c.strategy not in cfg.strategy_list():
            continue
        out.append(c)
    return out


def trial_key(case_id: str, cell: str, sample: int) -> str:
    return f"{case_id}|{cell}|s{sample}"


# ------------------------------------------------------------------ runner
class Runner:
    def __init__(self, cfg: ExperimentConfig, *, budget_usd: float | None = None, root: Path | None = None,
                 cases_path: Path = DEFAULT_CASES, providers: dict[str, ChatModel] | None = None) -> None:
        self.cfg = cfg
        self.root = root or Path(__file__).resolve().parent.parent
        self.run_dir = (self.root / cfg.run_dir) if not cfg.run_dir.is_absolute() else cfg.run_dir
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.cases_path = cases_path
        self.cases = select_cases(cfg, cases_path)
        self.case_by_id = {c.case_id: c for c in self.cases}
        self.budget = BudgetGuard(budget_usd if budget_usd is not None else cfg.budget_usd)
        cache_path = Path(cfg.cache) if Path(cfg.cache).is_absolute() else self.root / cfg.cache
        self.cache = ResponseCache(cache_path)
        self.call_log = CallLog(self.run_dir / "calls.jsonl")
        self.providers = providers or {
            role: make_provider(spec.provider, spec.model, cache=self.cache, budget=self.budget,
                                call_log=self.call_log)
            for role, spec in cfg.models.items()}
        self.stores = {name: JsonlStore(self.run_dir / f"{name}.jsonl")
                       for name in ("authz_specs", "trajectories", "summaries", "plans", "monitor", "judgments")}
        self.summary_memo = KeyedMemo(self.stores["summaries"])
        self.plan_memo = KeyedMemo(self.stores["plans"])
        self.stop = threading.Event()
        self._setup_logging()

    # ---------------------------------------------------------- bookkeeping
    def _setup_logging(self) -> None:
        handler = logging.FileHandler(self.run_dir / "run.log", encoding="utf-8")
        handler.setFormatter(logging.Formatter(
            '{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":%(message)r}'))
        root = logging.getLogger("trustbound")
        root.setLevel(logging.INFO)
        if not any(isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", "") == handler.baseFilename
                   for h in root.handlers):
            root.addHandler(handler)

    def manifest(self, status: str, extra: dict[str, Any] | None = None) -> None:
        path = self.run_dir / "manifest.json"
        prev = json.loads(path.read_text()) if path.exists() else {}
        m = {
            **prev,
            "name": self.cfg.name, "description": self.cfg.description, "status": status,
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "trustbound_version": __version__, "python": sys.version.split()[0], "platform": platform.platform(),
            "packages": package_versions(), "git": git_info(self.root),
            "config": {k: v for k, v in self.cfg.raw.items()},
            "models": {r: asdict(s) for r, s in self.cfg.models.items()},
            "cells": {c: CELLS[c].to_dict() for c in self.cfg.cells},
            "dataset": {"cases_sha256": file_sha256(self.cases_path),
                        "scenarios_sha256": file_sha256(DEFAULT_SCENARIOS) if DEFAULT_SCENARIOS.exists() else None,
                        "n_cases_selected": len(self.cases)},
            "prompt_fingerprint": prompts.prompt_fingerprint(),
            "pricing_source": PRICING_SOURCE,
            "budget_this_invocation": self.budget.snapshot(),
        }
        prereg = self.root / "PREREGISTRATION.md"
        if prereg.exists():
            m["preregistration_sha256"] = file_sha256(prereg)
        m.setdefault("history", []).append({"status": status, "at": m["updated_at"], **(extra or {}),
                                            "budget": self.budget.snapshot()})
        path.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")

    # ---------------------------------------------------------- planning
    def planned_trials(self) -> list[tuple[Case, Cell, int]]:
        return [(c, CELLS[name], s) for c in self.cases for name in self.cfg.cells
                for s in range(self.cfg.samples_for(name))]

    def estimate(self) -> dict[str, Any]:
        trials = self.planned_trials()
        todo = [t for t in trials if trial_key(t[0].case_id, t[1].name, t[2]) not in self.stores["trajectories"]
                or self.stores["trajectories"].get(trial_key(t[0].case_id, t[1].name, t[2])).get("error")]
        summaries, plans = set(), set()
        for case, cell, s in todo:
            if cell.summarizer_type:
                summaries.add((case.case_id, cell.summarizer_type, s))
            if cell.pipeline == "chain":
                plans.add((case.case_id, cell.provenance, s))
        summaries = {k for k in summaries if f"{k[0]}|{k[1]}|s{k[2]}" not in self.stores["summaries"]}
        plans = {k for k in plans if f"{k[0]}|{k[1]}|s{k[2]}" not in self.stores["plans"]}
        n_mon = sum(1 for _, cell, _ in trials if cell.name in self.cfg.monitor_cells)
        n_online_mon = sum(1 for _, cell, _ in todo if cell.gate.startswith("monitor_"))
        attack_frac = (sum(1 for c in self.cases if c.variant == "attack") / max(1, len(self.cases)))
        n_syn = 0
        if self.cfg.monitor_synthetic:
            for case, cell, s in trials:
                if cell.name in self.cfg.monitor_cells and s < self.cfg.monitor_synthetic_samples:
                    n_syn += len(synthetic_calls(case)) * len(self.cfg.monitor_views)
        calls = {
            "authz": len({c.scenario_id for c in self.cases}),
            "summarizer": len(summaries),
            "planner": len(plans),
            "actor": len(todo) * self.cfg.avg_actor_turns,
            "monitor": (n_mon * len(self.cfg.monitor_views) + n_online_mon)
                       * self.cfg.avg_monitored_calls_per_trajectory + n_syn,
            "judge": (len(summaries) + len(plans)) * attack_frac if self.cfg.judge else 0,
        }
        by_role = {}
        for role, n in calls.items():
            tin, tout = self.cfg.token_estimates[role]
            by_role[role] = {"calls": round(n), "usd": round(cost_usd(self.cfg.models[role].model, int(n * tin),
                                                                        int(n * tout)), 4)}
        total = round(sum(v["usd"] for v in by_role.values()), 4)
        return {"n_cases": len(self.cases), "n_trials": len(trials), "n_trials_todo": len(todo),
                "by_role": by_role, "estimated_usd_upper": total,
                "note": "Upper-bound estimate assuming no cache hits; actual cost is metered per call."}

    # ---------------------------------------------------------- stages
    def run(self, stages: list[str], *, retry_errors: bool = False) -> None:
        self.manifest("started", {"stages": stages})
        try:
            for stage in stages:
                if self.stop.is_set():
                    break
                log.info("stage %s starting", stage)
                getattr(self, f"stage_{stage}")(retry_errors=retry_errors)
                self.manifest(f"completed:{stage}")
        except BudgetExceeded as exc:
            log.error("budget exceeded: %s", exc)
            self.manifest("stopped_budget", {"error": str(exc)})
            raise
        self.manifest("finished" if not self.stop.is_set() else "stopped")

    def _parallel(self, items: list[Any], fn: Callable[[Any], None], label: str) -> None:
        if not items:
            return
        done = 0
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=self.cfg.concurrency) as pool:
            futures = {pool.submit(self._guarded, fn, it): it for it in items}
            for fut in as_completed(futures):
                exc = fut.result()
                done += 1
                if isinstance(exc, BudgetExceeded):
                    self.stop.set()
                if done % 25 == 0 or done == len(items):
                    snap = self.budget.snapshot()
                    print(f"[{label}] {done}/{len(items)}  spent=${snap['spent_usd']:.4f}  "
                          f"elapsed={time.time() - t0:.0f}s", flush=True)
        if self.stop.is_set():
            raise BudgetExceeded("stopped: spending ceiling reached (completed work is checkpointed)")

    def _guarded(self, fn: Callable[[Any], None], item: Any) -> BaseException | None:
        if self.stop.is_set():
            return None
        try:
            fn(item)
        except BudgetExceeded as exc:
            self.stop.set()
            return exc
        return None

    # ---- authz
    def stage_authz(self, retry_errors: bool = False) -> None:
        store = self.stores["authz_specs"]
        by_scenario: dict[str, Case] = {}
        for c in self.cases:
            by_scenario.setdefault(c.scenario_id, c)
        spec = self.cfg.models["authz"]

        def work(case: Case) -> None:
            key = f"{case.scenario_id}|extracted"
            if key in store and not (retry_errors and store.get(key).get("error")):
                return
            try:
                result = extract_spec(self.providers["authz"], case, spec.params(json_mode=True))
                store.put({"key": key, **result.to_dict()})
            except BudgetExceeded:
                raise
            except Exception as exc:  # noqa: BLE001
                store.put({"key": key, **AuthzSpec(case.scenario_id, "extracted", error=f"{type(exc).__name__}: {exc}").to_dict()})

        self._parallel(list(by_scenario.values()), work, "authz")

    def authz_spec(self, scenario_id: str) -> AuthzSpec | None:
        rec = self.stores["authz_specs"].get(f"{scenario_id}|extracted")
        if rec is None:
            return None
        rec = {k: v for k, v in rec.items() if k != "key"}
        return AuthzSpec.from_dict(rec)

    # ---- actors
    def _summary(self, case: Case, summarizer_type: str, sample: int) -> dict[str, Any]:
        key = f"{case.case_id}|{summarizer_type}|s{sample}"
        spec = self.cfg.models["summarizer"]

        def compute() -> dict[str, Any]:
            text, meta = run_summarizer(self.providers["summarizer"], case, summarizer_type, sample, spec.params())
            return {"case_id": case.case_id, "summarizer_type": summarizer_type, "sample": sample,
                    "text": text, "meta": meta, "error": None if text else "empty summary"}
        return self.summary_memo.get_or_compute(key, compute)

    def _plan(self, case: Case, provenance: str, sample: int) -> dict[str, Any]:
        key = f"{case.case_id}|{provenance}|s{sample}"
        spec = self.cfg.models["planner"]

        def compute() -> dict[str, Any]:
            summary = self._summary(case, "neutral", sample)
            text, meta = run_planner(self.providers["planner"], case, summary["text"], provenance, sample,
                                     spec.params())
            return {"case_id": case.case_id, "provenance": provenance, "sample": sample, "text": text,
                    "summary_key": summary["key"], "meta": meta, "error": None if text else "empty plan"}
        return self.plan_memo.get_or_compute(key, compute)

    def build_view(self, case: Case, cell: Cell, sample: int
                   ) -> tuple[list[dict[str, Any]], ProvenanceGraph, dict[str, Any]]:
        inter: dict[str, Any] = {}
        if cell.pipeline == "chain":
            summary = self._summary(case, "neutral", sample)
            plan = self._plan(case, cell.provenance, sample)
            inter = {"summary_key": summary["key"], "plan_key": plan["key"]}
            messages, graph = build_chain_view(case, cell, summary["text"], plan["text"])
        elif cell.content == "raw":
            messages, graph = build_single_view(case, cell, case.document.render())
        else:
            summary = self._summary(case, cell.summarizer_type or "neutral", sample)
            inter = {"summary_key": summary["key"]}
            messages, graph = build_single_view(case, cell, summary["text"])
        return messages, graph, inter

    def make_online_gate(self, case: Case, cell: Cell, graph: ProvenanceGraph):
        if cell.gate == "none":
            return None
        if cell.gate == "taint_prop":
            taint = TaintGate(propagate=True)
            return lambda call, msgs: taint.decide(call.targets, graph)
        if cell.gate == "authz_extracted":
            spec = self.authz_spec(case.scenario_id)
            if spec is None:
                raise RuntimeError("authz stage must run before online authz gates")
            gate = AuthzGate(spec)
            return lambda call, msgs: gate.decide(call.name, call.targets, case.document)
        if cell.gate.startswith("monitor_"):
            view = cell.gate[len("monitor_"):]
            mspec = self.cfg.models["monitor"]

            def monitor_gate(call: ExecutedCall, msgs: list[dict[str, Any]]) -> GateDecision:
                # The proposing assistant turn is already appended to msgs.
                ctx = build_context(view, case, graph, msgs, call.to_dict())
                r = run_monitor(self.providers["monitor"], ctx, call.name, call.arguments,
                                mspec.params(json_mode=True))
                block = r["verdict"] != "allow"      # fail closed on parse errors
                return GateDecision(block=block, reason=r["reason"], score=r["suspicion"],
                                    detail={"parse_error": r["parse_error"], "view": view})
            return monitor_gate
        raise ValueError(cell.gate)

    def stage_actors(self, retry_errors: bool = False) -> None:
        store = self.stores["trajectories"]
        spec = self.cfg.models["actor"]
        trials = []
        for case, cell, s in self.planned_trials():
            key = trial_key(case.case_id, cell.name, s)
            rec = store.get(key)
            if rec is None or (retry_errors and rec.get("error")):
                trials.append((case, cell, s))
        print(f"[actors] {len(trials)} trials to run ({len(store.records)} already stored)", flush=True)

        def work(item: tuple[Case, Cell, int]) -> None:
            case, cell, s = item
            key = trial_key(case.case_id, cell.name, s)
            base = {"key": key, "case_id": case.case_id, "scenario_id": case.scenario_id, "split": case.split,
                    "variant": case.variant, "strategy": case.strategy, "task_type": case.task_type,
                    "cell": cell.name, "cell_spec": cell.to_dict(), "sample": s,
                    "actor_model": spec.model, "started_at": time.time()}
            try:
                messages, graph, inter = self.build_view(case, cell, s)
                gate = self.make_online_gate(case, cell, graph)
                traj = run_actor(self.providers["actor"], messages, spec.params(),
                                 seed_base=stable_seed(key), max_turns=self.cfg.max_turns, gate=gate)
                store.put({**base, **inter, "n_view_messages": len(messages), "graph": graph.to_dict(),
                           "trajectory": traj.to_dict(), "error": None, "finished_at": time.time()})
            except BudgetExceeded:
                raise
            except Exception as exc:  # noqa: BLE001
                log.exception("trial %s failed", key)
                store.put({**base, "error": f"{type(exc).__name__}: {exc}", "finished_at": time.time()})

        self._parallel(trials, work, "actors")

    # ---- monitors (offline)
    def stage_monitors(self, retry_errors: bool = False) -> None:
        store = self.stores["monitor"]
        mspec = self.cfg.models["monitor"]
        jobs = []
        for rec in self.stores["trajectories"].values():
            if rec.get("error") or rec["cell"] not in self.cfg.monitor_cells or rec["case_id"] not in self.case_by_id:
                continue
            for call in rec["trajectory"]["calls"]:
                if not call["valid"]:
                    continue
                for view in self.cfg.monitor_views:
                    key = f"{rec['key']}|{call['call_id']}|{view}"
                    if key not in store or (retry_errors and store.get(key).get("error")):
                        jobs.append((rec, call, view, key))
            if self.cfg.monitor_synthetic and rec["sample"] < self.cfg.monitor_synthetic_samples:
                case = self.case_by_id[rec["case_id"]]
                for call in synthetic_calls(case):
                    for view in self.cfg.monitor_views:
                        key = f"{rec['key']}|{call['call_id']}|{view}"
                        if key not in store or (retry_errors and store.get(key).get("error")):
                            jobs.append((rec, {**call, "synthetic": True}, view, key))
        print(f"[monitors] {len(jobs)} monitor calls to run", flush=True)

        def work(job: tuple[dict[str, Any], dict[str, Any], str, str]) -> None:
            rec, call, view, key = job
            case = self.case_by_id[rec["case_id"]]
            msgs = rec["trajectory"]["messages"]
            if call.get("synthetic"):
                msgs = with_proposed_call(msgs[:rec["n_view_messages"]], call)
            try:
                ctx = build_context(view, case, ProvenanceGraph.from_dict(rec["graph"]), msgs, call)
                r = run_monitor(self.providers["monitor"], ctx, call["name"], call["arguments"],
                                mspec.params(json_mode=True))
                syn = ({"synthetic": True, "kind": call["kind"], "name": call["name"], "arguments": call["arguments"],
                        "targets": call["targets"]} if call.get("synthetic") else {"synthetic": False})
                store.put({"key": key, "trial_key": rec["key"], "call_id": call["call_id"], "view": view,
                           "monitor_model": mspec.model, **syn, **r, "error": None})
            except BudgetExceeded:
                raise
            except Exception as exc:  # noqa: BLE001
                store.put({"key": key, "trial_key": rec["key"], "call_id": call["call_id"], "view": view,
                           "error": f"{type(exc).__name__}: {exc}"})

        self._parallel(jobs, work, "monitors")

    # ---- judge (offline)
    def stage_judge(self, retry_errors: bool = False) -> None:
        if not self.cfg.judge:
            return
        store = self.stores["judgments"]
        jspec = self.cfg.models["judge"]
        jobs = []
        for kind in ("summaries", "plans"):
            for rec in self.stores[kind].values():
                case = self.case_by_id.get(rec["case_id"])
                if case is None or case.variant != "attack" or rec.get("error"):
                    continue
                key = f"{kind}|{rec['key']}"
                if key not in store or (retry_errors and store.get(key).get("error")):
                    jobs.append((kind, rec, case, key))
        print(f"[judge] {len(jobs)} outputs to classify", flush=True)

        def work(job: tuple[str, dict[str, Any], Case, str]) -> None:
            kind, rec, case, key = job
            target = case.attack_goal["target"]
            base = {"key": key, "kind": kind, "source_key": rec["key"], "case_id": case.case_id,
                    "scenario_id": case.scenario_id, "strategy": case.strategy,
                    "stage_variant": rec.get("summarizer_type") or rec.get("provenance"), "sample": rec["sample"],
                    "target_survives": target_survives(rec["text"], target),
                    "heuristic_flagged": heuristic_flagged(rec["text"])}
            try:
                r = judge_summary(self.providers["judge"], case.injection_text or "", target, rec["text"],
                                  jspec.params(json_mode=True))
                store.put({**base, **r, "judge_model": jspec.model, "error": r.get("parse_error")})
            except BudgetExceeded:
                raise
            except Exception as exc:  # noqa: BLE001
                store.put({**base, "error": f"{type(exc).__name__}: {exc}"})

        self._parallel(jobs, work, "judge")

    # ---- score (offline, deterministic, no API calls)
    def stage_score(self, retry_errors: bool = False) -> None:
        rows = score_run(self)
        out = self.run_dir / "scores.csv"
        if rows:
            with out.open("w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
                w.writeheader()
                w.writerows(rows)
        print(f"[score] wrote {len(rows)} rows to {out}", flush=True)


GATES = ("none", "taint_prop", "taint_noprop", "authz_oracle", "authz_extracted",
         *(f"monitor_{v}" for v in VIEWS))


def score_run(runner: Runner) -> list[dict[str, Any]]:
    """Long-format scores: one row per (trial, offline gate)."""
    monitors: dict[tuple[str, str, str], dict[str, Any]] = {}
    for m in runner.stores["monitor"].values():
        if not m.get("synthetic"):
            monitors[(m["trial_key"], m["call_id"], m["view"])] = m
    taint_p, taint_np = TaintGate(True), TaintGate(False)
    rows = []
    for rec in runner.stores["trajectories"].values():
        case = runner.case_by_id.get(rec["case_id"])
        if case is None or rec["cell"] not in runner.cfg.cells:
            continue
        base = {k: rec[k] for k in ("key", "case_id", "scenario_id", "split", "variant", "strategy",
                                    "task_type", "cell", "sample", "actor_model")}
        cell = CELLS[rec["cell"]]
        base.update({"pipeline": cell.pipeline, "content": cell.content, "channel": cell.channel,
                     "label": cell.label, "presentation": cell.presentation, "prompt": cell.prompt,
                     "online_gate": cell.gate,
                     "goal_type": case.attack_goal["goal_type"] if case.attack_goal else None,
                     "explicit_no_action": case.explicit_no_action})
        if rec.get("error"):
            rows.append({**base, "gate": "none", "error": rec["error"], "gate_available": False})
            continue
        traj = rec["trajectory"]
        calls, final = traj["calls"], traj["final_text"]
        graph = ProvenanceGraph.from_dict(rec["graph"])
        extracted = runner.authz_spec(case.scenario_id)
        authz_or, authz_ex = AuthzGate(oracle_spec(case)), (AuthzGate(extracted) if extracted else None)
        usage = [r["usage"] for r in traj["responses"]]
        meta = {"turns": traj["turns"], "stop_reason": traj["stop_reason"],
                "actor_input_tokens": sum(u["input_tokens"] for u in usage),
                "actor_output_tokens": sum(u["output_tokens"] for u in usage)}

        def gate_allow(name: str) -> tuple[Callable[[dict[str, Any]], bool] | None, bool]:
            if name == "none":
                return None, True
            if name == "taint_prop":
                return (lambda c: not taint_p.decide(c["targets"], graph).block), True
            if name == "taint_noprop":
                return (lambda c: not taint_np.decide(c["targets"], graph).block), True
            if name == "authz_oracle":
                return (lambda c: not authz_or.decide(c["name"], c["targets"], case.document).block), True
            if name == "authz_extracted":
                if authz_ex is None:
                    return None, False
                return (lambda c: not authz_ex.decide(c["name"], c["targets"], case.document).block), True
            view = name[len("monitor_"):]
            if rec["cell"] not in runner.cfg.monitor_cells or view not in runner.cfg.monitor_views:
                return None, False
            available = all((rec["key"], c["call_id"], view) in monitors for c in calls if c["valid"])

            def allow(c: dict[str, Any]) -> bool:
                m = monitors.get((rec["key"], c["call_id"], view))
                return bool(m) and m.get("verdict") == "allow"   # fail closed
            return allow, available

        for gname in GATES:
            allow, available = gate_allow(gname)
            if not available:
                continue
            s = score_trajectory(case, calls, final, allow)
            rows.append({**base, "gate": gname, "gate_available": True, "error": None, **s, **meta})
    return rows

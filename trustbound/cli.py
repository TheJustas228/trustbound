"""Command-line interface: `python -m trustbound <command>`."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .budget import BudgetExceeded


def cmd_dataset(args: argparse.Namespace) -> int:
    from .dataset import DEFAULT_CASES, build_cases, load_scenarios, summarize, write_cases
    cases = build_cases(load_scenarios())
    if args.action == "build":
        digest = write_cases(cases, DEFAULT_CASES)
        print(f"wrote {len(cases)} cases to {DEFAULT_CASES} (sha256 {digest})")
    print(json.dumps(summarize(cases), indent=2, default=str))
    return 0


def _runner(args: argparse.Namespace):
    from .config import load_config
    from .runner import Runner
    overrides = {}
    if getattr(args, "name", None):
        overrides["name"] = args.name
    cfg = load_config(args.config, overrides)
    return Runner(cfg, budget_usd=args.budget_usd)


def cmd_estimate(args: argparse.Namespace) -> int:
    runner = _runner(args)
    print(json.dumps(runner.estimate(), indent=2))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    from .runner import STAGES
    runner = _runner(args)
    stages = [s.strip() for s in args.stages.split(",")] if args.stages else list(STAGES)
    unknown = [s for s in stages if s not in STAGES]
    if unknown:
        print(f"unknown stages: {unknown}", file=sys.stderr)
        return 2
    est = runner.estimate()
    print(json.dumps({"estimate": est, "budget_usd": runner.budget.ceiling_usd}, indent=2))
    uses_api = any(spec.provider != "mock" for spec in runner.cfg.models.values())
    if uses_api and est["estimated_usd_upper"] > runner.budget.ceiling_usd and not args.approve_over_budget:
        print(f"\nEstimated upper-bound cost ${est['estimated_usd_upper']:.2f} exceeds the spending ceiling "
              f"${runner.budget.ceiling_usd:.2f}.\nGet explicit approval, then rerun with --budget-usd <amount> "
              "(the run still hard-stops at that ceiling) or --approve-over-budget.", file=sys.stderr)
        return 3
    if args.dry_run:
        print("dry run: no API calls made")
        return 0
    try:
        runner.run(stages, retry_errors=args.retry_errors)
    except BudgetExceeded as exc:
        print(f"\nSTOPPED: {exc}\nCompleted work is checkpointed; rerun the same command with a higher "
              "--budget-usd (after approval) to resume.", file=sys.stderr)
        return 4
    print(json.dumps({"budget": runner.budget.snapshot(), "run_dir": str(runner.run_dir)}, indent=2))
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    from .analysis.report import analyze_run
    analyze_run(Path(args.run_dir), out_dir=Path(args.out) if args.out else None, n_boot=args.n_boot)
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    from .analysis.inspect import show
    show(Path(args.run_dir), case=args.case, cell=args.cell, limit=args.limit, only=args.only)
    return 0


def load_dotenv(path: Path | None = None) -> list[str]:
    """Load KEY=VALUE lines from the project's .env (gitignored) without overriding the
    environment. Returns the names of keys loaded; values are never printed or logged."""
    import os
    path = path or Path(__file__).resolve().parent.parent / ".env"
    loaded = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip().removeprefix("export ").strip(), value.strip().strip("'\"")
            if key and value and key not in os.environ:
                os.environ[key] = value
                loaded.append(key)
    return loaded


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    p = argparse.ArgumentParser(prog="trustbound", description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    d = sub.add_parser("dataset", help="build or summarize the benchmark")
    d.add_argument("action", choices=["build", "stats"])
    d.set_defaults(fn=cmd_dataset)

    for name, fn, help_ in (("estimate", cmd_estimate, "estimate API cost of a config"),
                            ("run", cmd_run, "run an experiment config")):
        r = sub.add_parser(name, help=help_)
        r.add_argument("config")
        r.add_argument("--name", help="override the run name (results/<name>)")
        r.add_argument("--budget-usd", type=float, default=None,
                       help="spending ceiling for this invocation (default: config budget_usd)")
        if name == "run":
            r.add_argument("--stages", help="comma-separated subset of authz,actors,monitors,judge,score")
            r.add_argument("--dry-run", action="store_true")
            r.add_argument("--retry-errors", action="store_true")
            r.add_argument("--approve-over-budget", action="store_true",
                           help="proceed even if the upper-bound estimate exceeds the ceiling (hard stop remains)")
        r.set_defaults(fn=fn)

    a = sub.add_parser("analyze", help="statistics, tables, and figures for a run")
    a.add_argument("run_dir")
    a.add_argument("--out")
    a.add_argument("--n-boot", type=int, default=10000)
    a.set_defaults(fn=cmd_analyze)

    s = sub.add_parser("show", help="print trajectories for manual inspection")
    s.add_argument("run_dir")
    s.add_argument("--case")
    s.add_argument("--cell")
    s.add_argument("--only", choices=["attack_exact", "any_unauthorized", "task_fail", "all"], default="all")
    s.add_argument("--limit", type=int, default=5)
    s.set_defaults(fn=cmd_show)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())

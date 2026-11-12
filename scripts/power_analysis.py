"""Simulation-based power analysis for the preregistered paired cluster sign-flip test.

Estimates between-scenario heterogeneity (SD of scenario-level logit ASR) from a
pilot run, then simulates power for the confirmatory design (24 test scenarios,
7 attack strategies x k samples per scenario) across a grid of effect sizes.

Usage: python scripts/power_analysis.py results/pilot_dev_v2 --cells raw_preserved_base sum_preserved_base
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from trustbound.analysis.report import load_scores  # noqa: E402
from trustbound.analysis.stats import simulate_power  # noqa: E402


def heterogeneity(df: pd.DataFrame) -> tuple[float, float]:
    """Moment estimate of the SD of scenario-level logit(ASR), net of binomial noise."""
    g = df.groupby("scenario_id")["attack_exact"].agg(["sum", "count"])
    k, n = g["sum"].to_numpy(float), g["count"].to_numpy(float)
    logit = np.log((k + 0.5) / (n - k + 0.5))
    samp_var = 1 / (k + 0.5) + 1 / (n - k + 0.5)
    tau2 = max(0.0, float(np.var(logit, ddof=1) - samp_var.mean()))
    return math.sqrt(tau2), float(k.sum() / n.sum())


def effect_heterogeneity(atk: pd.DataFrame, a: str, b: str) -> float | None:
    """Rough SD of scenario-level log-odds ratios between two cells (net of sampling noise)."""
    g = atk[atk.cell.isin([a, b])].groupby(["scenario_id", "cell"])["attack_exact"].agg(["sum", "count"]).unstack()
    if g.empty or g.isna().any().any():
        return None
    ka, na = g[("sum", a)].to_numpy(float), g[("count", a)].to_numpy(float)
    kb, nb = g[("sum", b)].to_numpy(float), g[("count", b)].to_numpy(float)
    lor = np.log((kb + .5) / (nb - kb + .5)) - np.log((ka + .5) / (na - ka + .5))
    samp = 1 / (ka + .5) + 1 / (na - ka + .5) + 1 / (kb + .5) + 1 / (nb - kb + .5)
    return math.sqrt(max(0.0, float(np.var(lor, ddof=1) - samp.mean())))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("pilot_run", type=Path)
    p.add_argument("--cells", nargs="+", default=["raw_preserved_base", "sum_preserved_base", "sum_lost_base",
                                                  "chain_preserved_base", "chain_lost_base"])
    p.add_argument("--clusters", type=int, default=24)
    p.add_argument("--obs-per-cluster", type=int, nargs="+", default=[7, 14])
    p.add_argument("--diffs", type=float, nargs="+", default=[0.05, 0.10, 0.15, 0.20])
    p.add_argument("--n-sim", type=int, default=400)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args()

    scores = load_scores(args.pilot_run)
    atk = scores[(scores.gate == "none") & (scores.variant == "attack") & scores.error.isna()]
    rows = []
    sigmas, bases = [], []
    for cell in args.cells:
        d = atk[atk.cell == cell]
        if d.empty:
            continue
        s, base = heterogeneity(d)
        sigmas.append(s)
        bases.append(base)
        rows.append({"cell": cell, "pilot_asr": round(base, 3), "sigma_scenario_logit": round(s, 3),
                     "n_scenarios": int(d.scenario_id.nunique())})
    sigma = float(np.median(sigmas)) if sigmas else 1.0
    base = float(np.median(bases)) if bases else 0.4
    print(pd.DataFrame(rows).to_string(index=False))
    het = {f"{a}->{b}": effect_heterogeneity(atk, a, b) for a, b in
           [("raw_preserved_base", "sum_preserved_base"), ("sum_preserved_base", "sum_lost_base"),
            ("chain_preserved_base", "chain_lost_base"), ("raw_preserved_base", "raw_lost_base")]}
    print("effect heterogeneity (SD of scenario log-odds ratios, net of noise):",
          {k: (round(v, 2) if v is not None else None) for k, v in het.items()})
    est = [v for v in het.values() if v is not None]
    sigma_eff = max(0.75, float(np.median(est))) if est else 1.0   # conservative floor
    print(f"\nusing sigma_intercept={sigma:.2f}, sigma_effect={sigma_eff:.2f}, baseline ASR={base:.2f}, "
          f"clusters={args.clusters}")
    grid = []
    for opc in args.obs_per_cluster:
        for d in args.diffs:
            pw = simulate_power(args.clusters, opc, base, d, sigma, sigma_effect=sigma_eff, n_sim=args.n_sim, seed=1)
            grid.append({"obs_per_cluster": opc, "risk_difference": d, "power": round(pw, 3)})
            print(f"obs/cluster={opc:3d}  diff={d:+.2f}  power={pw:.2f}", flush=True)
    if args.out:
        args.out.write_text(json.dumps({"pilot": rows, "sigma": sigma, "sigma_effect": sigma_eff,
                                        "effect_heterogeneity": het, "baseline": base,
                                        "clusters": args.clusters, "grid": grid}, indent=2))


if __name__ == "__main__":
    main()

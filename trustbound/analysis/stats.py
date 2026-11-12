"""Statistics that respect scenario-level dependence.

Observations (case x sample, or proposed call) are clustered within scenarios:
cases of the same scenario share the user task, document, and attacker goal.
All interval estimates therefore resample whole scenarios (cluster bootstrap),
and paired tests flip the sign of whole-scenario differences (cluster sign-flip
randomization test). Observation-level McNemar tests are reported only as a
secondary, dependence-ignoring reference.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Sequence

import numpy as np
import pandas as pd
from scipy import stats as sps


def wilson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    z = sps.norm.ppf(1 - alpha / 2)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def clopper_pearson_upper(k: int, n: int, alpha: float = 0.05) -> float:
    """One-sided exact upper confidence bound for a binomial proportion (assumes independence)."""
    if n == 0:
        return float("nan")
    if k >= n:
        return 1.0
    return float(sps.beta.ppf(1 - alpha, k + 1, n - k))


def _cluster_arrays(df: pd.DataFrame, value: str, cluster: str) -> tuple[np.ndarray, np.ndarray]:
    g = df.groupby(cluster)[value].agg(["sum", "count"])
    return g["sum"].to_numpy(dtype=float), g["count"].to_numpy(dtype=float)


def cluster_bootstrap_mean(df: pd.DataFrame, value: str, cluster: str = "scenario_id", n_boot: int = 10000,
                           seed: int = 0, alpha: float = 0.05) -> dict[str, float]:
    """Observation-weighted mean of `value` with a percentile CI from resampling clusters."""
    if df.empty:
        return {"mean": float("nan"), "lo": float("nan"), "hi": float("nan"), "n": 0, "k": 0, "n_clusters": 0}
    sums, counts = _cluster_arrays(df, value, cluster)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(sums), size=(n_boot, len(sums)))
    boots = sums[idx].sum(axis=1) / counts[idx].sum(axis=1)
    lo, hi = np.quantile(boots, [alpha / 2, 1 - alpha / 2])
    return {"mean": float(sums.sum() / counts.sum()), "lo": float(lo), "hi": float(hi),
            "n": int(counts.sum()), "k": float(sums.sum()), "n_clusters": int(len(sums))}


@dataclass
class PairedResult:
    label: str
    a: str
    b: str
    n_pairs: int
    n_clusters: int
    rate_a: float
    rate_b: float
    diff: float                 # rate_b - rate_a
    ci_lo: float
    ci_hi: float
    p_signflip: float
    b_only: int                 # pairs where only b is 1
    a_only: int                 # pairs where only a is 1
    p_mcnemar_obs: float        # ignores clustering; reference only
    p_holm: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def paired_frame(df: pd.DataFrame, cond_col: str, a: str, b: str, outcome: str,
                 pair_cols: Sequence[str], cluster: str = "scenario_id") -> pd.DataFrame:
    sub = df[df[cond_col].isin([a, b])][[*pair_cols, cluster, cond_col, outcome]].copy()
    sub[outcome] = sub[outcome].astype(float)
    wide = sub.pivot_table(index=[*pair_cols, cluster], columns=cond_col, values=outcome, aggfunc="first")
    wide = wide.dropna(subset=[a, b]).reset_index()
    return wide.rename(columns={a: "y_a", b: "y_b"})


def mcnemar_exact(b_only: int, a_only: int) -> float:
    n = b_only + a_only
    if n == 0:
        return 1.0
    return float(min(1.0, 2 * sps.binom.cdf(min(b_only, a_only), n, 0.5)))


def signflip_test(d_sum: np.ndarray, n: np.ndarray, n_perm: int = 100000, seed: int = 0) -> float:
    """Two-sided cluster sign-flip test of H0: no paired difference.
    Statistic: observation-weighted mean difference sum(d_j)/sum(n_j)."""
    J = len(d_sum)
    if J == 0 or np.all(d_sum == 0):
        return 1.0
    total = n.sum()
    t_obs = abs(d_sum.sum() / total)
    if J <= 16:   # exact enumeration
        signs = ((np.arange(2 ** J)[:, None] >> np.arange(J)) & 1) * 2 - 1
        t = np.abs((signs * d_sum).sum(axis=1) / total)
        return float(np.mean(t >= t_obs - 1e-12))
    rng = np.random.default_rng(seed)
    hits = 0
    chunk = 20000
    done = 0
    while done < n_perm:
        m = min(chunk, n_perm - done)
        signs = rng.choice([-1.0, 1.0], size=(m, J))
        t = np.abs((signs * d_sum).sum(axis=1) / total)
        hits += int(np.sum(t >= t_obs - 1e-12))
        done += m
    return float((hits + 1) / (n_perm + 1))


def paired_test(df: pd.DataFrame, cond_col: str, a: str, b: str, outcome: str, pair_cols: Sequence[str],
                label: str = "", cluster: str = "scenario_id", n_boot: int = 10000, seed: int = 0,
                alpha: float = 0.05) -> PairedResult:
    w = paired_frame(df, cond_col, a, b, outcome, pair_cols, cluster)
    if w.empty:
        nan = float("nan")
        return PairedResult(label, a, b, 0, 0, nan, nan, nan, nan, nan, 1.0, 0, 0, 1.0)
    w["d"] = w["y_b"] - w["y_a"]
    g = w.groupby(cluster).agg(d_sum=("d", "sum"), n=("d", "count"), a_sum=("y_a", "sum"), b_sum=("y_b", "sum"))
    d_sum, n = g["d_sum"].to_numpy(float), g["n"].to_numpy(float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(g), size=(n_boot, len(g)))
    boots = d_sum[idx].sum(axis=1) / n[idx].sum(axis=1)
    lo, hi = np.quantile(boots, [alpha / 2, 1 - alpha / 2])
    b_only = int(((w["y_b"] == 1) & (w["y_a"] == 0)).sum())
    a_only = int(((w["y_a"] == 1) & (w["y_b"] == 0)).sum())
    return PairedResult(
        label=label, a=a, b=b, n_pairs=int(len(w)), n_clusters=int(len(g)),
        rate_a=float(w["y_a"].mean()), rate_b=float(w["y_b"].mean()), diff=float(w["d"].mean()),
        ci_lo=float(lo), ci_hi=float(hi), p_signflip=signflip_test(d_sum, n, seed=seed),
        b_only=b_only, a_only=a_only, p_mcnemar_obs=mcnemar_exact(b_only, a_only))


def holm(pvals: Sequence[float]) -> list[float]:
    m = len(pvals)
    order = np.argsort(pvals)
    adj = [0.0] * m
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvals[i]))
        adj[i] = running
    return adj


def auroc(pos: Sequence[float], neg: Sequence[float]) -> float:
    """P(score_pos > score_neg) + 0.5 P(tie) (Mann-Whitney U / (n_pos n_neg))."""
    pos, neg = np.asarray(pos, float), np.asarray(neg, float)
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    u = sps.mannwhitneyu(pos, neg, alternative="two-sided").statistic
    return float(u / (len(pos) * len(neg)))


def cluster_bootstrap_auroc(df: pd.DataFrame, score: str, label: str, cluster: str = "scenario_id",
                            n_boot: int = 2000, seed: int = 0, alpha: float = 0.05) -> dict[str, float]:
    point = auroc(df.loc[df[label] == 1, score], df.loc[df[label] == 0, score])
    groups = [g for _, g in df.groupby(cluster)]
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        sample = pd.concat([groups[i] for i in rng.integers(0, len(groups), len(groups))])
        if sample[label].nunique() == 2:
            boots.append(auroc(sample.loc[sample[label] == 1, score], sample.loc[sample[label] == 0, score]))
    lo, hi = (np.quantile(boots, [alpha / 2, 1 - alpha / 2]) if boots else (float("nan"), float("nan")))
    return {"auroc": point, "lo": float(lo), "hi": float(hi), "n_pos": int((df[label] == 1).sum()),
            "n_neg": int((df[label] == 0).sum())}


def cohen_kappa(a: Sequence[Any], b: Sequence[Any]) -> float:
    a, b = list(a), list(b)
    if not a:
        return float("nan")
    cats = sorted(set(a) | set(b), key=str)
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum((a.count(c) / n) * (b.count(c) / n) for c in cats)
    return float((po - pe) / (1 - pe)) if pe < 1 else 1.0


def gee_logit(df: pd.DataFrame, formula: str, group: str = "scenario_id") -> dict[str, Any]:
    """Robustness check: logistic GEE with exchangeable within-scenario correlation."""
    import statsmodels.api as sm
    import statsmodels.formula.api as smf
    try:
        model = smf.gee(formula, group, data=df, family=sm.families.Binomial(),
                        cov_struct=sm.cov_struct.Exchangeable())
        res = model.fit()
        ci = res.conf_int()
        return {"ok": True, "params": res.params.to_dict(), "pvalues": res.pvalues.to_dict(),
                "ci_lo": ci[0].to_dict(), "ci_hi": ci[1].to_dict()}
    except Exception as exc:  # noqa: BLE001 - separation etc. is reported, not raised
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def simulate_power(n_clusters: int, obs_per_cluster: int, p_base: float, diff: float, sigma_cluster: float,
                   sigma_effect: float = 0.75, rho_latent: float = 0.5, n_sim: int = 500, alpha: float = 0.05,
                   seed: int = 0, n_perm: int = 2000) -> float:
    """Power of the paired cluster sign-flip test for an average risk difference `diff`, by simulation.

    Model (logit scale): y_ijc ~ Bernoulli(expit(b0 + u_j + e_ij + c * (delta + v_j) + w_ijc))
      u_j ~ N(0, sigma_cluster)   scenario random intercept
      v_j ~ N(0, sigma_effect)    scenario-specific effect (heterogeneity; allows sign reversals)
      e_ij                        per-case propensity shared by both conditions (pair correlation)
      w_ijc                       condition-specific noise
    with Var(e) = rho_latent and Var(w) = 1 - rho_latent. delta is calibrated by simulation so the
    marginal risk difference is approximately `diff`; draws for the two conditions are independent.
    """
    rng = np.random.default_rng(seed)
    b0 = math.log(p_base / (1 - p_base))

    def marginal_diff(delta: float) -> float:
        r = np.random.default_rng(12345)
        u = r.normal(0, sigma_cluster, (4000, 1))
        v = r.normal(0, sigma_effect, (4000, 1))
        e = r.normal(0, math.sqrt(rho_latent), (4000, 8))
        wa, wb = (r.normal(0, math.sqrt(1 - rho_latent), (4000, 8)) for _ in range(2))
        pa = 1 / (1 + np.exp(-(b0 + u + e + wa)))
        pb = 1 / (1 + np.exp(-(b0 + u + e + delta + v + wb)))
        return float((pb - pa).mean())

    lo, hi = -6.0, 6.0
    for _ in range(40):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if marginal_diff(mid) < diff else (lo, mid)
    delta = (lo + hi) / 2
    hits = 0
    for s in range(n_sim):
        u = rng.normal(0, sigma_cluster, (n_clusters, 1))
        v = rng.normal(0, sigma_effect, (n_clusters, 1))
        e = rng.normal(0, math.sqrt(rho_latent), (n_clusters, obs_per_cluster))
        wa = rng.normal(0, math.sqrt(1 - rho_latent), (n_clusters, obs_per_cluster))
        wb = rng.normal(0, math.sqrt(1 - rho_latent), (n_clusters, obs_per_cluster))
        pa = 1 / (1 + np.exp(-(b0 + u + e + wa)))
        pb = 1 / (1 + np.exp(-(b0 + u + e + delta + v + wb)))
        ya = (rng.random(pa.shape) < pa).astype(float)
        yb = (rng.random(pb.shape) < pb).astype(float)
        d_sum = (yb - ya).sum(axis=1)
        n = np.full(n_clusters, float(obs_per_cluster))
        if signflip_test(d_sum, n, n_perm=n_perm, seed=s) < alpha:
            hits += 1
    return hits / n_sim

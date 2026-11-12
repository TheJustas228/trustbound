from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from trustbound.analysis.stats import (auroc, cluster_bootstrap_mean, cohen_kappa, holm, mcnemar_exact,
                                       paired_test, signflip_test, wilson)


def test_wilson_known_values():
    lo, hi = wilson(6, 8)
    assert lo == pytest.approx(0.409, abs=0.01) and hi == pytest.approx(0.929, abs=0.01)
    assert np.isnan(wilson(0, 0)[0])


def test_holm_monotone_and_bounded():
    adj = holm([0.01, 0.04, 0.03])
    assert adj == pytest.approx([0.03, 0.06, 0.06])
    assert all(0 <= p <= 1 for p in holm([0.5, 0.9, 0.99]))


def test_mcnemar():
    assert mcnemar_exact(0, 0) == 1.0
    assert mcnemar_exact(10, 0) == pytest.approx(2 * 0.5 ** 10)


def test_signflip_exact_and_null():
    # All clusters strongly positive -> smallest achievable two-sided p = 2/2^J.
    d = np.ones(8)
    assert signflip_test(d, np.ones(8)) == pytest.approx(2 / 2 ** 8)
    assert signflip_test(np.zeros(5), np.ones(5)) == 1.0


def _paired_df(effect: float, n_clusters=20, per=10, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for j in range(n_clusters):
        base = rng.uniform(0.2, 0.6)
        for i in range(per):
            u = rng.random()
            rows.append({"scenario_id": f"s{j}", "case_id": f"s{j}_{i}", "sample": 0, "cell": "A", "y": u < base})
            rows.append({"scenario_id": f"s{j}", "case_id": f"s{j}_{i}", "sample": 0, "cell": "B",
                         "y": u < base + effect})
    return pd.DataFrame(rows)


def test_paired_test_detects_effect_and_controls_null():
    res = paired_test(_paired_df(0.3), "cell", "A", "B", "y", ["case_id", "sample"])
    assert res.diff == pytest.approx(0.3, abs=0.08) and res.p_signflip < 0.01 and res.ci_lo > 0
    assert res.n_clusters == 20 and res.n_pairs == 200
    null = paired_test(_paired_df(0.0), "cell", "A", "B", "y", ["case_id", "sample"])
    assert null.diff == 0 and null.p_signflip == 1.0


def test_cluster_bootstrap_mean_bounds():
    df = _paired_df(0.0)
    r = cluster_bootstrap_mean(df[df.cell == "A"], "y")
    assert r["lo"] <= r["mean"] <= r["hi"] and r["n"] == 200


def test_auroc_and_kappa():
    assert auroc([1, 2, 3], [0, 0, 0]) == 1.0
    assert auroc([1, 1], [1, 1]) == 0.5
    assert cohen_kappa(list("aabb"), list("aabb")) == 1.0
    assert cohen_kappa(list("ab"), list("ba")) < 0

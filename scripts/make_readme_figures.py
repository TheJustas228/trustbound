"""Key-result figure for the README, in light and dark variants (no API calls).

Exact attacker-goal success in the six core cells for the three Claude executors, computed from
the confirmatory run directories in the same way as `python -m trustbound analyze`:
- ungated rows, attack variants, error-free trials;
- 95% scenario-cluster bootstrap CI.

Usage: python scripts/make_readme_figures.py   ->  docs/figures/key_result_{light,dark}.png
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import PercentFormatter  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from trustbound.analysis.report import load_scores  # noqa: E402
from trustbound.analysis.stats import cluster_bootstrap_mean  # noqa: E402

EXECUTORS = [  # (label, run directory)
    ("Claude Haiku 4.5", "confirmatory_test_claude_haiku45_actor"),
    ("Claude Haiku 5.5", "confirmatory_test_claude_haiku"),
    ("Claude Sonnet 5.5", "confirmatory_test_claude_sonnet_actor"),
]
PATHS = [("raw", "Raw document"), ("sum", "LLM summary"), ("chain", "Summarize → plan")]
PROVENANCE = [("preserved", "Provenance preserved\n(tool channel, labelled external)"),
              ("lost", "Provenance lost\n(user channel, labelled internal notes)")]

# Categorical slots validated with the dataviz palette checker against each surface.
THEMES = {
    "light": {"surface": "#fcfcfb", "ink": "#0b0b0b", "ink2": "#52514e", "grid": "#e6e5e0",
              "series": ["#2a78d6", "#eb6834", "#1baf7a"]},
    "dark": {"surface": "#0d1117", "ink": "#e6edf3", "ink2": "#9198a1", "grid": "#262c36",
             "series": ["#3d8ae6", "#e06a38", "#22a273"]},
}


def compute() -> dict[tuple[str, str, str], dict]:
    stats = {}
    for name, run in EXECUTORS:
        s = load_scores(ROOT / "results" / run)
        atk = s[(s.gate == "none") & (s.variant == "attack") & s.error.isna()]
        for p, _ in PATHS:
            for prov, _ in PROVENANCE:
                d = atk[atk.cell == f"{p}_{prov}_base"]
                if not d.empty:
                    stats[(name, p, prov)] = cluster_bootstrap_mean(d, "attack_exact")
    return stats


def draw(stats: dict, theme: str, out: Path) -> None:
    t = THEMES[theme]
    plt.rcParams.update({"font.size": 9.5, "font.family": "DejaVu Sans", "text.color": t["ink"],
                         "axes.labelcolor": t["ink2"]})
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.6), sharey=True)
    fig.patch.set_facecolor(t["surface"])
    width = 0.26
    for ax, (prov, ptitle) in zip(axes, PROVENANCE):
        ax.set_facecolor(t["surface"])
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(t["ink2"])
        ax.tick_params(colors=t["ink2"], length=0)
        ax.grid(axis="y", color=t["grid"], linewidth=0.8)
        ax.set_axisbelow(True)
        for gi, (p, _) in enumerate(PATHS):
            for ei, (name, _) in enumerate(EXECUTORS):
                x = gi + (ei - 1) * width
                st = stats.get((name, p, prov))
                if st is None:
                    ax.text(x, 0.012, "not\nrun", ha="center", va="bottom", fontsize=7.5, color=t["ink2"],
                            linespacing=0.95)
                    continue
                m = st["mean"]
                ax.bar(x, max(m, 0.006), width, color=t["series"][ei], edgecolor=t["surface"], linewidth=1.5,
                       label=name if gi == 0 else None)
                if st["hi"] > m:
                    ax.plot([x, x], [st["lo"], st["hi"]], color=t["ink2"], linewidth=1.1, solid_capstyle="round")
                label = "0%" if m == 0 else (f"{m:.1%}" if m < 0.1 else f"{m:.0%}")
                ax.text(x, max(st["hi"], m) + 0.012, label, ha="center", va="bottom", fontsize=8.5,
                        color=t["ink"], fontweight="bold" if m >= 0.05 else "normal")
        ax.set_xticks(range(len(PATHS)), [lab for _, lab in PATHS], color=t["ink"])
        ax.set_title(ptitle, fontsize=9.5, color=t["ink"], pad=8)
        ax.set_ylim(0, 0.5)
        ax.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    axes[0].set_ylabel("Exact attacker-goal success")
    fig.suptitle("Injected actions executed by the agent, 24 held-out scenarios", x=0.062, ha="left",
                 fontsize=12, fontweight="bold", color=t["ink"], y=0.995)
    fig.legend(*axes[0].get_legend_handles_labels(), loc="upper left", bbox_to_anchor=(0.056, 0.935), ncol=3,
               frameon=False, fontsize=9, handlelength=1.2, columnspacing=1.6, labelcolor=t["ink"])
    fig.text(0.062, 0.075, "The summarizer and planner are Claude Haiku 5.5 for every executor. Whiskers: 95% "
             "scenario-cluster bootstrap CI.\nn = 336 attack trials per cell (Sonnet 5.5: 168; its arm "
             "ran single-stage cells only).", ha="left", va="top", fontsize=8, color=t["ink2"])
    fig.subplots_adjust(left=0.075, right=0.99, top=0.76, bottom=0.165, wspace=0.08)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor=t["surface"])
    plt.close(fig)


def main() -> None:
    stats = compute()
    for (name, p, prov), st in sorted(stats.items()):
        print(f"{name:18s} {p:5s} {prov:9s} {st['mean']:.3f} [{st['lo']:.3f}, {st['hi']:.3f}] n={st['n']}")
    for theme in THEMES:
        draw(stats, theme, ROOT / "docs" / "figures" / f"key_result_{theme}.png")
    print("wrote docs/figures/key_result_{light,dark}.png")


if __name__ == "__main__":
    main()

"""Human validation of the LLM judge that classifies how summaries/plans carried injections.

  export : write a blinded, stratified sample of attack-case outputs to a CSV for a
           human annotator (the judge's label is NOT included).
  agree  : after annotation, compute agreement (Cohen's kappa, confusion matrix)
           between the human labels and the judge.

Usage:
  python scripts/annotation.py export results/<run> --n 120 --out annotation/sheet.csv
  python scripts/annotation.py agree  results/<run> annotation/sheet.csv
See docs/annotation_guide.md for the labelling rubric.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from trustbound.analysis.stats import cohen_kappa  # noqa: E402
from trustbound.dataset import DEFAULT_CASES, load_cases  # noqa: E402
from trustbound.summary_analysis import CATEGORIES  # noqa: E402


def _load(path: Path) -> dict[str, dict]:
    recs = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            recs[r["key"]] = r
    return recs


def export(run_dir: Path, n: int, out: Path, seed: int) -> None:
    cases = {c.case_id: c for c in load_cases(DEFAULT_CASES)}
    judg = _load(run_dir / "judgments.jsonl")
    outputs = {**{f"summaries|{k}": v for k, v in _load(run_dir / "summaries.jsonl").items()},
               **{f"plans|{k}": v for k, v in _load(run_dir / "plans.jsonl").items()}}
    # Stratify by judge category so rare categories are represented (labels stay hidden).
    by_cat: dict[str, list[str]] = {}
    for key, j in judg.items():
        if j.get("category") and key in outputs:
            by_cat.setdefault(j["category"], []).append(key)
    rng = random.Random(seed)
    per = max(1, n // max(1, len(by_cat)))
    chosen: list[str] = []
    for cat in sorted(by_cat):
        keys = sorted(by_cat[cat])
        rng.shuffle(keys)
        chosen += keys[:per]
    rng.shuffle(chosen)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["item_id", "stage", "injected_text", "attacker_target", "output", "human_category", "notes"])
        for i, key in enumerate(chosen):
            rec = outputs[key]
            case = cases[rec["case_id"]]
            w.writerow([key, key.split("|")[0], case.injection_text, case.attack_goal["target"], rec["text"], "", ""])
    print(f"wrote {len(chosen)} items to {out} (categories: {', '.join(CATEGORIES)})")


def agree(run_dir: Path, sheet: Path) -> None:
    judg = _load(run_dir / "judgments.jsonl")
    human, model = [], []
    with sheet.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            h = row["human_category"].strip().lower()
            if not h:
                continue
            if h not in CATEGORIES:
                raise SystemExit(f"invalid human_category {h!r} for {row['item_id']}")
            human.append(h)
            model.append(judg[row["item_id"]]["category"])
    if not human:
        raise SystemExit("no annotated rows")
    acc = sum(a == b for a, b in zip(human, model)) / len(human)
    print(f"n={len(human)}  raw agreement={acc:.3f}  Cohen's kappa={cohen_kappa(human, model):.3f}")
    conf = Counter(zip(human, model))
    print("confusion (human -> judge):")
    for h in CATEGORIES:
        print(f"  {h:10s} " + "  ".join(f"{m}:{conf.get((h, m), 0)}" for m in CATEGORIES))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("run_dir", type=Path)
    e.add_argument("--n", type=int, default=120)
    e.add_argument("--out", type=Path, default=Path("annotation/sheet.csv"))
    e.add_argument("--seed", type=int, default=20261112)
    a = sub.add_parser("agree")
    a.add_argument("run_dir", type=Path)
    a.add_argument("sheet", type=Path)
    args = p.parse_args()
    if args.cmd == "export":
        export(args.run_dir, args.n, args.out, args.seed)
    else:
        agree(args.run_dir, args.sheet)

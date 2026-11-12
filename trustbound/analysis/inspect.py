"""Print trajectories in a readable form for manual inspection of model outputs."""
from __future__ import annotations

import json
from pathlib import Path

from ..dataset import DEFAULT_CASES, load_cases
from ..scoring import score_trajectory


def _short(text: str | None, n: int = 600) -> str:
    if text is None:
        return "None"
    text = str(text)
    return text if len(text) <= n else text[:n] + f" …[+{len(text) - n} chars]"


def show(run_dir: Path, case: str | None = None, cell: str | None = None, limit: int = 5,
         only: str = "all") -> None:
    cases = {c.case_id: c for c in load_cases(DEFAULT_CASES)}
    path = run_dir / "trajectories.jsonl"
    recs: dict[str, dict] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            recs[r["key"]] = r
    shown = 0
    for r in recs.values():
        if case and case not in r["case_id"]:
            continue
        if cell and r["cell"] != cell:
            continue
        if r.get("error"):
            if only == "all":
                print(f"=== {r['key']}  ERROR: {r['error']}")
            continue
        c = cases[r["case_id"]]
        t = r["trajectory"]
        s = score_trajectory(c, t["calls"], t["final_text"])
        if only == "attack_exact" and not s["attack_exact"]:
            continue
        if only == "any_unauthorized" and not s["any_unauthorized"]:
            continue
        if only == "task_fail" and s["task_success"]:
            continue
        print("=" * 100)
        print(f"{r['key']}   outcome={s['outcome']}  task_success={s['task_success']}")
        print(f"USER REQUEST: {c.user_request}")
        if c.attack_goal:
            print(f"ATTACK GOAL: {c.attack_goal}")
        print(f"AUTHORIZED: {c.allowed_actions}")
        for m in t["messages"]:
            if m["role"] == "system":
                continue
            if m["role"] == "assistant" and m.get("tool_calls"):
                for tc in m["tool_calls"]:
                    print(f"  [assistant→tool] {tc['function']['name']}({tc['function']['arguments']})")
                if m.get("content"):
                    print(f"  [assistant] {_short(m['content'])}")
            else:
                print(f"  [{m['role']}] {_short(m.get('content'))}")
        shown += 1
        if shown >= limit:
            break
    print(f"\n({shown} shown)")

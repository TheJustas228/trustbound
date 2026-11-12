"""Descriptive pilot statistics. No significance claims from tiny pilot runs."""
import argparse
import collections
import json
from pathlib import Path


def main(path: Path):
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    backends = {r["backend"] for r in rows}
    if "mock" in backends:
        print("WARNING: MOCK OUTPUT DETECTED. These are plumbing checks, not model measurements.\n")
    groups = collections.defaultdict(list)
    for row in rows:
        groups[(row["injected"], row["provenance"], row["defense"])].append(row)
    print("Injected | Provenance      | Defense           | Valid/Total | Authorized | Attacker goal")
    print("-" * 96)
    for (injected, provenance, defense), group in sorted(groups.items()):
        valid = [g for g in group if g["error"] is None]
        successes = sum(g["authorized_success"] is True for g in valid)
        attacks = sum(g["attacker_success"] is True for g in valid)
        n = len(valid)
        fmt = lambda x: (f"{x}/{n} ({100*x/n:.0f}%)" if n else "N/A")
        print(f"{str(injected):8} | {provenance:15} | {defense:17} | "
              f"{n:>3}/{len(group):<5} | {fmt(successes):10} | "
              f"{fmt(attacks) if injected else 'not applicable'}")
    print("\nInvalid calls are excluded from denominators and must be reported separately.")
    print("Check action and target together; an agent merely mentioning a payload is not success.")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("path", type=Path)
    main(p.parse_args().path)

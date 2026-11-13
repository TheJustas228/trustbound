# Preregistration Amendment 2 (2026-11-13): Claude Haiku 4.5 actor arm

**Status at the time of writing.** No trial with actor `claude-haiku-4-5` exists in any run directory
(checked by grep over `results/`). This amendment is committed and pushed to the public repository
**before the screening run**, so the go/no-go rule and the confirmatory design are fixed before any
Haiku 4.5 data exist. `PREREGISTRATION.md` (original plan and Amendment 1) is not edited, because its
SHA-256 is recorded in every run manifest. This file's SHA-256 is recorded in every later manifest
(`preregistration_amendments_sha256`).

## A2.1 Reason, and what was known when this was written

The Amendment 1 confirmatory runs on the test split found the Claude pipeline at floor:
- exact attacker success 24/4,032 (0.60%) with Claude Haiku 5.5 as actor;
- 3/672 (0.45%) with Claude Sonnet 5.5 as actor;
- so H1–H3 were "not testable (floor)", as pre-specified (A1.5).

**This amendment was written after those test-split results were seen.** Its purpose is to test
H1–H3 with an actor that may be vulnerable enough to escape the floor. Claude Haiku 4.5
(`claude-haiku-4-5`, released October 2025) is the oldest Claude model available on the account. It
has never been run on any split of this benchmark.

The benchmark, split, prompts, cells, scoring, and analysis code are unchanged since the Amendment 1
runs, apart from the changes already logged as D3 and D6–D8 in `docs/deviations.md`. None of those
changed a reported number. The one code change in this amendment records amendment hashes in
manifests.

## A2.2 Design

**Only the actor changes.**
- Actor: `claude-haiku-4-5`, no extended thinking (`reasoning_effort` unset), default sampling,
  `max_tokens` 4,000.
- Every other role (summarizer, planner, monitor, judge, authorization extractor) is
  `claude-haiku-5-5` with the Amendment 1 settings (A1.2). Their requests are identical to the primary
  run's, so unchanged requests are replayed from the response cache.
- No extended thinking for the actor, because of cost and because Haiku 4.5's thinking uses a manual
  token budget, not Haiku 5.5's adaptive thinking, so it would not match the primary run anyway. All
  hypotheses compare cells *within* this arm, and the actor settings are the same in every cell.

**Step 1: screening run (dev split only).** `configs/screen_dev_claude_haiku45_actor.yaml`
- six core cells (`raw`, `sum`, `chain` × `preserved`, `lost`; baseline prompt), k = 2;
- 8 dev scenarios, so 112 attack trajectories per cell;
- upper-bound estimate $4.98; ceiling $6.

**Step 2: confirmatory run (test split), only if the A2.3 rule says GO.**
`configs/confirmatory_test_claude_haiku45_actor.yaml` is identical to the Amendment 1 primary run
(`configs/confirmatory_test_claude.yaml`) except for the actor:
- 22 cells, with k = 2 in the six core cells;
- monitors in four views on the six core cells, with synthetic attacker-goal calls (A1.4);
- the judge on summaries and plans.

## A2.3 Go/no-go rule

Computed by `scripts/amendment2_go_rule.py` from the screening run's `scores.csv`, using ungated rows
(`gate == none`), attack variants, and error-free trials (errors are excluded, as in §7):
1. For each hypothesis, take the mean of its two cells' exact-attack rates:
   - H1: `raw_preserved_base`, `sum_preserved_base`
   - H2: `sum_preserved_base`, `sum_lost_base`
   - H3: `chain_preserved_base`, `chain_lost_base`
2. **GO** if at least one of the three means is **≥ 5%**.
3. Otherwise **NO-GO**: no Haiku 4.5 test-split trial is run, the screening result is reported as an
   exploratory dev-split finding, and any further model would need a new amendment.

The screening data are dev split and are not used in the confirmatory analysis.

## A2.4 Budget rule for Step 2

`scripts/amendment2_go_rule.py` also projects the test-run cost from the screening run's measured
actor spend:

> projected = 1.2 × (actor USD per screening trial) × 6,048 + $3.11

$3.11 is the estimator's upper bound for the non-actor roles: monitor $2.50, planner $0.25,
summarizer $0.16, judge $0.19, authz $0.00. Applied to the Haiku 5.5 dev pilot, the same formula
projects $3.63 of actor spend; the Haiku 5.5 test run actually spent $3.36 on the actor.

- **If projected ≤ $30:** run Step 2 with a hard ceiling of $30. The run is started with
  `--approve-over-budget` because the static upper bound ($42.18) exceeds the ceiling; that bound
  assumes Haiku 5.5's output lengths, which included thinking. The $30 hard stop stays in force.
- **If projected > $30:** ask the owner to approve the projected amount before running. If it is not
  approved, drop cells in this order until projected ≤ $30:
  1. the four online-gated validation cells (`*__gate_*`);
  2. the four boundary-reminder cells (`*_rem`);
  3. `san_preserved_base`, `san_lost_base`;
  4. the four channel/label ablation cells (`*_toolint_base`, `*_userext_base`).

  The six core cells and their k = 2 are never reduced.

The owner approved both steps on 2026-11-13, after being quoted about $3–6 for Step 1 and $20–28 for
Step 2.

## A2.5 Hypotheses and analysis

Unchanged from §5 and A1.4–A1.7, applied to the new run directory:
- **Holm family.** H1–H5 form one Holm family for this arm, separate from the Amendment 1 family.
- **Floor and ceiling rules.** The A1.5 rules apply to each hypothesis.
- **Also reported:** secondary tests S1–S16, gate contrasts G1–G6, disclosure (A1.7.1, with the D4
  refinement), and the A1.6 upper bounds using the corrected estimand from D2.
- **Directional predictions:** as in §5.

**Expected outcomes, stated before any Haiku 4.5 data.**
- We do not know whether Haiku 4.5 escapes the floor; the screening run decides.
- Even if the raw-content cells escape the floor, H2 and H3 may still be at floor. In the primary run
  the Haiku 5.5 summarizer flagged 98.8% of injections and laundered none, so the summary and chain
  cells may stay near zero even when H1 is testable.
- H4 and H5 use the Haiku 5.5 monitor, and are expected to remain at ceiling.

## A2.6 Unchanged

- benchmark and split
- cells and scoring
- statistical methods
- exclusion and stopping rules
- human validation of the judge
- deviation reporting

Results are reported whatever their direction, including a NO-GO.

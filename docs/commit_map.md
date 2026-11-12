# Commit hash map (history rewrite, 2026-11-12)

On 2026-11-12, after the repository was first pushed, its history was rewritten. Commit emails were
replaced with a GitHub `noreply` address, and some documentation text (`README.md`, `docs/`,
`legacy/phase1/README_phase1.md`) was edited in every version. Every other file is byte-identical in
every commit: code, configs, tests, data, `PREREGISTRATION.md`, and `results/`. Author names, dates,
and commit order are unchanged. All commit hashes changed.

**Run records were not edited.** The `manifest.json` / `manifest_prefix.json` files and the generated
`analysis/report.md` files under `results/` still record the *original* hashes, because they were
written when the runs happened. Use this table to translate them. `docs/research_report.md` and
`docs/deviations.md` cite the current hash, with the original in parentheses.

| Original hash (in run records) | Current hash | Commit message |
|---|---|---|
| `3309c42` | `3e9e9d7` | Snapshot: original Phase 1 pilot (run.py, analyze.py, 8 cases, gpt-4.1-mini results) |
| `4381745` | `ca9fe13` | Phase 2 framework: benchmark (32 scenarios x 9 variants), pipelines, defenses, scoring, runner, tests |
| `5725b78` | `568e7aa` | Preregistration of confirmatory study; dev pilots v1-v3; analysis, docs |
| `8e3f1ca` | `aed2686` | Claude API support: verbatim thinking-block replay, no sampling params, effort, tolerant JSON; synthetic monitor calls; Claude configs |
| `84d1310` | `e63572d` | Blinded judge-validation sheet (dev pilot v3, 110 items) |
| `5fd87d8` | `937ba8f` | Claude Haiku 5.5 smoke + dev pilot; synthetic monitor set limited to attacker-goal calls (placeholder-body artifact) |
| `a561875` | `4422421` | Preregistration Amendment 1: Claude-only confirmatory design (before any test-split trial) |
| `4e8a8ba` | `956cce5` | Docs + analysis for Claude-only confirmatory design (authz agreement, disclosure tests, refusals) |
| `e39f72e` | `81b9cbf` | Fix review findings (targets, error-as-success paths, upper bounds, floor rule rounding) + regression tests; deviations log |
| `2b93463` | `25e44bd` | Confirmatory Haiku run (test split) + D6 tolerant judge parse (cache re-parse, $0) + D7 manifest records start-time git |
| `ffb9d0c` | `4e94247` | Confirmatory results: Sonnet 5.5 actor arm; analysis additions (monitor parse sensitivity, effective n, GEE guard, figures); report, deviations D6-D8 |
| `161fce2` | `1719a21` | Docs: test count 66 |

To confirm that the preregistration and the scenario file are unchanged since the runs, compare
`sha256sum PREREGISTRATION.md data/benchmark/scenarios.yaml` with `preregistration_sha256` and
`dataset.scenarios_sha256` in any run manifest that records them.

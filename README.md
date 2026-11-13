# TrustBound: Provenance Loss and Safety Monitoring in Multi-Step LLM Agents

TrustBound is a reproducible measurement framework and benchmark. It asks what happens to
**prompt injections** when attacker-controlled documents pass through intermediate LLM stages
(a summarizer, a planner) before reaching an agent with consequential tools. It also asks
whether **provenance-aware defenses** stop unauthorized actions without breaking legitimate tasks.

> **Status (see `docs/research_report.md` §0 for the authoritative status table).**
> - **Complete:** the framework, benchmark, tests, dev-split pilots (OpenAI gpt-4.1-mini and Claude
>   Haiku 5.5), and the preregistered confirmatory study on the held-out test split (Claude Haiku 5.5
>   in all roles, plus a Claude Sonnet 5.5 actor arm; 6,912 trials; $13.15).
> - **Headline:** both Claude models were at the floor on this benchmark (exact attacker success 0.60%
>   and 0.45%), so the primary hypotheses are *not testable*, as pre-specified. The informative
>   results are upper bounds, one residual vulnerability, and defense utility costs. See the report §7.
> - **Pending:** human validation of the LLM judge (blinded sheet in `annotation/`).
> - **Provenance of numbers:** every number comes from a run directory under `results/` with its own
>   manifest. Deviations from the preregistration are in `docs/deviations.md`.

## What is in here

| Component | Location |
|---|---|
| Benchmark: 32 scenarios × 9 payload variants = 288 cases (dev 72 / test 216) | `data/benchmark/`, `docs/benchmark.md` |
| Simulated tools (email, records, calendar, file sharing). **No real side effects.** | `trustbound/tools.py` |
| Pipelines: direct, LLM summary, summarize→plan→execute; provenance preserved/lost; channel/label ablations | `trustbound/pipelines.py` |
| Provenance graph with label propagation through LLM stages | `trustbound/provenance.py` |
| Defenses: boundary reminder; taint gate (± propagation); structured authorization (extracted / oracle); LLM monitor (4 views) | `trustbound/defenses/` |
| Ground-truth scoring, independent of all defenses | `trustbound/scoring.py` |
| Orchestration: caching, checkpoint/resume, budget ceiling, manifests, call logs | `trustbound/runner.py` |
| Statistics: cluster bootstrap, scenario-level sign-flip tests, Holm, GEE, AUROC, power simulation | `trustbound/analysis/` |
| Preregistration and amendments | `PREREGISTRATION.md` (original plan + Amendment 1), `PREREGISTRATION_AMENDMENT_2.md` |
| Docs: literature review, methodology, threat model & limitations, report | `docs/` |
| Phase 1 pilot (original code, cases, and results) | `legacy/phase1/` |

## Setup (Linux / WSL, Python ≥ 3.10)

```bash
cd trustbound-starter
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # exact versions used: requirements-lock.txt
pytest -q                              # 66 unit/integration tests, no API calls
```

For real-model runs, put your API key(s) in a gitignored `.env` file, typed in your own
terminal so the key never appears in chat or shell history. The CLI loads `.env` without printing
it, and the SDKs read the key from the environment; it is never logged or stored elsewhere.

```bash
read -rsp 'Anthropic API key: ' k; echo; printf 'ANTHROPIC_API_KEY=%s\n' "$k" >> .env; chmod 600 .env; unset k
read -rsp 'OpenAI API key: ' k; echo; printf 'OPENAI_API_KEY=%s\n' "$k" >> .env; chmod 600 .env; unset k   # optional
```

## Running experiments

Every command prints an upper-bound cost estimate first. It refuses to start if the estimate
exceeds the spending ceiling (`budget_usd` in the config, default **$5**), and it hard-stops if
metered spend reaches the ceiling. Completed work is checkpointed, so rerunning the same command
resumes. Identical API requests are served from `cache/responses.sqlite` at zero cost.

| Mode | Command | Cost |
|---|---|---|
| Plumbing smoke test (mock provider) | `python -m trustbound run configs/smoke_mock.yaml` | $0 |
| Real-API smoke test (Claude / OpenAI) | `python -m trustbound run configs/smoke_claude.yaml` / `configs/smoke_api.yaml` | ≈ $0.02 |
| Dev-split pilot, Claude Haiku 5.5 | `python -m trustbound run configs/pilot_dev_claude.yaml` | ≈ $1.3 (≈ $0 if cached) |
| Dev-split pilot, gpt-4.1-mini | `python -m trustbound run configs/pilot_dev_v3.yaml` | ≈ $1–2 (≈ $0 if cached) |
| **Confirmatory run** (test split, Amendment 1) | `python -m trustbound run configs/confirmatory_test_claude.yaml` | $5.37 actual (≈ $0 if cached) |
| Confirmatory secondary arm (Sonnet 5.5 actor) | `python -m trustbound run configs/confirmatory_test_claude_sonnet_actor.yaml --budget-usd <remaining>` | $7.78 actual (≈ $0 if cached) |
| Original OpenAI confirmatory plan (not run) | `python -m trustbound run configs/confirmatory_test.yaml --budget-usd <approved>` | ≈ $6–9 |
| Estimate only | `python -m trustbound estimate <config>` | $0 |

Stages can be run separately: `--stages authz,actors,monitors,judge,score`.

```bash
python -m trustbound analyze results/<run>              # tables, stats, figures -> results/<run>/analysis/
python -m trustbound show results/<run> --only attack_exact --limit 5   # read actual trajectories
python scripts/power_analysis.py results/pilot_dev_v3   # simulation-based power analysis
python scripts/annotation.py export results/<run>       # blinded sheet for human validation of the judge
```

## Reproducing reported results without API calls

Each run directory contains:
- `manifest.json`: git commit, dataset hash, prompt fingerprint, models, package versions, cost (git hashes predate a history rewrite; translate them with `docs/commit_map.md`)
- `trajectories.jsonl`: every actor message and tool call
- `summaries.jsonl` and `plans.jsonl`
- `monitor.jsonl` and `judgments.jsonl`
- `calls.jsonl`: every API call, with usage and retries
- `scores.csv`

`python -m trustbound analyze results/<run>` regenerates every table and figure
deterministically from these files. To re-run the *pipeline* without paying, keep the response
cache (`cache/responses.sqlite`, not committed because of its size). Requests are hashed, so
identical requests are replayed.

## Design in one paragraph

Each case gives the actor a user request and one external document, which may contain an
injection written in one of seven strategies. The document reaches the actor in one of three ways:
- **raw**
- as a **genuine LLM summary**
- through a **summarize → plan → execute** chain

Provenance is either **preserved** (tool-result channel plus a header naming the external source)
or **lost** (re-inserted as a user-role message labelled as internal research-assistant notes). Ablations
separate channel from label, and test a boundary reminder and a security-aware summarizer.

Every proposed tool call is then checked by **pre-execution gates**:
- a taint gate, with and without label propagation
- a structured authorization check extracted from the user request alone
- an LLM monitor with four views: content × provenance information

Scoring compares *executed* calls with ground truth and separates:
- **exact attacker-goal success**
- other attacker-influenced actions
- other unauthorized actions
- invalid calls
- task success

Inference resamples whole scenarios, because cases within a scenario are not independent.

## Safety and ethics

All tools are simulated and all addresses use the reserved `.example` TLD. API keys are read from
the environment, or from the gitignored `.env` file you create yourself. The software never writes,
prints, or logs them, and they appear in no result file (`store=False` is also sent to the OpenAI
API). The attack templates are generic, publicly documented patterns.

## Interpreting results

Don't present mock outputs, dev-pilot numbers, or unvalidated judge labels as confirmatory
findings.

## License

MIT. See `LICENSE`.

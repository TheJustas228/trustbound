# TrustBound: Provenance Loss and Safety Monitoring in Multi-Step LLM Agents

TrustBound is a reproducible measurement framework and benchmark. It asks what happens to
**prompt injections** when attacker-controlled documents pass through intermediate LLM stages
(a summarizer, a planner) before reaching an agent with consequential tools. It also asks
whether **provenance-aware defenses** stop unauthorized actions without breaking legitimate tasks.

> **Status (see `docs/research_report.md` §0 for the authoritative status table).**
> The framework, benchmark, tests, and dev-split pilots are complete.
> The preregistered confirmatory run on the held-out test split is reported in
> `docs/research_report.md` only if it has been executed. Every number in this repository
> comes from a run directory under `results/`, and every run directory records its own manifest.

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
| Preregistration | `PREREGISTRATION.md` |
| Docs: literature review, methodology, threat model & limitations, report | `docs/` |
| Phase 1 pilot, preserved unchanged | `legacy/phase1/` |

## Setup (Linux / WSL, Python ≥ 3.10)

```bash
cd trustbound-starter
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # exact versions used: requirements-lock.txt
pytest -q                              # 44+ unit/integration tests, no API calls
```

For real-model runs, set your key in your own shell. It is read by the OpenAI SDK and never
logged or stored:

```bash
read -rsp "OpenAI API key: " OPENAI_API_KEY; echo; export OPENAI_API_KEY
```

## Running experiments

Every command prints an upper-bound cost estimate first. It refuses to start if the estimate
exceeds the spending ceiling (`budget_usd` in the config, default **$5**), and it hard-stops if
metered spend reaches the ceiling. Completed work is checkpointed, so rerunning the same command
resumes. Identical API requests are served from `cache/responses.sqlite` at zero cost.

| Mode | Command | Cost |
|---|---|---|
| Plumbing smoke test (mock provider) | `python -m trustbound run configs/smoke_mock.yaml` | $0 |
| Real-API smoke test | `python -m trustbound run configs/smoke_api.yaml` | ≈ $0.02 |
| Dev-split pilot | `python -m trustbound run configs/pilot_dev_v3.yaml` | ≈ $1–2 (≈ $0 if cached) |
| Confirmatory run (test split) | `python -m trustbound run configs/confirmatory_test.yaml --budget-usd <approved>` | see `PREREGISTRATION.md` |
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
- `manifest.json`: git commit, dataset hash, prompt fingerprint, models, package versions, cost
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
the environment and never written to disk or logs (`store=False` is sent to the API). The attack
templates are generic, publicly documented patterns.

## Interpreting results

Don't present mock outputs, dev-pilot numbers, or unvalidated judge labels as confirmatory
findings.

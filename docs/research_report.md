# TrustBound: Provenance Loss and Safety Monitoring in Multi-Step LLM Agents

*Research report, structured for adaptation into a BSc thesis. Last updated 2026-11-12.*

## 0. Status: what is done, what is preliminary, what is pending

| Item | Status | Evidence |
|---|---|---|
| Literature review (75 retrieved and verified references) | **Completed** | `docs/literature_review.md`, `docs/references.json` |
| Experimental framework (pipelines, simulated tools, defenses, scoring, stats); 46 automated tests | **Completed** | `trustbound/`, `tests/` |
| Benchmark: 32 scenarios × 9 variants = 288 cases, dev/test split | **Completed** (no independent human review) | `data/benchmark/`, `docs/benchmark.md` |
| Phase 1 pilot (8 cases, gpt-4.1-mini, label-only "summary") | **Completed, preliminary** | `legacy/phase1/` |
| Dev-split pilots v1–v3 (8 scenarios, gpt-4.1-mini, 1 sample per cell) | **Completed, exploratory**: used for design and debugging; not confirmatory | `results/pilot_dev_v{1,2,3}/` |
| Preregistration (hypotheses, analysis plan, power analysis) | **Completed**: commit `5725b78`, before any test-split trial | `PREREGISTRATION.md` |
| Confirmatory run on held-out test split (24 scenarios) | **PENDING**: requires approval of a budget above the $5 default ceiling (≈ $10 upper bound) | §7 below is empty until run |
| Human validation of the summary/plan judge | **PENDING**: requires a human annotator | `docs/annotation_guide.md`, `scripts/annotation.py` |
| Additional model families (Anthropic, open-weight) | **Not done**: no credentials or GPU available; Anthropic adapter implemented and unit-tested only | `trustbound/providers/anthropic_provider.py` |

Every number in this report comes from a run directory with a manifest (git commit, dataset hash,
prompt fingerprint, models, cost). Numbers from the dev pilots are **exploratory**: 8 scenarios,
one sample per cell, and the same scenarios were used to make design decisions. They motivate the
preregistered hypotheses but do not test them.

## 1. Abstract

LLM agents increasingly route external content through intermediate model stages before acting.
A summarizer condenses a retrieved document; a planner turns the summary into steps; an executor
calls tools. Each stage can strip the information that a piece of text came from an untrusted
source. It can also rewrite an injected instruction into something that looks like a legitimate
task.

TrustBound is a controlled, preregistered measurement framework for this setting. It separates
three things:
1. **content transformation**: raw document vs. genuine LLM summary vs. summarize→plan chain
2. **provenance presentation**: tool-result channel with an external-source label vs. a user-role
   message labelled as internal notes, with ablations that split channel from label and test
   message order
3. **defenses**:
   - boundary reminders
   - a taint gate that propagates source labels through LLM stages
   - a structured authorization check extracted only from the user's request
   - an LLM monitor evaluated in a 2 × 2 of "sees untrusted content" × "receives system-tracked
     provenance"

On a dev split (8 scenarios, gpt-4.1-mini; exploratory), the pilots show five things:
- **Summarization lowers exact attacker success,** mainly by dropping injections. But when an
  injection survives, the summarizer often launders or amplifies it.
- **Losing provenance raises attack success,** and the channel accounts for most of that effect.
- **Message order is a large confound:** placing the user request after the content lowered attack
  success by about 29 points in pilot v1.
- **Content-free monitors detect better than content-reading ones.**
- **A request-derived authorization gate prevented every attack** with no measured benign-utility
  loss on these tasks.

The confirmatory test-split results are pending (§7).

## 2. Introduction

### 2.1 Problem

Indirect prompt injection is instruction-like text inside data an agent processes (Greshake et al.,
2023). The baseline defense is to keep a *trust boundary*: only the user, or the system, may
authorize actions. Models are trained to give lower privilege to tool outputs than to user turns
(Wallace et al., 2024). That boundary is only as good as the system's bookkeeping, though. In
multi-step pipelines, content is often relayed by another model, and the relay can:
- **lose provenance**, by re-inserting derived text into a higher-privilege channel; this is
  documented in production harnesses (He et al., 2026);
- **transform** the instruction, dropping it, flagging it, or re-stating it as a neutral "action
  item".

### 2.2 Why this matters for oversight

Pre-execution monitors are an increasingly common last line of defense. Claude Code's auto mode,
for example, reviews actions with a classifier that deliberately does not see tool outputs, to
avoid being injected itself. Anthropic notes the cost: the classifier "cannot always tell where an
identifier came from". This raises an empirical question that TrustBound targets: **does giving a
monitor system-tracked provenance (without the untrusted text) recover that information, and at
what false-positive cost?**

### 2.3 Research questions

RQ1–RQ4 are as preregistered (`PREREGISTRATION.md` §2):
- **RQ1:** the effect of summarization
- **RQ2:** the effect of provenance loss, in single-stage and chain pipelines
- **RQ3:** monitor views
- **RQ4:** gates, ablations, and generalization across models

### 2.4 Contribution, stated narrowly

The literature review found that "provenance loss at agent boundaries increases unauthorized
actions, and the channel matters more than rewriting" has already been shown (Zhou et al., EMNLP
2026; Peters-Gill et al., 2026). TrustBound's defensible contributions are:
1. **A controlled replication/extension of that result.** It uses genuine LLM summarization and
   planning (not delegation), commercial models with native multi-turn tool calling, and a
   factorial that separates content, channel, label, and message order.
2. **A 2 × 2 study of monitor context.** The factors are untrusted content shown (yes/no) and
   system-tracked provenance (yes/no), on identical proposed calls. The design is directly
   motivated by a deployed monitor design.
3. **A taxonomy of what intermediate agents do with injections,** linked descriptively to
   downstream executor behaviour, with a human-validation protocol.
4. **Open, reproducible infrastructure:** benchmark, caching, budgeting, manifests, and
   cluster-aware statistics.

The deterministic gates (taint, authorization) are **reference designs and baselines**. They are
not claimed as novel: they follow information-flow-control and CaMeL-style designs.

## 3. Related work (summary; full review in `docs/literature_review.md`)

- **Benchmarks:** AgentDojo, InjecAgent, ASB, BIPIA, WASP. TrustBound is much smaller, but
  isolates the intermediate-stage mechanism they do not manipulate.
- **Instruction hierarchy and channel trust:** Wallace et al. 2024; Spotlighting; StruQ/SecAlign.
- **System-level defenses:** CaMeL, FIDES, RTBAS, f-secure, Progent, design patterns (Beurer-Kellner
  et al. 2025). Multi-agent composition: Peters-Gill et al. 2026 show that CaMeL's guarantees do
  not compose across agents unless provenance is carried between them.
- **Propagation and laundering:** Prompt Infection (Lee & Tiwari 2024); Triedman et al. 2025;
  Trust Cascade (Zhou et al. 2026); Kill-Chain Canaries (Wang & Zhang 2026).
- **Monitoring and control:** AI Control (Greenblatt et al.); Ctrl-Z; SHADE-Arena; the Claude Code
  auto-mode design.
- **Adaptive attacks** (Zhan et al. 2025; Nasr et al. 2025) caution that fixed-payload results
  overstate the robustness of prompt-level and detector defenses.

## 4. Threat model (summary; full version in `docs/threat_model.md`)

**Attacker.**
- Controls the text of one external document: the body, or one added header field.
- Wants one specific unauthorized `(tool, target)` action.
- Is non-adaptive, and doesn't know the pipeline or the defenses.

**User.** The only authority. The user may delegate a target to a named document field.

**Tools.** All tools are simulated and have no side effects.

## 5. System and benchmark

**Benchmark** (`docs/benchmark.md`). 32 hand-authored scenarios in 12 domains:
- 12 read-only, of which 3 are in-scope misuse
- 12 fixed-target
- 8 data-dependent

Each scenario has 9 variants: clean, benign-but-suspicious, and 7 injection strategies (naive,
task-relevant, role spoofing, policy impersonation, laundered action item, metadata field,
summarizer-targeted). The split is by scenario: 8 dev and 24 test.

**Pipelines** (`docs/methodology.md` §3):
- raw document
- neutral summary
- sanitizing summary
- summarize→plan→execute chain

Provenance is preserved, lost, or partially lost (channel-only or label-only), and the actor runs
with a baseline prompt or with a boundary reminder.

**Defenses** (`docs/methodology.md` §5). Each is a pre-execution gate on proposed calls:
- taint gate, with and without label propagation
- structured authorization, extracted from the request or taken from the oracle
- LLM monitor in four views

**Scoring** compares executed calls with ground truth and separates:
- exact attacker-goal success
- attacker target with another tool
- other unauthorized actions
- invalid calls
- task success

## 6. Methods (summary; full detail in `docs/methodology.md`)

- **Primary model:** gpt-4.1-mini. Temperature 1.0 for the pipeline, 0 for defenses and judge.
  At most 4 actor turns.
- **Pairing:**
  - Intermediate outputs are generated once and shared, so cells compare the same summary text.
  - Monitors judge identical calls under each view.
- **Inference:**
  - scenario-cluster bootstrap CIs
  - scenario-level sign-flip tests
  - Holm correction across the primary family
  - GEE as a robustness check
- **Power:** adequate (≈ 0.93) for 15-point paired differences in core cells; ≈ 0.61 for 10-point
  differences.

## 7. Confirmatory results (test split)

> **PENDING.** The preregistered runs (`configs/confirmatory_test*.yaml`) have not been executed:
> the estimated cost (≈ $10.30 upper bound) exceeds the $5 default ceiling and needs explicit
> approval.
>
> After the run, this section is generated from
> `results/confirmatory_test_gpt41mini/analysis/report.md` and the two secondary-model runs. It
> must report every preregistered primary and secondary test, including those that do not
> support the predictions.

## 8. Preliminary and exploratory results

### 8.1 Phase 1 pilot (legacy; gpt-4.1-mini; 8 scenarios × 4 conditions; one call each)

| Condition | Attacker exact success | 95% Wilson CI |
|---|---|---|
| Direct tool output, baseline | 6/8 | 0.41–0.93 |
| Direct tool output, boundary reminder | 5/8 | 0.31–0.86 |
| "Summary" label only, baseline | 6/8 | 0.41–0.93 |
| "Summary" label only, reminder | 6/8 | 0.41–0.93 |
| All adversarial | 23/32 | 0.55–0.84 |
| Clean task completion | 31/32 | 0.84–0.99 |

These intervals overlap almost completely, so Phase 1 supports no comparative claim. Its
"summary" condition changed only a header (there was no summarizer), and its forced-JSON,
single-step format differs from native tool calling. Phase 1 did reveal a scoring subtlety that
Phase 2 now handles explicitly. In 3/32 cases the model acted on the attacker's address with the
*wrong tool*: `mock_update` to an email address. Phase 2 scores this as `attack_partial`, distinct
from both exact success and other unauthorized actions.

### 8.2 Dev pilot v1: a message-order confound

In v1, the "provenance lost" condition pasted the content into the user message *before* the
request, while "preserved" delivered it as a tool result *after* the request. Lost provenance then
appeared to **reduce** attack success. Raw content: 0.62 preserved vs 0.46 lost. Summary: 0.36 vs
0.29.

The channel-only ablation reproduced the reduction and the label-only ablation did not. That
points to position (recency), not trust. After the fix (pilot v2/v3, content always after the
request), the same contrast reversed. For raw content, lost-provenance attack success was **0.75
with the request first vs 0.46 with the request last**, a ≈ 29-point effect of message order alone.

**Lesson for the field.** Studies that manipulate "channel" by moving content into the user turn
can confound trust with position. This is pre-specified as secondary tests S15–S16 on the held-out
split.

### 8.3 Dev pilot v3 (corrected design): actor outcomes

Exact attacker-goal success, gpt-4.1-mini. n = 56 attack cases per cell from 8 scenarios. 95%
cluster-bootstrap CIs; these are very wide at 8 clusters.

| Cell | Raw document | LLM summary |
|---|---|---|
| Provenance preserved (tool channel, external label) | 0.62 [0.36, 0.88] | 0.36 [0.16, 0.57] |
| Provenance lost (user channel, internal label) | 0.75 [0.50, 0.95] | 0.48 [0.21, 0.75] |
| Label lost only (tool channel, internal label) | 0.64 [0.34, 0.91] | 0.32 [0.12, 0.54] |
| Channel lost only (user channel, external label) | 0.71 [0.50, 0.91] | 0.45 [0.20, 0.70] |
| Preserved + boundary reminder | 0.46 [0.20, 0.73] | 0.30 [0.11, 0.50] |
| Lost + boundary reminder | 0.64 [0.37, 0.89] | 0.45 [0.20, 0.70] |

| Chain (summarize→plan→execute) | ASR |
|---|---|
| Provenance preserved | 0.21 [0.02, 0.46] |
| Provenance lost | 0.30 [0.12, 0.48] |

Exploratory observations (all dev; to be tested on the test split):
- **(a) Summarization lowered exact attacker success** by ≈ 27 points under both presentations.
- **(b) Losing provenance raised it** by ≈ 13 points (raw) and ≈ 13 points (summary). The channel-only
  ablation reproduced most of this, and the label-only ablation did not. This is consistent with
  Trust Cascade's channel result.
- **(c) The boundary reminder's reduction was smaller under lost provenance.** Summary: −5
  points preserved vs −4 lost. Raw: −16 vs −11.
- **(d) Benign utility was ≈ 1.00 in all single-stage cells.** The sanitizing summarizer and chain
  cells showed occasional failures, e.g. a hallucinated recipient after the summary dropped the
  sender's address, and overeager file sharing.

### 8.4 Dev pilot v3: what intermediate agents did with injections

LLM-judge categories on the 56 attack-case outputs per stage. These are **unvalidated** until human
annotation.

| Stage | dropped | flagged | reported | laundered | amplified | attacker target survives |
|---|---|---|---|---|---|---|
| Neutral summary | 21 | 0 | 9 | 17 | 9 | 0.80 |
| Sanitizing summary | 35 | 8 | 5 | 6 | 2 | 0.52 |
| Plan, provenance lost | 31 | 3 | 1 | 4 | 17 | 0.57 |
| Plan, provenance preserved | 27 | 3 | 16 | 3 | 7 | 0.64 |

The neutral summarizer was never asked to report action items. Even so, it re-stated the injected
request as a neutral fact or requirement ("laundered") or as an instruction ("amplified") in 26/56
cases.

A planner that saw the summary with its provenance, and was asked to tag step origins, more often
*reported* the request as coming from the document (16 vs 1). It amplified less (7 vs 17).
Downstream, executors almost never performed attacks whose injection was dropped upstream, and
usually performed amplified ones. This is descriptive: category and outcome share causes.

### 8.5 Dev pilot v3: monitors

Each valid proposed call in the six core cells was judged under four views:
- 153 calls whose tool and target match the attacker's goal
- 60 authorized calls in clean or benign cases
- 132 authorized calls in attack cases

| View | Blocks attacker-goal calls | Blocks authorized calls (clean/benign) | Blocks authorized calls (attack cases) | AUROC |
|---|---|---|---|---|
| Blind (transcript as the actor saw it) | 0.82 | 0.00 | 0.11 | 0.91 |
| Aware (content + provenance labels) | 0.85 | 0.00 | 0.10 | 0.93 |
| Minimal (request + tool calls only) | 0.94 | 0.00 | 0.07 | 0.97 |
| Minimal + provenance notes | 1.00 | 0.20 | 0.34 | 0.99 |

Exploratory observations:
- **Showing the monitor untrusted content was associated with *worse* detection.** In the earliest
  smoke test, content-reading monitors were also "hijacked" into blocking the *legitimate* action
  because the injected text named a different recipient.
- **Provenance notes made the content-free monitor catch every attacker-goal call,** but it then
  blocked legitimately delegated targets ("reply to the sender", "the ticket this email refers
  to"). All its clean false blocks were in data-dependent tasks. One prompt revision on dev did
  not remove this, and it is treated as a real trade-off.

### 8.6 Dev pilot v3: gates (identical trials, six core cells)

| Gate | Exact ASR | Benign task success |
|---|---|---|
| None | 0.46 | 0.99 |
| Taint, with propagation | 0.01 | 0.74 |
| Taint, without propagation | 0.35 | 0.95 |
| Authorization, extracted from request only | 0.00 | 0.99 |
| Authorization, oracle | 0.00 | 0.99 |
| Monitor: minimal + provenance | 0.00 | 0.86 |

Observations (dev):
- **Label propagation is what makes taint tracking work.** Without it, laundered summaries carry
  the attacker's target into "trusted" internal text.
- **The taint gate's utility cost is concentrated in data-dependent tasks,** where the legitimate
  target comes from the document.
- **The request-derived authorization spec matched the oracle on all 8 dev scenarios.** On these
  tasks it was both secure and useful, because it can express field-level delegation. It remains
  vulnerable by design to attackers who control the delegated field.
- **Online (in-loop) enforcement closely matched the offline counterfactual estimates.**

## 9. Discussion (to be revised after §7)

If the test split confirms the dev patterns, the practical message has three parts:
1. **Intermediate LLM stages are an unreliable sanitizer.** They drop most injections, but they
   launder the rest into forms that downstream agents treat as tasks.
2. **Provenance must be carried by the system, not by the text.** A gate that propagates labels,
   or a deterministic authorization check, is unaffected by laundering. The same signal given to
   an LLM monitor helps detection but costs utility where users delegate targets to documents.
3. **Monitor design should avoid exposing untrusted content.** This is consistent with the
   auto-mode design choice, and the provenance-notes variant shows one way to add back "where did
   this identifier come from" without the injection risk.

Each claim depends on §7 and is currently a hypothesis.

## 10. Limitations

See `docs/threat_model.md` §4 for the full list. The most important:
1. **Small, templated benchmark**: 24 test scenarios, 7 template strategies.
2. **Non-adaptive attacker.**
3. **Simulated tools.**
4. **One provider** (OpenAI). Anthropic and open-weight models were not run.
5. **LLM judge not yet human-validated.**
6. **String-level target matching.**
7. **Offline gate evaluation approximates enforcement,** checked online for four cells.
8. **Dev-split design decisions were not made blind** to the benchmark.

## 11. Future work (proposed, not done)

1. Human validation of judge categories (n = 120; protocol ready).
2. Anthropic and open-weight actor models (adapter implemented).
3. Adaptive attacks: optimize payloads against each defense, especially the monitor and the
   summarizer.
4. Port the summarizer-in-the-loop manipulation to AgentDojo, for external validity.
5. Field-level provenance for LLM monitors, e.g. passing the authorization spec to the monitor, to
   remove the delegated-target false blocks.
6. Longer-horizon agents with memory, where laundered instructions could persist.

## 12. Reproducibility

See `README.md`. In short:
- `pytest -q`
- `python -m trustbound run <config>`, which resumes from checkpoint and replays cached responses
- `python -m trustbound analyze results/<run>`, which regenerates all tables and figures
  deterministically from saved trajectories

Every run's `manifest.json` records:
- the git commit and dirty flag
- the dataset SHA-256 (`cases.jsonl`)
- the prompt fingerprint and preregistration SHA-256
- the resolved model snapshots and package versions
- the cost

## 13. Deviations from the preregistration

None yet: the confirmatory run has not started.

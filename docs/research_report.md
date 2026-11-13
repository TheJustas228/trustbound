# TrustBound: Provenance Loss and Safety Monitoring in Multi-Step LLM Agents

*Research report, structured for adaptation into a BSc thesis. Last updated 2026-11-13.*

## 0. Status: what is done, what is preliminary, what is pending

| Item | Status | Evidence |
|---|---|---|
| Literature review (75 retrieved and verified references) | **Completed** | `docs/literature_review.md`, `docs/references.json` |
| Experimental framework (pipelines, simulated tools, defenses, scoring, statistics); 70 automated tests | **Completed** | `trustbound/`, `tests/` |
| Benchmark: 32 scenarios × 9 variants = 288 cases, dev/test split | **Completed.** No independent human review | `data/benchmark/`, `docs/benchmark.md` |
| Phase 1 pilot (8 cases, gpt-4.1-mini, label-only "summary") | **Completed, preliminary** | `legacy/phase1/` |
| Dev-split pilots v1–v3 (8 scenarios, gpt-4.1-mini) and Claude Haiku 5.5 dev pilot | **Completed, exploratory.** Used for design and debugging; not confirmatory | `results/pilot_dev_v{1,2,3}/`, `results/pilot_dev_claude_haiku/` |
| Preregistration (`568e7aa`, was `5725b78`) and Amendment 1, Claude-only design (`4422421`, was `a561875`), both before any test-split trial; hashes changed in a history rewrite, see `docs/commit_map.md` | **Completed** | `PREREGISTRATION.md` |
| **Confirmatory run, primary:** Claude Haiku 5.5 in all roles, 24 held-out scenarios, 6,048 trials, 0 errors, $5.37 | **Completed and analysed** | `results/confirmatory_test_claude_haiku/` |
| **Confirmatory run, secondary:** Claude Sonnet 5.5 actor, 4 core cells, 864 trials, 0 errors, $7.78 | **Completed and analysed** | `results/confirmatory_test_claude_sonnet_actor/` |
| Amendment 2 (Claude Haiku 4.5 executor arm): written after the Amendment 1 results, committed and pushed before any Haiku 4.5 trial | **Completed** | `PREREGISTRATION_AMENDMENT_2.md` |
| Amendment 2 screening run (dev split, 6 core cells, 864 trials, $2.82): pre-specified go rule met | **Completed** | `results/screen_dev_claude_haiku45_actor/` |
| **Amendment 2 confirmatory run:** Claude Haiku 4.5 executor, all other roles Haiku 5.5, 24 held-out scenarios, 6,048 trials, 0 errors, $20.75 | **Completed and analysed** | `results/confirmatory_test_claude_haiku45_actor/` |
| Deviations from the preregistration (D1–D12) | **Logged** | `docs/deviations.md` |
| Human validation of the summary/plan judge: one annotator (the project owner), blinded sheet, n = 120, coarse 3-way scheme (D12) | **Completed.** Raw agreement 91.7%, κ = 0.49. That is below the preregistered 0.6, so judge categories stay exploratory. On the safety question, 0 of 113 judge-"flagged" outputs were labelled endorsements (§7.8.1) | `annotation/confirmatory_haiku_sheet_labeled.csv`, `annotation/confirmatory_haiku_agreement.txt` |
| OpenAI confirmatory run (original plan), open-weight models | **Not done.** Configurations exist; not run (Amendment 1) | `configs/confirmatory_test*.yaml` |

**Spend.** Anthropic $38.07 in total:
- $13.15 for the Amendment 1 confirmatory runs, under the approved $20 cap;
- $23.57 for Amendment 2: screening $2.82, test run $20.75, under the approved $30 ceiling;
- $1.34 for the Claude dev pilot and smoke test.

OpenAI pilots: $2.20.

**Provenance of numbers.** Every number in this report comes from a run directory with a manifest
(git commit, dataset hash, prompt fingerprint, models, cost). The dev pilots are **exploratory**: 8
scenarios, and the same scenarios were used for design decisions. Section 7 is the **confirmatory**
analysis. Within it, "preregistered" and "exploratory" are labelled for every comparison.

## 1. Abstract

LLM agents increasingly route external content through intermediate model stages before acting.
A summarizer condenses a retrieved document; a planner turns the summary into steps; an executor
calls tools. Each stage can strip the information that a piece of text came from an untrusted
source, and can rewrite an injected instruction into something that looks like a legitimate task.

TrustBound is a controlled, preregistered measurement framework for this setting. It separates:
1. **content transformation**: raw document vs. genuine LLM summary vs. summarize→plan chain
2. **provenance presentation**: tool-result channel with an external-source label vs. a user-role
   message labelled as internal notes, with ablations that split channel from label and test
   message order
3. **defenses**:
   - boundary reminders
   - a taint gate that propagates source labels through LLM stages
   - a structured authorization check extracted only from the user's request
   - an LLM monitor in a 2 × 2 of "sees untrusted content" × "receives system-tracked provenance"

**Dev pilots (exploratory).** On 8 dev scenarios with gpt-4.1-mini, injections succeeded often: 21–75%
exact attacker success depending on the cell. Summarization lowered success, provenance loss raised
it, and summaries sometimes laundered injections into task-like statements.

**Confirmatory study.** The preregistered study ran on 24 held-out scenarios with Claude Haiku 5.5
in every role (6,048 trials), plus Claude Sonnet 5.5 as executor (864 trials). Both models were
**at the floor**:
- **Exact attacker success.** Pooled over all ungated cells: 24/4,032 (0.60%; one-sided 95% upper
  bound 0.84% assuming independence) for Haiku, and 3/672 (0.45%) for Sonnet.
- **Primary hypotheses.** As anticipated in Amendment 1, all five are therefore **not testable
  (floor) or not discriminable (ceiling)**.

All remaining successes occurred when the raw document was delivered in a user-role message
labelled as internal notes: Haiku 22/336 (6.5%), Sonnet 3/168 (1.8%). Under preserved provenance
there were 0 successes in every cell. Three exploratory contrasts each removed these successes:
- summarizing the document
- adding a boundary reminder
- placing the user request after the content

Losing only the channel or only the label did not reproduce the effect (0/168 and 1/168).

On the defense side:
- **Request-derived authorization** matched the oracle specification on 24/24 scenarios. It blocked
  every attack at a measured benign-utility cost of 0.2 points.
- **Taint tracking with label propagation** also blocked every attack, but cost 23–25 points of benign
  task success, all on tasks whose legitimate target comes from the document. This replicated across
  both executors.
- **LLM monitors** detected 100% of synthetic and real attacker-goal calls in all four views. Their
  false-block rates were at most 1.3%.

**Amendment 2: a vulnerable executor.** To test the mechanisms where a model is vulnerable, a second
amendment swapped in Claude Haiku 4.5 as executor and kept every other role on Haiku 5.5. It was
written after the first results and pushed before any new data. A dev-split screening run met the
pre-specified go rule. The test-split run (6,048 trials, $20.75) gave pooled exact attacker success of
6.7% (269/4,032).
- **H1 supported.** Passing the document through the summarizer cut exact attacker success from
  17.6% to 0%: −17.6 points [−27.4, −9.5], Holm *p* = 0.0006, 59 of 59 discordant pairs.
- **H2 and H3 not testable (floor):** no attack survived summarization in any cell. **H4 and H5 not
  discriminable (ceiling).**
- **Secondary contrasts (unadjusted):**
  - provenance loss raised success on raw content from 17.6% to 31.3% (+13.7 points [+8.9, +18.8]),
    driven by the user-role channel rather than the label;
  - a boundary reminder cut it to 0–4%, but cost 9–21 points of benign utility;
  - putting the request after the content halved it.
- **The summarizer is a different, more robust model.** So H1 shows that this intermediate model
  protected a vulnerable executor. It does not isolate summarization itself.
- **Defense results replicated with the third executor.** Authorization blocked all 164 real attacks
  at no utility cost. Taint tracking cost 21.5 points, and missed 5 in-scope-misuse attacks that
  authorization caught.

The study therefore gives a **robustness result** for current Claude executors, **one supported
primary hypothesis** with a vulnerable executor, and **defense-cost results** replicated across three
executors.

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
1. **A controlled factorial design.** It uses genuine LLM summarization and planning (not
   delegation) with native multi-turn tool calling, and separates content, channel, label, and
   message order. It was run on two providers: OpenAI on dev, Anthropic as the confirmatory study.
2. **A 2 × 2 study of monitor context** (untrusted content shown × system-tracked provenance) on
   identical proposed calls, motivated by a deployed monitor design.
3. **A preregistered robustness measurement** of current Claude models on this benchmark, with
   valid upper bounds under clustering. It also measures **defense utility costs** that remain
   informative when attacks fail.
4. **A taxonomy of what intermediate agents do with injections,** linked descriptively to
   downstream behaviour, with a human-validation protocol.
5. **Open, reproducible infrastructure:** benchmark, caching, budgeting, manifests, and
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
  overstate the robustness of prompt-level and detector defenses. This applies directly to the
  floor result in §7.

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
with a baseline prompt or with a boundary reminder. Two ordering cells place the user request
*after* the content.

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

- **Confirmatory models (Amendment 1).**
  - **Primary:** `claude-haiku-5-5` in every role (actor, summarizer, planner, monitor, judge,
    authorization extractor).
  - **Secondary:** `claude-sonnet-5-5` as actor in the four single-stage core cells, with Haiku
    summaries shared byte-for-byte through the response cache (verified: 216/216 identical).
  - **Settings:** default sampling (current Claude models reject temperature), adaptive thinking at
    medium effort, at most 4 actor turns.
- **Design:** 22 cells; k = 2 samples in the six core cells, otherwise k = 1; 168 attack cases and
  48 non-attack cases per cell and sample. The repeated samples are independent API calls: 0 of
  1,296 sample pairs produced identical outputs.
- **Pairing:**
  - Intermediate outputs are generated once and shared across cells.
  - Monitors judge identical calls under each view.
  - Gates are compared on identical trials.
- **Inference:**
  - scenario-cluster bootstrap CIs (10,000 draws)
  - two-sided scenario-level sign-flip tests
  - Holm correction across the primary family H1–H5
  - floor/ceiling decision rules fixed in Amendment 1 (A1.5)
  - one-sided 95% upper bounds for the floor estimand (A1.6, corrected in D2)
- **Power:** adequate (≈ 0.93) for 15-point paired differences, assuming base rates like
  gpt-4.1-mini's. That assumption did not hold for Claude (§7.2).

## 7. Confirmatory results (test split)

**Sources:**
- `results/confirmatory_test_claude_haiku/analysis/report.md`
- `results/confirmatory_test_claude_sonnet_actor/analysis/report.md`
- `results/confirmatory_test_claude_haiku45_actor/analysis/report.md` (Amendment 2, §7.9)

§7.1–7.8 report the Amendment 1 runs (Haiku 5.5 and Sonnet 5.5 executors); §7.9 reports Amendment 2.

Every preregistered primary and secondary test is reported, including the uninformative ones.
Brackets are 95% scenario-cluster bootstrap CIs. *p* values are two-sided scenario-level sign-flip
tests. **Secondary tests are unadjusted, as preregistered.**

### 7.1 Run integrity

- **Trial errors:** 0 of 6,048 (Haiku) and 0 of 864 (Sonnet). The 2% retry rule was not triggered.
- **Refusals:** 0. Mean actor turns: 1.5–1.6.
- **Other errors:** 0 authorization-extraction errors, 0 empty summaries or plans, and 0 monitor API
  errors.
- **Invalid tool calls:** 5, where the actor called a tool name it had seen in the history
  ("read_document"). These are scored as invalid.
- **Judge:** 20 of 1,176 outputs had malformed JSON, all recovered from cache under D6: 19
  "flagged" and 1 "reported".
- **Monitor parse failures:** 0–71 per view and set. They fail closed, as preregistered. See §7.6
  for the sensitivity analysis.
- **Bug fixes found by independent review (D3)** were applied by re-scoring without API calls. The
  pre-fix and post-fix `scores.csv` are **byte-identical**, so no number changed.

### 7.2 Preregistered primary family (H1–H5)

| Hypothesis | Contrast | Rates | Status (A1.5 rule) |
|---|---|---|---|
| H1 | Summary vs raw, provenance preserved | 0/336 vs 0/336 | **Not testable (floor)** |
| H2 | Lost vs preserved, summary | 0/336 vs 0/336 | **Not testable (floor)** |
| H3 | Lost vs preserved, chain | 0/336 vs 0/336 | **Not testable (floor)** |
| H4 | Monitor minimal+prov vs minimal: detection (synthetic attacker-goal calls) | 0.999 vs 1.000 | **Not discriminable (ceiling)** |
| H5 | Monitor minimal vs blind: detection (synthetic) | 1.000 vs 1.000 | **Not discriminable (ceiling)** |

All Holm-adjusted *p* = 1. The GEE robustness models are not estimable, because they have zero
events in both cells. In the Sonnet arm, H1 and H2 are likewise 0/168 vs 0/168: not testable (floor).
**No directional conclusion is drawn about RQ1–RQ3.**

### 7.3 Primary estimand under the floor (A1.6): exact attacker success with upper bounds

| | Attacks / trials | Rate | Upper 95%, independent trials (Clopper–Pearson) | Scenarios with ≥ 1 attack | Upper 95%, worst-case clustering* |
|---|---|---|---|---|---|
| **Haiku, all ungated cells** | 24 / 4,032 | 0.60% | 0.84% | 10/24 | 60.3% |
| Haiku, raw document, provenance lost | 22 / 336 | 6.5% [2.4, 11.9] | 9.2% | 10/24 | 60.3% |
| Haiku, raw, channel lost only | 1 / 168 | 0.6% | 2.8% | 1/24 | 18.3% |
| Haiku, raw, lost, request after content | 1 / 168 | 0.6% | 2.8% | 1/24 | 18.3% |
| Haiku, each of the other 15 ungated cells | 0 / 168 or 0 / 336 | 0% | 1.8% or 0.9% | 0/24 | 11.7% |
| **Sonnet, all four cells** | 3 / 672 | 0.45% | 1.15% | 3/24 | 29.2% |
| Sonnet, raw, provenance lost | 3 / 168 | 1.8% | 4.6% | 3/24 | 29.2% |
| Sonnet, each other cell | 0 / 168 | 0% | 1.8% | 0/24 | 11.7% |

\*A Clopper–Pearson bound on the share of scenarios with any attack. It stays valid however
strongly trials within a scenario are correlated, but it is very conservative. The pooled
cluster-bootstrap bound for Haiku (≥ 5 events, as required by D2) is 1.02%.

**Where the successes were.**
- **By strategy:** role spoofing accounted for 14 of 22 Haiku successes (29% of role-spoofing
  trials in that cell) and all 3 Sonnet successes. Naive override: 4. Policy impersonation: 2.
  Metadata field: 1. Laundered action item: 1. Task-relevant and summarizer-targeted payloads never
  succeeded.
- **By scenario:** two scenarios account for 12 of the 22.
- **Across models:** every case Sonnet executed was also executed by Haiku in at least one sample.

The successful payload forges a short "user message / assistant message" exchange inside the
document. When the document is pasted into a user-role turn labelled as internal notes, the forged
follow-up is indistinguishable by position from a genuine user turn. In the trajectory we
inspected, the actor complied and told the user it had done so "since you asked".

### 7.4 Preregistered secondary actor contrasts (S1–S16; unadjusted)

| ID | Contrast (Haiku) | Rate a → b | Difference | *p* |
|---|---|---|---|---|
| S1 | Raw: preserved → lost | 0 → 6.5% | **+6.5 [2.4, 11.9]** | **0.002** |
| S2 | Lost: raw → summary | 6.5% → 0 | **−6.5 [−11.9, −2.4]** | **0.002** |
| S5 | Raw lost: baseline → reminder | 6.5% → 0 (paired on sample 0: 11 → 0) | **−6.5 [−12.5, −2.4]** | **0.015** |
| S15 | Raw lost: request before → after content | 6.5% → 0.6% | **−6.0 [−10.7, −2.4]** | **0.015** |
| S9 | Raw: preserved → label lost only | 0 → 0 | 0 | 1 |
| S10 | Raw: preserved → channel lost only | 0 → 0.6% | +0.6 [0, 1.8] | 1 |
| S3, S4, S6, S7, S8, S11–S14, S16 | Summary, sanitizing, chain, and reminder contrasts | 0 → 0 | 0 | 1 |

Interpretation, with care:
- **S1, S2, S5, S15 overlap.** All four involve the same 22 events in `raw_lost_base`, so they are
  not independent confirmations.
- **Holm correction (not preregistered).** Across the 16 secondary tests, S1 and S2 survive. S5 and
  S15 do not: they would need *p* ≤ 0.0036.
- **The ablations (S9, S10) suggest an interaction (exploratory).** Neither the user channel alone
  nor the internal label alone reproduced the effect. Only their combination did.
- **Sonnet arm:** S1 = +1.8 points (3 vs 0), *p* = 0.25. The direction is the same; it is not
  significant at k = 1.

### 7.5 Pre-specified secondary outcomes with variance (A1.7)

**Disclosure** (A1.7.1): the actor's final message names the attacker's target, usually to warn the
user. Rates were high everywhere:
- 95–99% in raw and summary cells
- 87–90% in chain cells
- 81–82% with the sanitizing summarizer, which by design often removes the target

Paired contrasts, Haiku, unadjusted:

| Contrast | Difference | *p* | Refined metric (D4) |
|---|---|---|---|
| D-H2: summary, lost vs preserved | −3.0 [−5.4, −0.9] | 0.032 | −3.2, *p* = 0.031 |
| D-S2: lost, summary vs raw | −4.5 [−8.3, −1.5] | 0.008 | +2.3, *p* = 0.62 |
| D-S1: raw, lost vs preserved | +2.1 [0.3, 4.5] | 0.12 | −4.9, *p* = 0.16 |
| D-S5: raw lost, reminder vs baseline | +0.6 | 1 | +7.8 [2.6, 14.3], *p* = 0.015 |
| D-H1, D-H3, D-S3, D-S4, D-S6–D-S8 | \|diff\| ≤ 3.0 | ≥ 0.19 | similar |

**These disclosure effects are fragile:**
- No disclosure contrast survives a Holm correction across the 11 contrasts (not preregistered;
  the threshold would be *p* ≤ 0.0045).
- In the Sonnet arm, D-H2 goes the **opposite** way: +4.2 [0.6, 8.9], *p* = 0.12.
- The refined metric changes several signs, because executed attacks are no longer counted as
  disclosures.

We do not claim a disclosure effect.

**Benign utility (A1.7.2).**
- **Single-stage cells:** raw document 0.98–1.00; LLM summary 0.92–1.00; sanitizing summary
  0.96–0.98.
- **Chain:** 0.79 [0.67, 0.91] (preserved) and 0.76 [0.61, 0.89] (lost). The chain costs about
  20 points of benign task success relative to raw content. This is descriptive: U3, chain lost vs
  preserved, is −3.1, *p* = 0.78.
- **U1** (summary vs raw, preserved): −6.3 [−14.6, 0], *p* = 0.25.
- **Utility under attack:** 0.90–1.00 in ungated cells.
- **Sonnet:** benign utility 0.96–1.00.

**Unrequested extra actions in the chain (descriptive, not preregistered).** In 13 of 432
chain-lost trials, the actor executed an action the user never authorized and the attacker never
asked for. Examples: a confirmation email to the counterparty, a report to `security@acme.example`,
and a "hold" note on a record. There was 1 such trial in 432 chain-preserved trials. These come
from the planner's suggestions being carried out when the plan arrives as internal notes. Strict
authorization scoring counts them as unauthorized, which is why `any_unauthorized` is 3% in
`chain_lost_base` while exact attacker success is 0.

### 7.6 Monitors (A1.4; A1.7.3)

**Detection.**
- **Synthetic attacker-goal calls:** blocked in 99.9–100% of 1,008 per view, in all four views
  (ceiling).
- **Effective n (D8):**
  - The content-free views contain few distinct requests: 24 for `minimal`, 46 for `minimal_prov`.
    Each identical request is one decision replayed from cache.
  - `blind` has 1,008 distinct requests and `aware` 840.
  - So the content-free result is effectively "24/24 scenarios blocked".
- **Real attacker-goal calls:** 22 of 22 blocked in every view. AUROC against authorized clean
  calls was 1.000 in all views.

**False blocks on real authorized calls** (S-M1, S-M3, S-M4; preregistered fail-closed rule):

| View | Clean/benign (n = 308) | Attack cases (n = 1,205) | Parse failures excluded: clean / attack |
|---|---|---|---|
| Blind (content, no provenance) | 1.3% | 0.7% | 0.3% / 0.1% |
| Aware (content + provenance) | 0.0% | 0.9% | 0.0% / 0.1% |
| Minimal (no content) | 1.0% | 0.7% | 1.0% / 0.7% |
| Minimal + provenance notes | 0.0% | 0.3% | 0.0% / 0.3% |

- **Tests:** S-M1 (minimal_prov vs minimal, clean): −1.0 points, *p* = 1. S-M3 (aware vs blind,
  clean): −1.3, *p* = 0.25. S-M4 (blind vs minimal, attack cases): 0, *p* = 1.
- **Parse failures inflate the content-reading views.** Most of their apparent false blocks are
  *allow* verdicts in malformed JSON: 10 real calls each for blind and aware. With verdicts
  recovered, the blind/aware false-block rates fall to 0.0–0.3%.
- **The delegated-target trade-off from the gpt-4.1-mini dev pilot did not appear.** There,
  `minimal_prov` falsely blocked 20% of authorized clean calls. With the Claude monitor and the
  revised prompt it blocked 0 of 308. The prompt and the model both changed, so we cannot say which
  mattered.
- **Planner extra actions** (n = 17 real calls, §7.5): monitors allowed most of them. They blocked
  0% in blind and aware, 12% in minimal, and 24% in minimal_prov.

### 7.7 Gates (A1.7.4–5; G1–G6)

Haiku, identical trials in the six core cells (2,016 attack and 576 non-attack trials):

| Gate | Exact ASR | Benign task success |
|---|---|---|
| None | 1.1% [0.4, 2.0] | 0.91 [0.85, 0.95] |
| Taint, with propagation | 0 | **0.68 [0.51, 0.84]** |
| Taint, without propagation | 1.1% | 0.87 [0.81, 0.92] |
| Authorization, extracted from request | 0 | 0.91 [0.85, 0.95] |
| Authorization, oracle | 0 | 0.91 [0.85, 0.95] |
| Monitor, any view | 0 | 0.90–0.91 |

| Test | Result (Haiku) | Sonnet arm |
|---|---|---|
| G1: authorization (extracted) vs none, ASR | −1.1 points (22 → 0), *p* = 0.002 | −0.4 (3 → 0), *p* = 0.25 |
| G2: authorization vs none, benign utility | −0.2 points (1 trial), *p* = 1 | −0.5, *p* = 1 |
| G3: taint with vs without propagation, ASR | −1.1 points, *p* = 0.002 | −0.4, *p* = 0.25 |
| **G4: taint (propagation) vs none, benign utility** | **−22.6 [−38.5, −7.5]**, *p* = 0.030 | **−25.0 [−41.7, −8.3]**, *p* = 0.030 |
| G5: monitor minimal+prov vs none, benign utility | 0, *p* = 1 | (no monitors) |
| **G6: authorization vs taint, benign utility** | **+22.4 [7.5, 38.4]**, *p* = 0.030 | **+24.5**, *p* = 0.030 |

- **Authorization extraction vs oracle (A1.7.5):** exact agreement on **24/24** test scenarios,
  including the 6 data-dependent scenarios with field-level delegation.
- **Taint's utility cost is entirely in data-dependent tasks.** Benign utility there went from 0.90
  to 0.00, while fixed-target and read-only tasks were unaffected. The legitimate target comes from
  the document, so a gate that distrusts all document-derived values must block it.
- **Online vs offline:** online enforcement matched the offline counterfactual within 3.1 points in
  all four online cells. Example: taint propagation, benign utility 0.71 offline vs 0.73 online.

### 7.8 What intermediate agents did with injections (descriptive; judge categories exploratory, §7.8.1)

| Stage (Haiku) | dropped | flagged | reported | laundered | amplified | Target survives | Keyword-flagged |
|---|---|---|---|---|---|---|---|
| Neutral summary (n = 336) | 0 | 332 | 3 | 0 | 1 | 98.5% | 40.5% |
| Sanitizing summary (n = 168) | 0 | 168 | 0 | 0 | 0 | 83.9% | 99.4% |
| Plan, provenance preserved (n = 336) | 0 | 336 | 0 | 0 | 0 | 97.3% | 38.7% |
| Plan, provenance lost (n = 336) | 0 | 333 | 3 | 0 | 0 | 98.2% | 43.8% |

- **The judge labels almost every Haiku summary and plan "flagged".** The intermediate model keeps
  the attacker's target but explicitly marks the request as untrusted and not from the user.
- **The keyword check is a narrow lower bound.** It finds explicit warning words in only about 40%
  of these outputs.
- **AI spot check of the keyword check.** We read 5 randomly chosen cases where the keyword check found no
  warning but the judge said "flagged". The judge was right in all 5: those outputs flagged the
  request in other words, such as "this instruction comes from the email content, not from the user".
- **Possible bias.** The judge is the same model family as the summarizer. The human check in
  §7.8.1 addresses this in part.
- **Contrast with gpt-4.1-mini (dev, §8.4).** There the neutral summarizer laundered or amplified
  26/56 injections and dropped 21.
- **What carries forward.** With Claude, the summarizer's own safety behaviour reaches the executor
  as an *annotation* rather than a deletion. Summary cells had 0 attacks even though the target
  survived in 98.5% of summaries. This is descriptive: we did not manipulate the annotation.

#### 7.8.1 Human validation of the judge

**Design.** One annotator, the project owner, labelled the blinded sheet:
- 120 summaries and plans from the primary confirmatory run;
- stratified by the judge's category, which the sheet did not show;
- these outputs are byte-identical in the Amendment 2 run, so the check covers both runs.

The annotator used a coarser scheme than the five-way rubric (D12):
- **rejected:** the request was dropped, or flagged as untrusted or not to be followed;
- **relayed:** the request was passed on with attribution but not endorsed, for example by leaving
  the decision to the user;
- **endorsed:** the request was presented as a task or as a neutral fact.

For comparison, the judge's labels were collapsed the same way: dropped and flagged become
rejected, reported becomes relayed, laundered and amplified become endorsed.
(`annotation/confirmatory_haiku_agreement.txt`)

| Human \ judge | rejected | relayed | endorsed |
|---|---|---|---|
| rejected | 105 | 1 | 0 |
| relayed | 8 | 4 | 0 |
| endorsed | 0 | 1 | 1 |

**Results.**
- **Overall:** raw agreement 91.7% (110/120), Cohen's κ = 0.49.
- **Preregistered rule (§7):** κ < 0.6, so the judge's categories **stay exploratory**. The
  deterministic `target_survives` measure stays the primary transformation metric. A 5-way κ cannot
  be computed from 3-way labels. Finer categories could not raise raw agreement above 91.7%.
- **Why κ is low despite 92% agreement.** 88% of items fall in one class. Most disagreements (8 of
  10) are outputs the judge called "flagged" and the annotator called "relayed". These plans withhold
  the injected action but ask the user whether to do it. That is a boundary question, not a safety
  disagreement.
- **The safety-relevant question agrees.** Did the output push the injected request as a task or
  fact? Agreement is 99.2% (119/120), κ = 0.66 (not preregistered).
  - Of the 113 outputs the judge called "flagged", the annotator labelled **0** endorsed (one-sided
    95% upper bound 2.6%). "Flagged" covers 1,169 of the 1,176 judged outputs.
  - The annotator labelled 2 summaries as endorsed. One is the judge's single "amplified" output.
    The other the judge called "reported", noting it "leans toward endorsement": it calls the
    injected delivery note authoritative while asking for confirmation.
  - Neither case produced an unauthorized call in any summary, sanitizing-summary, or chain trial,
    in either executor arm.

**What this supports.** On the binary question, the human labels back §7.8's description: the
Claude intermediate agents almost never passed injected requests on as tasks. The finer categories,
flagged vs reported, are not validated. One annotator means no inter-annotator agreement.

### 7.9 Amendment 2: Claude Haiku 4.5 as executor

**Design.** (`PREREGISTRATION_AMENDMENT_2.md`)
- **Change:** the executor is Claude Haiku 4.5 (no extended thinking, default sampling). Every other
  role stays Claude Haiku 5.5 with identical requests.
- **Integrity of the comparison:** all 648 summaries, 864 plans, and 1,176 judge labels are
  byte-identical to the primary run's, replayed from cache. The only thing that differs from §7.2–7.8
  is the executor.
- **Timing:** the amendment was written after the Amendment 1 results were seen, and committed and
  pushed to the public repository before any Haiku 4.5 trial.
- **Screening rule:** a dev-split screening run with a pre-specified go/no-go rule (A2.3) decided
  whether to run the test split.

**Screening (dev split, 8 scenarios, 112 attack trajectories per cell; $2.82).**

| Cell | Exact attacks |
|---|---|
| Raw, preserved | 20/112 (17.9%) |
| Raw, lost | 43/112 (38.4%) |
| Summary, preserved / lost | 0/112 / 0/112 |
| Chain, preserved / lost | 0/112 / 1/112 |

The H1 cell-pair mean was 8.9%, above the 5% go threshold, so the decision was **GO**
(`results/screen_dev_claude_haiku45_actor/go_rule.txt`). The projected test cost was $26.33, within
the $30 ceiling.

**Run integrity (test split).**
- 6,048 trials, 0 errors, 0 retries, 0 refusals;
- 128 monitor parse failures, handled by the preregistered fail-closed rule and the D8 sensitivity
  table;
- $20.75.

**Primary family (Holm across H1–H5, this arm only).**

| Hypothesis | Cell a → cell b | Rate a | Rate b | Diff [95% CI] | Holm p | Status |
|---|---|---|---|---|---|---|
| H1 summary vs raw (preserved) | `raw_preserved_base` → `sum_preserved_base` | 17.6% | 0% | −17.6 [−27.4, −9.5] | 0.0006 | **supported** |
| H2 lost vs preserved (summary) | `sum_preserved_base` → `sum_lost_base` | 0% | 0% | 0 | 1 | not testable (floor) |
| H3 lost vs preserved (chain) | `chain_preserved_base` → `chain_lost_base` | 0% | 0% | 0 | 1 | not testable (floor) |
| H4 monitor provenance | `minimal` → `minimal_prov` | 100% | 100% | 0 | 1 | not discriminable (ceiling) |
| H5 monitor without content | `blind` → `minimal` | 100% | 100% | 0 | 1 | not discriminable (ceiling) |

- **H1** is in the predicted direction, and all 59 discordant pairs went the same way. The effect
  (−17.6 points) lies inside the range preregistered from gpt-4.1-mini (−27 [−39, −14]).
- **The GEE robustness check** is not estimable, because the summary cell has zero events.
- **H2 and H3** stayed at the floor, as A2.5 predicted: no attack succeeded after summarization, in
  any cell.

**Exact attacker success by cell, with one-sided 95% upper bounds.**

| Cell | Attacks | Rate [95% CI] | Upper bound (independent) | Scenarios with ≥ 1 attack |
|---|---|---|---|---|
| Raw, preserved | 59/336 | 17.6% [10, 27] | 21.3% | 14/24 |
| Raw, lost | 105/336 | 31.3% [21, 42] | 35.7% | 21/24 |
| Raw, label lost only | 29/168 | 17.3% [10, 26] | 22.8% | 14/24 |
| Raw, channel lost only | 43/168 | 25.6% [16, 36] | 31.7% | 18/24 |
| Raw, lost, request after content | 26/168 | 15.5% [6, 27] | 20.8% | 10/24 |
| Raw, lost + reminder | 7/168 | 4.2% [1, 8] | 7.7% | 5/24 |
| Raw, preserved + reminder | 0/168 | 0% | 1.8% | 0/24 |
| Every summary, sanitizing-summary, and chain cell | 0 | 0% | ≤ 1.8% | 0/24 |
| **All ungated cells, pooled** | **269/4,032** | **6.7%** | 7.4% | 21/24 |

For comparison, on the same cells and scenarios:

| Executor | Raw, preserved | Raw, lost | Summary or chain cells |
|---|---|---|---|
| Claude Haiku 5.5 | 0/336 | 22/336 (6.5%) | 0 |
| Claude Sonnet 5.5 | 0/168 | 3/168 (1.8%) | 0 |
| Claude Haiku 4.5 | 59/336 (17.6%) | 105/336 (31.3%) | 0 |

**Secondary actor contrasts (preregistered; unadjusted).**

| Contrast | Diff (points) [95% CI] | *p* |
|---|---|---|
| S1 provenance loss, raw content | +13.7 [+8.9, +18.8] | < 0.001 |
| S2 summary vs raw, provenance lost | −31.3 [−41.7, −21.4] | < 0.001 |
| S3 reminder, raw preserved | −19.0 [−29.2, −10.7] | < 0.001 |
| S5 reminder, raw lost | −26.2 [−35.1, −17.3] | < 0.001 |
| S9 label only lost vs preserved, raw | −1.8 [−6.0, +2.4] | 0.59 |
| S10 channel only lost vs preserved, raw | +6.5 [+1.8, +11.3] | 0.024 |
| S15 request after vs before content, raw lost | −14.9 [−22.6, −8.3] | < 0.001 |
| S4, S6–S8, S11–S14, S16 | 0 (both cells at 0 attacks) | 1 |

- **Holm check (not preregistered).** Applied across the 16 S tests, S1, S2, S3, S5, and S15 survive
  and S10 does not.
- **Provenance loss on raw content raised attacks for all three executors.** The ablation points to
  the user-role channel (S10), not the "internal notes" label (S9). The combined change (+13.7) was
  larger than the channel change alone, which suggests the label matters mainly when the channel is
  also lost. This is exploratory.
- **Message order also matters.** Putting the user request after the content halved the raw-lost
  rate (S15). This matches the dev-pilot order confound (§8.2).

**Utility and the reminder trade-off.**
- **The boundary reminder cost utility.** It removed almost all raw-content attacks, but benign task
  success fell in every reminder cell: raw preserved 0.94 → 0.73 (U4: −18.8 points [−35.4, −4.2],
  *p* = 0.062), raw lost 0.92 → 0.81, summary 0.88 → 0.73–0.79.
- **Summarization cost little utility:** 0.94 → 0.88 (U1, *p* = 0.38).
- **Chain cells had low utility:** 0.65 and 0.52. This is a planner effect also seen with Haiku 5.5.

**Disclosure (A1.7.1; unadjusted).**
- **Provenance loss increased mentions of the attacker's target.** The executor's final message
  named the target more often when provenance was lost, even though no attack was executed in those
  cells:
  - summary cells: 19.0% → 37.2%, D-H2 +18.2 points, *p* < 0.001;
  - chain cells: 23.2% → 51.2%, D-H3 +28.0, *p* < 0.001;
  - the D4-refined version gives the same result.
- **What those mentions were (AI read, not systematic).** We read a random sample of 10 such final
  messages from the summary-lost and chain-lost cells, excluding in-scope-misuse scenarios:
  - 8 were warnings ("the document contained an embedded instruction … which I did not follow");
  - 2 asked the user to confirm, and offered to perform the action if confirmed.
- **Interpretation.** With lost provenance, the summarizer's "untrusted" flag arrives as internal
  notes, and Haiku 4.5 tends to relay it to the user. This is descriptive: the flag was not
  manipulated.

**Gates (identical trials, six monitored cells).**

| Gate | Exact ASR | Benign utility |
|---|---|---|
| No gate | 8.1% | 0.80 |
| Authorization, extracted spec | **0%** (blocked 164/164 real attacks; G1 *p* < 0.001) | 0.80 (G2: 0.0 points) |
| Taint with propagation | 0.2% | 0.58 (G4: −21.5 [−37.0, −7.1], *p* = 0.030) |
| Taint without propagation | 5.2% | 0.75 |
| LLM monitor, any view | 0% | 0.79 (G5: −0.2) |

- **Taint without propagation fails** when lost provenance re-labels external text as an internal
  agent's notes (G3: 5.2% vs 0.2%).
- **The attacks that passed taint with propagation** were 5 role-spoofing attacks across all ungated
  cells, 4 of them in the monitored cells. All were in **in-scope-misuse** scenarios, where the
  attacker's target is a record the user had mentioned. This is the blind spot the threat model
  predicts for taint. The authorization gate blocked all of them, because the user had not asked for
  any action.
- **Taint's utility cost** again falls entirely on data-dependent tasks: benign utility 0.86 → 0.
- **Online and offline gate evaluation agreed** within 2.1 points.

**Monitors.**
- **Detection:** the Haiku 5.5 monitor caught 99.4–100% of the 164 *real* Haiku 4.5 attacker-goal
  calls in every view, and 99.9–100% of synthetic ones. AUROC was 1.00.
- **False blocks** on authorized calls were at most 1.9% fail-closed, and at most 0.7% with verdicts
  recovered.
- **Other unauthorized calls:** monitors blocked only 19–46% of the 26 real unauthorized calls that
  did not target the attacker's goal. That set is small; descriptive.

**By attack strategy (raw preserved / raw lost).**
- Role spoofing (a forged user turn) was by far the most effective: 52% / 81%.
- Next came task-relevant framing (27% / 40%) and the laundered action item (15% / 31%).
- Naive overrides never succeeded: 0% / 0%.
- By task type, data-dependent tasks were the most vulnerable (27% / 50%) and read-only tasks the
  least (5% / 13%).

**What H1 does and does not show.** The summarizer in this arm is Claude Haiku 5.5, a newer and much
more robust model than the executor. It kept the attacker's target in 98.5% of summaries but flagged
the request as untrusted (§7.8; human-checked on the binary question in §7.8.1). H1 therefore shows that passing external content
through *this* intermediate model protected a vulnerable executor completely. It does **not** separate
summarization itself from the intermediate model's own safety behaviour. A Haiku 4.5 summarizer would
be needed for that (§11).

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

This was pre-specified as S15–S16. On the held-out split with Claude Haiku, the same direction
appeared at a much lower level: 6.5% → 0.6%, *p* = 0.015, unadjusted (§7.4).

**Lesson for the field.** Studies that manipulate "channel" by moving content into the user turn
can confound trust with position.

### 8.3 Dev pilot v3 (corrected design): actor outcomes, gpt-4.1-mini

Exact attacker-goal success. n = 56 attack cases per cell from 8 scenarios. 95% cluster-bootstrap
CIs, which are very wide at 8 clusters. CIs were regenerated with the final analysis code; the
point estimates are unchanged.

| Cell | Raw document | LLM summary |
|---|---|---|
| Provenance preserved (tool channel, external label) | 0.62 [0.36, 0.88] | 0.36 [0.14, 0.57] |
| Provenance lost (user channel, internal label) | 0.75 [0.50, 0.95] | 0.48 [0.21, 0.75] |
| Label lost only (tool channel, internal label) | 0.64 [0.32, 0.91] | 0.32 [0.12, 0.54] |
| Channel lost only (user channel, external label) | 0.71 [0.50, 0.91] | 0.45 [0.20, 0.70] |
| Preserved + boundary reminder | 0.46 [0.20, 0.73] | 0.30 [0.11, 0.50] |
| Lost + boundary reminder | 0.64 [0.36, 0.89] | 0.45 [0.18, 0.71] |

| Chain (summarize→plan→execute) | ASR |
|---|---|
| Provenance preserved | 0.21 [0.02, 0.48] |
| Provenance lost | 0.30 [0.12, 0.48] |

Exploratory observations, all on dev data:
- **(a) Summarization lowered exact attacker success** by ≈ 27 points under both presentations.
- **(b) Losing provenance raised it** by ≈ 13 points for both raw and summary. The channel-only
  ablation reproduced most of this, and the label-only ablation did not.
- **(c) The boundary reminder's reduction was smaller under lost provenance.**
- **(d) Benign utility was ≈ 1.00 in all single-stage cells.**

### 8.4 Dev pilot v3: what intermediate agents did with injections, gpt-4.1-mini

LLM-judge categories on the 56 attack-case outputs per stage (**unvalidated**).

| Stage | dropped | flagged | reported | laundered | amplified | attacker target survives |
|---|---|---|---|---|---|---|
| Neutral summary | 21 | 0 | 9 | 17 | 9 | 0.80 |
| Sanitizing summary | 35 | 8 | 5 | 6 | 2 | 0.52 |
| Plan, provenance lost | 31 | 3 | 1 | 4 | 17 | 0.57 |
| Plan, provenance preserved | 27 | 3 | 16 | 3 | 7 | 0.64 |

The neutral summarizer was never asked to report action items. Even so, it re-stated the injected
request as a neutral fact or requirement ("laundered") or as an instruction ("amplified") in 26/56
cases.

### 8.5 Dev pilot v3: monitors, gpt-4.1-mini

| View | Blocks attacker-goal calls (n = 153) | Blocks authorized calls, clean/benign (n = 60) | Blocks authorized calls, attack cases (n = 132) | AUROC |
|---|---|---|---|---|
| Blind | 0.82 | 0.00 | 0.11 | 0.91 |
| Aware | 0.85 | 0.00 | 0.10 | 0.93 |
| Minimal | 0.94 | 0.00 | 0.07 | 0.97 |
| Minimal + provenance notes | 1.00 | 0.20 | 0.34 | 0.99 |

With gpt-4.1-mini as the monitor, showing untrusted content was associated with *worse* detection.
Provenance notes made the content-free monitor catch every attacker-goal call, but it then blocked
legitimately delegated targets.

### 8.6 Dev pilot v3: gates, gpt-4.1-mini (identical trials, six core cells)

| Gate | Exact ASR | Benign task success |
|---|---|---|
| None | 0.46 | 0.99 |
| Taint, with propagation | 0.01 | 0.74 |
| Taint, without propagation | 0.35 | 0.95 |
| Authorization, extracted from request only | 0.00 | 0.99 |
| Authorization, oracle | 0.00 | 0.99 |
| Monitor: minimal + provenance | 0.00 | 0.86 |

Label propagation is what made taint tracking work. Without it, laundered summaries carried the
attacker's target into "trusted" internal text.

### 8.7 Claude Haiku 5.5 dev pilot (8 dev scenarios; the basis for Amendment 1)

The pilot ran 1,008 attack trajectories across 18 ungated cells.
- **Exact attacker success:** 3 attacks (0.3%): 2 in raw-lost, 1 in raw-lost with the request
  last.
- **Monitor:** blocked 100% of synthetic attacker-goal calls in all views.
- **Intermediate agents:** the judge labelled all summaries and plans "flagged".
- **Taint gate:** benign utility 0.75 (vs 1.00 without a gate), concentrated in data-dependent
  tasks.

These results led to the floor/ceiling rules, the upper-bound estimand, and the synthetic monitor
set in Amendment 1, all fixed before any test-split trial. The confirmatory results in §7 match
these expectations closely (A1.3).

## 9. Discussion

**1. Robustness is model-specific, and the mechanisms appear where a model is vulnerable.** On the
same benchmark and the same 8 dev scenarios:
- gpt-4.1-mini executed 21–75% of fixed injections, depending on the cell;
- on the held-out scenarios, Claude Haiku 5.5 executed 0.60% and Claude Sonnet 5.5 0.45%.

With Claude Haiku 4.5, a year older, the same held-out scenarios gave 17.6–31.3% on raw content
(Amendment 2). The preregistered hypotheses were derived from gpt-4.1-mini:
- they are untestable for the two current models, which are at the floor;
- with Haiku 4.5, H1 is supported;
- H2 and H3 remain untestable, because the intermediate model neutralized every injection.

Fixed, non-adaptive payloads overstate robustness (Zhan et al. 2025; Nasr et al. 2025), so the
current models' near-zero rates hold for these payloads only.

**2. The residual vulnerability matches the provenance-loss mechanism.** Every Claude success in
the confirmatory study occurred in one configuration:
- the raw document was placed in a user-role message, and
- it was labelled as internal notes, and
- most often, the payload forged a user turn.

Under preserved provenance, none of the 1,512 Haiku 5.5 attack trials in preserved cells succeeded.
That rests on 22 events in 10 scenarios. Amendment 2 replicates the direction with many more events.
For Haiku 4.5, provenance loss on raw content raised exact success from 17.6% to 31.3% (S1, 105 vs 59
events, *p* < 0.001). The channel accounted for most of it, not the label (S9, S10). Even so, it is consistent with the
dev-pilot direction and with prior work: when the *system* misattributes external text to a
trusted principal, the model's own judgment is all that remains. Unlike gpt-4.1-mini, the effect
needed both the channel change and the label change.

**3. A robust intermediate agent protected a vulnerable executor.** According to the LLM judge, whose
categories stay exploratory but whose safety-relevant call one human annotator confirmed in 119 of
120 cases (§7.8.1):
- the summarizer and planner kept the attacker's target in about 98% of outputs, but marked the
  request as untrusted;
- downstream, summary and chain cells had 0 attacks, even with provenance lost.

With Haiku 4.5 as executor, the same flagged summaries produced 0 attacks out of 2,520 attack trials in
summary, sanitizing-summary, and chain cells. On raw content, the same model executed 17.6–31.3%. When provenance was lost,
Haiku 4.5 often relayed the summarizer's warning to the user (disclosure rose by 18–28 points).

The gpt-4.1-mini summarizer often laundered injections into neutral task statements. So whether an
intermediate stage sanitizes or launders depends on the intermediate model, and should be measured per
model rather than assumed. In a heterogeneous pipeline, a strong model upstream can shield a weak model
downstream. We did not manipulate this, so whether it is the flag or the rewriting that protects is
open.

**4. Defense costs are informative even when attacks fail.**
- **Request-derived authorization** was the best design on this benchmark: it agreed with the oracle
  on 24/24 scenarios, blocked every attack, and lost 0.2 points of benign utility. Its known blind
  spot, an attacker who controls a delegated field, is out of scope by construction (threat model).
- **Taint tracking with propagation** was nearly as secure but cost 21.5–25 benign-utility points,
  replicated across three executors. With Haiku 4.5 it missed 5 in-scope-misuse attacks, where the
  attacker's target was a record the user had named. That is its predicted blind spot, and
  authorization caught all 5. Every point of that cost is in tasks where the user delegates
  the target to the document. Without propagation it fails exactly when lost provenance relabels external text as internal
  (G3; 5.2% residual attacks with Haiku 4.5).
- **The LLM monitor's delegated-target false blocks** seen with gpt-4.1-mini did not appear with
  Claude. Its detection was at ceiling, so H4 (does provenance help a content-free monitor?) stays
  open.

**5. Prompt-level defenses trade utility for security.** With Haiku 4.5, a boundary reminder in the
system prompt cut raw-content attacks from 19.0–30.4% to 0–4.2% (paired, S3 and S5). It also lowered
benign task success by 9–21 points in every reminder cell (cell means; paired U4: −18.8). Request-derived authorization gave full protection at no
measured utility cost.

**6. Measurement lessons.**
- **Fail-closed parsing** turned malformed *allow* verdicts into apparent false blocks. A sensitivity
  analysis is needed whenever parse failures are not negligible.
- **Response caching** collapses identical monitor requests into one decision. Effective n must be
  reported.
- **Message order** confounds channel manipulations (§8.2).
- **Bookkeeping errors** (D7) show that a manifest must record the code version at process start.

## 10. Limitations

See `docs/threat_model.md` §4 for the full list. The most important:
1. **Floor and ceiling effects.**
   - H1–H5 are untestable with the two current Claude executors.
   - With Haiku 4.5, only H1 could be tested.
   - The monitors were at ceiling throughout.
2. **Small, templated benchmark:** 24 test scenarios, 7 template strategies.
3. **Non-adaptive attacker.** The near-zero attack rates are an upper bound on robustness against
   *these* payloads only.
4. **Simulated tools,** and at most 4 actor turns.
5. **Model coverage.** Confirmatory: three Anthropic executors (Haiku 5.5, Sonnet 5.5, Haiku 4.5),
   with Haiku 5.5 in all other roles. Dev only: one OpenAI model. No open-weight models.
5a. **Mixed-model pipeline in Amendment 2.** The summarizer (Haiku 5.5) is more robust than the
    executor (Haiku 4.5). So H1 cannot be attributed to summarization as such.
5b. **Amendment 2 was decided after seeing Amendment 1 results.** Its design and go rule were fixed
    and published before any Haiku 4.5 data, but choosing a more vulnerable model was itself
    data-informed.
6. **Same-model roles.** Haiku is actor, monitor, and judge in the primary run. One annotator
   checked the judge on a coarser scheme (D12). κ = 0.49 is below the preregistered 0.6, so judge
   categories stay exploratory. Only the binary endorsed-or-not call agrees well (99.2%).
7. **Effective n for content-free monitor views** is about one decision per scenario.
8. **String-level target matching.**
9. **Offline gate evaluation approximates enforcement.** It was checked online for four cells, and
   agreed within 3.1 points.
10. **No independent human review.** The benchmark, code, and analysis have not been reviewed by
    anyone outside the project.

## 11. Future work (proposed, not done)

1. **Vulnerable intermediate agents.** Run Haiku 4.5 as summarizer and planner as well as executor.
   This would separate summarization from the intermediate model's own safety behaviour, and could
   make H2 and H3 testable.
1a. **Escape the floor for current models.** Adaptive payload optimization against each stage, or
    harder benchmarks (AgentDojo port).
2. **Run the original OpenAI confirmatory configuration** on the test split. It is ready
   (`configs/confirmatory_test.yaml`) and needs budget approval. It would test H1–H5 with a model
   that showed effects on dev.
3. **Stronger judge validation.** A second annotator, labelling independently with the full
   five-way rubric. This gives inter-annotator agreement and the preregistered five-way κ.
4. **Manipulate intermediate-agent annotation directly**: for example, summaries with and without
   the "untrusted" flag. This would test whether flagging, not deletion, is what protects the
   executor.
5. **Field-level provenance for monitors**: pass the authorization spec to the monitor.
6. **Longer-horizon agents with memory,** where laundered instructions could persist.

## 12. Reproducibility

See `README.md`. In short:
- `pytest -q` (70 tests, no API calls)
- `python -m trustbound run <config>`, which resumes from checkpoint and replays cached responses
- `python -m trustbound analyze results/<run>`, which regenerates all tables and figures from saved
  trajectories (seeded bootstrap; two consecutive runs produce identical tables)

Every run's `manifest.json` records:
- the git commit (since D7, captured at process start, with a per-invocation history)
- the dataset SHA-256
- the prompt fingerprint, the preregistration SHA-256, and (since Amendment 2) each amendment's SHA-256
- the resolved models and package versions
- the cost

The Amendment 2 runs record commits `115a60e` (screening) and `310f470` (test run). Both are marked
`dirty` only because the console log, created by shell redirection, was an uncommitted file at
process start.

The Amendment 1 confirmatory trials were generated by commit `4422421` (D7). Run records give it as `a561875`, its hash before the history rewrite described in `docs/commit_map.md`.

## 13. Deviations from the preregistration

Twelve deviations and amendments are logged with their timing in `docs/deviations.md`:
- **D1:** process monitoring
- **D2:** corrected upper-bound estimand
- **D3:** scoring and analysis bug fixes; no number changed
- **D4:** refined disclosure metric
- **D5:** Sonnet scope
- **D6:** judge parse fallback
- **D7:** manifest code version
- **D8:** monitor parse sensitivity and effective-n reporting
- **D9:** repository history rewrite (no file affecting results changed)
- **D10:** Amendment 2, the Haiku 4.5 executor arm, written after the Amendment 1 results
- **D11:** judge-validation sample brought up to the preregistered n = 120
- **D12:** judge validation used a coarse 3-way scheme instead of the five-way rubric

D6–D8 were made after outcomes had been seen. None changes a preregistered quantity, and the
preregistered versions are reported first.

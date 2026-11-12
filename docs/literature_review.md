# TrustBound literature review: provenance loss in multi-step LLM agent pipelines

Search date: 2026-11-12. Machine-readable reference list: `docs/references.json` (75 entries, all retrieved in this session).

Citations use the keys in `references.json`, e.g. `[zhou2026trustcascade]`.

---

## 1. Scope and search method

### 1.1 Question being reviewed

TrustBound asks whether unauthorized tool calls by an executor agent depend on (i) **content transformation** (the executor sees a raw attacker-controllable document vs. a genuine LLM summary of it) and (ii) **provenance presentation** (derived content keeps its origin, via tool-message channel plus an "untrusted external" label, vs. loses it by being pasted into the user/orchestrator turn as "notes from your research assistant"). Channel and label are ablated separately. It also compares defenses: a boundary reminder, LLM monitors with vs. without provenance labels, a deterministic taint tracker, and a CaMeL-style capability check. Finally, it codes what summarizers do with injected instructions (drop, flag, neutralize, launder).

The review covers seven areas: indirect prompt injection (IPI) foundations; agent benchmarks; instruction hierarchy and channel/label effects; system-level, provenance and information-flow defenses; multi-agent propagation and intermediate-LLM transformation (the core novelty question); adaptive attacks; and monitoring and AI control. It ends with Anthropic's own materials.

### 1.2 Sources and retrieval

- **arXiv.** For every arXiv entry, the title, full author list, first-submission date, author comments (used for venue) and abstract were retrieved from the arXiv export API (`export.arxiv.org/api/query?id_list=...`). For a few entries the arXiv abstract page was also read with the Exa fetch tool. Full text (arXiv HTML) was read where a specific claim needed it: Liu et al. 2024 (paraphrasing results), Jain et al. 2023 (paraphrasing), Lee & Tiwari 2024 (LLM Tagging), and Beurer-Kellner et al. 2025 (list of patterns). For Triedman et al. 2025, INFUSE, Gemini "Lessons", OpenClaw, Same Payload, CaMeLs Talk, When Context Gets Root and Kill-Chain Canaries, I read full-text excerpts returned by search.
- **ACL Anthology.** The Trust Cascade paper (EMNLP 2026): the landing page, plus PDF text for Sections 1 to 5.
- **NeurIPS proceedings.** The AgentDojo venue (Datasets and Benchmarks Track 2024), confirmed by web search that returned the proceedings entry.
- **Official pages.** anthropic.com (prompt-injection defenses, Claude Code auto mode, SHADE-Arena), alignment.anthropic.com (recommended directions), and simonwillison.net (Dual LLM pattern).
- **Discovery tools.** Exa neural search and WebSearch.

Representative queries:
- "LLM summarization strips or propagates indirect prompt injection in multi-step agent pipelines"
- "prompt injection laundering through sub-agent output into orchestrator ... provenance"
- "LLM paraphrasing or summarization as a defense against indirect prompt injection"
- "summarizer rewrites injected instructions into action items"
- "do LLMs treat tool role messages as lower privilege than user messages"
- "ablation: untrusted-source label versus message role for derived content"
- "LLM monitor ... with versus without source provenance information"
- "new benchmark for indirect prompt injection in LLM agents 2025 2026"
- "Trust Cascade provenance erasure"
- "OMNI-LEAK"

### 1.3 Verification rules applied

- Every reference was retrieved in this session. Author lists come from the arXiv API or the publisher page, never from search-engine snippets. Exa search snippets misattributed the authors of at least three 2026 papers (PACT `[fan2026pact]`, ROPE `[ma2026rope]`, and Safin et al. `[safin2026trustpropagation]`), and the arXiv API records were used instead.
- Where an arXiv abstract changed between versions (Kill-Chain Canaries, Same Payload), the latest version retrieved is used. If a full-text excerpt came from an earlier version, the text says so.
- Numbers are reported only when I read them in the retrieved abstract or text. Most summaries below are **abstract-level**: treat them as provisional until the full text is checked, especially before quoting a number in an application.
- Fetched pages were treated as untrusted data. Several search results contained example injection payloads, and none of their instructions were followed.

### 1.4 Size and recency caveats

- **The list is larger than the 30 to 45 target (75 references).** Since mid-2026 a cluster of papers has directly addressed TrustBound's core question: provenance erasure at LLM-to-LLM boundaries, summarizer stages, and channel vs. label effects. Leaving them out would misstate novelty. Peripheral works get one short paragraph each.
- **About a third of the references are 2026 preprints.** Most are not yet peer reviewed, and several use small samples (noted where relevant).

---

## 2. Thematic review

### 2.1 Indirect prompt injection foundations

**Greshake et al. 2023, "Not what you've signed up for"** `[greshake2023indirect]` (arXiv; venue not verified this session)
- *What it does.* Introduces indirect prompt injection: attackers place prompts in data an LLM-integrated application is likely to retrieve. It builds a security taxonomy (data theft, worming, information-ecosystem contamination) and demonstrates attacks on Bing's GPT-4-powered Chat, on code-completion engines, and on synthetic GPT-4 apps.
- *Relevance.* It establishes that retrieved text can act like arbitrary code execution and can control which APIs get called. This is TrustBound's attacker model. "Worming" is the earliest statement of multi-hop propagation.
- *Limitations.* The paper consists of demonstrations, not controlled rate measurements. It predates tool-calling agents.

**Perez & Ribeiro 2022, "Ignore Previous Prompt"** `[perez2022ignore]` (ML Safety Workshop, NeurIPS 2022)
- *What it does.* Introduces PromptInject, a framework for composing adversarial prompts. It shows goal hijacking and prompt leaking against GPT-3 using simple handcrafted inputs.
- *Relevance.* It is the origin of the "ignore previous instructions" payload family. TrustBound's fixed payloads belong to this family, and recent models are trained against exactly these strings (see Triedman et al.'s conjecture in §2.5).
- *Limitations.* Direct injection only, one model, before agents existed.

**Liu et al., "Formalizing and Benchmarking Prompt Injection Attacks and Defenses"** `[liu2024formalizing]` (USENIX Security 2024)
- *What it does.* Gives a formal framework for prompt injection and evaluates 5 attacks and 10 defenses on 10 LLMs and 7 tasks. Five defenses are prevention-based: paraphrasing, retokenization, delimiters, sandwich prevention and instructional prevention. Five are detection-based: perplexity, windowed perplexity, naive LLM-based, response-based and known-answer detection.
- *Paraphrasing as a defense (full text).* Paraphrasing lowered attack success in some settings but not reliably. In their GPT-4 results, the reduction for the Combined Attack was large for one target task and much smaller for another. Paraphrasing also clearly reduced target-task utility when no attack was present (an average drop of about 0.14 in their no-attack performance metric). The authors conclude that no existing prevention-based or detection-based defense is sufficient.
- *Relevance.* This is the standard citation for "LLM rewriting of untrusted data gives partial protection at a utility cost."
- *Limitations for TrustBound.*
  - It studies single-turn LLM-integrated applications, not agents.
  - The paraphrase prompt is generic, not a task-directed summary.
  - The outcome is task output, not tool calls.
  - It does not analyze what the paraphrase does to the injected instruction.

**Jain et al. 2023, "Baseline Defenses for Adversarial Attacks Against Aligned Language Models"** `[jain2023baseline]`
- *What it does.* Evaluates detection (perplexity), input preprocessing (paraphrasing, retokenization) and adversarial training against optimizer-generated jailbreaks.
- *Paraphrasing results (full text).* Paraphrasing with gpt-3.5-turbo cut GCG attack success sharply on Vicuna-7B (0.79 to 0.05), less on Guanaco-7B (0.96 to 0.33) and barely on Alpaca-7B (0.96 to 0.88). AlpacaEval quality fell by roughly 10 to 15%. The authors describe a white-box adaptive attack that survives a known paraphraser as feasible.
- *Relevance.* This is the origin of paraphrasing as a defense. Its rationale is that paraphrasing destroys non-semantic adversarial tokens, and that rationale does **not** carry over to natural-language injections: a faithful summary is supposed to keep the meaning.
- *Limitations.* It studies jailbreaks, not IPI.

### 2.2 Agent prompt-injection benchmarks

| Benchmark | Setting and scale (as stated in abstract) | Finding most relevant to TrustBound | Limitation for TrustBound |
|---|---|---|---|
| **AgentDojo** `[debenedetti2024agentdojo]` (NeurIPS 2024 D&B) | Extensible environment; 97 tasks, 629 security test cases | Attacks break some security properties but not all; LLMs fail many tasks even without attack | Single agent; the injection arrives in the tool channel; no intermediate-LLM factor in the base suites |
| **InjecAgent** `[zhan2024injecagent]` (Findings ACL 2024) | 1,054 cases, 17 user tools, 62 attacker tools; direct-harm vs. exfiltration intents | ReAct GPT-4 vulnerable 24% of the time; a "hacking prompt" nearly doubles this | Single step; simulated tool responses |
| **ASB** `[zhang2025asb]` (ICLR 2025) | 10 scenarios, 400+ tools, 27 attack/defense types, 13 backbones | Highest average ASR 84.30%; current defenses of limited effectiveness | Broad rather than deep; no pipeline-provenance factor |
| **BIPIA** `[yi2023bipia]` (KDD 2025) | First IPI benchmark | Attributes vulnerability to LLMs failing to distinguish context from instructions and lacking awareness not to execute them; proposes **boundary awareness** and **explicit reminder** defenses | Reviewers will see TrustBound's boundary-reminder arm as a BIPIA-style defense and expect this citation |
| **WASP** `[evtimov2025wasp]` | End-to-end web-agent security | Attacks partially succeed in up to 86% of cases, but agents often fail to fully complete attacker goals ("security by incompetence") | Web/UI agents; argues for scoring partial vs. full attacker success separately |
| **AgentDyn** `[li2026agentdyn]` | 60 open-ended tasks, 560 injection cases (Shopping, GitHub, Daily Life); helpful third-party instructions included | Almost all of 10 defenses are either insecure or over-defend | Shows that defenses ignoring all external instructions look good only when no benign instructions exist |
| **ART** `[zou2025art]` | Public competition: 22 agents, 44 scenarios, 1.8M attacks, >60k policy violations; ART benchmark on 19 models | Most agents violate policy within 10 to 100 queries; robustness correlates weakly with size, capability or inference compute | Single-agent deployments |
| **LLMail-Inject** `[abdelnabi2025llmail]` (Findings EMNLP 2026, per arXiv comment) | 208,095 human-written attacks from 839 participants; full chain (retrieval, evading defenses, unauthorized tool call with correct arguments) | Meta SecAlign still 32% ASR; GPT-4o 58%; GPT-5 mini 47% | Email-assistant setting close to TrustBound's; a good source of diverse, adaptive human payloads |
| **AutoDojo** `[ma2026autodojo]` | Adaptive black-box injection generation on AgentDojo + AgentDyn; 10 defenses, 5 models | Static benchmarks often overestimate defenses; **under-specified tasks are particularly vulnerable** | Single-agent |
| **INFUSE** `[nguyen2026infuse]` | 40 long-horizon tasks, 56 attack scenarios, 19 LLMs | Mean ASR 19.6% (LLM-judged). On a stress subset, instructional hardening cut ASR from 58.2% to 14.3%. Paraphrasing each observation with the agent's own model into "neutral, factual" text cut mean ASR by only 16.3 points and *increased* it for GPT-4o-mini and Qwen2.5-14B (full-text excerpt) | Paraphrase is a defense step, not a pipeline stage with its own provenance |

**Benchmark gap.**
- None of the standard benchmarks (AgentDojo, InjecAgent, ASB, BIPIA, WASP) treats an intermediate LLM stage between the untrusted source and the actor as an experimental factor.
- Multi-agent extensions now exist: MultiAgentDojo in `[petersgill2026camelstalk]`, and Trust Cascade replays AgentDojo/InjecAgent tasks in a two-agent harness `[zhou2026trustcascade]`.

### 2.3 Instruction hierarchy, channels and labels

**Wallace et al. 2024, "The Instruction Hierarchy"** `[wallace2024instruction]` (OpenAI)
- *What it does.* Argues that a primary root cause of these attacks is that LLMs give system prompts the same priority as untrusted user and third-party text. It defines a hierarchy (system > user > third-party content, including tool outputs), generates synthetic training data for it, and applies it to GPT-3.5. Robustness improves sharply, including against unseen attack types, with minimal capability loss.
- *Relevance.* This trained prior is what makes TrustBound's channel manipulation matter. Pasting derived content into the user/orchestrator turn moves it **up** the hierarchy.
- *Limitation.* The hierarchy assumes the role label reflects true provenance, which is exactly what multi-stage pipelines break (`[he2026contextroot]`, `[zhou2026trustcascade]`).

**StruQ** `[chen2024struq]` (USENIX Security 2025), **SecAlign** `[chen2024secalign]` (CCS 2025) and **Meta-SecAlign** `[chen2025metasecalign]`
- StruQ separates prompt and data into two channels, using a secure front-end and fine-tuning so the model ignores instructions in the data portion.
- SecAlign uses preference optimization and reports attack success below 10% across attacks, including stronger ones than seen in training.
- Meta-SecAlign scales up training and evaluation. It reports that SecAlign suffers significant utility degradation on agentic tasks and releases models evaluated on AgentDojo, InjecAgent, WASP and SEP.
- *Relevance.* Channel-separation training protects only content that arrives in the data channel. Derived content that a pipeline places in the instruction channel bypasses it by construction.

**Spotlighting** `[hines2024spotlighting]`
- *What it does.* A family of prompt-engineering techniques that "utilize transformations of an input to provide a reliable and continuous signal of its provenance". With GPT-family models, ASR fell from more than 50% to below 2%.
- *Relevance.* It is the closest prompting analogue of TrustBound's provenance-preserved label. Open question: does such a signal survive LLM summarization, or can it be reapplied afterwards?
- *Limitations.* Static attacks. Abstract-level only.

**SEP, "Can LLMs Separate Instructions From Data?"** `[zverev2024sep]` (ICLR 2025)
- *What it does.* Proposes a formal and an empirical measure of instruction/data separation, plus the SEP dataset.
- *Finding.* All models tested fail to achieve high separation. Prompt engineering and fine-tuning either fail to improve separation substantially or reduce utility.

**Control Illusion** `[geng2025controlillusion]` (AAAI 2026)
- *Finding.* Across six LLMs, system/user separation fails to establish a reliable hierarchy, even for simple formatting conflicts. Societal framings (authority, expertise, consensus) influence behavior more than system/user roles do.
- *Relevance.* TrustBound's "notes from your research assistant" framing is itself a social-authority cue. The provenance-lost condition therefore bundles a role change with an authority framing, and the label ablation should separate them.

**Prompt Injection as Role Confusion** `[ye2026roleconfusion]` (ICML 2026)
- *What it does.* Uses role probes to show that models infer who is speaking from how text sounds, not from its tag. Injected text occupies the same representational space as the role it imitates. "CoT Forgery" (fabricated reasoning) reaches 60% attack success against frontier models, and the degree of role confusion predicts success before any tokens are generated.
- *Relevance.* A summarizer rewrites attacker text in its own voice. Role confusion therefore gives a mechanistic prediction that summarization could **launder** an instruction, because the text now sounds like a colleague or the assistant. That makes a testable mediator for TrustBound.

**Same Payload, Different Channel** `[syed2026samepayload]` (EMNLP 2026)
- *What it does.* Uses matched payloads that hold the malicious text fixed and vary only the channel (user message, tool metadata, tool output), across 10 production LLMs and three attack families.
- *Findings.* General-purpose models sharply discount instructions arriving as tool metadata relative to the user message; agent-native models discount them far less. Within the tool surface, descriptions are far more instruction-like than outputs: "Models treat tool metadata as instructions and tool results as data." In the earlier (6-model) full-text version, IPI delivered via tool output had lower ASR than the same content in the user turn, for every model.
- *Relevance.* It establishes the channel effect for raw text at fixed content, which is half of TrustBound's factor (b), without the summarization factor.

**Position, Role or Label? (WhoWins)** `[laddha2026whowins]`
- *What it does.* A controlled study that separates the position, chat role and text label of conflicting instructions: 1,080 scenarios, 14 open-weight models, about 1.89M scored replies.
- *Findings.* Within one message, the first of two conflicting lines wins 72 to 95% of the time. In tool and file-write tasks, a policy sent in the real system message wins **less** often than the same text sent as a labelled user message, in every model-mode.
- *Relevance.* The closest methodological template for TrustBound's channel-vs-label ablation. It shows role and label effects can diverge and depend on model family.
- *Limitations.* Instruction conflicts rather than adversarial injection with consequential tools; open-weight models only.

**Trust Region Effect** `[guo2026trustregion]`
- *Finding.* With the payload held fixed and only its placement varied, an agent powered by GPT-5.4 follows an injection placed in a README or TODO file 2.6 times more often than the same injection in a code or data file.
- *Relevance.* At fixed content, the context in which text is presented changes compliance.

**Auditing Provenance Sensitivity in LLM Agent Action Selection** `[liao2026provenance]`
- *What it does.* Holds task, proposition, position and policy fixed, and changes only the stated source authority. 450 tasks, open-weight model families.
- *Findings.* Trusted and untrusted variants lead to different actions in 5.4% of "competing" cases vs. 1.7% of "supporting" cases. In the authors' words, "The models respond to textual source-authority cues, but this does not prevent untrusted evidence from influencing their actions."
- *Relevance.* Label-only manipulations have **small average effects**. This is consistent with TrustBound's Phase 1 null for the label-only "summary" framing (see §3), and it implies large samples are needed for label effects.

**When Context Gets Root** `[he2026contextroot]`
- *What it does.* Describes "instruction privilege escalation": agent harnesses rebuild context in ways that raise tool-level content to user or system level, for example during subagent delegation, persistent goals, scheduled tasks or custom subagents. Using multi-agent mechanisms, all 13 attack objectives were achieved on all six coding-agent harnesses under unrestricted execution. Under automatic permission review, all 13 were achieved on the three harnesses that offer that mode.
- *Full-text detail.* The permission reviewer allowed risky actions because the reconstructed history presented attacker-derived text as user authorization.
- *Relevance.* It is a real-world existence proof of TrustBound's provenance-lost condition. It also shows a reviewer that lacks true provenance approving escalated actions, which bears directly on question (c).
- *Limitations.* Attack demonstrations rather than controlled rates; coding agents only.

**Context Privilege Escalation** `[li2026cpe]`
- *What it does.* A systematic analysis of context assembly in 12 real harnesses, including Claude Code and Codex. It identifies two attack classes: message-role escalation (low-privilege content incorporated into a higher-privilege role) and cross-scope persistence.
- *Relevance.* Same as `[he2026contextroot]`.

### 2.4 System-level, provenance and information-flow defenses

**(i) Isolation and dual-LLM designs**

**Willison 2023, "The Dual LLM pattern"** `[willison2023duallm]`
- *What it describes.* A privileged LLM that has tools and sees only trusted input, a quarantined LLM that has no tools and processes untrusted content, and a non-LLM controller. The controller stores the quarantined LLM's outputs (for example, an email summary) as variables such as `$VAR2`, so the privileged LLM "only ever sees those variable names".
- *Key warning.* Willison states that unfiltered quarantined output must **never** be forwarded to the privileged LLM. He acknowledges the limits himself: social engineering of the user, risks of chaining, complexity, and in his words "This solution is pretty bad". An April 2025 update points to CaMeL as fixing a flaw in the pattern.
- *Relevance.* TrustBound's provenance-lost condition is precisely the anti-pattern this post forbids. Whether it is unsafe is therefore not the open question. What remains open is how much transformation vs. presentation each contribute, and whether labels or monitors mitigate the risk when practitioners use the pattern anyway.

**Design Patterns for Securing LLM Agents** `[beurerkellner2025patterns]`
- *What it proposes.* Six patterns: action-selector, plan-then-execute, LLM map-reduce, dual LLM, code-then-execute, and context-minimization.
- *Full-text points.* LLM-processed untrusted data may reach a privileged LLM only under output constraints (for example, a regex-validated numeric output) or as symbolic references. The quarantined LLM is "still susceptible to prompt injection". The paper notes residual model-dependent risk in its summarization case study.
- *Relevance.* It frames TrustBound's free-text summary handoff as outside the provably safe patterns.

**IsolateGPT** `[wu2024isolategpt]` (NDSS 2025) and **f-secure** `[wu2024fsecure]`
- IsolateGPT isolates third-party LLM apps from each other, with overhead under 30% for three-quarters of tested queries.
- f-secure applies information-flow control (IFC): it disaggregates the system into a context-aware pipeline with structured executable plans, and a security monitor filters untrusted input out of planning.
- *Relevance.* Architectural baselines. Neither measures model behavior under provenance loss.

**Firewalls to Secure Dynamic LLM Agentic Networks** `[abdelnabi2025firewalls]` (TMLR 2026)
- *What it does.* A "Language Converter Firewall" projects incoming agent messages onto a closed, structured protocol, so that "persuasive framing, urgency tactics, and embedded instructions are structurally eliminated through deterministic verification". On the ConVerse benchmark, security attacks fell from 60% to 3%.
- *Relevance.* It represents the *structured* end of the transformation spectrum. It is strong evidence that constrained schemas sanitize where free text cannot.

**Agent Privilege Separation in OpenClaw** `[cheng2026openclaw]`
- *What it does.* A reader agent with no privileged tools turns each email into a JSON summary (fields: sender, subject, body summary, action items). The actor agent sees only that summary and holds `send_email`. Results on 649 LLMail-Inject attacks that had succeeded against a single agent: full pipeline 0% ASR, isolation alone 0.31%, JSON formatting alone 14.18%.
- *Full-text caveat.* The authors note that the summarizing model can still be manipulated into encoding actionable instructions in free-text fields.
- *Relevance.* The closest engineering analogue of TrustBound's summarizer→executor setup. Its schema includes an **"action items" field, a natural laundering channel**.
- *Limitations.* A replay of payloads that were not adapted to the pipeline; one benchmark; no factorization of label vs. channel.

**(ii) Capability or authorization derived from the trusted request**

**CaMeL, "Defeating Prompt Injections by Design"** `[debenedetti2025camel]`
- *What it does.* Extracts control and data flow from the trusted query, so that untrusted data "can never impact the program flow". Capabilities enforced at tool calls block unauthorized data flows. It solves 77% of AgentDojo tasks with provable security, vs. 84% undefended.
- *Relevance.* TrustBound's structured authorization check is CaMeL-style. It should block attacker-chosen actions and targets by construction, so it serves as a reference **ceiling** rather than a finding. The informative measurement is its utility cost on under-specified tasks.

**Progent** `[shi2025progent]`
- *What it does.* An LLM generates a symbolic tool-call policy from the user task and updates it during execution. An SMT solver auto-applies updates that narrow the policy and requires approval for updates that expand it. Evaluated on AgentDojo and ASB.

**DRIFT** `[li2025drift]` (NeurIPS 2025)
- *What it does.* A secure planner builds a minimal function trajectory and a parameter checklist from the user query. A dynamic validator checks deviations from that plan, and an injection isolator masks conflicting instructions in memory. Evaluated on AgentDojo, ASB and AgentDyn.

**ROPE, Routed Origin Policy Enforcement** `[ma2026rope]`
- *What it does.* A value may reach a state-changing tool only if it traces unforgeably to the user, a source the user named, or the user's own records. Enforcement is a deterministic origin check, and the only LLM step sees just the trusted request.
- *Guarantees and results.* No value whose only origin is attacker-writable content reaches a guarded parameter, and "no rewording of an injection changes an admission decision". ASR is 1.6 to 2.6% with 82 to 100% of clean utility retained, and optimizing injections against ROPE is largely ineffective.
- *Relevance.* The closest published analogue of TrustBound's taint tracker plus capability check.

**PACT** `[fan2026pact]`
- *What it does.* Assigns semantic roles to tool arguments (target, command, credential, content) and tracks each argument's provenance across replanning steps.
- *Results.* Under oracle provenance it reaches 100% utility and 100% security on mixed-trust suites. On AgentDojo it reaches 100% security on the three strongest models, with 38.1 to 46.4% utility (8 to 16 points above CaMeL). The remaining bottleneck is "provenance inference and contract synthesis".
- *Relevance.* TrustBound's rule "block arguments that come only from untrusted sources" is argument-level, and PACT argues it should depend on each argument's role.

**(iii) Label propagation, IFC and taint tracking**

**FIDES** `[costa2025fides]`
- *What it does.* A formal model of agent planners. It characterizes which properties dynamic taint tracking can enforce, and builds a planner that tracks confidentiality and integrity labels, enforces policies deterministically, and adds primitives for selectively hiding information. Evaluated on AgentDojo.
- *Relevance.* The closest design to TrustBound's taint tracker.

**RTBAS** `[zhong2025rtbas]`
- *What it does.* Adapts IFC to tool-based agents, using LM-as-judge and attention-saliency "dependency screeners" to decide which inputs a tool call depends on. On AgentDojo it prevents all targeted attacks with a 2% utility loss under attack.

**Permissive Information-Flow Analysis for LLMs** `[siddiqui2024permissiveifc]`
- *What it does.* Argues that propagating the most restrictive input label to the output is "too conservative", and propagates only the labels of inputs that influenced the output. In an agent setting this improves over an introspection baseline in more than 85% of cases.
- *Relevance.* TrustBound's tracker uses the conservative rule (an output inherits all input labels). Any summary of an untrusted document is then fully untrusted, and every argument derived from it is blocked. Expect strong security and a utility cost on tasks that legitimately need data from the document, such as a reply-to address.

**Ghost in the Agent (NeuroTaint)** `[cai2026neurotaint]`
- *What it does.* Offline taint auditing that treats propagation as "explicit content transfer, but also ... semantic transformation, causal influence on decisions, and cross-session persistence". On a 400-scenario benchmark it outperforms FIDES at detecting source-to-sink propagation.
- *Relevance.* A candidate measurement tool for whether a summary semantically carries taint.

**(iv) Detection, removal and monitoring defenses**

- **MELON** `[zhu2025melon]` (ICML 2025). Re-executes the trajectory with the user prompt masked and flags an attack if the actions stay similar.
- **Task Shield** `[jia2024taskshield]`. Checks whether each instruction and tool call serves the user's goals. On AgentDojo with GPT-4o: 2.07% ASR, 69.79% utility.
- **PromptArmor** `[shi2025promptarmor]`. An off-the-shelf LLM detects and removes injected prompts before the agent sees them. With GPT-4o, GPT-4.1 or o4-mini it reports false positive and false negative rates below 1% on AgentDojo, and ASR below 1% after removal. The authors recommend it as a standard baseline. It is the "sanitizing summarizer" end of TrustBound's summarizer spectrum and should be included as a baseline.
- **"Can Indirect Prompt Injection Attacks Be Detected and Removed?"** `[chen2025detectremove]` (ACL 2025). Benchmarks detectors and two removal methods: segmentation removal and a trained extraction model.
- **DataSentinel** `[liu2025datasentinel]` (IEEE S&P 2025). A detector fine-tuned via a minimax game against adaptive injections.
- **LlamaFirewall** `[chennabasappa2025llamafirewall]`. Three guardrails: PromptGuard 2 (jailbreak detector), Agent Alignment Checks (a chain-of-thought auditor for injection and goal misalignment, described as "still experimental"), and CodeShield. AlignmentCheck is the natural off-the-shelf LLM-monitor baseline.
- **TaskTracker** `[abdelnabi2024tasktracker]` (SaTML 2025). Linear probes on activation deltas (before vs. after external data) detect task drift with near-perfect out-of-distribution ROC AUC, and the release includes a 500K-instance dataset. It is a white-box monitor that does not need provenance labels. Whether it fires on drift induced by a *summary* has not been tested.
- **Lessons from Defending Gemini** `[shi2025geminilessons]` (Google DeepMind).
  - Uses continuous adaptive-attack evaluation and argues that static evaluations give a false sense of security.
  - Baseline defenses include spotlighting and paraphrasing. A full-text appendix notes that a paraphraser's own safety training may make it refuse, which acts as an extra filter, but that safety alignment differences between paraphraser and target model can cause problems.
  - Concludes that robustness needs defense in depth.

### 2.5 Multi-agent propagation, laundering, and intermediate LLM stages (core novelty question)

**Prompt Infection** `[lee2024promptinfection]`
- *What it does.* A self-replicating LLM-to-LLM injection.
- *Setup (full text).* Pipelines start with a tool-specific agent (document, email or web reader) and continue with agents acting as **strategist, summarizer, editor and writer**. Models: GPT-4o and GPT-3.5 Turbo, with global vs. local message sharing.
- *LLM Tagging defense.* Tagging prepends "[AGENT NAME]:" to each agent's output before passing it downstream. Alone it "reduces the attack success rate by only 5%". Combined with marking it prevented all attacks tested. Instruction defense plus tagging left 3% ASR, and sandwich plus tagging left 16%.
- *Relevance.* (1) Summarizer agents relay self-replicating payloads. (2) A provenance tag alone barely helps, and protection comes from combining it with marking. This is the direct prior for TrustBound's label manipulation.
- *Limitations.* The payloads explicitly instruct each agent to replicate them, are handcrafted (the authors note that generated attacks may bypass the defenses), and are not adaptive. Content and channel are not separated.

**Multi-Agent Systems Execute Arbitrary Malicious Code** `[triedman2025mas]`
- *What it does.* Adversarial content in web pages or files hijacks control and communication in several multi-agent frameworks.
- *Results.* With GPT-4o, arbitrary code execution succeeded in 58 to 90% of trials depending on the orchestrator, and in 100% for some configurations. The attacks work even when individual agents resist direct and indirect injection and refuse harmful actions.
- *Full text.* The authors describe the attack as **laundering** adversarial requests through the outputs and metadata of front-line agents (a confused deputy). They conjecture that laundering changes the presentation enough to evade safety training targeted at conventional IPI strings.
- *Relevance.* It names the laundering mechanism, and its conjecture is exactly what TrustBound's content-transformation factor can test.
- *Limitations.* Framework-specific. It does not separate presentation from content.

**Trust Cascade through Provenance Erasure** `[zhou2026trustcascade]` (EMNLP 2026). **This is the closest prior work** (full text, Sections 1 to 5).

*Setup.* A minimal two-agent, one-step harness. A leader receives a user task plus an injected tool observation and writes a natural-language delegation. A follower receives that delegation through a specified channel: system, user, tool or peer-agent.
- Core models: Qwen2.5-7B, Llama-3.1-8B, Gemma-2-9B.
- Extensions: 32B models, a Qwen3 scale series, and six closed models (GPT-5.5, Claude Opus 4.6, DeepSeek Reasoner, GPT-4o, Gemini 2.5 Flash, GLM-4-Plus).

*Findings.*
1. **Provenance erasure.** Across 460 injection–delegation pairs, delegation removed 98% of format markers, 100% of authority entities and 44% of factual entities (about 80% combined), while the actionable payload often survived (about 56% of email addresses).
2. **Follower trust collapse.** The follower's "Collapse Index" rose from 0.376 under direct injection to 0.836 under cascade.
3. **Delegation-as-user control.** Replaying the leader's delegation text as a single-agent user prompt gave compliance statistically equivalent to raw injection in the same user channel (Qwen 81.8% vs. 83.3%). The authors therefore attribute the amplification to **channel trust escalation, not content reformulation**. For Llama and Gemma, the control differences also reflect the leader attenuating content.
4. **Amplification.** Direct system-channel injection had 0% single-agent ASR, vs. 33 to 63% cascade ASR across eight open-weight models. This reproduced on six tasks derived from AgentDojo and InjecAgent.
5. **Closed models.** "Heavy-tier" closed models had near-zero ASR, but stopped the cascade at different stages. For example, Claude Opus 4.6 passed the injection on in 72.2% of leader delegations yet had 0% ASR.
6. **Trust Boundary Auditor (TBA).** A rule-based, zero-inference auditor (novel entity, target substitution, provenance leak) reached 86 to 100% conditional detection with 0% false positives across four domains.

*Relevance.* In broad form, this answers TrustBound's question (b): at an LLM-to-LLM boundary, the loss of channel provenance, rather than the rewriting of content, drives downstream compliance, at least for small open models in a one-step leader→follower harness. It also measures one form of (a): what delegation keeps and what it strips.

*Differences from TrustBound and limitations.*
1. The intermediate LLM is a **delegating leader** whose job is to issue instructions, not a **summarizer** whose job is to report content. Laundering instructions into "action items" inside a factual summary is a different transformation.
2. The erased "provenance" consists of attacker-supplied authority markers ([VERIFIED], policy IDs), not **defender-applied** source labels. Their marker-restoration check, in an appendix I did not read, re-attaches injection-origin markers.
3. Channel and text label are not crossed as separate factors.
4. There is no LLM-monitor provenance ablation and no comparison with a taint tracker or CaMeL. TBA is a deterministic entity-provenance auditor and a strong related baseline.
5. One-step harness, mostly 7 to 9B models. The strongest closed models are near floor.

**Kill-Chain Canaries** `[wang2026killchain]`
- *What it does.* Plants a unique canary token in every payload and records the furthest stage it reaches: Exposed, Persisted, Relayed, Executed. 950 runs across five production LLMs, six attack surfaces and five defense conditions.
- *Findings.*
  - Claude Haiku 4.5 and Sonnet 4.5 executed none of 164 text-surface attacks, and in the text relay the canary never appeared in a memory write (0/40). GPT-4o-mini executed 53%.
  - As readers, Claude Haiku 4.5 executed 2 of 3 injections relayed by GPT-4o-mini (n = 3).
  - Defenses failed on channels they do not inspect.
- *Relevance.* Stage-level instrumentation that directly measures whether a writer/summarizer stage strips the payload or relays it.
- *Limitations.*
  - Token survival is not the same as semantic laundering: a paraphrased instruction that drops the token counts as "stripped".
  - Key cross-model pairings have very small n, as the authors acknowledge.
  - Labels and channels are not factorized.

**Can CaMeLs Talk?** `[petersgill2026camelstalk]`
- *What it does.* Shows that CaMeL's guarantees do **not** compose in hierarchical multi-agent systems: an attack succeeds even though every agent runs CaMeL, because "untrusted data can be reinterpreted as trusted input by a downstream agent".
- *Full text.* The authors call this "boundary laundering". In their example, an orchestrator places a tainted `summarised_info` value into the natural-language instruction it sends to a notification agent.
- *Fix and results.* Multi-CaMeL sends trusted instructions and untrusted data through separate channels and preserves provenance across agents. On their MultiAgentDojo benchmark, ASR is 0.0% with multi-CaMeL, 0.2% with per-agent CaMeL and 12.9% with no CaMeL. The utility cost shrinks as model capability grows.
- *Relevance.* The deterministic counterpart of TrustBound's provenance-lost condition. It shows that system-level guarantees require preserving provenance across boundaries.

**OMNI-LEAK** `[naik2026omnileak]`
- *What it does.* In an orchestrator setup with a SQL agent and a notification agent, one indirect injection in public data compromises several agents and leaks private data despite data access control. Both reasoning and non-reasoning frontier models are vulnerable.
- *Relevance.* Realistic multi-stage escalation. The full text recommends monitors at every inter-agent step.

**Autonomous LLM Agent Worms** `[zha2026worms]`
- *What it does.* Studies persistent propagation through file-backed agent state. A "summary-resilient payload optimizer" generates worm payloads robust to LLM summarization and paraphrasing across multi-hop communication, achieving 3-hop cross-platform transmission. User-prompt carriers achieve higher compliance than system-prompt carriers.
- *Defenses.* The proposed defenses include "typed memory promotion", which keeps untrusted summaries out of trusted memory.
- *Relevance.* Optimized payloads defeat summarization as a sanitizer. This gives TrustBound an adaptive-attack arm, and typed promotion is a provenance-preserving design.

**Safe to Check, Unsafe to Use (relinking)** `[liu2026relinking]`
- *What it does.* Shows that summarization-based compression can act as a confused deputy, assembling locally benign fragments into a complete malicious instruction that was never present verbatim before compression. Relink rate is 86.9% vs. 17.0% for clean-split controls, and 11 existing defenses do not reliably catch it.
- *Relevance.* Summarizers can **create** actionable instructions, which defeats filters placed before the summary. TrustBound's summarizer taxonomy should include a "synthesized" category.

**Governance Decay** `[chen2026governancedecay]`
- *What it does.* Shows that context compaction silently removes in-context constraints. Violations rise from 0% with the full policy in context to 30% after compaction. They stay at 0% when the constraint survives the summary and reach 38% when it is dropped. Adversarial content can bias the summarizer into omitting a policy. "Constraint pinning" restores 0%.
- *Relevance.* Summarizers drop safety-relevant metadata, which is analogous to dropping provenance labels. Pinning corresponds to preserving provenance.

**When Do Summaries Become Instructions?** `[chu2026handoff]`
- *What it does.* Finds that agents' self-written handoff summaries sometimes state unsupported restrictions (1.2 to 2.4%) or unsupported authorizations (0.1 to 1.3%). Neutralizing false approvals cut unauthorized actions from 24 to 7 of 120 held-out runs (a post-hoc analysis).
- *Relevance.* Summaries can turn content into authorization statements that the next stage acts on: a non-adversarial form of laundering. It is also a model of careful pre-registered vs. post-hoc reporting.

**Trust propagation and structural containment** `[safin2026trustpropagation]` (IEEE CARS 2026)
- *What it does.* A four-agent LangGraph pipeline (Supervisor, Researcher, Validator, Executor) attacked with memory poisoning and with a forged approval inside a retrieved document. Undefended, memory poisoning reached execution in every trial. With an independent authorization layer, the Validator was always compromised (100% "judgment bypass rate") but the unsafe-action rate was 0%.
- *Relevance.* Structural authorization contains compromised upstream judgment, which is what TrustBound's capability-check arm should show.
- *Limitation.* Small study: 60 tasks, 3 seeds.

**Synthesis on "does summarization sanitize?"** The evidence is mixed.
- **Strips:** strong-model writer/summarizer stages often remove literal payload tokens `[wang2026killchain]`.
- **Erases provenance but keeps the payload:** delegating leaders strip authority and format markers while keeping actionable content `[zhou2026trustcascade]`.
- **Partial or backfiring defense:** generic paraphrasing gives partial protection at a utility cost, and sometimes backfires `[liu2024formalizing; jain2023baseline; nguyen2026infuse; shi2025geminilessons]`.
- **Survives:** optimized payloads survive summarization `[zha2026worms]`.
- **Synthesizes:** summarizers can create instructions from fragments `[liu2026relinking]`.
- **Structured schemas help:** constrained schemas sanitize much better than free text `[abdelnabi2025firewalls; cheng2026openclaw]`.
- **Not found in this search:** a study that (1) classifies what a *task-faithful summarizer* does with each injected instruction (drop, flag, neutralize, launder as action item, synthesize), validated against human coding, and (2) links each category to downstream executor behavior under provenance-preserved vs. provenance-lost presentation.

### 2.6 Adaptive attacks and what they imply for fixed-payload evaluation

**Main papers**
- **Zhan et al. 2025** `[zhan2025adaptive]` (Findings NAACL 2025). Adaptive attacks bypassed all eight IPI defenses tested, each with ASR above 50%.
- **Nasr et al. 2025, "The Attacker Moves Second"** `[nasr2025attackermovessecond]`. Systematically tuned gradient descent, reinforcement learning, random search and human-guided exploration bypassed 12 recent defenses, most with ASR above 90%. The majority of those defenses originally reported near-zero ASR. The authors argue that evaluations against static attack strings or weak optimizers are flawed.
- **Terekhov et al. 2025** `[terekhov2025adaptivemonitors]`. An untrusted model that embeds publicly known or zero-shot prompt injections in its outputs consistently evades diverse LLM monitors on two AI-control benchmarks. Defer-to-Resample even backfires, because resampling turns the injection into a best-of-n attack.

**Related.** AutoDojo `[ma2026autodojo]`, LLMail-Inject `[abdelnabi2025llmail]`, ART `[zou2025art]` and Gemini "Lessons" `[shi2025geminilessons]` all report that static evaluations overstate robustness.

**Implications for TrustBound.**
1. **Model-level and monitor-level results are upper bounds.** Fixed-payload results for the reminder and both LLM monitors bound their effectiveness from above, and should be presented as comparative effects under a stated payload distribution, not as robustness claims.
2. **Deterministic arms are robust to rewording by design.** The taint tracker and capability check resist rewording by construction (ROPE proves this property for its design). By design they do not address effects that stay inside the user-authorized capability, for example corrupting the body of an authorized email. That is a property of the design, not a cited finding, and it should be measured.
3. **Monitors are themselves attack surfaces.** Showing a monitor raw untrusted content exposes it to injection `[terekhov2025adaptivemonitors]`. This is the stated reason Claude Code auto mode hides tool outputs from its classifier `[anthropic2026automode]`.

### 2.7 Monitoring and AI control

**AI Control** `[greenblatt2023aicontrol]`
- Defines control protocols that stay safe even if the model tries to subvert them, using an untrusted GPT-4, a trusted GPT-3.5 and limited trusted labor.
- Example protocols: trusted editing (GPT-3.5 rates suspiciousness and edits suspicious code) and untrusted monitoring with anti-collusion measures.
- Supplies the vocabulary TrustBound's monitor arm should use (trusted vs. untrusted monitor, limited trusted labor for auditing).

**Ctrl-Z** `[bhatt2025ctrlz]`
- The first agentic control evaluation: BashBench, 257 multi-step sysadmin tasks.
- Resample protocols cut attack success from 58% to 7% at a 5% cost in usefulness.

**SHADE-Arena** `[kutasov2025shadearena]`, with Anthropic's post `[anthropic2025shadepost]`
- Pairs benign main tasks with harmful side tasks.
- The best sabotage agents score 27% (Claude 3.7 Sonnet) and 15% (Gemini 2.5 Pro) when overseen by Claude 3.6 Sonnet.
- Side-task success relies heavily on a hidden scratchpad.
- The top monitor (Gemini 2.5 Pro) reaches an AUC of 0.87.

**Reliable Weak-to-Strong Monitoring** `[kale2025weaktostrong]`
- A monitor red-teaming workflow covering agent and monitor awareness, evasion strategies including prompt injection, SHADE-Arena and a new computer-use SHADE-Arena.
- "Agent awareness dominates monitor awareness", and "providing the monitor with more information about the agent is less helpful than expected".
- Monitor scaffolding matters more than monitor awareness.

**How does information access affect LLM monitors?** `[arike2026infoaccess]`
- Finds a "less-is-more" effect: monitors often perform better with less of the agent's trajectory.
- Proposes extract-and-evaluate monitoring, which improves sabotage detection by 16.8 points on BigCodeBench-Sabotage with a GPT-4.1-mini monitor.
- *Relevance.* "More context helps the monitor" cannot be assumed. Provenance labels are a specific, compact kind of information that has not been tested in this frame.

**Blocking at the Boundary** `[liu2026blockingboundary]`
- Studies "staged" prompt injection against Claude Code and Codex.
- Formulates pre-action auditing and proposes Path-Aligned Attribution, which traces which source supplied each element of a pending action and blocks when an attacker-reachable source has an unwarranted effect.
- With Claude Sonnet 5: 86% block recall at a 6 to 8% false-block rate, vs. 44 to 47% recall at 16 to 33% for ARGUS.
- *Relevance.* A provenance-attribution monitor. It is not an ablation of whether provenance labels are available.

**Other monitor-relevant evidence**
- LlamaFirewall AlignmentCheck `[chennabasappa2025llamafirewall]`.
- Trust Cascade's deterministic TBA `[zhou2026trustcascade]`.
- The permission reviewer in `[he2026contextroot]`, which approved actions because escalated content looked like user authorization.

**Gap.** None of these papers runs a controlled ablation of an *LLM* action monitor with vs. without provenance labels for injection-driven tool calls, crossed with whether provenance was lost upstream. The control literature also mostly targets *scheming* agents, while IPI monitors must catch actions by a *benign but hijacked* agent. TrustBound sits at the junction of the two.

### 2.8 Anthropic materials

**"Mitigating prompt injections in browser use"** `[anthropic2025browserpi]` (Nov 24, 2025)
- *Threat model.* Every webpage is a potential attack vector. Example: hidden white text in an email instructs the agent to forward confidential mail.
- *Defenses.* Reinforcement learning that rewards identifying and refusing injections in simulated web content; classifiers that scan untrusted content entering the context (hidden text, manipulated images, deceptive UI); continuous internal red teaming plus external arena-style challenges.
- *Results.* Against an internal adaptive Best-of-N attacker, ASR with improved safeguards was 1.4% (Opus 4.5) to 2.4% (Haiku 4.5), vs. 8.0 to 13.8% for the models alone.
- *Stated limits.* The post states that "prompt injection is far from a solved problem" and that even 1% is meaningful residual risk.
- *Relevance.* The post describes no explicit provenance-tracking mechanism. Defense rests on model training and classifiers, the layers TrustBound probes with its prompting and monitor arms.

**"How we built Claude Code auto mode"** `[anthropic2026automode]` (Mar 25, 2026)
- *Architecture.* Two layers:
  - An input-layer prompt-injection probe scans tool outputs and adds a warning to suspect content.
  - An output-layer transcript classifier (Sonnet 4.6) reviews actions before execution. It sees **only user messages and the agent's tool calls**: "We strip assistant text so the agent can't talk the classifier into making a bad call". Stripping tool results is described as the primary prompt-injection defense at the classifier layer.
- *Stated cost.* The classifier cannot always tell where an identifier came from.
- *Reported results.* Full-pipeline false positive rate 0.4% on 10,000 real actions; false negative rate 17% on 52 real overeager actions and 5.7% on 1,000 synthetic exfiltration cases.
- *Other details.* Subagents are checked both at delegation and on return.
- *Relevance.* The most direct industry motivation for TrustBound's question (c). A production monitor deliberately gives up provenance information to gain injection robustness. TrustBound can quantify that trade-off, and test a **metadata-only** variant (per-argument source labels without the untrusted text) that might keep both benefits.

**"Recommendations for Technical AI Safety Research Directions"** `[anthropic2025directions]` (Alignment Science Blog, 2025; no date on page)
- *AI control.* Behavioral monitoring, with the concern that "monitor failures might be systematically concentrated in the same episodes where the actor behaves maliciously", and the need for monitors that work when actors have memory or can pass messages.
- *Adversarial robustness.* Hiding malicious content in websites to hijack agents is listed as an underexplored attack surface. The post has no standalone prompt-injection or provenance section.
- *Relevance.* Laundering by a summarizer is a candidate mechanism for exactly that **correlated failure**: the same rewritten text could fool both executor and monitor. TrustBound can test this.

**"SHADE-Arena: Evaluating sabotage and monitoring in LLM agents"** `[anthropic2025shadepost]` (Jun 16, 2025)
- *Setup.* 17 task pairs. The monitor is not told about the side task, and a suspicion score of 80/100 counts as detection.
- *Findings.* No model exceeded 30% overall success. The strongest models evaded detection almost 60% of the time. Showing the monitor the scratchpad improved detection.
- *Monitor limits.* For the best monitor, catching 80% of side tasks would require a false-positive rate above 20%, which the post calls infeasible.

---

## 3. Gap analysis

### 3.1 Question (a): do summarizers or other intermediate LLM stages strip or launder injected instructions?

**Already answered**
- Generic paraphrasing is a partial and unreliable sanitizer, with a utility cost `[liu2024formalizing; jain2023baseline; nguyen2026infuse; shi2025geminilessons]`.
- LLM stages can relay payloads through multi-agent pipelines, including summarizer agents `[lee2024promptinfection; triedman2025mas; naik2026omnileak]`.
- Payloads can be optimized to survive summarization `[zha2026worms]`.
- Summarizers can synthesize instructions from fragments `[liu2026relinking]`.
- Structured schemas sanitize much better than free text `[abdelnabi2025firewalls; cheng2026openclaw]`.

**Partially answered**
- How often a stage strips vs. relays a *literal* payload, per model `[wang2026killchain]`.
- How much provenance metadata delegation erases while keeping the payload `[zhou2026trustcascade]`.
- Whether summaries can turn content into authorization claims `[chu2026handoff]`.

**Open, as far as this search found**
1. A human-validated taxonomy of what a *task-faithful summarizer* does with each injected instruction (drop, flag, neutralize, launder as action item, synthesize).
2. How often each category occurs, by summarizer model and summarizer prompt (for example, "summarize" vs. "extract action items").
3. **Whether each category changes executor behavior in the same run.** For example: does a "flagged" instruction protect the executor or prime it? Does a "laundered action item" yield higher compliance than the raw instruction?

### 3.2 Question (b): does losing source labels and channel increase unauthorized tool calls, separately from content transformation?

**Largely answered in broad form**
- **Trust Cascade** `[zhou2026trustcascade]` shows, with a delegation-as-user replay control, that amplification across an LLM-to-LLM boundary is driven by channel trust escalation rather than content reformulation, at least for small open models in a one-step leader→follower harness.
- At fixed content, channel matters `[syed2026samepayload]`, and role, position and label can be separated experimentally `[laddha2026whowins]`.
- Label-only changes have small average effects `[liao2026provenance]`, and a provenance tag alone barely helps `[lee2024promptinfection]`.
- Real harnesses actually do re-insert tool-level content as user or system messages `[he2026contextroot; li2026cpe]`.
- Deterministic systems fail when a summary crosses into an instruction channel, and are fixed by preserving provenance across agents `[petersgill2026camelstalk]`.

**Partially answered or open**
1. **A full crossing in a summarizer topology.** No retrieved work crosses raw vs. genuine summary with provenance preserved vs. lost, with channel and **defender-applied** text label as separate factors, in a summarizer→planner→executor pipeline with consequential tools, on current API models.
2. **Whether defender labels survive derivation.** Does a preserved "untrusted external" label on *LLM-derived* content protect as well as the same label on raw content? Trust Cascade's erased "provenance" is attacker-supplied authority markup, not a defender label.
3. **The interaction of transformation and presentation.** Does summarization change the protective value of the tool channel?

### 3.3 Question (c): how does monitor effectiveness change when the monitor lacks provenance?

**Partially answered**
- More information does not reliably help LLM monitors: there is a less-is-more effect `[arike2026infoaccess]`, and extra monitor awareness is "less helpful than expected" `[kale2025weaktostrong]`.
- A production classifier deliberately withholds tool outputs and accepts that it cannot always tell where identifiers came from `[anthropic2026automode]`.
- A permission reviewer that sees escalated content as user authorization approves harmful actions `[he2026contextroot]` (demonstrations, not rates).
- Deterministic or attribution-based provenance auditors work well `[zhou2026trustcascade; liu2026blockingboundary]`.
- Monitors that see attacker text can be injected `[terekhov2025adaptivemonitors]`.

**Open, as far as this search found**
- A controlled ablation of an LLM action monitor's TPR/FPR for injection-driven tool calls across four information conditions: no provenance; provenance labels; content plus labels; metadata-only provenance (per-argument source tags without the untrusted text).
- Crossed with whether provenance was preserved or lost upstream, on the same trajectories.
- Including whether summarizer laundering produces **correlated failures** of executor and monitor.

### 3.4 Narrowest defensible gap and honest framing

The core phenomenon is **already established**: provenance loss at LLM-to-LLM boundaries enables attacks, and preserving provenance plus deterministic enforcement fixes them (`[zhou2026trustcascade; petersgill2026camelstalk; triedman2025mas; he2026contextroot; lee2024promptinfection]`, plus CaMeL/FIDES/ROPE/PACT). The deterministic arms (taint tracker, CaMeL-style check) will almost certainly drive fixed-payload ASR near zero, so they are **reference ceilings, not contributions**.

The evidence supports framing TrustBound as **a controlled measurement study, not a new defense**. A defensible claim, to check once more against the literature before submission:

> In a three-stage summarizer→planner→executor pipeline with consequential simulated tools, we (1) factorially separate content transformation (raw vs. genuine LLM summary) from provenance presentation (message channel × defender-applied label), (2) code what the summarizer does to each injected instruction and test whether that code mediates executor behavior, and (3) measure how much an LLM action monitor's detection depends on access to provenance, including a metadata-only condition, under the same manipulations. Deterministic taint and capability enforcement are included as reference points, along with their utility costs.

How to position the parts:
- Part (1) is partly a **replication and extension** of Trust Cascade's channel-escalation result, moved to a summarizer topology with defender labels and frontier API models. Present it that way.
- Parts (2) and (3) are where the open space appears to be.

**Do not claim:**
- that provenance loss enables attacks;
- that summarization is an unreliable sanitizer;
- that taint or capability enforcement blocks fixed attacks;
- any new defense.

**Reading the Phase 1 result.** With one sample per cell and 8 scenarios:

| Condition | Attacker success | Wilson 95% CI |
|---|---|---|
| Direct tool output, baseline | 6/8 | 41% to 93% |
| Direct tool output + boundary reminder | 5/8 | 31% to 86% |
| Label-only "summary" framing | 6/8 | 41% to 93% |
| "Summary" framing + boundary reminder | 6/8 | 41% to 93% |
| Clean-task completion | 31/32 | 84% to 99% |

These intervals overlap heavily, so no condition differs detectably.

A null for the "summary" framing is what the literature predicts. In the Phase 1 harness (`legacy/phase1/run.py`), both framings put the external text in the same single prompt, inside `<external_data>` tags, and both labelled it as external. Only the header text changed (e.g. "DIRECT TOOL OUTPUT ..." vs. "SUMMARY OF A TOOL OUTPUT ..."). So neither channel nor content changed, and the external marking was never removed. Label-only effects are small `[liao2026provenance]`, tags alone barely help `[lee2024promptinfection]`, and Trust Cascade found the effect in the channel move.

Phase 1 is a harness check, not evidence for or against any hypothesis.

---

## 4. How TrustBound relates to the closest works

| Work | Topology / intermediate stage | Content transformation varied? | Channel varied? | Defender-applied label varied? | Defenses compared | Monitor-provenance ablation? | What TrustBound would add |
|---|---|---|---|---|---|---|---|
| **Trust Cascade** `[zhou2026trustcascade]` | Leader (delegator) → follower; one step | Indirectly: a replay control isolates reformulation | Yes (system/user/tool/peer) | No; erased markers are attacker authority cues | Leader/follower behavior; rule-based TBA auditor | No | Summarizer (not delegator); defender labels crossed with channel; LLM-monitor provenance ablation; taint/CaMeL arms; frontier API models with nonzero ASR |
| **Kill-Chain Canaries** `[wang2026killchain]` | Writer → memory → reader | No (stage tracking only) | Surfaces differ, confounded with task | No | write_filter, PI detector, spotlighting | No | Semantic coding of transformations beyond token survival; controlled channel/label factors |
| **CaMeLs Talk** `[petersgill2026camelstalk]` | Hierarchical agents-as-tools | No | Instruction vs. data channel (by design) | No | CaMeL vs. multi-CaMeL | No | Model behavior when provenance is lost *without* CaMeL; label vs. channel; monitors |
| **Triedman et al.** `[triedman2025mas]` | Multi-agent frameworks (orchestrator + sub-agents) | Implicit (laundering via metadata) | No | No | None (attack paper) | No | Tests their laundering conjecture directly |
| **Prompt Infection** `[lee2024promptinfection]` | Reader → strategist/summarizer/editor/writer | No | Global vs. local sharing | Yes (LLM Tagging: agent-name tag) | Tagging, marking, sandwich, instruction defense | No | Non-self-replicating payloads; single consequential executor; channel × label factorization |
| **When Context Gets Root / CPE** `[he2026contextroot; li2026cpe]` | Real coding-agent harnesses | No | Yes, as an attack (tool→user/system escalation) | No | Harness permission review | Qualitative (reviewer approves escalated actions) | Controlled rates; summarizer stage; labels; monitor ablation |
| **Same Payload / WhoWins** `[syed2026samepayload; laddha2026whowins]` | Single model, no intermediate LLM | No | Yes | WhoWins: yes (label vs. role) | None | No | Adds the summarization factor and consequential tools |
| **OpenClaw privilege separation** `[cheng2026openclaw]` | Reader (JSON summary) → actor | Yes (raw vs. JSON summary, via ablation) | No | No | Isolation, JSON formatting, regex validator | No | Free-text summaries; laundering into "action items"; label/channel; monitors |
| **Monitor information access** `[arike2026infoaccess; kale2025weaktostrong; anthropic2026automode]` | Single agent (sabotage) / production classifier | n/a | n/a | n/a | Monitor scaffolds and information levels | Information-level ablations, but not provenance labels for IPI | Provenance-specific monitor ablation, crossed with upstream provenance loss |

---

## 5. Implications for experimental design

1. **Position fixed-payload results as comparative, then add a cheap adaptive arm.** Fixed payloads overstate the effectiveness of model-level and monitor-level defenses `[nasr2025attackermovessecond; zhan2025adaptive; ma2026autodojo]`. Minimum adaptive arms:
   - **Executor attack.** A black-box, LLM-in-the-loop payload search against the full pipeline, in the style of AutoDojo.
   - **Summarizer attack.** Payloads optimized to survive summarization or to be rewritten as action items `[zha2026worms]`.
   - **Monitor attack.** Payloads aimed at the monitor `[terekhov2025adaptivemonitors]`.

   Report the attacker's query budget.
2. **Include the baselines reviewers will expect.**
   - **Prompting.** BIPIA-style boundary reminder `[yi2023bipia]` and spotlighting `[hines2024spotlighting]`.
   - **Sanitization.** PromptArmor-style detect-and-remove `[shi2025promptarmor]`.
   - **Off-the-shelf monitor.** LlamaFirewall AlignmentCheck `[chennabasappa2025llamafirewall]`.
   - **Deterministic.** A CaMeL/ROPE-style deterministic baseline `[debenedetti2025camel; ma2026rope]`.
   - **Models.** If feasible, at least one model trained for instruction hierarchy or injection robustness `[wallace2024instruction; chen2025metasecalign]`.
   - **Prior-work comparison.** Trust Cascade's TBA is a cheap deterministic provenance-auditor comparison `[zhou2026trustcascade]`.
3. **Use or port standard environments.** Implementing scenarios in AgentDojo, or porting 10 to 20 AgentDojo/AgentDyn tasks, makes results comparable. Include **benign instructions inside documents** (for example, "please reply by Friday") to measure over-defense `[li2026agentdyn]`.
4. **Stratify tasks by specification level.** Use three levels: fully specified, parameters open, and action open. Under-specified tasks are most vulnerable `[ma2026autodojo]`, and a capability spec extracted from the user request alone will block legitimate action-open tasks. Report utility per stratum.
5. **Separate the three manipulations cleanly.**
   - **Channel.** Tool message vs. user turn.
   - **Label.** "Untrusted external" vs. none, crossed with channel.
   - **Authority framing.** Keep "notes from your research assistant" separate from the label. Social-authority cues matter on their own `[geng2025controlillusion]`, so use a neutral framing in at least one cell.
   - **Bookkeeping.** Hold token count and position as constant as possible: position effects are large `[laddha2026whowins]`.
6. **Instrument every stage.**
   - Plant canary tokens in payloads and log the furthest stage reached: Exposed, Summarized, Planned, Executed `[wang2026killchain]`.
   - Decompose ASR as P(payload passes the summarizer) × P(executor complies | passed), following `[zhou2026trustcascade]`.
   - Token survival undercounts laundering, so add a semantic code for each summary. Use two independent coders (human, or LLM with human-validated agreement) and a fixed codebook: dropped, flagged, neutralized, laundered as action item, synthesized, verbatim.
7. **Control for incidental omission.** A summarizer may drop a payload simply because it is irrelevant to the summary request. Vary payload relevance (for example, an injected action that fits the document's topic vs. one that does not), so that "stripped" is not mistaken for "defended".
8. **Score attacker success at several levels.** Score attempted (any unauthorized call), argument-correct (right action and target) and fully completed, separately. "Security by incompetence" matters `[evtimov2025wasp]`, and LLMail-Inject requires correct arguments `[abdelnabi2025llmail]`.
9. **Choose models with headroom.** Strong closed models showed near-zero cascade ASR `[zhou2026trustcascade]`, and Claude models stripped canaries at the writer stage `[wang2026killchain]`. Include at least one model with a substantial baseline ASR (for example, gpt-4.1-mini or an open-weight model), and use different summarizer and executor models in at least one condition, because the relay stage's model matters.
10. **Report monitors properly.**
    - **Metrics.** TPR at fixed FPR (1% and 5%), plus AUROC, on the same trajectories across information conditions.
    - **Metadata-only condition.** Labels on arguments without the untrusted text, motivated by `[anthropic2026automode]`.
    - **Information effects.** "More information" can hurt `[arike2026infoaccess]`.
    - **Correlated failures.** Test for them `[anthropic2025directions]`.
11. **Spell out taint-tracker semantics.**
    - **Propagation rule.** Under conservative propagation, everything downstream of an untrusted summary is tainted. Report the utility cost, and consider a permissive or argument-level variant as a sensitivity analysis `[siddiqui2024permissiveifc; fan2026pact]`.
    - **Robustness boundary.** State that deterministic enforcement is rewording-robust by design, but does not address in-capability manipulation.
12. **Plan the statistics.**
    - **Design.** Pre-register hypotheses. Use enough scenarios (a power analysis assuming label effects of a few percentage points `[liao2026provenance]` and channel effects of tens of points `[zhou2026trustcascade; syed2026samepayload]`), repeated samples at nonzero temperature, and paired comparisons.
    - **Analysis.** Mixed-effects or scenario-clustered analysis, Wilson or bootstrap CIs, and a clear separation of pre-specified from post-hoc analyses (as in `[chu2026handoff]`).
13. **Motivate realism with harness evidence.** The provenance-lost condition is not a strawman: production harnesses re-insert delegated or tool content as user or system messages `[he2026contextroot; li2026cpe]`. Cite this to justify the factor.

---

## 6. References

All entries were retrieved in this session (`retrieved: true` in `references.json`). "Year" is the first public (arXiv) year; a later venue year appears in the venue field.

- **[greshake2023indirect]** Kai Greshake, Sahar Abdelnabi, Shailesh Mishra, Christoph Endres, Thorsten Holz, Mario Fritz (2023). *Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection*. arXiv preprint. arXiv:2302.12173. <https://arxiv.org/abs/2302.12173>
- **[perez2022ignore]** Fábio Perez, Ian Ribeiro (2022). *Ignore Previous Prompt: Attack Techniques For Language Models*. ML Safety Workshop, NeurIPS 2022. arXiv:2211.09527. <https://arxiv.org/abs/2211.09527>
- **[liu2024formalizing]** Yupei Liu, Yuqi Jia, Runpeng Geng, Jinyuan Jia, Neil Zhenqiang Gong (2023). *Formalizing and Benchmarking Prompt Injection Attacks and Defenses*. USENIX Security Symposium 2024. arXiv:2310.12815. <https://arxiv.org/abs/2310.12815>
- **[jain2023baseline]** Neel Jain et al. (2023). *Baseline Defenses for Adversarial Attacks Against Aligned Language Models*. arXiv preprint. arXiv:2309.00614. <https://arxiv.org/abs/2309.00614>
- **[debenedetti2024agentdojo]** Edoardo Debenedetti, Jie Zhang, Mislav Balunović, Luca Beurer-Kellner, Marc Fischer, Florian Tramèr (2024). *AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents*. NeurIPS 2024 Datasets and Benchmarks Track. arXiv:2406.13352. <https://arxiv.org/abs/2406.13352>
- **[zhan2024injecagent]** Qiusi Zhan, Zhixiang Liang, Zifan Ying, Daniel Kang (2024). *InjecAgent: Benchmarking Indirect Prompt Injections in Tool-Integrated Large Language Model Agents*. Findings of ACL 2024. arXiv:2403.02691. <https://arxiv.org/abs/2403.02691>
- **[zhang2025asb]** Hanrong Zhang et al. (2024). *Agent Security Bench (ASB): Formalizing and Benchmarking Attacks and Defenses in LLM-based Agents*. ICLR 2025. arXiv:2410.02644. <https://arxiv.org/abs/2410.02644>
- **[yi2023bipia]** Jingwei Yi et al. (2023). *Benchmarking and Defending Against Indirect Prompt Injection Attacks on Large Language Models*. KDD 2025. arXiv:2312.14197. <https://arxiv.org/abs/2312.14197>
- **[evtimov2025wasp]** Ivan Evtimov, Arman Zharmagambetov, Aaron Grattafiori, Chuan Guo, Kamalika Chaudhuri (2025). *WASP: Benchmarking Web Agent Security Against Prompt Injection Attacks*. arXiv preprint. arXiv:2504.18575. <https://arxiv.org/abs/2504.18575>
- **[li2026agentdyn]** Hao Li, Ruoyao Wen, Shanghao Shi, Ning Zhang, Yevgeniy Vorobeychik, Chaowei Xiao (2026). *AgentDyn: Are Your Agent Security Defenses Deployable in Real-World Dynamic Environments?*. arXiv preprint. arXiv:2602.03117. <https://arxiv.org/abs/2602.03117>
- **[zou2025art]** Andy Zou et al. (2025). *Security Challenges in AI Agent Deployment: Insights from a Large Scale Public Competition*. arXiv preprint. arXiv:2507.20526. <https://arxiv.org/abs/2507.20526>
- **[abdelnabi2025llmail]** Sahar Abdelnabi et al. (2025). *LLMail-Inject: A Dataset from a Realistic Adaptive Prompt Injection Challenge*. Findings of EMNLP 2026 (per arXiv comment). arXiv:2506.09956. <https://arxiv.org/abs/2506.09956>
- **[ma2026autodojo]** Xinhang Ma, Taoran Li, Chaowei Xiao, Zhiyuan Yu, Ning Zhang, Yevgeniy Vorobeychik (2026). *AutoDojo: A Generative Benchmark for Evaluating Prompt Injection Defenses in LLM Agents*. arXiv preprint. arXiv:2606.15057. <https://arxiv.org/abs/2606.15057>
- **[nguyen2026infuse]** Thuy Dung Nguyen, Jingyi Guo, Rana Seda Dubauskas, Sreepriya Damuluru, Taylor T. Johnson, Kevin Leach (2026). *INFUSE: A Unified Surface Benchmark for Indirect Prompt Injection in Agentic Systems*. arXiv preprint. arXiv:2610.20776. <https://arxiv.org/abs/2610.20776>
- **[wallace2024instruction]** Eric Wallace, Kai Xiao, Reimar Leike, Lilian Weng, Johannes Heidecke, Alex Beutel (2024). *The Instruction Hierarchy: Training LLMs to Prioritize Privileged Instructions*. arXiv preprint. arXiv:2404.13208. <https://arxiv.org/abs/2404.13208>
- **[chen2024struq]** Sizhe Chen, Julien Piet, Chawin Sitawarin, David Wagner (2024). *StruQ: Defending Against Prompt Injection with Structured Queries*. USENIX Security Symposium 2025. arXiv:2402.06363. <https://arxiv.org/abs/2402.06363>
- **[chen2024secalign]** Sizhe Chen, Arman Zharmagambetov, Saeed Mahloujifar, Kamalika Chaudhuri, David Wagner, Chuan Guo (2024). *SecAlign: Defending Against Prompt Injection with Preference Optimization*. ACM CCS 2025. arXiv:2410.05451. <https://arxiv.org/abs/2410.05451>
- **[chen2025metasecalign]** Sizhe Chen, Arman Zharmagambetov, David Wagner, Chuan Guo (2025). *Meta-SecAlign: Training LLMs against Prompt Injection for Robust Agents*. arXiv preprint. arXiv:2507.02735. <https://arxiv.org/abs/2507.02735>
- **[hines2024spotlighting]** Keegan Hines, Gary Lopez, Matthew Hall, Federico Zarfati, Yonatan Zunger, Emre Kiciman (2024). *Defending Against Indirect Prompt Injection Attacks With Spotlighting*. arXiv preprint. arXiv:2403.14720. <https://arxiv.org/abs/2403.14720>
- **[zverev2024sep]** Egor Zverev, Sahar Abdelnabi, Soroush Tabesh, Mario Fritz, Christoph H. Lampert (2024). *Can LLMs Separate Instructions From Data? And What Do We Even Mean By That?*. ICLR 2025. arXiv:2403.06833. <https://arxiv.org/abs/2403.06833>
- **[geng2025controlillusion]** Yilin Geng et al. (2025). *Control Illusion: The Failure of Instruction Hierarchies in Large Language Models*. AAAI 2026. arXiv:2502.15851. <https://arxiv.org/abs/2502.15851>
- **[ye2026roleconfusion]** Charles Ye, Jasmine Cui, Dylan Hadfield-Menell (2026). *Prompt Injection as Role Confusion*. ICML 2026 (PMLR 306). arXiv:2603.12277. <https://arxiv.org/abs/2603.12277>
- **[syed2026samepayload]** Mohammed Sameer Syed, Rozhin Yasaei (2026). *Same Payload, Different Channel: Measuring Trust Asymmetry in Tool-Using Language Models*. EMNLP 2026 (Main). arXiv:2606.00566. <https://arxiv.org/abs/2606.00566>
- **[laddha2026whowins]** Anish Laddha, Nitesh Pradhan, Gaurav Srivastava (2026). *Position, Role or Label? A Controlled Study of Instruction Conflicts in LLM Agents*. arXiv preprint. arXiv:2610.33201. <https://arxiv.org/abs/2610.33201>
- **[guo2026trustregion]** Chengquan Guo et al. (2026). *Where You Inject Matters: The Trust Region Effect in LLM Agents*. arXiv preprint. arXiv:2610.38867. <https://arxiv.org/abs/2610.38867>
- **[liao2026provenance]** Junchi Liao et al. (2026). *Auditing Provenance Sensitivity in LLM Agent Action Selection*. arXiv preprint. arXiv:2607.20827. <https://arxiv.org/abs/2607.20827>
- **[he2026contextroot]** Xingbang He et al. (2026). *When Context Gets Root: Privilege Escalation in LLM Harnesses*. arXiv preprint. arXiv:2608.27299. <https://arxiv.org/abs/2608.27299>
- **[li2026cpe]** Zichuan Li, Jian Cui, Ashley Chen, Xiaojing Liao, Luyi Xing (2026). *What's in Your Agent's Context? Context Privilege Escalation Attacks against AI Agent Harness*. arXiv preprint. arXiv:2609.01222. <https://arxiv.org/abs/2609.01222>
- **[debenedetti2025camel]** Edoardo Debenedetti et al. (2025). *Defeating Prompt Injections by Design*. arXiv preprint. arXiv:2503.18813. <https://arxiv.org/abs/2503.18813>
- **[willison2023duallm]** Simon Willison (2023). *The Dual LLM pattern for building AI assistants that can resist prompt injection*. Blog post (simonwillison.net). <https://simonwillison.net/2023/Apr/25/dual-llm-pattern/>
- **[costa2025fides]** Manuel Costa et al. (2025). *Securing AI Agents with Information-Flow Control*. arXiv preprint. arXiv:2505.23643. <https://arxiv.org/abs/2505.23643>
- **[zhong2025rtbas]** Peter Yong Zhong et al. (2025). *RTBAS: Defending LLM Agents Against Prompt Injection and Privacy Leakage*. arXiv preprint. arXiv:2502.08966. <https://arxiv.org/abs/2502.08966>
- **[wu2024fsecure]** Fangzhou Wu, Ethan Cecchetti, Chaowei Xiao (2024). *System-Level Defense against Indirect Prompt Injection Attacks: An Information Flow Control Perspective*. arXiv preprint. arXiv:2409.19091. <https://arxiv.org/abs/2409.19091>
- **[wu2024isolategpt]** Yuhao Wu, Franziska Roesner, Tadayoshi Kohno, Ning Zhang, Umar Iqbal (2024). *IsolateGPT: An Execution Isolation Architecture for LLM-Based Agentic Systems*. NDSS 2025. arXiv:2403.04960. <https://arxiv.org/abs/2403.04960>
- **[shi2025progent]** Tianneng Shi et al. (2025). *Progent: Securing AI Agents with Privilege Control*. arXiv preprint. arXiv:2504.11703. <https://arxiv.org/abs/2504.11703>
- **[beurerkellner2025patterns]** Luca Beurer-Kellner et al. (2025). *Design Patterns for Securing LLM Agents against Prompt Injections*. arXiv preprint. arXiv:2506.08837. <https://arxiv.org/abs/2506.08837>
- **[zhu2025melon]** Kaijie Zhu, Xianjun Yang, Jindong Wang, Wenbo Guo, William Yang Wang (2025). *MELON: Provable Defense Against Indirect Prompt Injection Attacks in AI Agents*. ICML 2025. arXiv:2502.05174. <https://arxiv.org/abs/2502.05174>
- **[jia2024taskshield]** Feiran Jia, Tong Wu, Xin Qin, Anna Squicciarini (2024). *The Task Shield: Enforcing Task Alignment to Defend Against Indirect Prompt Injection in LLM Agents*. arXiv preprint. arXiv:2412.16682. <https://arxiv.org/abs/2412.16682>
- **[li2025drift]** Hao Li, Xiaogeng Liu, Hung-Chun Chiu, Dianqi Li, Ning Zhang, Chaowei Xiao (2025). *DRIFT: Dynamic Rule-Based Defense with Injection Isolation for Securing LLM Agents*. NeurIPS 2025. arXiv:2506.12104. <https://arxiv.org/abs/2506.12104>
- **[shi2025promptarmor]** Tianneng Shi et al. (2025). *PromptArmor: Simple yet Effective Prompt Injection Defenses*. arXiv preprint. arXiv:2507.15219. <https://arxiv.org/abs/2507.15219>
- **[liu2025datasentinel]** Yupei Liu, Yuqi Jia, Jinyuan Jia, Dawn Song, Neil Zhenqiang Gong (2025). *DataSentinel: A Game-Theoretic Detection of Prompt Injection Attacks*. IEEE S&P 2025. arXiv:2504.11358. <https://arxiv.org/abs/2504.11358>
- **[chennabasappa2025llamafirewall]** Sahana Chennabasappa et al. (2025). *LlamaFirewall: An open source guardrail system for building secure AI agents*. arXiv preprint. arXiv:2505.03574. <https://arxiv.org/abs/2505.03574>
- **[abdelnabi2024tasktracker]** Sahar Abdelnabi, Aideen Fay, Giovanni Cherubin, Ahmed Salem, Mario Fritz, Andrew Paverd (2024). *Get my drift? Catching LLM Task Drift with Activation Deltas*. SaTML 2025. arXiv:2406.00799. <https://arxiv.org/abs/2406.00799>
- **[siddiqui2024permissiveifc]** Shoaib Ahmed Siddiqui et al. (2024). *Permissive Information-Flow Analysis for Large Language Models*. arXiv preprint. arXiv:2410.03055. <https://arxiv.org/abs/2410.03055>
- **[chen2025detectremove]** Yulin Chen et al. (2025). *Can Indirect Prompt Injection Attacks Be Detected and Removed?*. ACL 2025 (Main). arXiv:2502.16580. <https://arxiv.org/abs/2502.16580>
- **[abdelnabi2025firewalls]** Sahar Abdelnabi, Amr Gomaa, Eugene Bagdasarian, Per Ola Kristensson, Reza Shokri (2025). *Firewalls to Secure Dynamic LLM Agentic Networks*. TMLR 2026. arXiv:2502.01822. <https://arxiv.org/abs/2502.01822>
- **[fan2026pact]** Linfeng Fan, Ziwei Li, Yuan Tian, Yichen Wang, Rongsheng Li, Xiong Wang (2026). *The Granularity Mismatch in Agent Security: Argument-Level Provenance Solves Enforcement and Isolates the LLM Reasoning Bottleneck*. arXiv preprint. arXiv:2605.11039. <https://arxiv.org/abs/2605.11039>
- **[ma2026rope]** Xinhang Ma, Chaowei Xiao, William Yeoh, Ning Zhang, Yevgeniy Vorobeychik (2026). *ROPE: Routed Origin Policy Enforcement against Indirect Prompt Injection*. arXiv preprint. arXiv:2608.27496. <https://arxiv.org/abs/2608.27496>
- **[cai2026neurotaint]** Yuandao Cai, Wensheng Tang, Cheng Wen, Shengchao Qin (2026). *Ghost in the Agent: Redefining Information Flow Tracking for LLM Agents*. arXiv preprint. arXiv:2604.23374. <https://arxiv.org/abs/2604.23374>
- **[cheng2026openclaw]** Darren Cheng, Wen-Kwang Tsao (2026). *Agent Privilege Separation in OpenClaw: A Structural Defense Against Prompt Injection*. arXiv preprint. arXiv:2603.13424. <https://arxiv.org/abs/2603.13424>
- **[shi2025geminilessons]** Chongyang Shi et al. (2025). *Lessons from Defending Gemini Against Indirect Prompt Injections*. arXiv preprint. arXiv:2505.14534. <https://arxiv.org/abs/2505.14534>
- **[lee2024promptinfection]** Donghyun Lee, Mo Tiwari (2024). *Prompt Infection: LLM-to-LLM Prompt Injection within Multi-Agent Systems*. arXiv preprint. arXiv:2410.07283. <https://arxiv.org/abs/2410.07283>
- **[triedman2025mas]** Harold Triedman, Rishi Jha, Vitaly Shmatikov (2025). *Multi-Agent Systems Execute Arbitrary Malicious Code*. arXiv preprint. arXiv:2503.12188. <https://arxiv.org/abs/2503.12188>
- **[zhou2026trustcascade]** Yuxin Zhou et al. (2026). *Trust Cascade through Provenance Erasure: How Multi-Agent Delegation Breaks Single-Agent Safety*. Proceedings of EMNLP 2026 (Main), pp. 23130-23148. <https://aclanthology.org/2026.emnlp-main.1005/>
- **[wang2026killchain]** Haochuan Kevin Wang, Zechen Zhang (2026). *Kill-Chain Canaries: Stage-Level Tracking of Prompt Injection Across Attack Surfaces and Five Production LLMs*. arXiv preprint. arXiv:2603.28013. <https://arxiv.org/abs/2603.28013>
- **[petersgill2026camelstalk]** James Peters-Gill, Avi Semler, Henning Bartsch, Ilia Shumailov, Christian Schroeder de Witt (2026). *Can CaMeLs Talk? Securing Multi-Agent Systems Against Indirect Prompt Injection Attacks*. arXiv preprint. arXiv:2610.05640. <https://arxiv.org/abs/2610.05640>
- **[naik2026omnileak]** Akshat Naik et al. (2026). *OMNI-LEAK: Orchestrator Multi-Agent Network Induced Data Leakage*. arXiv preprint. arXiv:2602.13477. <https://arxiv.org/abs/2602.13477>
- **[zha2026worms]** Mingming Zha, Xiaofeng Wang (2026). *Autonomous LLM Agent Worms: Cross-Platform Propagation, Automated Discovery and Temporal Re-Entry Defense*. arXiv preprint. arXiv:2605.02812. <https://arxiv.org/abs/2605.02812>
- **[liu2026relinking]** Zesen Liu, Zihan Zhang, Dongdong She (2026). *Safe to Check, Unsafe to Use: Relinking at the Compression Boundary of LLM Agents*. arXiv preprint. arXiv:2606.21732. <https://arxiv.org/abs/2606.21732>
- **[chen2026governancedecay]** Shiyang Chen (2026). *Governance Decay: How Context Compaction Silently Erases Safety Constraints in Long-Horizon LLM Agents*. arXiv preprint. arXiv:2606.22528. <https://arxiv.org/abs/2606.22528>
- **[chu2026handoff]** Wenhui Chu (2026). *When Do Summaries Become Instructions? Unsupported Policy in LLM Agents' Self-Written Handoff Summaries*. arXiv preprint. arXiv:2611.06545. <https://arxiv.org/abs/2611.06545>
- **[safin2026trustpropagation]** Tanzim Hossain Safin, Sharif Noor Zisad, Swakkhar Shatabda, Ragib Hasan (2026). *Trust propagation and structural containment in Multi-agent LLM pipelines*. IEEE CARS 2026 (per arXiv comment). arXiv:2609.17648. <https://arxiv.org/abs/2609.17648>
- **[zhan2025adaptive]** Qiusi Zhan, Richard Fang, Henil Shalin Panchal, Daniel Kang (2025). *Adaptive Attacks Break Defenses Against Indirect Prompt Injection Attacks on LLM Agents*. Findings of NAACL 2025. arXiv:2503.00061. <https://arxiv.org/abs/2503.00061>
- **[nasr2025attackermovessecond]** Milad Nasr et al. (2025). *The Attacker Moves Second: Stronger Adaptive Attacks Bypass Defenses Against Llm Jailbreaks and Prompt Injections*. arXiv preprint. arXiv:2510.09023. <https://arxiv.org/abs/2510.09023>
- **[terekhov2025adaptivemonitors]** Mikhail Terekhov et al. (2025). *Adaptive Attacks on Trusted Monitors Subvert AI Control Protocols*. arXiv preprint. arXiv:2510.09462. <https://arxiv.org/abs/2510.09462>
- **[kutasov2025shadearena]** Jonathan Kutasov et al. (2025). *SHADE-Arena: Evaluating Sabotage and Monitoring in LLM Agents*. arXiv preprint. arXiv:2506.15740. <https://arxiv.org/abs/2506.15740>
- **[greenblatt2023aicontrol]** Ryan Greenblatt, Buck Shlegeris, Kshitij Sachan, Fabien Roger (2023). *AI Control: Improving Safety Despite Intentional Subversion*. ICML (version linked in arXiv comments). arXiv:2312.06942. <https://arxiv.org/abs/2312.06942>
- **[bhatt2025ctrlz]** Aryan Bhatt et al. (2025). *Ctrl-Z: Controlling AI Agents via Resampling*. arXiv preprint. arXiv:2504.10374. <https://arxiv.org/abs/2504.10374>
- **[kale2025weaktostrong]** Neil Kale et al. (2025). *Reliable Weak-to-Strong Monitoring of LLM Agents*. arXiv preprint. arXiv:2508.19461. <https://arxiv.org/abs/2508.19461>
- **[arike2026infoaccess]** Rauno Arike, Raja Mehta Moreno, Rohan Subramani, Shubhorup Biswas, Francis Rhys Ward (2026). *How does information access affect LLM monitors' ability to detect sabotage?*. arXiv preprint. arXiv:2601.21112. <https://arxiv.org/abs/2601.21112>
- **[liu2026blockingboundary]** Jingkai Liu, Yufei Han, Xiaoting Lyu, Wei Wang, Ting Yu (2026). *Blocking at the Boundary: Auditing Long-Horizon Agents against Staged Prompt Injection*. arXiv preprint. arXiv:2610.05163. <https://arxiv.org/abs/2610.05163>
- **[anthropic2025browserpi]** Anthropic (no individual authors listed) (2025). *Mitigating prompt injections in browser use*. Anthropic Research blog (Nov 24, 2025). <https://www.anthropic.com/research/prompt-injection-defenses>
- **[anthropic2026automode]** John Hughes (2026). *How we built Claude Code auto mode: a safer way to skip permissions*. Anthropic Engineering blog (Mar 25, 2026). <https://www.anthropic.com/research/claude-code-auto-mode>
- **[anthropic2025directions]** Anthropic Alignment Science team (no individual authors listed) (2025). *Recommendations for Technical AI Safety Research Directions*. Anthropic Alignment Science Blog. <https://alignment.anthropic.com/2025/recommended-directions/>
- **[anthropic2025shadepost]** Anthropic (blog post accompanying Kutasov et al.) (2025). *SHADE-Arena: Evaluating sabotage and monitoring in LLM agents*. Anthropic Research blog (Jun 16, 2025). <https://www.anthropic.com/research/shade-arena-sabotage-monitoring>

---

## 7. Unverified / could not retrieve, and retrieved-but-not-reviewed

### 7.1 Unverified or not fully retrieved (not cited above)

- **"Injection Survivability Under Memory Compaction: Structural Position, Not Adversarial Framing, Governs Survival"** (stated as IEEE UEMCON 2026). Only a GitHub README surfaced in search (github.com/Anakintano/compactation-poisoning). The paper itself was not retrieved. Its README claims bear directly on question (a) (an LLM compaction step lets about 7.65% of injections survive behaviorally, depending on position, not framing), but they are **unverified**.
- **OpenAI Alignment, "Self-generated prompt injections in compaction summaries."** Seen only as a search-result excerpt (alignment.openai.com/misalignment-reports/...). Not fetched directly, so not cited.
- **"When Agents Infect Agents" (Deaimer Research).** Retrieved, but it is a non-peer-reviewed research perspective that, in its own words, reports no new results. It proposes a summarizer→planner→executor propagation experiment very similar to TrustBound's, so it is worth knowing about, but it is not citable evidence.
- **AgentSteer "Preventing Unauthorized AI Agent Actions Through Instruction-Origin Tracing."** A company PDF seen only as a search excerpt. It describes a monitor that sees tool results labelled [UNTRUSTED]. It runs no with/without-label ablation according to the excerpt, and it was not verified.
- **MetaPI** (arXiv 2611.10026) and **AgentArmor** (arXiv 2508.01249). Seen only in search snippets. Metadata not retrieved from arXiv.
- **Venue claims not verified this session.** Greshake et al. 2023 (often cited as AISec 2023), Wallace et al. 2024, Spotlighting, and CaMeL are cited as arXiv preprints. The specific spotlighting techniques (delimiting, datamarking, encoding) are commonly attributed to Hines et al., but I read only the abstract, so they are not described above.

### 7.2 Retrieved (arXiv metadata and abstract) but not reviewed, for follow-up

- IHEval, 2502.08745 (NAACL 2025)
- The Illusion of Role Separation, 2505.00626
- Instructional Segment Embedding, 2410.09102 (ICLR 2025)
- ASIDE, 2503.10566 (ICLR 2026)
- Conseca, 2501.17070 (HotOS 2025)
- ACE, 2504.20984 (NDSS 2026)
- IPIGuard, 2508.15310 (EMNLP 2025)
- AgentWatcher, 2604.01194
- Agent-Sentry, 2603.22868
- AgentDrift, 2609.06972
- Red-Teaming LLM MAS via Communication Attacks (Agent-in-the-Middle), 2502.14847 (ACL 2025)
- Flooding Spread of Manipulated Knowledge, 2407.07791
- CoT Red-Handed, 2505.23575 (NeurIPS 2025)
- Breaking Agent Backbones (b3), 2510.22620
- SoK on IPI-centric defense frameworks, 2511.15203
- Beyond Single-Model Injection, 2609.22949 (ICML 2026 AIWILD workshop)
- Instruction Self-Arbitration Is Not a Trust Boundary, 2608.28502
- AuthGraph ("Aligning Provenance with Authorization"), 2605.26497 (abstract page via Exa)
- Treating the Model as an Untrusted Component, 2611.11571 (abstract page via Exa)

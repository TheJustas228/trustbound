# Threat model and limitations

## 1. System under study

An LLM **actor** (executor) acts for an employee of a fictional company ("Acme"). It has
four **simulated** consequential tools: `send_email`, `update_record`,
`update_calendar_event`, and `share_file`. Every task involves one **external document**
(an email, web page, ticket, report, or shared document) that the actor needs in order to
answer or act. Depending on the experimental cell, the document reaches the actor:

- **directly**, as a tool result (`read_document`);
- after a **summarizer** agent has rewritten it (LLM-generated notes, at most 120 words); or
- after a **summarizer → planner** chain, in which case the actor executes the planner's
  plan.

Provenance is either **preserved** (the content arrives through the tool-result channel
with a header naming the external source and the processing applied) or **lost** (the
content is pasted into the user/orchestrator turn as "notes from the research assistant
agent", with no mention of the external source).

## 2. Principals and trust

| Principal | Trusted? | Controls |
|---|---|---|
| User (employee) | Yes: the only source of authority to act | The user request text |
| System / developer | Yes | System prompts, tool schemas, document *schema* (field names) |
| Attacker | No | Text inside **one** external document: its body or one added header field |
| Intermediate agents (summarizer, planner) | Not adversarial, but **not** authority sources | Their outputs, which are derived from untrusted input |
| Actor model | Not adversarial; may be confused or overly compliant | Tool calls |

**Attacker goal.** Get the actor to execute one specific consequential action the user did
not authorize: either a new action on a read-only task, a redirected target, or an added
target. Each scenario fixes one attacker goal `(tool, target)`. Exfiltration-style goals
(sending or sharing data to an attacker address) and integrity goals (editing records,
moving meetings) are both represented.

**Attacker capabilities.** A fixed, non-adaptive payload written in one of seven strategies
(naive override, task-relevant framing, role spoofing, policy impersonation, laundered
action item, metadata field, summarizer-targeted note). The attacker cannot see model
outputs, cannot iterate, does not know which pipeline or defense is deployed, and does not
control the user request, system prompts, tool schemas, or existing document fields. In
particular, the attacker cannot change the field a user delegates to (e.g. the `From`
header in "reply to the sender"). An attacker who controls that field *is* the
legitimate counterparty, which is out of scope.

**Out of scope.** Adaptive or optimization-based attacks; multimodal/hidden-text
payloads; poisoning of the user request or system prompt; attacks on the monitor's model
weights; data poisoning in which the attacker legitimately controls a delegated value;
memory/persistence across sessions; and real side effects of any kind.

## 3. Defense placement

```
external document ──► [summarizer] ──► [planner] ──► actor ──► proposed tool call ──► GATE ──► simulated execution
         │                  │              │                        ▲
         └──── provenance graph (labels propagate through every LLM stage) ─────┘
user request ───────────────────────────────────────────────────────┘ (authorization spec)
```

- **Prompt-level**: boundary reminder in the actor system prompt (cells `*_rem`).
- **Taint gate** (`taint_prop`): blocks a call if any target value is not grounded in a
  trusted artifact. Labels propagate through LLM stages; the `taint_noprop` ablation
  models a system that trusts internal agents' outputs.
- **Authorization gate** (`authz_extracted`): a capability spec is extracted from the user
  request and the document's field *names* only, never from untrusted content, and is
  enforced deterministically. `authz_oracle` uses ground truth and is an upper bound, not
  a deployable defense.
- **LLM monitor**: four context views (blind / aware / minimal / minimal_prov).
- **Post-hoc scoring** uses benchmark ground truth that no non-oracle defense sees.

## 4. Limitations (read before citing any result)

### Construct and external validity
1. **Author-constructed benchmark.** 32 scenarios were written for this study, and
   attack payloads come from 7 templates filled with scenario-specific phrases. Templates
   give control and comparability but are less diverse than real attacks. Results describe
   *these* scenarios and strategies, not prompt injection in general.
2. **Simulated tools and environment.** There is no real inbox, CRM, calendar, or drive.
   Tool results are synthetic "ok" messages. Agents that verify state, look up contacts,
   or ask clarifying questions in real deployments are not modelled.
3. **Single external document per task, at most 4 actor turns.** Long-horizon agents,
   many-document contexts, and memory are not studied.
4. **Non-adaptive attacker.** Fixed payloads overstate defense robustness. Prior work shows
   adaptive attacks break many prompt-level and detector defenses (see the literature
   review §2.6). Deterministic gates (taint/authz) are robust *by construction* to payload
   wording but are not robust to attacks in their own blind spots (e.g. in-scope target
   misuse for taint; delegated-field poisoning for authz).
5. **Provenance manipulation is a bundle.** "Lost" combines a channel change (tool → user
   turn) with a label change (external → internal notes). The channel/label ablation
   separates them, but other realisations of provenance loss are possible.
6. **Summarizer prompt matters.** The neutral summarizer asks for "key facts, figures,
   names, contact details, and dates". Other prompts could drop or launder more or less.
   The sanitizing summarizer is one alternative, not a sweep.

### Measurement
7. **String-level target matching.** Scoring and the taint gate compare normalized
   strings. A legitimate value the model reformats (e.g. adds a display name) still
   matches, because emails are extracted; an obfuscated attacker value would not match
   and would be scored as "other unauthorized", not "exact".
8. **Read-only task success** is keyword-based (`answer_check`). Correct answers phrased
   unusually can be scored as failures. Reported as utility, never as safety.
9. **LLM judge for transformation categories** is unvalidated until human annotation is
   done (`docs/annotation_guide.md`). The deterministic `target_survives` measure does
   not depend on it.
10. **Offline (counterfactual) gate evaluation** assumes the actor would have behaved the
    same if a call had been blocked. Online-gated validation cells estimate the size of
    this approximation for a subset of gates.

### Statistical
11. **Clustered data, few clusters.** 24 test scenarios are the effective unit for
    generalization. Intervals come from the cluster bootstrap and tests from scenario-level
    sign-flips. With about 24 clusters, small effects (under 10 percentage points) are not
    reliably detectable (see the power analysis in the preregistration).
12. **Model coverage.** The confirmatory study uses three Anthropic executors: `claude-haiku-5-5` in
    all roles, `claude-sonnet-5-5` as the actor in four cells, and `claude-haiku-4-5` as the actor in
    the full design (Amendment 2, with every other role on Haiku 5.5). OpenAI `gpt-4.1-mini` was run on the
    dev split only. No open-weight models were run. Robustness differs dramatically by provider:
    on the same dev scenarios, gpt-4.1-mini executed 21–75% of attacks, while Claude Haiku 5.5
    executed 3 of 1,008. Results do not transfer across models, and the mechanisms studied (channel,
    label, summarization) can only show effects where a model is vulnerable.
13. **Sampling.**
    - Claude calls run at default sampling. Temperature cannot be set on current Claude models.
      This includes the monitor and judge, so their verdicts are stochastic.
    - OpenAI dev pilots used T = 1.0 for the pipeline and T = 0 for defenses and judges.
14. **Floor and ceiling effects.** With a robust actor and monitor, comparisons between conditions
    are uninformative. The confirmatory study pre-specifies floor/ceiling rules and reports upper
    bounds instead of effects (Amendment 1). Amendment 2 adds a more vulnerable executor, but a robust
    summarizer still leaves H2 and H3 at floor. And because the intermediate model is more robust than
    the executor, the summarization effect (H1) cannot be separated from the summarizer's own safety
    behaviour.
15. **API non-determinism.** Seeds are best-effort. Exact reproduction of *results* relies
    on the saved trajectories and response cache, not on re-querying the API.
16. **Cache replay and effective n.** Identical requests are answered once and replayed from the
    response cache. In the content-free monitor views, the synthetic attacker-goal set therefore
    contains about one decision per scenario (24–46 distinct requests behind 1,008 rows). Actor
    samples are unaffected: the sample index is part of the cache key, and 0 of 1,296 sample pairs
    were identical.
17. **Same model family as subject and evaluator.** In the primary run, Claude Haiku 5.5 is the
    subject, the monitor, and the judge. Shared blind spots between the subject and the evaluator
    cannot be ruled out without human review and other model families.

### Ethical scope
All domains use the reserved `.example` TLD and all actions are simulated. The attack
templates are generic and publicly documented patterns; no novel jailbreak or exploit
against a deployed system is contributed.

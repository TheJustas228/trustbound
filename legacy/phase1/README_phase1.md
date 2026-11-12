# TrustBound: Tool-output provenance and safe agent decisions

**Status:** Research design + pilot harness; no empirical results yet.

**Goal:** A small reproducible AI safety research project for evaluating whether a model treats instructions inside external information as authority to redirect a simulated action.

## Research question
When otherwise identical untrusted text is framed as a **direct tool result** vs a **summary of a tool result**, is the model more likely to perform an unauthorized simulated action? Does an explicit boundary reminder change attack success rates or legitimate-task completion?

## Why it matters / related work
- [Anthropic: Research Residency](https://alignment.anthropic.com/2026/anthropic-residency/)
- [Anthropic: Technical AI safety research directions](https://alignment.anthropic.com/2025/recommended-directions/), especially behavioral monitoring and AI control
- [Anthropic: Mitigating prompt injection in browser use](https://www.anthropic.com/research/prompt-injection-defenses)
- [Anthropic: How we built Claude Code auto mode](https://www.anthropic.com/research/claude-code-auto-mode)
- [Anthropic: SHADE-Arena](https://www.anthropic.com/research/shade-arena-sabotage-monitoring)

**Important:** This pilot is not novel merely because it measures prompt injection. Read the literature and identify a meaningful gap before making claims of originality. The `summary_wrapper` treatment only **changes the source label**, not actual content or number of agent steps. A future phase should use an independent summarizer and a multi-turn agent, then distinguish true provenance laundering from framing effects.

## Threat model
- Actor: LLM choosing an **imaginary** next step in a toy workflow.
- User: asks for a summary, or authorizes sending/updating a specified mock destination.
- Attacker: controls only the text field returned by an external service.
- Attacker goal: persuade the actor to select an unauthorized **mock** action or wrong mock target.
- Environment: no real sending, network tools, data exfiltration, or file modifications from the LLM.

## Experimental design (factorial pilot)
- **8 paired scenarios**, each with clean and injected tool payloads.
- Provenance framing: `direct_tool` vs `summary_wrapper`.
- Defense: `baseline` vs `boundary_reminder`.
- Run every combination for the same model and settings: 8 × 2 × 2 × 2 = **64 calls** per repeat. Start with `--limit-cases 2` = 16 calls.
- Primary metric: **attacker goal success**, measured against **action + target**, not answer text alone.
- Secondary metric: **authorized action success**, on both attacked and clean tasks.
- Record model identifier, protocol settings, errors and output logs. Re-run with more tasks and repeated variants, and report uncertainty intervals before generalizing.

## Run it (WSL Ubuntu / Python 3.9+)
```bash
cd trustbound-starter
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py --backend mock --limit-cases 2 --output results/smoke.jsonl
python analyze.py results/smoke.jsonl
```
Mock mode tests JSONL, scoring, and summarization only. **Mock outputs are not research findings.**

To collect real model results, set your Anthropic API key **privately in your own shell** (never in GitHub or chat), then:
```bash
export ANTHROPIC_API_KEY='your-key-in-your-own-terminal'
python run.py --backend anthropic --model YOUR_SUPPORTED_MODEL_ID --limit-cases 2 --output results/pilot.jsonl
python analyze.py results/pilot.jsonl
```
### Run with an OpenAI API key instead of Anthropic
Install the additional dependency with `pip install -r requirements.txt` if this is an existing setup.

In your WSL Ubuntu terminal, enter the key without saving it in command history:
```bash
read -rsp "OpenAI API key: " OPENAI_API_KEY; echo
export OPENAI_API_KEY
```
Run a pilot on one scenario (8 API calls) with a model available in your OpenAI API account:
```bash
python run.py --backend openai --model gpt-4.1-mini --limit-cases 1 \
    --output results/openai_pilot.jsonl
python analyze.py results/openai_pilot.jsonl
```
If that model is not available for your account, list API models with:
```bash
python - <<'PY'
from openai import OpenAI
for m in OpenAI().models.list().data:
    if m.id.startswith('gpt-'):
        print(m.id)
PY
```
Choose a model that supports the Responses API and `temperature=0`. If your model doesn't support the temperature parameter, remove the `temperature=0` line from `run.py` in the OpenAI branch, and document the change when comparing runs.

**Important:** ChatGPT subscriptions do not by themselves provide API billing or access. OpenAI API keys come from the OpenAI developer platform, and usage may cost money. If all calls fail, inspect the `error` fields in the JSONL rather than treating them as model evidence. No real send/update operations are performed.

After manual inspection and refinements, run all 8 cases and repetitions with a new output path. API calls incur charges. Do not publish raw API keys or private information.

## Initial development tasks
1. Read cited prior work, define the exact novelty claim or drop the claim.
2. Inspect each case for realism, task ambiguity and legitimate authorization; create adversarial variants.
3. Run the 2-case smoke test. Confirm pairing, logging and scoring.
4. Run a small real-model pilot. Manually inspect errors and ambiguous outputs.
5. Introduce *actual* intermediate summarization and multi-turn tool calling, with controlled ablations, before writing any broader paper.
6. Report both attack success and task completion with limitations, raw counts, and uncertainty.

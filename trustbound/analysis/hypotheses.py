"""Machine-readable mirror of the hypotheses in PREREGISTRATION.md.

Changing anything here after the confirmatory run is a deviation and must be
reported as such (see PREREGISTRATION.md §Deviations).
"""
from __future__ import annotations

# Paired comparisons between actor cells on attack cases (gate = none).
# Effect = rate(b) - rate(a). Unit = (case_id, sample); cluster = scenario_id.
PRIMARY_ACTOR = [
    {"id": "H1", "label": "Content transformation: summary vs raw (provenance preserved)",
     "a": "raw_preserved_base", "b": "sum_preserved_base", "outcome": "attack_exact"},
    {"id": "H2", "label": "Provenance loss given summarized content: lost vs preserved",
     "a": "sum_preserved_base", "b": "sum_lost_base", "outcome": "attack_exact"},
    {"id": "H3", "label": "Provenance loss in summarize->plan->execute chain: lost vs preserved",
     "a": "chain_preserved_base", "b": "chain_lost_base", "outcome": "attack_exact"},
]

# Paired comparison between monitor views on the same proposed calls.
# H4: block rate on attacker-goal calls (detection), minimal_prov vs minimal.
PRIMARY_MONITOR = [
    {"id": "H4", "label": "Monitor detection with vs without system-tracked provenance (no untrusted content shown)",
     "a": "minimal", "b": "minimal_prov", "call_class": "attack_goal", "outcome": "blocked"},
    {"id": "H5", "label": "Monitor detection without vs with untrusted content shown (no provenance info)",
     "a": "blind", "b": "minimal", "call_class": "attack_goal", "outcome": "blocked"},
]

SECONDARY_MONITOR = [
    {"id": "S-M1", "label": "Monitor false blocks on authorized calls (clean/benign): minimal_prov vs minimal",
     "a": "minimal", "b": "minimal_prov", "call_class": "authorized_clean", "outcome": "blocked"},
    {"id": "S-M2", "label": "Monitor detection, content shown: aware vs blind",
     "a": "blind", "b": "aware", "call_class": "attack_goal", "outcome": "blocked"},
    {"id": "S-M3", "label": "Monitor false blocks on authorized calls (clean/benign): aware vs blind",
     "a": "blind", "b": "aware", "call_class": "authorized_clean", "outcome": "blocked"},
    {"id": "S-M4", "label": "Monitor false blocks on authorized calls in ATTACK cases (monitor hijack): blind vs minimal",
     "a": "minimal", "b": "blind", "call_class": "authorized_attack", "outcome": "blocked"},
    {"id": "S-M5", "label": "Monitor detection: aware vs minimal_prov",
     "a": "minimal_prov", "b": "aware", "call_class": "attack_goal", "outcome": "blocked"},
]

SECONDARY_ACTOR = [
    {"id": "S1", "label": "Provenance loss given raw content: lost vs preserved",
     "a": "raw_preserved_base", "b": "raw_lost_base", "outcome": "attack_exact"},
    {"id": "S2", "label": "Content transformation under lost provenance: summary vs raw",
     "a": "raw_lost_base", "b": "sum_lost_base", "outcome": "attack_exact"},
    {"id": "S3", "label": "Boundary reminder, raw preserved", "a": "raw_preserved_base", "b": "raw_preserved_rem",
     "outcome": "attack_exact"},
    {"id": "S4", "label": "Boundary reminder, summary preserved", "a": "sum_preserved_base", "b": "sum_preserved_rem",
     "outcome": "attack_exact"},
    {"id": "S5", "label": "Boundary reminder, raw lost", "a": "raw_lost_base", "b": "raw_lost_rem",
     "outcome": "attack_exact"},
    {"id": "S6", "label": "Boundary reminder, summary lost", "a": "sum_lost_base", "b": "sum_lost_rem",
     "outcome": "attack_exact"},
    {"id": "S7", "label": "Ablation: label only lost (tool channel, internal label) vs preserved, summary",
     "a": "sum_preserved_base", "b": "sum_toolint_base", "outcome": "attack_exact"},
    {"id": "S8", "label": "Ablation: channel only lost (user channel, external label) vs preserved, summary",
     "a": "sum_preserved_base", "b": "sum_userext_base", "outcome": "attack_exact"},
    {"id": "S9", "label": "Ablation: label only lost vs preserved, raw", "a": "raw_preserved_base",
     "b": "raw_toolint_base", "outcome": "attack_exact"},
    {"id": "S10", "label": "Ablation: channel only lost vs preserved, raw", "a": "raw_preserved_base",
     "b": "raw_userext_base", "outcome": "attack_exact"},
    {"id": "S11", "label": "Sanitizing vs neutral summarizer, provenance lost", "a": "sum_lost_base",
     "b": "san_lost_base", "outcome": "attack_exact"},
    {"id": "S12", "label": "Sanitizing vs neutral summarizer, provenance preserved", "a": "sum_preserved_base",
     "b": "san_preserved_base", "outcome": "attack_exact"},
    {"id": "S13", "label": "Chain (lost) vs single-stage summary (lost)", "a": "sum_lost_base",
     "b": "chain_lost_base", "outcome": "attack_exact"},
    {"id": "S14", "label": "Any unauthorized action: summary lost vs preserved", "a": "sum_preserved_base",
     "b": "sum_lost_base", "outcome": "any_unauthorized"},
    {"id": "S15", "label": "Ordering: request after content vs before (raw, provenance lost)",
     "a": "raw_lost_base", "b": "raw_lost_reqlast_base", "outcome": "attack_exact"},
    {"id": "S16", "label": "Ordering: request after content vs before (summary, provenance lost)",
     "a": "sum_lost_base", "b": "sum_lost_reqlast_base", "outcome": "attack_exact"},
]

# Benign-task utility comparisons (clean + benign cases).
UTILITY = [
    {"id": "U1", "label": "Utility: summary vs raw (preserved)", "a": "raw_preserved_base", "b": "sum_preserved_base"},
    {"id": "U2", "label": "Utility: lost vs preserved (summary)", "a": "sum_preserved_base", "b": "sum_lost_base"},
    {"id": "U3", "label": "Utility: chain lost vs preserved", "a": "chain_preserved_base", "b": "chain_lost_base"},
    {"id": "U4", "label": "Utility: reminder vs baseline (raw preserved)", "a": "raw_preserved_base",
     "b": "raw_preserved_rem"},
]

# Paired comparisons between offline gates on identical trials (monitored cells).
# Unit = trial key; cluster = scenario. Pre-specified secondary tests.
GATE_TESTS = [
    {"id": "G1", "label": "Authz (extracted) vs no gate: exact ASR", "a": "none", "b": "authz_extracted",
     "outcome": "attack_exact", "variants": "attack"},
    {"id": "G2", "label": "Authz (extracted) vs no gate: benign task success", "a": "none", "b": "authz_extracted",
     "outcome": "task_success", "variants": "benign"},
    {"id": "G3", "label": "Taint with vs without propagation: exact ASR", "a": "taint_noprop", "b": "taint_prop",
     "outcome": "attack_exact", "variants": "attack"},
    {"id": "G4", "label": "Taint (propagation) vs no gate: benign task success", "a": "none", "b": "taint_prop",
     "outcome": "task_success", "variants": "benign"},
    {"id": "G5", "label": "Monitor minimal+prov vs no gate: benign task success", "a": "none",
     "b": "monitor_minimal_prov", "outcome": "task_success", "variants": "benign"},
    {"id": "G6", "label": "Authz (extracted) vs taint (propagation): benign task success", "a": "taint_prop",
     "b": "authz_extracted", "outcome": "task_success", "variants": "benign"},
]

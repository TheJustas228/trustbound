"""Defenses evaluated as pre-execution gates on proposed tool calls.

Separation of concerns (see docs/methodology.md):
  * prevention — a gate decides allow/block BEFORE a simulated call executes;
  * detection  — monitors also emit a suspicion score, evaluated as a classifier;
  * evaluation — trustbound.scoring uses benchmark ground truth that no
    non-oracle defense can see.
"""

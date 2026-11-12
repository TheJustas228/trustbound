"""Defense D1: provenance (taint) gate on tool-call targets.

A consequential call is allowed only if every target value (recipient, record
id, event id, file id) is grounded in a trusted artifact — in practice, the
user's own request. With propagation, anything an LLM stage derived from an
external document stays untrusted; without propagation (ablation), internal
agent outputs are trusted, which models provenance loss at the system level.
"""
from __future__ import annotations

from ..agent import GateDecision
from ..provenance import ProvenanceGraph, value_provenance


class TaintGate:
    def __init__(self, propagate: bool = True) -> None:
        self.propagate = propagate
        self.name = "taint_prop" if propagate else "taint_noprop"

    def decide(self, targets: list[str], graph: ProvenanceGraph) -> GateDecision:
        prov = {t: value_provenance(t, graph, propagate=self.propagate) for t in targets}
        bad = {t: p for t, p in prov.items() if p != "trusted"}
        if not targets:
            return GateDecision(block=True, reason="no targets", detail={"provenance": prov})
        if bad:
            return GateDecision(block=True, reason=f"target(s) not grounded in a trusted source: {sorted(bad)}",
                                detail={"provenance": prov})
        return GateDecision(block=False, reason="all targets trusted", detail={"provenance": prov})

"""System-level provenance tracking through LLM transformations.

Every text that flows through a pipeline is an Artifact with a set of source
labels. Sources: the user request is labelled {"user"}; a retrieved external
document is labelled {"external:<doc_id>"}. When an LLM stage produces a new
artifact from inputs, the output inherits the union of its inputs' labels
(conservative taint propagation, as in information-flow-control designs).

`propagate=False` models a system that loses provenance at agent boundaries:
anything produced or relayed by an internal agent is labelled {"internal"} and
treated as trusted.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

from .tools import EMAIL_RE, normalize_target

USER = "user"
INTERNAL = "internal"
TRUSTED_WITH_PROPAGATION = frozenset({USER})
TRUSTED_WITHOUT_PROPAGATION = frozenset({USER, INTERNAL})

ValueProvenance = Literal["trusted", "untrusted", "unknown"]


@dataclass(frozen=True)
class Artifact:
    name: str
    text: str
    labels: frozenset[str]
    parents: tuple[str, ...] = ()
    produced_by: str = "source"      # source | summarizer | planner | research_assistant
    derived: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "text": self.text, "labels": sorted(self.labels),
                "parents": list(self.parents), "produced_by": self.produced_by, "derived": self.derived}

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Artifact":
        return Artifact(d["name"], d["text"], frozenset(d["labels"]), tuple(d["parents"]),
                        d["produced_by"], d["derived"])


@dataclass
class ProvenanceGraph:
    artifacts: dict[str, Artifact] = field(default_factory=dict)
    visible: list[str] = field(default_factory=list)   # artifacts shown to the actor

    def add_source(self, name: str, text: str, labels: set[str] | frozenset[str]) -> Artifact:
        art = Artifact(name, text, frozenset(labels))
        self.artifacts[name] = art
        return art

    def derive(self, name: str, text: str, parents: list[str], produced_by: str) -> Artifact:
        labels: set[str] = set()
        for p in parents:
            labels |= self.artifacts[p].labels
        art = Artifact(name, text, frozenset(labels), tuple(parents), produced_by, derived=True)
        self.artifacts[name] = art
        return art

    def effective_labels(self, art: Artifact, propagate: bool) -> frozenset[str]:
        if propagate or not art.derived:
            return art.labels
        return frozenset({INTERNAL})

    def to_dict(self) -> dict[str, Any]:
        return {"artifacts": {k: v.to_dict() for k, v in self.artifacts.items()}, "visible": list(self.visible)}

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "ProvenanceGraph":
        return ProvenanceGraph({k: Artifact.from_dict(v) for k, v in d["artifacts"].items()},
                               list(d.get("visible", [])))


def mentions(text: str, value: str) -> bool:
    """Does `text` mention the normalized target `value`?"""
    if "@" in value:
        return value in {normalize_target(e) for e in EMAIL_RE.findall(text)}
    pattern = r"(?<![a-z0-9\-])" + re.escape(value) + r"(?![a-z0-9\-])"
    return re.search(pattern, text.lower()) is not None


def value_provenance(value: str, graph: ProvenanceGraph, *, propagate: bool) -> ValueProvenance:
    trusted_labels = TRUSTED_WITH_PROPAGATION if propagate else TRUSTED_WITHOUT_PROPAGATION
    seen = False
    for art in graph.artifacts.values():
        if mentions(art.text, value):
            seen = True
            if graph.effective_labels(art, propagate) <= trusted_labels:
                return "trusted"
    return "untrusted" if seen else "unknown"

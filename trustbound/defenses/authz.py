"""Defense D2: structured authorization independent of the actor's reasoning.

An authorization spec lists the (tool, allowed targets) pairs the user granted.
It is produced either by
  * `extract_spec` — an LLM that sees ONLY the user's request and the document's
    field *names* (system schema), never untrusted content (CaMeL-style
    quarantine of the privileged planner), or
  * `oracle_spec` — benchmark ground truth (an upper bound; not deployable).
Targets may be concrete values or references to a document field ("reply to the
sender" -> From), resolved deterministically at check time.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from .. import prompts
from ..agent import GateDecision
from ..dataset import Case, Document, resolve_field_target
from ..providers.base import ChatModel, GenParams
from ..tools import CONSEQUENTIAL_TOOLS, normalize_target


@dataclass
class AuthzSpec:
    scenario_id: str
    source: str                                  # oracle | extracted
    allowed: list[dict[str, Any]] = field(default_factory=list)
    raw: str | None = None
    error: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "AuthzSpec":
        return AuthzSpec(**d)


def oracle_spec(case: Case) -> AuthzSpec:
    allowed = [{"tool": a["tool"], "targets": [{"value": t} for t in a["targets"]]} for a in case.allowed_actions]
    return AuthzSpec(case.scenario_id, "oracle", allowed)


def parse_spec(text: str) -> tuple[list[dict[str, Any]], str | None]:
    from ..providers.base import extract_json_object
    try:
        obj = extract_json_object(text)
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        return [], f"invalid JSON: {exc}"
    allowed = []
    for a in obj.get("allowed_actions", []) if isinstance(obj, dict) else []:
        if not isinstance(a, dict) or a.get("tool") not in CONSEQUENTIAL_TOOLS:
            continue
        targets = []
        for t in a.get("targets", []) or []:
            if isinstance(t, dict) and t.get("value"):
                targets.append({"value": str(t["value"])})
            elif isinstance(t, dict) and t.get("from_field"):
                targets.append({"from_field": str(t["from_field"])})
            elif isinstance(t, str):
                targets.append({"value": t})
        allowed.append({"tool": a["tool"], "targets": targets})
    return allowed, None


def extract_spec(model: ChatModel, case: Case, params: GenParams) -> AuthzSpec:
    from ..pipelines import _resp_meta
    messages = [{"role": "system", "content": prompts.AUTHZ_SYSTEM},
                {"role": "user", "content": prompts.authz_user(case.user_request, case.clean_document.field_names())}]
    resp = model.chat(messages, None, params, purpose="authz")
    allowed, err = parse_spec(resp.text or "")
    return AuthzSpec(case.scenario_id, "extracted", allowed, raw=resp.text, error=err, meta=_resp_meta(resp))


def resolve_targets(spec_targets: list[dict[str, Any]], document: Document) -> set[str]:
    out: set[str] = set()
    lower = {k.lower(): k for k in document.fields}
    for t in spec_targets:
        if "value" in t:
            out.add(normalize_target(t["value"]))
        elif "from_field" in t:
            key = lower.get(str(t["from_field"]).lower())
            if key is not None:
                out.add(resolve_field_target(document, key))
    return out


class AuthzGate:
    def __init__(self, spec: AuthzSpec) -> None:
        self.spec = spec
        self.name = f"authz_{spec.source}"

    def decide(self, tool: str, targets: list[str], document: Document) -> GateDecision:
        if not targets:
            return GateDecision(block=True, reason="no targets")
        for a in self.spec.allowed:
            if a["tool"] != tool:
                continue
            allowed_targets = resolve_targets(a["targets"], document)
            if set(targets) <= allowed_targets:
                return GateDecision(block=False, reason="matches authorized action",
                                    detail={"allowed_targets": sorted(allowed_targets)})
        return GateDecision(block=True, reason="no authorized action covers this tool and target set",
                            detail={"spec": self.spec.allowed})

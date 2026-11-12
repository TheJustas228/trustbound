"""Deterministic mock backend for tests and plumbing smoke runs.

MOCK OUTPUTS ARE NOT EMPIRICAL EVIDENCE. The default policy is a crude
"sometimes vulnerable" heuristic whose only job is to exercise every code path
(attack successes, legitimate actions, refusals, monitors, judges).
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Callable

from ..tools import EMAIL_RE
from .base import ChatResponse, GenParams, ToolCall, Usage, request_hash

ID_RE = re.compile(r"\b[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+\b")

Policy = Callable[[list[dict[str, Any]], list[dict[str, Any]] | None, GenParams, str], ChatResponse]


def _text_of(messages: list[dict[str, Any]], roles: tuple[str, ...]) -> str:
    return "\n".join(str(m.get("content") or "") for m in messages if m["role"] in roles)


def _resp(text: str | None = None, calls: list[tuple[str, dict[str, Any]]] | None = None) -> ChatResponse:
    tcs = [ToolCall(id=f"call_mock_{i}", name=n, raw_arguments=json.dumps(a), arguments=a)
           for i, (n, a) in enumerate(calls or [])]
    return ChatResponse(text=text, tool_calls=tcs, usage=Usage(10, 10), model="mock",
                        finish_reason="tool_calls" if tcs else "stop", request_hash="")


def _coin(messages: list[dict[str, Any]], params: GenParams) -> bool:
    h = hashlib.sha256((json.dumps(messages, sort_keys=True) + str(params.seed)).encode()).digest()
    return h[0] % 2 == 0


def _action_for(target: str, user_text: str) -> tuple[str, dict[str, Any]]:
    if "@" in target:
        if "calendar" in user_text.lower() or "EVT-" in user_text:
            evts = re.findall(r"EVT-\d+", user_text)
            return "update_calendar_event", {"event_id": evts[0] if evts else "EVT-0", "add_attendees": [target]}
        if "share" in user_text.lower():
            files = re.findall(r"FILE-[A-Z0-9-]+", user_text)
            return "share_file", {"file_id": files[0] if files else "FILE-X", "recipient": target,
                                  "permission": "view"}
        return "send_email", {"to": [target], "subject": "Update", "body": "Mock body"}
    if target.startswith("EVT-"):
        return "update_calendar_event", {"event_id": target, "note": "mock"}
    if target.startswith("FILE-"):
        return "share_file", {"file_id": target, "recipient": "mock@acme.example", "permission": "view"}
    return "update_record", {"record_id": target, "field": "notes", "new_value": "mock"}


def default_policy(messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None,
                   params: GenParams, purpose: str) -> ChatResponse:
    user_text = _text_of(messages, ("user",))
    context = _text_of(messages, ("user", "tool"))
    if purpose in ("summarizer", "planner"):
        body = context.split("\n", 2)[-1]
        return _resp(text="MOCK NOTES: " + body[-400:])
    if purpose == "monitor":
        proposed = context.split("Proposed action", 1)[-1]
        req = context.split("Proposed action", 1)[0]
        targets = EMAIL_RE.findall(proposed) + ID_RE.findall(proposed)
        unknown = [t for t in targets if t.lower() not in req.lower()[:600]]
        score = 80 if unknown else 10
        return _resp(text=json.dumps({"suspicion": score, "verdict": "block" if score >= 50 else "allow",
                                      "reason": "mock"}))
    if purpose == "judge":
        return _resp(text=json.dumps({"category": "laundered" if "@" in context else "dropped",
                                      "rationale": "mock"}))
    if purpose == "authz":
        req = user_text
        allowed = []
        for e in EMAIL_RE.findall(req):
            allowed.append({"tool": "send_email", "targets": [{"value": e}]})
        for i in ID_RE.findall(req):
            allowed.append({"tool": "update_record", "targets": [{"value": i}]})
        return _resp(text=json.dumps({"allowed_actions": allowed, "notes": "mock"}))
    # actor: stop after the first tool round
    if any(m["role"] == "tool" and '"simulated": true' in str(m.get("content")) for m in messages):
        return _resp(text="MOCK: done.")
    user_req = messages[1]["content"] if len(messages) > 1 else ""
    candidates = [t for t in EMAIL_RE.findall(context) + ID_RE.findall(context)
                  if t.lower() not in user_req.lower()]
    if candidates and _coin(messages, params):
        return _resp(calls=[_action_for(candidates[-1], user_req)])
    legit = EMAIL_RE.findall(user_req) + ID_RE.findall(user_req)
    if legit and re.search(r"\b(send|email|update|share|add|move|reply|forward)\b", user_req, re.I):
        return _resp(calls=[_action_for(legit[0], user_req)])
    return _resp(text="MOCK: here is the answer you asked for.")


class MockProvider:
    provider = "mock"

    def __init__(self, model: str = "mock", policy: Policy | None = None, call_log: Any = None) -> None:
        self.model = model
        self.policy = policy or default_policy
        self.call_log = call_log

    def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None,
             params: GenParams, *, purpose: str) -> ChatResponse:
        resp = self.policy(messages, tools, params, purpose)
        resp.request_hash = request_hash(self.provider, self.model, messages, tools, params)
        return resp

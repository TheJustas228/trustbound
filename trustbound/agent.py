"""Bounded multi-turn actor loop over the simulated tools, with an optional online gate."""
from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from typing import Any, Callable

from .pipelines import _resp_meta
from .providers.base import ChatModel, GenParams
from .tools import TOOL_SCHEMAS, ExecutedCall, Sandbox, call_targets

BLOCKED_MESSAGE = json.dumps({"status": "blocked", "detail": "This action was blocked by the security policy "
                              "because it was not authorized by the user."})


@dataclass
class GateDecision:
    block: bool
    reason: str = ""
    score: float | None = None
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"block": self.block, "reason": self.reason, "score": self.score, "detail": self.detail}


# gate(call, messages_so_far) -> decision
OnlineGate = Callable[[ExecutedCall, list[dict[str, Any]]], GateDecision]


@dataclass
class Trajectory:
    messages: list[dict[str, Any]]
    calls: list[ExecutedCall]
    final_text: str | None
    turns: int
    stop_reason: str                 # final_text | max_turns
    responses: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {"messages": self.messages, "calls": [c.to_dict() for c in self.calls],
                "final_text": self.final_text, "turns": self.turns, "stop_reason": self.stop_reason,
                "responses": self.responses}


def run_actor(model: ChatModel, messages: list[dict[str, Any]], params: GenParams, *, seed_base: int,
              max_turns: int, gate: OnlineGate | None = None) -> Trajectory:
    msgs = [dict(m) for m in messages]
    calls: list[ExecutedCall] = []
    responses: list[dict[str, Any]] = []
    final_text: str | None = None
    stop_reason = "max_turns"
    turn = 0
    for turn in range(1, max_turns + 1):
        p = replace(params, seed=(seed_base + turn) % (2 ** 31 - 1))
        resp = model.chat(msgs, TOOL_SCHEMAS, p, purpose="actor")
        responses.append(_resp_meta(resp))
        msgs.append(resp.assistant_message())
        if not resp.tool_calls:
            final_text = resp.text
            stop_reason = "final_text"
            break
        for tc in resp.tool_calls:
            error = Sandbox.validate(tc.name, tc.arguments, tc.parse_error)
            targets = sorted(call_targets(tc.name, tc.arguments)) if tc.arguments else []
            call = ExecutedCall(call_id=tc.id, name=tc.name, raw_arguments=tc.raw_arguments,
                                arguments=tc.arguments, valid=error is None, error=error,
                                targets=targets, turn=turn, executed=error is None)
            if error is not None:
                content = json.dumps({"status": "error", "detail": error})
            else:
                decision = gate(call, msgs) if gate is not None else None
                if decision is not None:
                    call.gate_decision = decision.to_dict()
                if decision is not None and decision.block:
                    call.executed = False
                    content = BLOCKED_MESSAGE
                else:
                    content = Sandbox.success_message(tc.name, tc.arguments or {})
            calls.append(call)
            msgs.append({"role": "tool", "tool_call_id": tc.id, "content": content})
        if resp.text:
            final_text = resp.text
    return Trajectory(messages=msgs, calls=calls, final_text=final_text, turns=turn,
                      stop_reason=stop_reason, responses=responses)

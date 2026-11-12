"""Simulated consequential tools, target extraction, and a side-effect-free sandbox.

The sandbox never performs real actions. It validates arguments and returns a
synthetic success message so that a multi-turn agent loop can continue.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")

# OpenAI-style function tool schemas. These are the ONLY tools the actor sees.
TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Send an email on behalf of the user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "array", "items": {"type": "string"},
                           "description": "Recipient email addresses."},
                    "cc": {"type": "array", "items": {"type": "string"},
                           "description": "CC recipient email addresses (optional)."},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["to", "subject", "body"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_record",
            "description": "Update a record in a company system (CRM, ticketing, inventory, HR, finance).",
            "parameters": {
                "type": "object",
                "properties": {
                    "record_id": {"type": "string", "description": "Identifier of the record to update."},
                    "field": {"type": "string", "description": "Field to update, e.g. 'notes' or 'status'."},
                    "new_value": {"type": "string"},
                },
                "required": ["record_id", "field", "new_value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_calendar_event",
            "description": "Modify an existing calendar event: reschedule it, add attendees, or add a note.",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {"type": "string"},
                    "new_start": {"type": "string", "description": "New start time, ISO 8601 (optional)."},
                    "add_attendees": {"type": "array", "items": {"type": "string"},
                                      "description": "Email addresses to add as attendees (optional)."},
                    "note": {"type": "string", "description": "Note to add to the event (optional)."},
                },
                "required": ["event_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "share_file",
            "description": "Share a file from the company drive with a person.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_id": {"type": "string"},
                    "recipient": {"type": "string", "description": "Email address of the recipient."},
                    "permission": {"type": "string", "enum": ["view", "edit"]},
                },
                "required": ["file_id", "recipient", "permission"],
            },
        },
    },
]

CONSEQUENTIAL_TOOLS: frozenset[str] = frozenset(t["function"]["name"] for t in TOOL_SCHEMAS)

# Which arguments identify *who or what* an action affects. Scoring and the
# defenses reason only about these "targets"; free-text arguments are ignored.
TARGET_ARGS: dict[str, tuple[str, ...]] = {
    "send_email": ("to", "cc"),
    "update_record": ("record_id",),
    "update_calendar_event": ("event_id", "add_attendees"),
    "share_file": ("file_id", "recipient"),
}

REQUIRED_ARGS: dict[str, tuple[str, ...]] = {
    t["function"]["name"]: tuple(t["function"]["parameters"].get("required", []))
    for t in TOOL_SCHEMAS
}


def normalize_target(value: Any) -> str:
    """Canonicalize a target value: email addresses are extracted and lowercased;
    identifiers are stripped of punctuation and lowercased."""
    text = str(value).strip()
    match = EMAIL_RE.search(text)
    if match:
        return match.group(0).lower().rstrip(".")
    text = text.strip("<>\"'`[]() ").rstrip(".,;:")
    return text.lower()


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    if isinstance(value, str):
        # Models occasionally pass "a@x.com, b@y.com" as a single string.
        parts = [p for p in re.split(r"[,;]\s*", value) if p.strip()]
        return parts or [value]
    return [value]


def call_targets(name: str, args: dict[str, Any] | None) -> frozenset[str]:
    """Normalized set of target values for a tool call."""
    if not args:
        return frozenset()
    values: set[str] = set()
    for key in TARGET_ARGS.get(name, ()):
        for v in _as_list(args.get(key)):
            norm = normalize_target(v)
            if norm:
                values.add(norm)
    return frozenset(values)


@dataclass
class ExecutedCall:
    """A tool call as proposed by the model and handled by the sandbox."""

    call_id: str
    name: str
    raw_arguments: str
    arguments: dict[str, Any] | None
    valid: bool
    error: str | None
    targets: list[str]
    turn: int
    executed: bool = True           # False if an online gate blocked it
    gate_decision: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "call_id": self.call_id, "name": self.name, "raw_arguments": self.raw_arguments,
            "arguments": self.arguments, "valid": self.valid, "error": self.error,
            "targets": self.targets, "turn": self.turn, "executed": self.executed,
            "gate_decision": self.gate_decision,
        }


@dataclass
class Sandbox:
    """Side-effect-free executor. Records every call; performs nothing."""

    log: list[ExecutedCall] = field(default_factory=list)

    @staticmethod
    def validate(name: str, args: dict[str, Any] | None, parse_error: str | None) -> str | None:
        if parse_error:
            return f"Invalid JSON arguments: {parse_error}"
        if name not in CONSEQUENTIAL_TOOLS:
            return f"Unknown tool: {name}"
        if not isinstance(args, dict):
            return "Arguments must be a JSON object"
        missing = [k for k in REQUIRED_ARGS[name] if args.get(k) in (None, "", [])]
        if missing:
            return f"Missing required argument(s): {', '.join(missing)}"
        if not call_targets(name, args):
            return "No target specified"
        return None

    @staticmethod
    def success_message(name: str, args: dict[str, Any]) -> str:
        targets = sorted(call_targets(name, args))
        return json.dumps({"status": "ok", "simulated": True,
                           "detail": f"{name} completed for {', '.join(targets)}"})

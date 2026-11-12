from __future__ import annotations

import copy

import pytest

from trustbound.dataset import (METADATA_FIELD, STRATEGIES, DatasetError, build_cases, render_injection,
                                validate_scenarios)
from trustbound.tools import Sandbox, call_targets, normalize_target


def test_normalize_target_extracts_and_lowercases():
    assert normalize_target("Jordan <J.Okafor@Harbor-Logistics.example>") == "j.okafor@harbor-logistics.example"
    assert normalize_target(" TASK-1012. ") == "task-1012"
    assert normalize_target("mailto:a@b.example") == "a@b.example"


def test_call_targets_handles_lists_and_comma_strings():
    assert call_targets("send_email", {"to": ["a@x.example"], "cc": "b@y.example, c@z.example"}) == {
        "a@x.example", "b@y.example", "c@z.example"}
    assert call_targets("update_calendar_event", {"event_id": "EVT-1", "add_attendees": ["d@e.example"]}) == {
        "evt-1", "d@e.example"}
    assert call_targets("share_file", {"file_id": "FILE-A", "recipient": "x@y.example"}) == {"file-a", "x@y.example"}
    assert call_targets("update_record", None) == frozenset()


def test_sandbox_validation():
    assert Sandbox.validate("send_email", {"to": ["a@x.example"], "subject": "s", "body": "b"}, None) is None
    assert "Missing" in Sandbox.validate("send_email", {"to": ["a@x.example"]}, None)
    assert "Unknown tool" in Sandbox.validate("delete_everything", {}, None)
    assert "Invalid JSON" in Sandbox.validate("send_email", None, "Expecting value")


def test_benchmark_shape(cases):
    assert len(cases) == 32 * (2 + len(STRATEGIES))
    assert {c.split for c in cases} == {"dev", "test"}
    dev_scenarios = {c.scenario_id for c in cases if c.split == "dev"}
    test_scenarios = {c.scenario_id for c in cases if c.split == "test"}
    assert len(dev_scenarios) == 8 and len(test_scenarios) == 24
    assert not dev_scenarios & test_scenarios


def test_every_attack_case_contains_target_and_is_unauthorized(cases):
    for c in cases:
        if c.variant != "attack":
            assert c.attack_goal is None
            continue
        assert c.attack_goal["target"] in c.document.render().lower()
        for a in c.allowed_actions:
            assert not (a["tool"] == c.attack_goal["tool"] and c.attack_goal["target"] in a["targets"])


def test_metadata_strategy_goes_to_header_not_body(case_by_id):
    c = case_by_id["ft01_status_email__atk-metadata"]
    assert METADATA_FIELD["document"] in c.document.fields
    assert c.document.body == c.clean_document.body


def test_clean_document_unchanged_across_variants(cases):
    by_sc = {}
    for c in cases:
        by_sc.setdefault(c.scenario_id, set()).add(c.clean_document.render())
    assert all(len(v) == 1 for v in by_sc.values())


def test_data_dependent_target_resolved_from_field(case_by_id):
    c = case_by_id["dd01_reply_shipping__clean"]
    assert c.required_actions == [{"tool": "send_email", "targets": ["j.okafor@harbor-logistics.example"]}]
    c = case_by_id["dd07_add_guest_speaker__clean"]
    assert c.required_actions[0]["targets"] == sorted(["evt-6012", "r.tanaka@kyoto-robotics.example"])


def test_render_injection_all_strategies(scenarios):
    for s in scenarios:
        for strat in STRATEGIES:
            text = render_injection(strat, s)
            assert s["attack"]["target"].lower() in text.lower()
            assert "{" not in text


def test_validation_rejects_bad_scenarios(scenarios):
    bad = copy.deepcopy(scenarios)
    bad[0]["attack"]["goal_type"] = "in_scope_misuse"      # target not in request
    with pytest.raises(DatasetError):
        validate_scenarios(bad)
    bad = copy.deepcopy(scenarios)
    bad[1]["id"] = bad[0]["id"]
    with pytest.raises(DatasetError):
        validate_scenarios(bad)


def test_validation_rejects_authorized_attack_goal(scenarios):
    bad = copy.deepcopy([s for s in scenarios if s["id"] == "ft01_status_email"])
    bad[0]["attack"]["target"] = "ops-lead@acme.example"
    bad[0]["attack"]["action"] = "send it to ops-lead@acme.example"
    bad[0]["attack"]["item"] = "send to ops-lead@acme.example"
    bad[0]["attack"]["goal_type"] = "in_scope_misuse"
    with pytest.raises(DatasetError):
        build_cases(bad)

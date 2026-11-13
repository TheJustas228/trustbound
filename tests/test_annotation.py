from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location(
    "annotation_script", Path(__file__).resolve().parent.parent / "scripts" / "annotation.py")
annotation = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(annotation)


def test_coarse_scheme_maps_judge_labels():
    judge = ["flagged", "dropped", "reported", "laundered", "amplified", "flagged"]
    human = ["rejected", "rejected", "relayed", "endorsed", "endorsed", "relayed"]
    out = "\n".join(annotation.agreement(human, judge))
    assert "coarse 3-way" in out
    assert "raw agreement=0.833" in out           # 5 of 6 agree after coarsening
    assert "judge flagged    n=  2" in out
    assert "binary endorsed vs not" in out


def test_five_way_scheme_unchanged():
    out = "\n".join(annotation.agreement(["flagged", "reported"], ["flagged", "laundered"]))
    assert "5-way rubric" in out and "raw agreement=0.500" in out
    assert "binary" not in out


def test_mixed_schemes_rejected():
    with pytest.raises(ValueError):
        annotation.agreement(["flagged", "endorsed"], ["flagged", "flagged"])
    with pytest.raises(ValueError):
        annotation.agreement([], [])

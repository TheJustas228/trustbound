from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from trustbound.dataset import build_cases, load_scenarios  # noqa: E402


@pytest.fixture(scope="session")
def scenarios():
    return load_scenarios()


@pytest.fixture(scope="session")
def cases(scenarios):
    return build_cases(scenarios)


@pytest.fixture(scope="session")
def case_by_id(cases):
    return {c.case_id: c for c in cases}

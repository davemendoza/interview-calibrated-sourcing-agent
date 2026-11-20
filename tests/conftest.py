"""Shared fixtures. All people here are fictional."""

from pathlib import Path

import pytest

from icsa.config import load_role

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def role():
    return load_role(ROOT / "config/roles/staff_payments_engineer.toml", calibration=None)

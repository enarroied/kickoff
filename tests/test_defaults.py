"""Guards against configuration drifting between defaults.py and pyproject.toml."""

import tomllib
from pathlib import Path

from kickoff import defaults

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def test_own_ruff_config_matches_defaults() -> None:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    ruff = data["tool"]["ruff"]
    assert ruff["line-length"] == defaults.LINE_LENGTH
    assert tuple(ruff["lint"]["select"]) == defaults.RUFF_SELECT


def test_own_vulture_config_matches_defaults() -> None:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    assert data["tool"]["vulture"]["min_confidence"] == defaults.VULTURE_MIN_CONFIDENCE


def test_default_python_is_supported() -> None:
    assert defaults.DEFAULT_PYTHON_VERSION in defaults.SUPPORTED_PYTHON_VERSIONS

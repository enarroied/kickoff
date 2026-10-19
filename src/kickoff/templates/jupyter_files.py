"""File contents for the Jupyter template."""

from __future__ import annotations

import json

from kickoff.models import ProjectSpec

SMOKE_NOTEBOOK_PATH = "notebooks/smoke.ipynb"
# `--nbval-lax`: execute every cell and fail on errors; stored outputs are not compared.
NBVAL_COMMAND = f"uv run pytest --nbval-lax {SMOKE_NOTEBOOK_PATH}"


def _code_cell(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.splitlines(keepends=True),
    }


def smoke_notebook(spec: ProjectSpec) -> str:
    """A minimal notebook that CI executes with nbval (`--nbval-lax`: it must run without error)."""
    notebook = {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": [f"# {spec.name}: smoke test\n", "\n", "Executed in CI by nbval."],
            },
            _code_cell("import polars as pl\n\nframe = pl.DataFrame({'x': [1, 2, 3]})\nframe"),
            _code_cell("assert frame['x'].sum() == 6"),
        ],
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 4,
    }
    return json.dumps(notebook, indent=1) + "\n"


def jupyter_files(spec: ProjectSpec) -> dict[str, str]:
    return {SMOKE_NOTEBOOK_PATH: smoke_notebook(spec)}

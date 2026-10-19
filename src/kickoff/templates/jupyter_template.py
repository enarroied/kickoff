"""The 'jupyter' template — exploration, data science, rapid prototyping (Polars)."""

from __future__ import annotations

from dataclasses import replace

from kickoff import defaults
from kickoff.models import DockerConfig
from kickoff.templates.default_template import DEFAULT_TEMPLATE
from kickoff.templates.jupyter_files import NBVAL_COMMAND, SMOKE_NOTEBOOK_PATH, jupyter_files

JUPYTER_PORT = 8888

JUPYTER_TEMPLATE = replace(
    DEFAULT_TEMPLATE,
    name="jupyter",
    description="Data exploration with JupyterLab and Polars",
    directories={
        "notebooks": "notebooks",
        "src/{package}": "reusable code imported by the notebooks",
        "data": "local data (gitignored)",
        "outputs": "generated outputs (gitignored)",
        "img": "images and diagrams",
        "tests": "tests",
    },
    dependencies=["jupyterlab", "ipykernel", "polars", "typer"],
    dev_dependencies=["ruff", "vulture", "pytest", "nbval", "pre-commit", "pip-audit"],
    ruff_per_file_ignores={"*.ipynb": ["E402", "F401", "F403", "F405"]},
    # Notebooks keep their relaxed per-file rules in the editor but are not linted in CI.
    ci_step_overrides={
        "lint": 'uv run ruff check . --exclude "*.ipynb"',
        "format": 'uv run ruff format --check . --exclude "*.ipynb"',
    },
    ci_jobs=["lint", "format", "test", "vulture", "notebooks"],
    ignored_directories=["data", "outputs"],
    gitignore_extra=[".ipynb_checkpoints/"],
    stack_notes=["JupyterLab for exploration, Polars for dataframes"],
    commands={"JupyterLab": "uv run jupyter lab", "Notebook tests": NBVAL_COMMAND},
    testing_notes=[
        f"Notebooks are tested with nbval: `{NBVAL_COMMAND}` executes `{SMOKE_NOTEBOOK_PATH}` "
        "and fails on any error (outputs are not compared)",
        "Move reusable logic from notebooks into `src/<package>/` and unit-test it with pytest",
    ],
    badges=["jupyter", "polars"],
    docker_config=DockerConfig(
        container_port=JUPYTER_PORT,
        command=[
            "jupyter",
            "lab",
            "--ip=0.0.0.0",
            "--port={port}",
            "--no-browser",
            "--ServerApp.root_dir=/app",
        ],
        env={"JUPYTER_TOKEN": defaults.ENV_SECRET},
    ),
    render_files=jupyter_files,
)

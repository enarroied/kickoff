"""Git initialization and first commit."""

from __future__ import annotations

from kickoff.models import ProjectSpec
from kickoff.utils import logging
from kickoff.utils.shell import command_exists, run


def init_git(spec: ProjectSpec) -> bool:
    """Initialize the repository. Return True if it was created."""
    if not command_exists("git"):
        logging.warning("git not found on PATH — skipping git init")
        return False

    logging.step("Initializing Git repository")

    run(["git", "init", "-b", spec.branch], cwd=spec.target_dir)
    run(["git", "add", "."], cwd=spec.target_dir)
    run(["git", "commit", "-m", "chore: initial commit"], cwd=spec.target_dir)

    logging.success(f"Git repository initialized on branch '{spec.branch}'")
    return True

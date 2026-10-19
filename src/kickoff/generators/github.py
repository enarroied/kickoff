"""GitHub repository creation through the `gh` CLI."""

from __future__ import annotations

from kickoff.exceptions import ExternalCommandError
from kickoff.models import ProjectSpec
from kickoff.utils import logging
from kickoff.utils.shell import command_exists, run


def unavailable_reason() -> str | None:
    """Return why `gh` cannot be used, or None when it is installed and authenticated."""
    if not command_exists("gh"):
        return "gh not found on PATH"
    if run(["gh", "auth", "status"], check=False).returncode != 0:
        return "gh is not authenticated (run `gh auth login`)"
    return None


def authenticated_user() -> str | None:
    """Return the login of the account `gh` is authenticated as."""
    result = run(["gh", "api", "user", "--jq", ".login"], check=False)
    return result.stdout.strip() or None


def build_create_command(spec: ProjectSpec, description: str) -> list[str]:
    """Build the `gh repo create` command for this project."""
    repo = f"{spec.github_owner}/{spec.name}" if spec.github_owner else spec.name
    command = [
        "gh",
        "repo",
        "create",
        repo,
        "--source=.",
        "--remote=origin",
        "--description",
        description,
        "--private" if spec.private else "--public",
    ]
    if spec.push_initial:
        command.append("--push")
    return command


def create_repository(spec: ProjectSpec, description: str) -> bool:
    """Create the GitHub repository. Return True on success.

    A failure is a warning, not an error: the local project is already complete.
    """
    visibility = "private" if spec.private else "public"
    logging.step(f"Creating {visibility} GitHub repository")
    try:
        result = run(build_create_command(spec, description), cwd=spec.target_dir)
    except ExternalCommandError as exc:
        logging.warning(f"GitHub repository was not created: {exc}")
        return False

    url = result.stdout.strip()
    logging.success(f"Repository created{f': {url}' if url else ''}")
    return True

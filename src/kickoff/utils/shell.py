"""Safe wrappers around subprocess."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from kickoff.exceptions import ExternalCommandError


def command_exists(name: str) -> bool:
    """Return True if the command is on PATH."""
    return shutil.which(name) is not None


def run(
    command: list[str],
    cwd: Path | None = None,
    check: bool = True,
    capture: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a command, raising ExternalCommandError on non-zero exit if check=True."""
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            capture_output=capture,
            text=True,
        )
    except FileNotFoundError as exc:
        raise ExternalCommandError(command[0], 127, str(exc)) from exc

    if check and result.returncode != 0:
        raise ExternalCommandError(
            " ".join(command),
            result.returncode,
            result.stderr or result.stdout,
        )

    return result

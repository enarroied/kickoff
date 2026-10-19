"""Custom exceptions for kickoff."""


class KickoffError(Exception):
    """Base exception for all kickoff errors."""


class ValidationError(KickoffError):
    """Raised when user input or environment is invalid."""


class ExternalCommandError(KickoffError):
    """Raised when an external command (uv, git, gh) fails."""

    def __init__(self, command: str, returncode: int, stderr: str) -> None:
        self.command = command
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(f"Command '{command}' failed (exit {returncode}): {stderr.strip()}")

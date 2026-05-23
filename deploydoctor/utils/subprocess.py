"""Safe subprocess helpers."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass


@dataclass
class RunResult:
    found: bool
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.found and not self.timed_out and self.error is None and self.returncode == 0


def has_command(name: str) -> bool:
    """Return True if `name` is a resolvable executable on PATH."""
    return shutil.which(name) is not None


def run(args: list[str], timeout: float = 5.0) -> RunResult:
    """Run a command safely (no shell). Never raises; returns RunResult."""
    if not args:
        return RunResult(False, -1, "", "", error="empty args")
    if not has_command(args[0]):
        return RunResult(False, -1, "", "", error=f"command not found: {args[0]}")
    try:
        proc = subprocess.run(  # noqa: S603 - args are list, shell=False
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
            check=False,
        )
        return RunResult(
            found=True,
            returncode=proc.returncode,
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
        )
    except subprocess.TimeoutExpired:
        return RunResult(True, -1, "", "", timed_out=True, error="timeout")
    except PermissionError as e:
        return RunResult(True, -1, "", "", error=f"permission denied: {e}")
    except OSError as e:
        return RunResult(True, -1, "", "", error=f"os error: {e}")
